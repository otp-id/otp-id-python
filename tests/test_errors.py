"""Tests for otpid.errors: error code constants and exception hierarchy.

Ports the intent of otp-id-go/errors_test.go: constant values are the API
contract, APIError carries structured fields, and its string form matches
the Go SDK's `Error()` output (module-prefix free, per the Python design).
"""

from __future__ import annotations

import pytest

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

# Guards the constants against typos -- values are the API contract.
EXPECTED_CODE_VALUES = {
    "ERR_UNAUTHORIZED": (ERR_UNAUTHORIZED, "UNAUTHORIZED"),
    "ERR_VALIDATION": (ERR_VALIDATION, "VALIDATION_ERROR"),
    "ERR_INVALID_CHANNEL": (ERR_INVALID_CHANNEL, "INVALID_CHANNEL"),
    "ERR_INVALID_NUMBER": (ERR_INVALID_NUMBER, "INVALID_NUMBER"),
    "ERR_INSUFFICIENT_BALANCE": (ERR_INSUFFICIENT_BALANCE, "INSUFFICIENT_BALANCE"),
    "ERR_OTP_NOT_FOUND": (ERR_OTP_NOT_FOUND, "OTP_NOT_FOUND"),
    "ERR_DUPLICATE_EXTERNAL_ID": (ERR_DUPLICATE_EXTERNAL_ID, "DUPLICATE_EXTERNAL_ID"),
    "ERR_OTP_EXPIRED": (ERR_OTP_EXPIRED, "OTP_EXPIRED"),
    "ERR_TOO_MANY_ATTEMPTS": (ERR_TOO_MANY_ATTEMPTS, "TOO_MANY_ATTEMPTS"),
    "ERR_ALREADY_USED": (ERR_ALREADY_USED, "ALREADY_USED"),
    "ERR_RATE_LIMITED": (ERR_RATE_LIMITED, "RATE_LIMITED"),
    "ERR_DESTINATION_RATE_LIMITED": (
        ERR_DESTINATION_RATE_LIMITED,
        "DESTINATION_RATE_LIMITED",
    ),
    "ERR_CHANNEL_UNAVAILABLE": (ERR_CHANNEL_UNAVAILABLE, "CHANNEL_UNAVAILABLE"),
    "ERR_IP_NOT_ALLOWED": (ERR_IP_NOT_ALLOWED, "IP_NOT_ALLOWED"),
    "ERR_INTERNAL": (ERR_INTERNAL, "INTERNAL_ERROR"),
    "ERR_INVALID_RESPONSE": (ERR_INVALID_RESPONSE, "INVALID_RESPONSE"),
}


@pytest.mark.parametrize(
    ("got", "want"), EXPECTED_CODE_VALUES.values(), ids=EXPECTED_CODE_VALUES.keys()
)
def test_error_code_values(got: str, want: str) -> None:
    assert got == want


def test_api_error_attributes() -> None:
    err = APIError(
        code=ERR_DUPLICATE_EXTERNAL_ID,
        message="external_id already used",
        http_status=409,
        details={"existing_otp_id": "OTP20260807ABCD000001"},
    )
    assert err.code == ERR_DUPLICATE_EXTERNAL_ID
    assert err.message == "external_id already used"
    assert err.http_status == 409
    assert err.details == {"existing_otp_id": "OTP20260807ABCD000001"}


def test_api_error_details_defaults_to_none() -> None:
    err = APIError(code=ERR_OTP_EXPIRED, message="expired", http_status=422)
    assert err.details is None


def test_api_error_str_format() -> None:
    err = APIError(
        code=ERR_INSUFFICIENT_BALANCE,
        message="saldo tidak cukup",
        http_status=402,
    )
    assert str(err) == "INSUFFICIENT_BALANCE: saldo tidak cukup (http 402)"


def test_api_error_is_otpid_error_and_exception() -> None:
    err = APIError(code=ERR_UNAUTHORIZED, message="bad key", http_status=401)
    assert isinstance(err, OtpIdError)
    assert isinstance(err, Exception)


@pytest.mark.parametrize(
    "exc_class",
    [InvalidSignatureError, StaleTimestampError, UnexpectedEventError],
)
def test_webhook_exceptions_are_otpid_errors(exc_class: type[OtpIdError]) -> None:
    err = exc_class("boom")
    assert isinstance(err, OtpIdError)
    assert isinstance(err, Exception)
