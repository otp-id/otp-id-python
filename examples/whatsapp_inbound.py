"""Example: WhatsApp Inbound -- the USER sends a WhatsApp message to OTP.ID
instead of typing a code. There is nothing to verify manually: OTP.ID
matches the incoming message to the transaction automatically. This
example polls GET /v3/otp/{otp_id} (via otp_status) until the status
becomes "verified".

Mirrors the docs cURL:

    curl -X POST https://api.otp.id/v3/request \\
      -d '{"channel": "whatsapp_inbound", "brand": "MyApp", "ttl": 300}'

Do NOT call verify_otp for this channel -- inbound transactions carry no
code, so any submission counts as a failed attempt. In production, prefer
the otp.verified webhook over polling (see the root README).

Run:

    OTPID_API_KEY=... python examples/whatsapp_inbound.py
"""

from __future__ import annotations

import os
import sys
import time

from otpid import CHANNEL_WHATSAPP_INBOUND, APIError, Client

_POLL_INTERVAL_SECONDS = 3
_POLL_TIMEOUT_SECONDS = 5 * 60


def main() -> None:
    api_key = os.environ.get("OTPID_API_KEY")
    if not api_key:
        sys.exit("set OTPID_API_KEY first")

    client = Client(api_key)

    try:
        res = client.request_otp(
            channel=CHANNEL_WHATSAPP_INBOUND,
            brand="MyApp",
            ttl=300,
        )
    except APIError as e:
        sys.exit(f"api error: {e}")

    if res.verification is None:
        sys.exit("expected a verification block for whatsapp_inbound")

    print(f"created: otp_id={res.otp_id} status={res.status}")
    print("ask the user to tap this link and send the pre-filled message:")
    print(f"  {res.verification.wa_link}")
    print(
        f'(or message "{res.verification.message}" to {res.verification.wa_number} '
        f"-- valid until {res.verification.expires_at})"
    )

    print("waiting for the user's WhatsApp message...")
    deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            status = client.otp_status(res.otp_id)
        except APIError as e:
            sys.exit(f"api error: {e}")
        if status.status == "verified":
            print("verified at", status.verified_at)
            return

    print("timed out -- the user never sent the message")


if __name__ == "__main__":
    main()
