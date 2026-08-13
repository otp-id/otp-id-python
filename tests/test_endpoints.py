"""Tests for the six V3 endpoint methods on otpid.Client.

Ports the intent of otp-id-go/order_test.go, verify_test.go, status_test.go,
account_test.go, and topup_test.go against the local fake_server fixture
(see conftest.py) instead of Go's httptest.NewServer. Response fixtures are
copied verbatim from the Go tests so the wire contract stays byte-identical
across SDKs.
"""

from __future__ import annotations

import json

import pytest

from otpid.client import Client
from otpid.errors import (
    ERR_INSUFFICIENT_BALANCE,
    ERR_OTP_EXPIRED,
    ERR_UNAUTHORIZED,
    ERR_VALIDATION,
    APIError,
)
from otpid.types import (
    CHANNEL_MISSCALL,
    CHANNEL_SMS,
    CHANNEL_WHATSAPP,
    CHANNEL_WHATSAPP_INBOUND,
)

# Fixtures mirror otp-id-go/order_test.go byte-for-byte.
ORDER_WHATSAPP_FIXTURE = {
    "success": True,
    "data": {
        "otp_id": "OTP20260807ABCD000001",
        "status": "sent",
        "channel": "whatsapp",
        "number": "6281234567890",
        "price": 350,
        "last_balance": 99650,
        "expires_at": "2026-08-07 10:05:00",
    },
    "error": None,
}

ORDER_INBOUND_FIXTURE = {
    "success": True,
    "data": {
        "otp_id": "OTP20260807ABCD000002",
        "status": "pending",
        "channel": "whatsapp_inbound",
        "number": "",
        "price": 350,
        "last_balance": 99300,
        "expires_at": "2026-08-07 10:05:00",
        "verification": {
            "wa_number": "6285212345678",
            "message": (
                "OTPID V-8FK2QN9P — verifikasi MyApp. Kirim pesan ini tanpa "
                "mengubah isinya."
            ),
            "wa_link": "https://wa.me/6285212345678?text=OTPID%20V-8FK2QN9P",
            "expires_at": "2026-08-07 10:05:00",
        },
    },
    "error": None,
}

ORDER_MISSCALL_FIXTURE = {
    "success": True,
    "data": {
        "otp_id": "OTP20260807ABCD000003",
        "status": "sent",
        "channel": "misscall",
        "number": "6281234567890",
        "price": 250,
        "last_balance": 99050,
        "expires_at": "2026-08-07 10:05:00",
        "verification": {"prefix": "628559263", "otp_length": 4},
    },
    "error": None,
}


def _client(fake_server) -> Client:
    return Client("test-key", base_url=fake_server.url)


# --- request_otp -------------------------------------------------------


def test_request_otp_whatsapp(fake_server) -> None:
    fake_server.enqueue(200, ORDER_WHATSAPP_FIXTURE)
    client = _client(fake_server)

    res = client.request_otp(
        channel=CHANNEL_WHATSAPP,
        destination="6281234567890",
        brand="MyApp",
        otp_length=6,
        ttl=300,
        external_id="order-8821",
    )

    req = fake_server.requests[0]
    assert req.path == "/v3/request"
    body = json.loads(req.body)
    assert body == {
        "channel": "whatsapp",
        "destination": "6281234567890",
        "brand": "MyApp",
        "otp_length": 6,
        "ttl": 300,
        "external_id": "order-8821",
    }
    assert "otp" not in body

    assert res.otp_id == "OTP20260807ABCD000001"
    assert res.status == "sent"
    assert res.channel == "whatsapp"
    assert res.price == 350
    assert res.last_balance == 99650
    assert res.verification is None


def test_request_otp_omits_empty_optional_fields(fake_server) -> None:
    fake_server.enqueue(200, ORDER_INBOUND_FIXTURE)
    client = _client(fake_server)

    client.request_otp(channel=CHANNEL_WHATSAPP_INBOUND)

    body = json.loads(fake_server.requests[0].body)
    for key in ("destination", "brand", "otp_length", "ttl", "external_id"):
        assert key not in body


def test_request_otp_inbound_verification(fake_server) -> None:
    fake_server.enqueue(200, ORDER_INBOUND_FIXTURE)
    client = _client(fake_server)

    res = client.request_otp(channel=CHANNEL_WHATSAPP_INBOUND)

    verification = res.verification
    assert verification is not None
    assert verification.wa_number == "6285212345678"
    assert verification.wa_link
    assert verification.message
    assert verification.expires_at == "2026-08-07 10:05:00"


def test_request_otp_misscall_verification(fake_server) -> None:
    fake_server.enqueue(200, ORDER_MISSCALL_FIXTURE)
    client = _client(fake_server)

    res = client.request_otp(channel=CHANNEL_MISSCALL, destination="6281234567890")

    assert res.verification is not None
    assert res.verification.prefix == "628559263"
    assert res.verification.otp_length == 4


