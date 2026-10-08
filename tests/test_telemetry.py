"""Logfire records what was asked, never who asked."""

import json

import pytest
from fastapi.testclient import TestClient
from logfire.testing import CaptureLogfire

from adapters.web.main import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["/?lonn=654321&meg=barnefamilie", "/meg?lonn=654321", "/api/meg?lonn=654321", "/api/kvittering?skatt=654321"])
def test_spans_keep_the_query_and_drop_the_client_address(capfire: CaptureLogfire, path: str) -> None:
    client.get(path, headers={"HX-Request": "true"})
    spans = capfire.exporter.exported_spans_as_dict()
    root = next(s for s in spans if "http.route" in s["attributes"])
    assert "654321" in json.dumps(root["attributes"], default=str)
    assert "testclient" not in json.dumps([s["attributes"].get(k) for s in spans for k in ("net.peer.ip", "client.address")])


def test_health_check_is_not_traced(capfire: CaptureLogfire) -> None:
    client.get("/helse")
    assert capfire.exporter.exported_spans_as_dict() == []



def _root(capfire: CaptureLogfire) -> dict[str, object]:
    return next(s for s in capfire.exporter.exported_spans_as_dict() if "http.route" in s["attributes"])["attributes"]


def test_spans_record_where_the_visit_came_from(capfire: CaptureLogfire) -> None:
    headers = {"Referer": "https://example.org/some/thread/", "Sec-Fetch-Site": "cross-site"}
    client.get("/?utm_source=a&utm_medium=b&xclid=c", headers=headers)
    attrs = _root(capfire)
    assert attrs["visit.referrer"] == "example.org"
    assert "some/thread" not in json.dumps(attrs, default=str)
    assert attrs["visit.fetch_site"] == "cross-site"
    assert attrs["visit.utm_source"] == "a"
    assert attrs["visit.utm_medium"] == "b"
    assert attrs["visit.click_id"] == "xclid"


def test_links_within_the_site_are_not_a_referrer(capfire: CaptureLogfire) -> None:
    client.get("/meg?lonn=500000", headers={"Referer": "http://testserver/", "Sec-Fetch-Site": "same-origin"})
    attrs = _root(capfire)
    assert "visit.referrer" not in attrs
    assert attrs["visit.fetch_site"] == "same-origin"
