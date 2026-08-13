"""Result types and channel constants for the OTP.ID V3 API.

Field names mirror the wire format (snake_case) 1:1 with the Go SDK
(`otp-id-go/order.go`, `verify.go`, `status.go`, `account.go`, `topup.go`,
`webhook.go`, `channels.go`) so no field-name mapping is needed anywhere in
this codebase or in the docs shared across SDKs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Channel = Literal["whatsapp", "sms", "voice", "email", "misscall", "whatsapp_inbound"]

CHANNEL_WHATSAPP: Channel = "whatsapp"
CHANNEL_SMS: Channel = "sms"
CHANNEL_VOICE: Channel = "voice"
CHANNEL_EMAIL: Channel = "email"
CHANNEL_MISSCALL: Channel = "misscall"
CHANNEL_WHATSAPP_INBOUND: Channel = "whatsapp_inbound"


@dataclass(frozen=True)
class Verification:
    """Flat superset of the per-channel ``verification`` response block.

    Which fields are set depends on the channel: whatsapp_inbound fills
    wa_number/message/wa_link/expires_at; misscall fills prefix (and
    otp_length on order responses). All other channels have no
    verification block at all -- the parent result's ``verification``
    attribute is ``None`` in that case, and this class is never built.
    """

    wa_number: str | None = None
    message: str | None = None
    wa_link: str | None = None
    expires_at: str | None = None
    prefix: str | None = None
    otp_length: int | None = None

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "Verification":
        return cls(
            wa_number=d.get("wa_number"),
            message=d.get("message"),
            wa_link=d.get("wa_link"),
            expires_at=d.get("expires_at"),
            prefix=d.get("prefix"),
            otp_length=d.get("otp_length"),
        )


def _verification_from_dict(d: dict[str, Any]) -> Verification | None:
    block = d.get("verification")
    return Verification._from_dict(block) if block else None


@dataclass(frozen=True)
class OrderResult:
    """Success payload of ``POST /v3/request`` and ``POST /v3/send``."""

    otp_id: str
    status: str  # pending | sent | success | failed
    channel: Channel
    number: str
    price: int
    # last_balance is the remaining credit after this transaction. It stays
    # unchanged when delivery failed (status "failed") or on an idempotency
    # replay.
    last_balance: int
    # expires_at is "YYYY-MM-DD HH:MM:SS" in WIB (UTC+7). Kept as a string;
    # the SDK does not parse server datetimes.
    expires_at: str
    verification: Verification | None = None

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "OrderResult":
        return cls(
            otp_id=d["otp_id"],
            status=d["status"],
            channel=d["channel"],
            number=d["number"],
            price=d["price"],
            last_balance=d["last_balance"],
            expires_at=d["expires_at"],
            verification=_verification_from_dict(d),
        )


@dataclass(frozen=True)
class VerifyResult:
    """Success payload of ``POST /v3/verify``."""

    otp_id: str
    verified: bool
    # "" when verified is True, "mismatch" when the code was wrong. A
    # mismatch is HTTP 200 and therefore NOT an error from verify_otp().
    # Expired / locked / already-used transactions come back as APIError
    # (OTP_EXPIRED, TOO_MANY_ATTEMPTS, ALREADY_USED) instead.
    reason: str

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "VerifyResult":
        return cls(otp_id=d["otp_id"], verified=d["verified"], reason=d["reason"])


@dataclass(frozen=True)
class StatusResult:
    """Success payload of ``GET /v3/otp/{otp_id}``."""

    otp_id: str
    status: str  # sent | success | failed | pending | verified
    channel: Channel
    number: str
    attempts: int
    expires_at: str
    verified_at: str  # "" until verified
    price: int
    # Only present for not-yet-verified misscall transactions (prefix
    # field), so polling clients can build their UI.
    verification: Verification | None = None

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "StatusResult":
        return cls(
            otp_id=d["otp_id"],
            status=d["status"],
            channel=d["channel"],
            number=d["number"],
            attempts=d["attempts"],
            expires_at=d["expires_at"],
            verified_at=d["verified_at"],
            price=d["price"],
            verification=_verification_from_dict(d),
        )


@dataclass(frozen=True)
class AccountResult:
    """Success payload of ``GET /v3/account``. Never contains credentials."""

    merchant_id: str
    name: str
    brand_name: str
    brand_email: str
    email: str
    saldo: int  # current credit balance

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "AccountResult":
        return cls(
            merchant_id=d["merchant_id"],
            name=d["name"],
            brand_name=d["brand_name"],
            brand_email=d["brand_email"],
            email=d["email"],
            saldo=d["saldo"],
        )


@dataclass(frozen=True)
class TopupResult:
    """Success payload of ``POST /v3/topups``.

    payment_url is a signed OTP.ID payment page that opens without a
    dashboard login.
    """

    topup_id: str
    payment_url: str
    payment_hash: str
    amount: int
    payment_total: int  # amount + admin fee; display as-is
    payment_method_id: int
    payment_method: str
    payment_type: str
    payment_expired_at: str
    status: str

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "TopupResult":
        return cls(
            topup_id=d["topup_id"],
            payment_url=d["payment_url"],
            payment_hash=d["payment_hash"],
            amount=d["amount"],
            payment_total=d["payment_total"],
            payment_method_id=d["payment_method_id"],
            payment_method=d["payment_method"],
            payment_type=d["payment_type"],
            payment_expired_at=d["payment_expired_at"],
            status=d["status"],
        )


@dataclass(frozen=True)
class VerifiedEvent:
    """Payload of the ``otp.verified`` webhook."""

    event: str  # always "otp.verified"
    otp_id: str
    external_id: str  # "" when the merchant sent no external_id
    channel: Channel
    number: str
    verified_at: str  # "YYYY-MM-DD HH:MM:SS" WIB

    @classmethod
    def _from_dict(cls, d: dict[str, Any]) -> "VerifiedEvent":
        return cls(
            event=d["event"],
            otp_id=d["otp_id"],
            external_id=d["external_id"],
            channel=d["channel"],
            number=d["number"],
            verified_at=d["verified_at"],
        )
