"""Example: WhatsApp OTP -- server-generated code, then verify.

Mirrors the docs cURL:

    curl -X POST https://api.otp.id/v3/request \\
      -d '{"channel": "whatsapp", "number": "6281234567890", "brand": "MyApp", "ttl": 300}'

Run:

    OTPID_API_KEY=... OTPID_DESTINATION=6281234567890 python examples/whatsapp.py
"""

from __future__ import annotations

import os
import sys

from otpid import CHANNEL_WHATSAPP, APIError, Client


def main() -> None:
    api_key = os.environ.get("OTPID_API_KEY")
    destination = os.environ.get("OTPID_DESTINATION")
    if not api_key or not destination:
        sys.exit("set OTPID_API_KEY and OTPID_DESTINATION first")

    client = Client(api_key)

    try:
        res = client.request_otp(
            channel=CHANNEL_WHATSAPP,
            destination=destination,
            brand="MyApp",
            ttl=300,
        )
    except APIError as e:
        sys.exit(f"api error: {e}")

    print(
        f"sent: otp_id={res.otp_id} status={res.status} "
        f"price={res.price} last_balance={res.last_balance}"
    )

    code = input("enter the code the user received on WhatsApp: ").strip()

    try:
        v = client.verify_otp(res.otp_id, code)
    except APIError as e:
        sys.exit(f"api error: {e}")

    if v.verified:
        print("verified!")
    else:
        print("wrong code:", v.reason)  # "mismatch" -- not an error


if __name__ == "__main__":
    main()
