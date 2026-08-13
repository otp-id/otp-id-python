"""Tests for otpid.client: Client construction and the _do_request transport core.

Ports the intent of otp-id-go/client_test.go against a local
http.server.ThreadingHTTPServer fixture (see conftest.py's `fake_server`)
instead of Go's httptest.NewServer.
"""

from __future__ import annotations

import pytest

from otpid.client import VERSION, Client
from otpid.errors import ERR_DUPLICATE_EXTERNAL_ID, ERR_INVALID_RESPONSE, APIError


def test_new_client_strips_api_key_and_has_defaults() -> None:
    client = Client("  test-key  ")
    assert client._api_key == "test-key"
    assert client._base_url == "https://api.otp.id"
    assert client._timeout == 30.0


def test_base_url_rstrips_trailing_slash() -> None:
    client = Client("k", base_url="https://example.com/")
    assert client._base_url == "https://example.com"


def test_empty_api_key_raises_value_error_without_network(fake_server) -> None:
    with pytest.raises(ValueError):
        Client("   ", base_url=fake_server.url)
    assert fake_server.requests == []


def test_do_request_sends_headers(fake_server) -> None:
    fake_server.enqueue(200, {"success": True, "data": {}, "error": None})
    client = Client("test-key", base_url=fake_server.url)

    client._do_request("POST", "/v3/request", {"a": "b"})

    assert len(fake_server.requests) == 1
    req = fake_server.requests[0]
    assert req.headers.get("Authorization") == "Bearer test-key"
    assert req.headers.get("User-Agent") == f"otp-id-python/{VERSION}"
    assert req.headers.get("Content-Type") == "application/json"


def test_do_request_get_has_no_content_type(fake_server) -> None:
    fake_server.enqueue(200, {"success": True, "data": {}, "error": None})
    client = Client("test-key", base_url=fake_server.url)

    client._do_request("GET", "/v3/account", None)

    req = fake_server.requests[0]
    assert req.headers.get("Content-Type") is None


def test_do_request_api_error_with_details(fake_server) -> None:
    fake_server.enqueue(
        409,
        {
            "success": False,
            "data": None,
            "error": {
                "code": ERR_DUPLICATE_EXTERNAL_ID,
                "message": "external_id already used",
                "details": {"existing_otp_id": "OTP20260807ABCD000001"},
            },
        },
    )
    client = Client("test-key", base_url=fake_server.url)

    with pytest.raises(APIError) as exc_info:
        client._do_request("POST", "/v3/request", {}, expect_data=False)

    err = exc_info.value
    assert err.code == ERR_DUPLICATE_EXTERNAL_ID
    assert err.http_status == 409
    assert err.details == {"existing_otp_id": "OTP20260807ABCD000001"}


def test_do_request_non_json_response_yields_invalid_response_snippet(fake_server) -> None:
    fake_server.enqueue(502, "<html>502 Bad Gateway</html>")
    client = Client("test-key", base_url=fake_server.url)

    with pytest.raises(APIError) as exc_info:
        client._do_request("GET", "/v3/account", None, expect_data=False)

    err = exc_info.value
    assert err.code == ERR_INVALID_RESPONSE
    assert err.http_status == 502
    assert "502 Bad Gateway" in err.message


def test_do_request_fail_without_error_body_is_invalid_response(fake_server) -> None:
    fake_server.enqueue(500, {"success": False, "data": None, "error": None})
    client = Client("test-key", base_url=fake_server.url)

    with pytest.raises(APIError) as exc_info:
        client._do_request("GET", "/v3/account", None, expect_data=False)

    assert exc_info.value.code == ERR_INVALID_RESPONSE


def test_do_request_success_null_data_is_invalid_response(fake_server) -> None:
    fake_server.enqueue(200, {"success": True, "data": None, "error": None})
    client = Client("test-key", base_url=fake_server.url)

    with pytest.raises(APIError) as exc_info:
        client._do_request("GET", "/v3/account", None, expect_data=True)

    assert exc_info.value.code == ERR_INVALID_RESPONSE
