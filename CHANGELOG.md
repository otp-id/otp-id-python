# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `DeliveryFailure` (`code` + `message`) and `FAILURE_*` code constants
  (`FAILURE_NUMBER_NOT_ON_WHATSAPP`, `FAILURE_TOO_FREQUENT`,
  `FAILURE_CHANNEL_UNAVAILABLE`, `FAILURE_PROVIDER_UNAVAILABLE`,
  `FAILURE_DELIVERY_FAILED`). `OrderResult.failure` and
  `StatusResult.failure` are populated from the response's `failure` block
  whenever `status == "failed"`, `None` otherwise.
- `StatusResult.verification` (`otp_status` / `GET /v3/otp/{otp_id}`) is now
  also populated for a pending, not-yet-expired `whatsapp_inbound`
  transaction (`wa_number`/`message`/`wa_link`/`expires_at`), matching what
  `request_otp` already returned, so polling clients can recover the wa.me
  link.

## [0.1.0] - 2026-08-14

### Added

- `Client` with `request_otp`, `send_otp`, `verify_otp`, `otp_status`,
  `account`, and `create_topup` covering the full OTP.ID V3 API.
- `verify_webhook_signature` and `parse_verified_event` for the
  `otp.verified` webhook (HMAC-SHA256, constant-time comparison, ±5 minute
  replay window by default).
- Typed `APIError` with the complete V3 error code set.
- Zero-dependency implementation (standard library only), Python 3.10+.
- `py.typed` marker for full type-checker support.
- `README.md` and runnable examples for every channel (`whatsapp`, `sms`,
  `voice`, `email`, `misscall`, `whatsapp_inbound`, `send`), mirroring the
  cURL examples in the API docs.
