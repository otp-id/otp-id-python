"""Transport core for the OTP.ID V3 API client.

Ports the request/response handling of ``otp-id-go/client.go``: build an
authenticated HTTP request via ``urllib.request``, decode the V3
``{success, data, error}`` envelope, and raise ``APIError`` for both
API-reported failures and malformed responses. See ``client_test.go`` for
the behavior this module mirrors branch-for-branch.

The six public V3 endpoint methods (``request_otp``, ``send_otp``, ...) are
added on top of ``Client`` in a later module; this file only owns the
transport core (``__init__`` + ``_do_request``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from otpid.errors import ERR_INVALID_RESPONSE, APIError

# VERSION is the SDK version, sent in the User-Agent header.
VERSION = "0.1.0"

_DEFAULT_BASE_URL = "https://api.otp.id"
_DEFAULT_TIMEOUT = 30.0
_MAX_BODY_BYTES = 1_048_576  # 1 MiB guard against abnormal responses
_BODY_SNIPPET_MAX_CHARS = 200


class Client:
    """An OTP.ID V3 API client."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        key = api_key.strip()
        if not key:
            raise ValueError("otpid: api key is empty")
        self._api_key = key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = opener if opener is not None else urllib.request.build_opener()

    def _do_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        expect_data: bool = True,
    ) -> dict[str, Any]:
        """Perform a single HTTP call (no retries) and decode the V3 envelope.

        Returns the decoded ``data`` object of a successful envelope.
        Raises ``APIError`` for:

        - a non-success envelope (``error`` is surfaced as-is);
        - a response body that cannot be decoded as the V3 envelope
          (``ERR_INVALID_RESPONSE``, message = a ~200 char body snippet);
        - a successful envelope whose ``data`` is null/missing when
          ``expect_data`` is True (``ERR_INVALID_RESPONSE``).

        A plain ``URLError`` (network failure, no HTTP response at all) is
        intentionally not caught -- it propagates to the caller unchanged.
        ``HTTPError`` (raised by urllib for any HTTP status >= 400) IS
        caught here because its body still carries a V3 envelope that must
        be decoded like any other response.
        """
        data_bytes: bytes | None = None
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": f"otp-id-python/{VERSION}",
        }
        if body is not None:
            data_bytes = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self._base_url + path, data=data_bytes, headers=headers, method=method
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                raw = response.read(_MAX_BODY_BYTES + 1)
                status = response.status
        except urllib.error.HTTPError as http_error:
            with http_error:
                raw = http_error.read(_MAX_BODY_BYTES + 1)
                status = http_error.code

        return _decode_envelope(raw, status, expect_data)


def _decode_envelope(raw: bytes, status: int, expect_data: bool) -> dict[str, Any]:
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise _invalid_response(raw, status) from None

    if not isinstance(envelope, dict):
        raise _invalid_response(raw, status)

    if not envelope.get("success"):
        error = envelope.get("error")
        if not isinstance(error, dict):
            raise _invalid_response(raw, status)
        raise APIError(
            code=error.get("code", ""),
            message=error.get("message", ""),
            http_status=status,
            details=error.get("details"),
        )

    data = envelope.get("data")
    if expect_data:
        if data is None:
            raise _invalid_response(raw, status)
        return data
    return data if isinstance(data, dict) else {}


def _invalid_response(raw: bytes, status: int) -> APIError:
    return APIError(code=ERR_INVALID_RESPONSE, message=_body_snippet(raw), http_status=status)


def _body_snippet(raw: bytes) -> str:
    """First ~200 characters of a raw body for diagnostics."""
    text = raw.decode("utf-8", errors="replace").strip()
    if len(text) > _BODY_SNIPPET_MAX_CHARS:
        return text[:_BODY_SNIPPET_MAX_CHARS]
    return text
