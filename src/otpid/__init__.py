"""Official Python SDK for the OTP.ID V3 API."""

from __future__ import annotations

from otpid.errors import (
    ERR_ALREADY_USED,
    ERR_CHANNEL_UNAVAILABLE,
    ERR_DESTINATION_RATE_LIMITED,
    ERR_DUPLICATE_EXTERNAL_ID,
    ERR_INSUFFICIENT_BALANCE,
    ERR_INTERNAL,
    ERR_INVALID_CHANNEL,
    ERR_INVALID_NUMBER,
    ERR_INVALID_RESPONSE,
    ERR_IP_NOT_ALLOWED,
    ERR_OTP_EXPIRED,
    ERR_OTP_NOT_FOUND,
    ERR_RATE_LIMITED,
    ERR_TOO_MANY_ATTEMPTS,
    ERR_UNAUTHORIZED,
    ERR_VALIDATION,
    APIError,
    InvalidSignatureError,
    OtpIdError,
    StaleTimestampError,
    UnexpectedEventError,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ERR_UNAUTHORIZED",
    "ERR_VALIDATION",
    "ERR_INVALID_CHANNEL",
    "ERR_INVALID_NUMBER",
    "ERR_INSUFFICIENT_BALANCE",
    "ERR_OTP_NOT_FOUND",
    "ERR_DUPLICATE_EXTERNAL_ID",
    "ERR_OTP_EXPIRED",
    "ERR_TOO_MANY_ATTEMPTS",
    "ERR_ALREADY_USED",
    "ERR_RATE_LIMITED",
    "ERR_DESTINATION_RATE_LIMITED",
    "ERR_CHANNEL_UNAVAILABLE",
    "ERR_IP_NOT_ALLOWED",
    "ERR_INTERNAL",
    "ERR_INVALID_RESPONSE",
    "OtpIdError",
    "APIError",
    "InvalidSignatureError",
    "StaleTimestampError",
    "UnexpectedEventError",
]
