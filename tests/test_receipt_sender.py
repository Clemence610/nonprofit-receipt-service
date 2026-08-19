from nonprofit_mail.receipt_sender import DonorReceipt, deliver_notification


class RecordingSender:
    def __init__(self) -> None:
        self.sent: dict[str, str] = {}

    def send(self, **message: str) -> dict[str, object]:
        self.sent = message
        return {"message_id": "msg_receipt_42"}


def test_receipt_preserves_cents_and_uses_request_as_delivery_identity() -> None:
    sender = RecordingSender()
    receipt = DonorReceipt(
        kind="donor_receipt",
        request_id="donation-event-42",
        to="donor@example.org",
        donor_name="Rae & Sam",
        donation_cents=12345,
        donation_date="2026-08-19",
        receipt_number="R-0042",
    )

    result = deliver_notification(receipt, sender)

    assert result.message_id == "msg_receipt_42"
    assert "$123.45" in sender.sent["html"]
    assert "Rae &amp; Sam" in sender.sent["html"]
    assert sender.sent["idempotency_key"] == "nonprofit-mail:donation-event-42"

