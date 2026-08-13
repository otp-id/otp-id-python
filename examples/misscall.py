"""Example: Missed Call OTP -- the code is the last digits of the number
that calls the user, then verify.

Mirrors the docs cURL:

    curl -X POST https://api.otp.id/v3/request \\
      -d '{"channel": "misscall", "number": "6281234567890"}'

Notes: brand is not needed (no message body), and otp_length has no
effect -- the code length is set by the telephony vendor. The response's
verification.prefix is the calling number MINUS the code digits, so the
UI can render "628559263-____" and ask the user to complete it from
their missed-call log.

Run:

    OTPID_API_KEY=... OTPID_DESTINATION=6281234567890 python examples/misscall.py
"""

from __future__ import annotations

import os
import sys

from otpid import CHANNEL_MISSCALL, APIError, Client


def main() -> None:
    api_key = os.environ.get("OTPID_API_KEY")
    destination = os.environ.get("OTPID_DESTINATION")
    if not api_key or not destination:
        sys.exit("set OTPID_API_KEY and OTPID_DESTINATION first")

    client = Client(api_key)

    try:
        res = client.request_otp(channel=CHANNEL_MISSCALL, destination=destination)
    except APIError as e:
        sys.exit(f"api error: {e}")

    print(f"calling: otp_id={res.otp_id} status={res.status} price={res.price}")
    if res.verification is not None:
        print(
            f"the incoming call number starts with: {res.verification.prefix} "
            f"(complete the last {res.verification.otp_length} digits)"
        )

    code = input("enter the LAST digits of the number that called: ").strip()

    try:
        v = client.verify_otp(res.otp_id, code)
    except APIError as e:
        sys.exit(f"api error: {e}")

    if v.verified:
        print("verified!")
    else:
        print("wrong digits:", v.reason)


if __name__ == "__main__":
    main()
