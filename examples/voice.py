"""Example: Voice OTP -- a phone call speaks a 4-digit code, then verify.

Mirrors the docs cURL:

    curl -X POST https://api.otp.id/v3/request \\
      -d '{"channel": "voice", "number": "6281234567890", "brand": "MyApp", "ttl": 300}'

Notes: brand is REQUIRED by the server for voice, and the code length is
always 4 (any otp_length in the request is ignored for this channel).

Run:

    OTPID_API_KEY=... OTPID_DESTINATION=6281234567890 python examples/voice.py
"""

from __future__ import annotations

import os
import sys

from otpid import CHANNEL_VOICE, APIError, Client


def main() -> None:
    api_key = os.environ.get("OTPID_API_KEY")
    destination = os.environ.get("OTPID_DESTINATION")
    if not api_key or not destination:
        sys.exit("set OTPID_API_KEY and OTPID_DESTINATION first")

    client = Client(api_key)

    try:
        res = client.request_otp(
            channel=CHANNEL_VOICE,
            destination=destination,
            brand="MyApp",  # required for voice
            ttl=300,
        )
    except APIError as e:
        sys.exit(f"api error: {e}")

    print(
        f"calling: otp_id={res.otp_id} status={res.status} "
        f"price={res.price} last_balance={res.last_balance}"
    )

    code = input("enter the 4-digit code spoken in the call: ").strip()

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
