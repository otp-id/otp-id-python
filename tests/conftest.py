"""Shared pytest fixtures for otpid tests.

`fake_server` ports the `httptest.NewServer` pattern used throughout
`otp-id-go/client_test.go`: each test gets an isolated
`http.server.ThreadingHTTPServer` bound to an OS-assigned port (port 0),
running in a background thread, with a queue of canned (status, body)
responses to return and a log of every request it received.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, NamedTuple

import pytest


class RecordedRequest(NamedTuple):
    method: str
    path: str
    # email.message.Message (http.client.HTTPMessage): .get() is
    # case-insensitive, matching real HTTP header semantics.
    headers: Any
    body: bytes


class FakeServer:
    """A canned-response HTTP server for Client transport tests."""

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self._responses: deque[tuple[int, bytes]] = deque()
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self))
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        port = self._httpd.server_address[1]
        return f"http://127.0.0.1:{port}"

    def enqueue(self, status: int, body: bytes | str | dict[str, Any]) -> None:
        """Queue the next response this server will return, in order."""
        if isinstance(body, dict):
            encoded = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            encoded = body.encode("utf-8")
        else:
            encoded = body
        with self._lock:
            self._responses.append((status, encoded))

    def _next_response(self) -> tuple[int, bytes]:
        with self._lock:
            if self._responses:
                return self._responses.popleft()
        return 200, b'{"success":true,"data":{},"error":null}'

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


def _make_handler(server: FakeServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            server.requests.append(
                RecordedRequest(
                    method=self.command, path=self.path, headers=self.headers, body=body
                )
            )
            status, resp_body = server._next_response()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)

        def do_GET(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            self._handle()

        def log_message(self, format: str, *args: Any) -> None:
            pass  # silence default request logging to stderr

    return Handler


@pytest.fixture
def fake_server():
    server = FakeServer()
    try:
        yield server
    finally:
        server.close()
