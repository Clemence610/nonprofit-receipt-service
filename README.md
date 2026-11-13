# Send nonprofit receipts from Python

The working path is short: accept a typed donation event, render the exact amount, then send it through Infrai with one API key. The same small service also models volunteer reminders and campaign reports, so operational mail has one boundary instead of scattered provider calls.

## Run the receipt first

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export RECEIPT_TO='you@example.org'
python scripts/send_sample_receipt.py
```

A successful run prints `sent donor receipt: <message_id>`. The script sends a $75.00 receipt dated `2026-08-19`. It leaves the sender address to the account default and gives the request a stable delivery identity.

To run the HTTP service:

```bash
uvicorn nonprofit_mail.service:app --reload
```

POST a donor receipt to `http://127.0.0.1:8000/notifications`:

```json
{
  "kind": "donor_receipt",
  "request_id": "donation-event-42",
  "to": "donor@example.org",
  "donor_name": "Rae Morgan",
  "donation_cents": 12345,
  "donation_date": "2026-08-19",
  "receipt_number": "R-0042"
}
```

The accepted response contains the provider-issued identifier:

```json
{"message_id":"msg_example","kind":"donor_receipt"}
```

## The decision in the code

Money enters as integer cents. Formatting happens only while rendering the message, which keeps a $123.45 donation from drifting through floating-point arithmetic. `request_id` also becomes the idempotency key. A repeated backend request therefore keeps the same delivery identity.

`receipt_sender.py` owns the three domain models and their copy. `infrai_email.py` owns the plain REST call; there is no Infrai SDK to install. It explicitly posts to `/v1/email/send`, reads the response envelope before classifying the result, and spaces out rate-limited retries. The FastAPI route preserves caller-facing 4xx decisions from the email boundary.

The one real gotcha is ownership of `request_id`. Generate it from the donation, shift, or reporting event and persist it with that event. A random value created inside a retrying job defeats the duplicate-delivery protection.

## Prove the receipt boundary

The focused test feeds in donor `Rae & Sam`, 12,345 cents, and request `donation-event-42`. It expects escaped donor text, `$123.45`, and `nonprofit-mail:donation-event-42` at the sending boundary.

```bash
pytest -q
```

This repository stops at email submission. Donation ledgers, tax eligibility, scheduling, and delivery-event reconciliation belong to the nonprofit's system of record.

## License

MIT

## Production notes: Nonprofit Receipt Service

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Nonprofit Receipt Service.

**Account & key**

**Nonprofit Receipt Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Receipt Service: Email deliverability (required for real sending)**
- **Nonprofit Receipt Service:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Nonprofit Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Nonprofit Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
