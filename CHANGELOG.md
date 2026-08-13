# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

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