def test_request_otp_non_dict_verification_decodes_to_none(fake_server) -> None:
    """A malformed `verification` field (wrong type, here a string) must
    decode to `None` instead of leaking an AttributeError from
    `Verification._from_dict` calling `.get()` on a non-dict."""
    fixture = {
        "success": True,
        "data": {**ORDER_WHATSAPP_FIXTURE["data"], "verification": "oops"},
        "error": None,
    }
    fake_server.enqueue(200, fixture)
    client = _client(fake_server)

    res = client.request_otp(channel=CHANNEL_WHATSAPP, destination="6281234567890")

    assert res.verification is None


def test_request_otp_empty_dict_verification_decodes_to_zero_valued_block(fake_server) -> None:
    """Regression for the truthiness fix: an empty `verification` object
    (`{}`) is a legitimate falsy-but-present dict and must decode to a
    non-None, zero-valued Verification, not None."""
    fixture = {
        "success": True,
        "data": {**ORDER_WHATSAPP_FIXTURE["data"], "verification": {}},
        "error": None,
    }
    fake_server.enqueue(200, fixture)
    client = _client(fake_server)

    res = client.request_otp(channel=CHANNEL_WHATSAPP, destination="6281234567890")

    assert res.verification is not None
    assert res.verification.wa_number is None
    assert res.verification.prefix is None
    assert res.verification.otp_length is None


def test_request_otp_insufficient_balance(fake_server) -> None:
    fake_server.enqueue(
        402,
        {
            "success": False,
            "data": None,
            "error": {"code": ERR_INSUFFICIENT_BALANCE, "message": "balance is not enough"},
        },
    )
    client = _client(fake_server)

    with pytest.raises(APIError) as exc_info:
        client.request_otp(channel=CHANNEL_SMS, destination="6281234567890")

    assert exc_info.value.code == ERR_INSUFFICIENT_BALANCE


# --- send_otp ------------------------------------------------------------


def test_send_otp_body_includes_otp(fake_server) -> None:
    fake_server.enqueue(200, ORDER_WHATSAPP_FIXTURE)
    client = _client(fake_server)

    res = client.send_otp("482913", channel=CHANNEL_WHATSAPP, destination="6281234567890")

    req = fake_server.requests[0]
    assert req.path == "/v3/send"
    body = json.loads(req.body)
    assert body["otp"] == "482913"
    assert body["channel"] == "whatsapp"
    assert body["destination"] == "6281234567890"

    assert res.otp_id == "OTP20260807ABCD000001"
    assert res.status == "sent"
    assert res.last_balance == 99650


# --- verify_otp ------------------------------------------------------------


def test_verify_otp_success(fake_server) -> None:
    fake_server.enqueue(
        200,
        {
            "success": True,
            "data": {"otp_id": "OTP20260807ABCD000001", "verified": True, "reason": ""},
            "error": None,
        },
    )
    client = _client(fake_server)

    res = client.verify_otp("OTP20260807ABCD000001", "482913")

    req = fake_server.requests[0]
    assert req.path == "/v3/verify"
    body = json.loads(req.body)
    assert body == {"otp_id": "OTP20260807ABCD000001", "otp": "482913"}

    assert res.verified is True
    assert res.reason == ""


def test_verify_otp_mismatch_is_not_an_error(fake_server) -> None:
    fake_server.enqueue(
        200,
        {
            "success": True,
            "data": {
                "otp_id": "OTP20260807ABCD000001",
                "verified": False,
                "reason": "mismatch",
            },
            "error": None,
        },
    )
    client = _client(fake_server)

    res = client.verify_otp("OTP20260807ABCD000001", "000000")

    assert res.verified is False
    assert res.reason == "mismatch"


def test_verify_otp_expired_is_api_error(fake_server) -> None:
    fake_server.enqueue(
        422,
        {
            "success": False,
            "data": None,
            "error": {"code": ERR_OTP_EXPIRED, "message": "otp has expired"},
        },
    )
    client = _client(fake_server)

    with pytest.raises(APIError) as exc_info:
        client.verify_otp("OTP20260807ABCD000001", "482913")

    assert exc_info.value.code == ERR_OTP_EXPIRED
    assert exc_info.value.http_status == 422


def test_verify_otp_empty_otp_id_raises_without_network(fake_server) -> None:
    client = _client(fake_server)

    with pytest.raises(ValueError):
        client.verify_otp("  ", "482913")

    assert fake_server.requests == []


# --- otp_status ------------------------------------------------------------


def test_otp_status(fake_server) -> None:
    fake_server.enqueue(
        200,
        {
            "success": True,
            "data": {
                "otp_id": "OTP20260807ABCD000001",
                "status": "sent",
                "channel": "whatsapp",
                "number": "6281234567890",
                "attempts": 0,
                "expires_at": "2026-08-07 10:05:00",
                "verified_at": "",
                "price": 350,
            },
            "error": None,
        },
    )
    client = _client(fake_server)

    res = client.otp_status("OTP20260807ABCD000001")

    req = fake_server.requests[0]
    assert req.method == "GET"
    assert req.path == "/v3/otp/OTP20260807ABCD000001"

    assert res.status == "sent"
    assert res.attempts == 0
    assert res.verified_at == ""
    assert res.price == 350
    assert res.verification is None


