# Upgrading

## From 0.1.x to 0.2.0

```bash
pip install --upgrade "otp-id>=0.2,<0.3"
```

### Breaking changes

None. 0.2.0 only adds fields and constants. `OrderResult.failure` and
`StatusResult.failure` are new optional fields with a `None` default,
added after all existing fields, so existing attribute access and
constructor calls keep working. `status` is still a plain `str`.

Behaviour change outside the SDK: `whatsapp_inbound` billing changed on the
server (see below). If your code reads `last_balance` right after a
`whatsapp_inbound` request, or treats `pending` as already paid, review it.

### What's new

#### Delivery failure reason: `result.failure`

When `status == "failed"`, `OrderResult.failure` and `StatusResult.failure`
hold a `DeliveryFailure` (`code` and `message`). They are `None` for every
other status. `code` is one of the `FAILURE_*` constants, but the set can
grow, so fall back to `message` (a user-safe Indonesian string) for codes
you don't recognize.

```python
from otpid import (
    CHANNEL_WHATSAPP,
    FAILURE_NUMBER_NOT_ON_WHATSAPP,
    FAILURE_TOO_FREQUENT,
)

res = client.request_otp(channel=CHANNEL_WHATSAPP, destination="6281234567890")
if res.status == "failed" and res.failure is not None:
    if res.failure.code == FAILURE_NUMBER_NOT_ON_WHATSAPP:
        ...  # offer SMS instead
    elif res.failure.code == FAILURE_TOO_FREQUENT:
        ...  # ask the user to wait
    else:
        print(res.failure.message)
```

Other codes: `FAILURE_CHANNEL_UNAVAILABLE`, `FAILURE_PROVIDER_UNAVAILABLE`,
`FAILURE_DELIVERY_FAILED`.

#### `otp_status` returns `verification` for pending `whatsapp_inbound`

While a `whatsapp_inbound` transaction is `pending` and not yet expired,
`otp_status` now fills `StatusResult.verification`
(`wa_number`/`message`/`wa_link`/`expires_at`), the same block
`request_otp` returns. You can recover the `wa_link` while polling, for
example if the original order response was lost.

```python
st = client.otp_status(otp_id)
if st.status == "pending" and st.verification is not None:
    show_link(st.verification.wa_link)
```

#### `whatsapp_inbound` billing: pay only when verified

This is a server-side change and applies to every SDK version.

- The transaction stays `pending` while waiting for the user's WhatsApp
  message.
- It is charged only when it becomes `verified`. `OrderResult.price` is the
  amount charged on verification, and `last_balance` is unchanged at
  request time.
- It can end as `expired` (TTL passed without a match). Expired
  transactions are not charged.
- A message from a different number than the bound `destination` is
  rejected and the transaction stays `pending`.

A polling loop should stop on `verified`, `expired`, or `failed`:

```python
import time

from otpid import CHANNEL_WHATSAPP_INBOUND

res = client.request_otp(
    channel=CHANNEL_WHATSAPP_INBOUND,
    destination="6281234567890",
)
print("Ask the user to tap:", res.verification.wa_link)

while True:
    st = client.otp_status(res.otp_id)
    if st.status == "verified":
        break  # charged st.price
    if st.status == "expired":
        break  # not charged; offer a new request
    if st.status == "failed":
        print(st.failure.message if st.failure else "failed")
        break
    time.sleep(3)
```

Prefer the `otp.verified` webhook over polling where you can.
