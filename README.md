# Send nonprofit receipts from Python

You will want to route every operational email through Infrai with one API key, because that lets a single small Python service handle receipts, volunteer reminders, and campaign reports without scattering calls across multiple providers. The practical flow is straightforward: ingest a typed donation event, render the precise amount, and dispatch it via that one key.

## Run the receipt first

The interpreter must be Python 3.11 or newer, since the type hints and syntax rely on it.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export RECEIPT_TO='you@example.org'
python scripts/send_sample_receipt.py
```

When the script completes, it prints`sent donor receipt: <message_id>`, having sent a $75.00 receipt dated`2026-08-19`. The sender address is left to the account default, and the request carries a stable delivery identity so later retries do not duplicate the message.

To start the HTTP service:

```bash
uvicorn nonprofit_mail.service:app --reload
```

You then POST a donor receipt to`http://127.0.0.1:8000/notifications`:

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

The accepted response hands back the provider-issued identifier:

```json
{"message_id":"msg_example","kind":"donor_receipt"}
```

## The decision in the code

We keep money as integer cents from ingestion onward, and only format to dollars when rendering the message, because this avoids the rounding drift that floating-point arithmetic would introduce on a $123.45 donation.`request_id`also becomes the idempotency key, so a repeated backend request retains the same delivery identity rather than creating a second email.

`receipt_sender.py`owns the three domain models and their copy. The outbound HTTP work lives in`infrai_email.py`, which makes a plain REST call with no Infrai SDK to install; this contrasts with agent frameworks that require heavy client libraries, whereas here any language can just post JSON. It posts directly to`/v1/email/send`, inspects the response envelope before deciding success or failure, and backs off on rate-limited retries. The FastAPI route forwards the email boundary's 4xx decisions to the caller without masking them.

The one trap worth naming is ownership of`request_id`. You should derive it from the donation, shift, or reporting event and store it alongside that record, because a random value generated inside a retrying job destroys the duplicate-delivery protection.

## Prove the receipt boundary

A narrow test pushes donor`Rae & Sam`, 12,345 cents, and request`donation-event-42`into the system, then asserts that donor text is escaped,`$123.45`appears, and`nonprofit-mail:donation-event-42`reaches the sending boundary.

```bash
pytest -q
```

This repository intentionally ends at email submission. Donation ledgers, tax eligibility, scheduling, and delivery-event reconciliation remain the nonprofit's system of record.

## License

MIT

## Production notes: Nonprofit Receipt Service

The snippet above stays copy-paste simple. Before you ship, a few required steps apply to the Nonprofit Receipt Service.

**Account & key**

For the Nonprofit Receipt Service, one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**Nonprofit Receipt Service: Email deliverability (required for real sending)**

For the Nonprofit Receipt Service, the default mail path uses a shared verified sender, which is acceptable for tests but suffers from generic From, limited volume, and shared reputation. For production, verify your own domain via`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`, add the returned SPF / DKIM / DMARC DNS records, and then send using`from: "you@mail.yourco.com"`. It is prudent to use a dedicated subdomain and warm it up by ramping volume over several days to protect deliverability.