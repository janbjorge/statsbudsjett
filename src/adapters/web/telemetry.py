"""Tracing and metrics with Logfire. Sends only when LOGFIRE_TOKEN is set, so local runs and tests stay offline.

Query strings and endpoint arguments are recorded as they are: they hold no name or account.
The client address is blanked before the span leaves the process, because the site has no use for it.
Where a visit came from is kept as `visit.*` attributes: the referring site's host (never its path), how the
browser got here, and the campaign tags and click id name in the link.
"""

import os
from typing import Any
from urllib.parse import parse_qs, urlsplit

import logfire
from fastapi import FastAPI
from opentelemetry.trace import Span

REDACTED = "x"

# OpenTelemetry ASGI attributes that hold the visitor's address, old and new semantic conventions
_CLIENT_ATTRS = ("http.client_ip", "client.address", "net.peer.ip", "net.sock.peer.addr")


def _visit(scope: dict[str, Any]) -> dict[str, str]:
    headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope.get("headers", [])}
    query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
    visit: dict[str, str] = {}
    referrer = urlsplit(headers.get("referer", "")).hostname
    if referrer and referrer != urlsplit(f"//{headers.get('host', '')}").hostname:
        visit["visit.referrer"] = referrer
    # "none" means typed, bookmarked or opened from an app such as a mail client; "cross-site" means a link elsewhere
    if site := headers.get("sec-fetch-site"):
        visit["visit.fetch_site"] = site
    for key, values in query.items():
        if key.startswith("utm_"):
            visit[f"visit.{key}"] = values[0]
    # Ad and social platforms append a click id parameter ending in "clid"; its name says which one, its value nothing
    if click := next((key for key in query if key.endswith("clid")), None):
        visit["visit.click_id"] = click
    return visit


def _on_request(span: Span, scope: dict[str, Any]) -> None:
    """Runs when the request span starts, before anything is exported."""
    if not span.is_recording():
        return
    attrs: dict[str, Any] = getattr(span, "attributes", None) or {}
    for key in _CLIENT_ATTRS:
        if key in attrs:
            span.set_attribute(key, REDACTED)
    span.set_attributes(_visit(scope))


def setup(app: FastAPI) -> None:
    on_fly = "FLY_APP_NAME" in os.environ
    logfire.configure(
        send_to_logfire="if-token-present",
        service_name="statsbudsjett",
        service_version=os.environ.get("GIT_SHA", "dev"),
        environment="production" if on_fly else "local",
        console=False,
        # Public site with no upstream services: ignore trace headers that visitors send
        distributed_tracing=False,
        code_source=logfire.CodeSource(
            repository="https://github.com/janbjorge/statsbudsjett",
            revision=os.environ.get("GIT_SHA", "main"),
        ),
    )
    logfire.instrument_fastapi(app, server_request_hook=_on_request, excluded_urls="/helse,/static/.*")
    if on_fly:
        logfire.instrument_system_metrics()
