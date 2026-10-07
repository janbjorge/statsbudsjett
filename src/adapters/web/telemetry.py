"""Tracing and metrics with Logfire. Sends only when LOGFIRE_TOKEN is set, so local runs and tests stay offline.

Query strings and endpoint arguments are recorded as they are: they hold no name or account.
The client address is blanked before the span leaves the process, because the site has no use for it.
"""

import os
from typing import Any

import logfire
from fastapi import FastAPI
from opentelemetry.trace import Span

REDACTED = "x"

# OpenTelemetry ASGI attributes that hold the visitor's address, old and new semantic conventions
_CLIENT_ATTRS = ("http.client_ip", "client.address", "net.peer.ip", "net.sock.peer.addr")


def _drop_client_address(span: Span, _scope: dict[str, Any]) -> None:
    """Runs when the request span starts, before anything is exported."""
    if not span.is_recording():
        return
    attrs: dict[str, Any] = getattr(span, "attributes", None) or {}
    for key in _CLIENT_ATTRS:
        if key in attrs:
            span.set_attribute(key, REDACTED)


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
    logfire.instrument_fastapi(app, server_request_hook=_drop_client_address, excluded_urls="/helse,/static/.*")
    if on_fly:
        logfire.instrument_system_metrics()
