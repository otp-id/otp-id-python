"""Tests for otpid.webhook: HMAC signature verification and event parsing.

Ports otp-id-go/webhook_test.go, including its known-good test vector
(identical secret/timestamp/body/signature) so the two SDKs cannot
silently drift from the server's signing scheme.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from otpid import webhook as webhook_module
from otpid.errors import (
    ERR_INVALID_RESPONSE,
    APIError,
    InvalidSignatureError,
    StaleTimestampError,
    UnexpectedEventError,
)
from otpid.webhook import (
    WEBHOOK_TOLERANCE_SECONDS,
    parse_verified_event,
    verify_webhook_signature,
)

# Known-good vector, independently precomputed (identical to the Go SDK's):
#   HMAC-SHA256("whsec_testsecret", "1765700000" + "." + WEBHOOK_BODY)
WEBHOOK_SECRET = "whsec_testsecret"
WEBHOOK_TIMESTAMP = "1765700000"
WEBHOOK_SIGNATURE = "41c831b6192fa304f0564bd03bb147587119a97a579bb7a0fc12ae9b2c8ed4ca"
WEBHOOK_BODY = (
    b'{"event":"otp.verified","otp_id":"OTP20260807ABCD000001",'
    b'"external_id":"order-8821","channel":"whatsapp","number":"6281234567890",'
    b'"verified_at":"2026-08-07 10:01:30"}'
)


def _reference_signature(secret: str, timestamp: str, body: bytes) -> str:
    """Inline reference HMAC, independent of the module under test."""
    mac = hmac.new(secret.encode("utf-8"), (timestamp + ".").encode("utf-8"), hashlib.sha256)
    mac.update(body)
    return mac.hexdigest()


def test_verify_webhook_signature_vector() -> None:
    assert verify_webhook_signature(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_BODY, WEBHOOK_SIGNATURE)


def test_verify_webhook_signature_matches_reference_hmac() -> None:
    # Cross-check against an inline reference implementation so the SDK
    # cannot silently drift from the server's signing scheme.
    ref = _reference_signature(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_BODY)
    assert verify_webhook_signature(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_BODY, ref)


@pytest.mark.parametrize(
    ("secret", "timestamp", "signature", "body"),
    [
        pytest.param("other-secret", WEBHOOK_TIMESTAMP, WEBHOOK_SIGNATURE, WEBHOOK_BODY, id="wrong secret"),
        pytest.param(WEBHOOK_SECRET, "1765700001", WEBHOOK_SIGNATURE, WEBHOOK_BODY, id="wrong timestamp"),
        pytest.param(
            WEBHOOK_SECRET,
            WEBHOOK_TIMESTAMP,
            WEBHOOK_SIGNATURE,
            b'{"event":"otp.verified","otp_id":"HACKED"}',
            id="tampered body",
        ),
        pytest.param(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, "deadbeef", WEBHOOK_BODY, id="wrong signature"),
    ],
)
def test_verify_webhook_signature_rejects(secret: str, timestamp: str, signature: str, body: bytes) -> None:
    assert not verify_webhook_signature(secret, timestamp, body, signature)


def test_parse_verified_event_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000 + 30)

    ev = parse_verified_event(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_SIGNATURE, WEBHOOK_BODY)

    assert ev.event == "otp.verified"
    assert ev.otp_id == "OTP20260807ABCD000001"
    assert ev.external_id == "order-8821"
    assert ev.channel == "whatsapp"
    assert ev.number == "6281234567890"
    assert ev.verified_at == "2026-08-07 10:01:30"


def test_parse_verified_event_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000)

    with pytest.raises(InvalidSignatureError):
        parse_verified_event("other-secret", WEBHOOK_TIMESTAMP, WEBHOOK_SIGNATURE, WEBHOOK_BODY)


def test_parse_verified_event_stale_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    # 6 minutes after the signed timestamp: outside the 5-minute tolerance.
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000 + 6 * 60)

    with pytest.raises(StaleTimestampError):
        parse_verified_event(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_SIGNATURE, WEBHOOK_BODY)


def test_parse_verified_event_future_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    # Clock skew guard also applies in the other direction.
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000 - 6 * 60)

    with pytest.raises(StaleTimestampError):
        parse_verified_event(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_SIGNATURE, WEBHOOK_BODY)


def test_parse_verified_event_non_numeric_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000)
    ts = "not-a-number"
    sig = _reference_signature(WEBHOOK_SECRET, ts, WEBHOOK_BODY)

    with pytest.raises(StaleTimestampError):
        parse_verified_event(WEBHOOK_SECRET, ts, sig, WEBHOOK_BODY)


def test_parse_verified_event_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000)
    body = b"{not-json"
    sig = _reference_signature(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, body)

    with pytest.raises(APIError) as exc_info:
        parse_verified_event(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, sig, body)

    assert exc_info.value.code == ERR_INVALID_RESPONSE
    assert exc_info.value.http_status == 0


def test_parse_verified_event_unexpected_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000)
    body = json.dumps({"event": "otp.expired", "otp_id": "OTP20260807ABCD000001"}).encode("utf-8")
    sig = _reference_signature(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, body)

    with pytest.raises(UnexpectedEventError) as exc_info:
        parse_verified_event(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, sig, body)

    assert "otp.expired" in str(exc_info.value)


def test_parse_verified_event_custom_tolerance(monkeypatch: pytest.MonkeyPatch) -> None:
    # 90 seconds after the signed timestamp: within the default 300s
    # tolerance but outside a custom 60s tolerance.
    monkeypatch.setattr(webhook_module, "_now", lambda: 1765700000 + 90)

    ev = parse_verified_event(WEBHOOK_SECRET, WEBHOOK_TIMESTAMP, WEBHOOK_SIGNATURE, WEBHOOK_BODY)
    assert ev.event == "otp.verified"

    with pytest.raises(StaleTimestampError):
        parse_verified_event(
            WEBHOOK_SECRET,
            WEBHOOK_TIMESTAMP,
            WEBHOOK_SIGNATURE,
            WEBHOOK_BODY,
            tolerance_seconds=60,
        )


def test_webhook_tolerance_seconds_default() -> None:
    assert WEBHOOK_TOLERANCE_SECONDS == 300
