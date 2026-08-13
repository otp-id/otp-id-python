"""Transport core and the six V3 endpoint methods for the OTP.ID API client.

Ports the request/response handling of ``otp-id-go/client.go`` (build an
authenticated HTTP request via ``urllib.request``, decode the V3
``{success, data, error}`` envelope, and raise ``APIError`` for both
API-reported failures and malformed responses) plus the six public
endpoint methods from ``order.go``, ``verify.go``, ``status.go``,
``account.go``, and ``topup.go``. See the corresponding ``*_test.go``
files for the behavior this module mirrors branch-for-branch.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from otpid.errors import ERR_INVALID_RESPONSE, APIError
from otpid.types import (
    AccountResult,
    Channel,
    OrderResult,
    StatusResult,
    TopupResult,
    VerifyResult,
)

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
        - a successful envelope whose ``data`` is null/missing, or is not a
          JSON object (e.g. a list, string, or number), when
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

    def request_otp(
        self,
        *,
        channel: Channel,
        destination: str | None = None,
        brand: str | None = None,
        otp_length: int | None = None,
        ttl: int | None = None,
        external_id: str | None = None,
    ) -> OrderResult:
        """Create an OTP transaction with a server-generated code.

        ``POST /v3/request``. The code itself is never returned.
        """
        body = _order_params_body(
            channel=channel,
            destination=destination,
            brand=brand,
            otp_length=otp_length,
            ttl=ttl,
            external_id=external_id,
        )
        data = self._do_request("POST", "/v3/request", body)
        return OrderResult._from_dict(data)

    def send_otp(
        self,
        otp: str,
        *,
        channel: Channel,
        destination: str | None = None,
        brand: str | None = None,
        ttl: int | None = None,
        external_id: str | None = None,
    ) -> OrderResult:
        """Deliver a client-generated code.

        ``POST /v3/send``. The server rejects channel "voice" and
        "whatsapp_inbound" for this endpoint; use "whatsapp", "sms", or
        "email".
        """
        body = _order_params_body(
            channel=channel,
            destination=destination,
            brand=brand,
            otp_length=None,
            ttl=ttl,
            external_id=external_id,
        )
        body["otp"] = otp
        data = self._do_request("POST", "/v3/send", body)
        return OrderResult._from_dict(data)

    def verify_otp(self, otp_id: str, otp: str) -> VerifyResult:
        """Check a user-submitted code against a transaction.

        ``POST /v3/verify``. Do not call this for whatsapp_inbound
        transactions. Raises ``ValueError`` (no network call) if
        ``otp_id`` is empty or whitespace-only.
        """
        stripped_otp_id = otp_id.strip()
        if not stripped_otp_id:
            raise ValueError("otpid: otp_id is empty")
        body = {"otp_id": stripped_otp_id, "otp": otp}
        data = self._do_request("POST", "/v3/verify", body)
        return VerifyResult._from_dict(data)

    def otp_status(self, otp_id: str) -> StatusResult:
        """Fetch the current state of a transaction.

        ``GET /v3/otp/{otp_id}`` (path-escaped). Raises ``ValueError`` (no
        network call) if ``otp_id`` is empty or whitespace-only.
        """
        stripped_otp_id = otp_id.strip()
        if not stripped_otp_id:
            raise ValueError("otpid: otp_id is empty")
        path = "/v3/otp/" + urllib.parse.quote(stripped_otp_id, safe="")
        data = self._do_request("GET", path, None)
        return StatusResult._from_dict(data)

    def account(self) -> AccountResult:
        """Fetch the merchant profile and credit balance for the API key in use.

        ``GET /v3/account``.
        """
        data = self._do_request("GET", "/v3/account", None)
        return AccountResult._from_dict(data)

    def create_topup(self, amount: int, payment_method_id: int) -> TopupResult:
        """Create a credit top-up invoice.

        ``POST /v3/topups``. Call this from server-side code only -- never
        expose your API key to browsers or mobile apps.
        """
        body = {"amount": amount, "payment_method_id": payment_method_id}
        data = self._do_request("POST", "/v3/topups", body)
        return TopupResult._from_dict(data)


def _order_params_body(
    *,
    channel: Channel,
    destination: str | None,
    brand: str | None,
    otp_length: int | None,
    ttl: int | None,
    external_id: str | None,
) -> dict[str, Any]:
    """Build the OrderParams request body, dropping unset (None) fields.

    Mirrors the Go SDK's `json:",omitempty"` tags on `OrderParams`: a field
    left at its Python default (None) is omitted from the JSON body
    entirely rather than sent as null.
    """
    body: dict[str, Any] = {"channel": channel}
    if destination is not None:
        body["destination"] = destination
    if brand is not None:
        body["brand"] = brand
    if otp_length is not None:
        body["otp_length"] = otp_length
    if ttl is not None:
        body["ttl"] = ttl
    if external_id is not None:
        body["external_id"] = external_id
    return body


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
        if data is None or not isinstance(data, dict):
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
