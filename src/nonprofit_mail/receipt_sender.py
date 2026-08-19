from __future__ import annotations

from html import escape
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, EmailStr, Field, PositiveInt


class DonorReceipt(BaseModel):
    kind: Literal["donor_receipt"]
    request_id: str = Field(min_length=1, max_length=120)
    to: EmailStr
    donor_name: str = Field(min_length=1, max_length=120)
    donation_cents: PositiveInt
    donation_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    receipt_number: str = Field(min_length=1, max_length=80)


class VolunteerReminder(BaseModel):
    kind: Literal["volunteer_reminder"]
    request_id: str = Field(min_length=1, max_length=120)
    to: EmailStr
    volunteer_name: str = Field(min_length=1, max_length=120)
    shift_name: str = Field(min_length=1, max_length=160)
    starts_at: str = Field(min_length=1, max_length=80)


class CampaignReport(BaseModel):
    kind: Literal["campaign_report"]
    request_id: str = Field(min_length=1, max_length=120)
    to: EmailStr
    campaign_name: str = Field(min_length=1, max_length=160)
    donation_count: int = Field(ge=0)
    total_cents: int = Field(ge=0)


NotificationRequest = Annotated[
    DonorReceipt | VolunteerReminder | CampaignReport,
    Field(discriminator="kind"),
]


class DeliveryResult(BaseModel):
    message_id: str
    kind: str


class EmailSender(Protocol):
    def send(
        self, *, to: str, subject: str, html: str, idempotency_key: str
    ) -> dict[str, object]:
        raise AssertionError("Protocol methods are used through concrete senders")


def deliver_notification(request: NotificationRequest, sender: EmailSender) -> DeliveryResult:
    subject, html = render_notification(request)
    data = sender.send(
        to=str(request.to),
        subject=subject,
        html=html,
        idempotency_key=f"nonprofit-mail:{request.request_id}",
    )
    return DeliveryResult(message_id=str(data["message_id"]), kind=request.kind)


def render_notification(request: NotificationRequest) -> tuple[str, str]:
    if isinstance(request, DonorReceipt):
        amount = request.donation_cents / 100
        return (
            f"Donation receipt {request.receipt_number}",
            f"<h1>Thank you, {escape(request.donor_name)}</h1>"
            f"<p>We received your donation of <strong>${amount:,.2f}</strong> "
            f"on {escape(request.donation_date)}.</p>"
            f"<p>Receipt: {escape(request.receipt_number)}</p>",
        )
    if isinstance(request, VolunteerReminder):
        return (
            f"Reminder: {request.shift_name}",
            f"<h1>Hello {escape(request.volunteer_name)}</h1>"
            f"<p>Your {escape(request.shift_name)} shift starts at "
            f"{escape(request.starts_at)}.</p>",
        )
    return (
        f"Campaign report: {request.campaign_name}",
        f"<h1>{escape(request.campaign_name)}</h1>"
        f"<p>{request.donation_count:,} donations totaling "
        f"${request.total_cents / 100:,.2f}.</p>",
    )
