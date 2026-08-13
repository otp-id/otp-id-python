"""HMAC-SHA256 signature verification and parsing for the `otp.verified`
webhook.

Ports `otp-id-go/webhook.go`: the signature covers
``timestamp + "." + body``, comparison is constant-time
(``hmac.compare_digest``), and ``parse_verified_event`` validates in a
strict order -- signature, then timestamp freshness (anti-replay), then
JSON decoding, then the event-type guard -- before returning a
``VerifiedEvent``. See ``webhook_test.go`` for the test vector this
module's tests are ported from.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Callable

from otpid.errors import (
    ERR_INVALID_RESPONSE,
    APIError,
    InvalidSignatureError,
    StaleTimestampError,
    UnexpectedEventError,
)
from otpid.types import VerifiedEvent

# WEBHOOK_TOLERANCE_SECONDS is the default maximum accepted clock
# difference between the X-OTPID-Timestamp header and the local clock in
# parse_verified_event.
WEBHOOK_TOLERANCE_SECONDS = 300

# _now is the package clock. It is monkeypatched in tests
# (`otpid.webhook._now`) to freeze time near a known vector timestamp.
_now: Callable[[], float] = time.time


def _compute_signature(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode("utf-8") + b"." + body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_webhook_signature(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    """Report whether ``signature`` matches
    ``hex(HMAC-SHA256(secret, timestamp + "." + body))``.

    The comparison is constant-time. This performs no timestamp freshness
    check -- use ``parse_verified_event`` for the full validation.
    """
    expected = _compute_signature(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)


def parse_verified_event(
    secret: str,
    timestamp: str,
    signature: str,
    body: bytes,
    *,
    tolerance_seconds: int = WEBHOOK_TOLERANCE_SECONDS,
) -> VerifiedEvent:
    """Validate an incoming ``otp.verified`` webhook and return its payload.

    Checks, strictly in order:

    1. the signature (constant-time) -- raises ``InvalidSignatureError``;
    2. the timestamp freshness (``tolerance_seconds`` in either direction,
       anti-replay; a non-numeric timestamp is treated as stale) --
       raises ``StaleTimestampError``;
    3. the body decodes as JSON -- raises ``APIError`` with code
       ``ERR_INVALID_RESPONSE`` and ``http_status=0`` otherwise;
    4. the ``event`` field is ``"otp.verified"`` -- raises
       ``UnexpectedEventError`` (carrying the actual event name)
       otherwise.

    Pass the raw request body and the ``X-OTPID-Timestamp`` /
    ``X-OTPID-Signature`` header values unmodified.
    """
    if not verify_webhook_signature(secret, timestamp, body, signature):
        raise InvalidSignatureError("otpid: invalid webhook signature")

    try:
        ts = int(timestamp.strip())
    except ValueError:
        raise StaleTimestampError("otpid: webhook timestamp outside tolerance") from None

    if abs(_now() - ts) > tolerance_seconds:
        raise StaleTimestampError("otpid: webhook timestamp outside tolerance")

    try:
        decoded = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise APIError(
            code=ERR_INVALID_RESPONSE,
            message=f"otpid: decode webhook payload: {exc}",
            http_status=0,
        ) from exc

    if not isinstance(decoded, dict):
        raise APIError(
            code=ERR_INVALID_RESPONSE,
            message="otpid: decode webhook payload: not a JSON object",
            http_status=0,
        )

    event = decoded.get("event", "")
    if event != "otp.verified":
        raise UnexpectedEventError(f"otpid: unexpected webhook event: {event!r}")

    return VerifiedEvent._from_dict(decoded)
