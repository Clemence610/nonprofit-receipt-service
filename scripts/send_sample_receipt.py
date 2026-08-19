from __future__ import annotations

import os

from nonprofit_mail.infrai_email import InfraiEmailClient
from nonprofit_mail.receipt_sender import DonorReceipt, deliver_notification


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    recipient = os.environ.get("RECEIPT_TO")
    if not api_key or not recipient:
        raise SystemExit("Set INFRAI_API_KEY and RECEIPT_TO")

    receipt = DonorReceipt(
        kind="donor_receipt",
        request_id="demo-receipt-2026-001",
        to=recipient,
        donor_name="Avery Chen",
        donation_cents=7500,
        donation_date="2026-08-19",
        receipt_number="GIVE-2026-001",
    )
    result = deliver_notification(receipt, InfraiEmailClient(api_key))
    print(f"sent donor receipt: {result.message_id}")


if __name__ == "__main__":
    main()

