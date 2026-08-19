from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_email import InfraiEmailClient, InfraiError
from .receipt_sender import DeliveryResult, NotificationRequest, deliver_notification

app = FastAPI(title="Nonprofit mail service")


@app.post("/notifications", response_model=DeliveryResult, status_code=202)
def send_notification(request: NotificationRequest) -> DeliveryResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")

    try:
        return deliver_notification(request, InfraiEmailClient(api_key))
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc.details.get("message", exc.code))},
        ) from exc

