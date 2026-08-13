"""Error codes and exception hierarchy for the OTP.ID V3 API.

Error codes are kept in sync with the server contract. See the Go SDK
(`otp-id-go/errors.go`) for the reference implementation this module ports.
"""

from __future__ import annotations

ERR_UNAUTHORIZED = "UNAUTHORIZED"
ERR_VALIDATION = "VALIDATION_ERROR"
ERR_INVALID_CHANNEL = "INVALID_CHANNEL"
ERR_INVALID_NUMBER = "INVALID_NUMBER"
ERR_INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
ERR_OTP_NOT_FOUND = "OTP_NOT_FOUND"
ERR_DUPLICATE_EXTERNAL_ID = "DUPLICATE_EXTERNAL_ID"
ERR_OTP_EXPIRED = "OTP_EXPIRED"
ERR_TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS"
ERR_ALREADY_USED = "ALREADY_USED"
ERR_RATE_LIMITED = "RATE_LIMITED"
ERR_DESTINATION_RATE_LIMITED = "DESTINATION_RATE_LIMITED"
ERR_CHANNEL_UNAVAILABLE = "CHANNEL_UNAVAILABLE"
ERR_IP_NOT_ALLOWED = "IP_NOT_ALLOWED"
ERR_INTERNAL = "INTERNAL_ERROR"

# ERR_INVALID_RESPONSE is produced by the SDK itself (never by the server)
# when a response body cannot be decoded as a V3 JSON envelope.
ERR_INVALID_RESPONSE = "INVALID_RESPONSE"


class OtpIdError(Exception):
    """Base class for all exceptions raised by this SDK."""


class APIError(OtpIdError):
    """Raised for any non-success API response.

    Match on `.code` (one of the `ERR_*` constants) to branch on the
    specific error condition.
    """

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details

    def __str__(self) -> str:
        return f"{self.code}: {self.message} (http {self.http_status})"


class InvalidSignatureError(OtpIdError):
    """Raised when a webhook signature does not match the expected HMAC."""


class StaleTimestampError(OtpIdError):
    """Raised when a webhook timestamp is outside the allowed tolerance."""


class UnexpectedEventError(OtpIdError):
    """Raised when a webhook payload's `event` field is not `otp.verified`."""
