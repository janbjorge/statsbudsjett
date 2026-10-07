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
