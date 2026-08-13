"""Example: send_otp -- you generate the code yourself and OTP.ID only
delivers it (POST /v3/send). Supported delivery channels: whatsapp, sms,
email.

Mirrors the docs cURL:

    curl -X POST https://api.otp.id/v3/send \\
      -d '{"channel": "sms", "number": "6281234567890", "otp": "482913",
           "brand": "MyApp", "ttl": 180, "external_id": "order-8822"}'

Run:

    OTPID_API_KEY=... OTPID_DESTINATION=6281234567890 python examples/send.py
"""

from __future__ import annotations

import os
import secrets
import sys

from otpid import CHANNEL_SMS, APIError, Client


def main() -> None:
    api_key = os.environ.get("OTPID_API_KEY")
    destination = os.environ.get("OTPID_DESTINATION")
    if not api_key or not destination:
        sys.exit("set OTPID_API_KEY and OTPID_DESTINATION first")

    # Generate our own 6-digit code -- with send_otp, code generation and
    # storage are the caller's responsibility; OTP.ID only delivers it.
    code = f"{secrets.randbelow(1_000_000):06d}"

    client = Client(api_key)

    try:
        res = client.send_otp(
            code,
            channel=CHANNEL_SMS,
            destination=destination,
            brand="MyApp",
            ttl=180,
            external_id="order-8822",
        )
    except APIError as e:
        sys.exit(f"api error: {e}")

    print(f"sent our own code: otp_id={res.otp_id} status={res.status} price={res.price}")

    entered = input("enter the code the user received: ").strip()

    # Verification still goes through OTP.ID -- it stored a hash of the
    # code it delivered, so verify_otp works exactly like with request_otp.
    try:
        v = client.verify_otp(res.otp_id, entered)
    except APIError as e:
        sys.exit(f"api error: {e}")

    if v.verified:
        print("verified!")
    else:
        print("wrong code:", v.reason)


if __name__ == "__main__":
    main()
