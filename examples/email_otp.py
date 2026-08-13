"""Example: Email OTP -- server-generated code delivered by email, then verify.

Mirrors the docs cURL:

    curl -X POST https://api.otp.id/v3/request \\
      -d '{"channel": "email", "number": "user@example.com", "brand": "MyApp"}'

Set OTPID_DESTINATION to the recipient email address for this example.

Named `email_otp.py` (not `email.py`) on purpose: `examples/` is prepended
to `sys.path` when a script here is run directly, and a same-directory
`email.py` would shadow the standard library `email` package that
`urllib.request` imports internally -- breaking every example in this
directory, not just this one.

Run:

    OTPID_API_KEY=... OTPID_DESTINATION=user@example.com python examples/email_otp.py
"""

from __future__ import annotations

import os
import sys

from otpid import CHANNEL_EMAIL, APIError, Client


def main() -> None:
    api_key = os.environ.get("OTPID_API_KEY")
    destination = os.environ.get("OTPID_DESTINATION")
    if not api_key or not destination:
        sys.exit("set OTPID_API_KEY and OTPID_DESTINATION (an email address) first")

    client = Client(api_key)

    try:
        res = client.request_otp(
            channel=CHANNEL_EMAIL,
            destination=destination,
            brand="MyApp",
        )
    except APIError as e:
        sys.exit(f"api error: {e}")

    print(
        f"sent: otp_id={res.otp_id} status={res.status} "
        f"price={res.price} last_balance={res.last_balance}"
    )

    code = input("enter the code from the email: ").strip()

    try:
        v = client.verify_otp(res.otp_id, code)
    except APIError as e:
        sys.exit(f"api error: {e}")

    if v.verified:
        print("verified!")
    else:
        print("wrong code:", v.reason)


if __name__ == "__main__":
    main()
