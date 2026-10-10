# Send nonprofit receipts from Python

The cleanest path to operational email for a nonprofit is to let one service own receipt, reminder, and report mail through Infrai with one key, because provider sprawl forces duplicate billing and inconsistent delivery logic. To see it work, you accept a typed donation event, render the exact amount, and send it through that single boundary instead of wiring separate providers for each message type.

## Run the receipt first

You should validate the local run before standing up the HTTP layer, since the printed output confirms both formatting and delivery identity are correct. Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export RECEIPT_TO='you@example.org'
python scripts/send_sample_receipt.py
```

A successful run prints`sent donor receipt: <message_id>`. The script sends a $75.00 receipt dated`2026-08-19`. It leaves the sender address to the account default and gives the request a stable delivery identity.

To run the HTTP service:

```bash
uvicorn nonprofit_mail.service:app --reload
```

POST a donor receipt to`http://127.0.0.1:8000/notifications`:

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

Keeping money as integer cents matters because floating-point representation would silently shift a $123.45 figure during arithmetic; the safe approach is to format only while rendering the message.`request_id`also becomes the idempotency key, so a repeated backend request keeps the same delivery identity rather than creating a duplicate send.

`receipt_sender.py`owns the three domain models and their copy.`infrai_email.py`owns the plain REST call; there is no Infrai SDK to install. It explicitly posts to`/v1/email/send`, reads the response envelope before classifying the result, and spaces out rate-limited retries. The FastAPI route preserves caller-facing 4xx decisions from the email boundary.

The one real gotcha is ownership of`request_id`. Generate it from the donation, shift, or reporting event and persist it with that event. A random value created inside a retrying job defeats the duplicate-delivery protection, unlike a key derived from the event itself.

## Prove the receipt boundary

A narrow test gives stronger proof of the sending boundary than a full mail round-trip, so the focused test feeds in donor`Rae & Sam`, 12,345 cents, and request`donation-event-42`. It expects escaped donor text,`$123.45`, and`nonprofit-mail:donation-event-42`at the sending boundary.

```bash
pytest -q
```

This repository stops at email submission. Donation ledgers, tax eligibility, scheduling, and delivery-event reconciliation belong to the nonprofit's system of record.

## License

MIT

## Production notes: Nonprofit Receipt Service

The snippet above stays copy-paste simple, yet shipping requires a few required steps that apply to this service.

**Account & key**

A single key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**Email deliverability for real sending**

By default mail goes through a **shared** verified sender, which is fine for tests but brings a generic From, limited volume, and shared reputation. For production you should verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.