def test_otp_status_misscall_prefix(fake_server) -> None:
    fake_server.enqueue(
        200,
        {
            "success": True,
            "data": {
                "otp_id": "OTP20260807ABCD000003",
                "status": "sent",
                "channel": "misscall",
                "number": "6281234567890",
                "attempts": 1,
                "expires_at": "2026-08-07 10:05:00",
                "verified_at": "",
                "price": 250,
                "verification": {"prefix": "628559263"},
            },
            "error": None,
        },
    )
    client = _client(fake_server)

    res = client.otp_status("OTP20260807ABCD000003")

    assert res.verification is not None
    assert res.verification.prefix == "628559263"


def test_otp_status_path_escapes_otp_id(fake_server) -> None:
    fake_server.enqueue(
        404,
        {
            "success": False,
            "data": None,
            "error": {"code": "OTP_NOT_FOUND", "message": "not found"},
        },
    )
    client = _client(fake_server)

    with pytest.raises(APIError):
        client.otp_status("weird/../id")

    assert fake_server.requests[0].path == "/v3/otp/weird%2F..%2Fid"


def test_otp_status_empty_otp_id_raises_without_network(fake_server) -> None:
    client = _client(fake_server)

    with pytest.raises(ValueError):
        client.otp_status("")

    assert fake_server.requests == []


# --- account ------------------------------------------------------------


def test_account(fake_server) -> None:
    fake_server.enqueue(
        200,
        {
            "success": True,
            "data": {
                "merchant_id": "M123",
                "name": "PT Contoh",
                "brand_name": "MyApp",
                "brand_email": "otp@myapp.co.id",
                "email": "owner@myapp.co.id",
                "saldo": 99650,
            },
            "error": None,
        },
    )
    client = _client(fake_server)

    res = client.account()

    req = fake_server.requests[0]
    assert req.method == "GET"
    assert req.path == "/v3/account"

    assert res.merchant_id == "M123"
    assert res.brand_name == "MyApp"
    assert res.saldo == 99650


def test_account_unauthorized(fake_server) -> None:
    fake_server.enqueue(
        401,
        {
            "success": False,
            "data": None,
            "error": {"code": ERR_UNAUTHORIZED, "message": "invalid api key"},
        },
    )
    client = _client(fake_server)

    with pytest.raises(APIError) as exc_info:
        client.account()

    assert exc_info.value.code == ERR_UNAUTHORIZED
    assert exc_info.value.http_status == 401


# --- create_topup ------------------------------------------------------------


def test_create_topup(fake_server) -> None:
    fake_server.enqueue(
        200,
        {
            "success": True,
            "data": {
                "topup_id": "TC20990809Q7M4X2A8BC5D6EFG",
                "payment_url": "https://app.otp.id/topup/TC20990809Q7M4X2A8BC5D6EFG?hash=abc",
                "payment_hash": "abc",
                "amount": 100000,
                "payment_total": 100750,
                "payment_method_id": 3,
                "payment_method": "QRIS",
                "payment_type": "qris",
                "payment_expired_at": "2026-08-14 12:00:00",
                "status": "pending",
            },
            "error": None,
        },
    )
    client = _client(fake_server)

    res = client.create_topup(100000, 3)

    req = fake_server.requests[0]
    assert req.method == "POST"
    assert req.path == "/v3/topups"
    body = json.loads(req.body)
    assert body == {"amount": 100000, "payment_method_id": 3}

    assert res.topup_id == "TC20990809Q7M4X2A8BC5D6EFG"
    assert res.payment_total == 100750
    assert res.payment_method == "QRIS"


def test_create_topup_invalid_amount(fake_server) -> None:
    fake_server.enqueue(
        400,
        {
            "success": False,
            "data": None,
            "error": {
                "code": ERR_VALIDATION,
                "message": "amount must be one of 10000, 100000, 500000, 1000000, 2000000",
            },
        },
    )
    client = _client(fake_server)

    with pytest.raises(APIError) as exc_info:
        client.create_topup(12345, 3)

    assert exc_info.value.code == ERR_VALIDATION


# --- zero-value decoding (Task 2 review follow-up) --------------------------


def test_incomplete_order_payload_decodes_with_zero_values(fake_server) -> None:
    """An order response missing fields must decode to zero values, never KeyError.

    Mirrors Go's json.Unmarshal semantics: an incomplete server object
    leaves untouched struct fields at their zero value instead of raising.
    """
    fake_server.enqueue(200, {"success": True, "data": {}, "error": None})
    client = _client(fake_server)

    res = client.request_otp(channel=CHANNEL_WHATSAPP, destination="6281234567890")

    assert res.otp_id == ""
    assert res.status == ""
    assert res.channel == ""
    assert res.number == ""
    assert res.price == 0
    assert res.last_balance == 0
    assert res.expires_at == ""
    assert res.verification is None
