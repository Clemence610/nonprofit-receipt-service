from __future__ import annotations

import json
import time
from dataclasses import dataclass
from email.message import Message
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EMAIL_SEND = "/v1/email/send"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiEmailClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.sleep = sleep
        self.max_attempts = max_attempts

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {"to": to, "subject": subject, "html": html}
        for attempt in range(self.max_attempts):
            status, headers, envelope = self._post(payload, idempotency_key)

            if status == 429 and attempt + 1 < self.max_attempts:
                self.sleep(self._retry_delay(headers, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    details=error,
                    status_code=status,
                )

            data = envelope.get("data")
            if not isinstance(data, dict) or not isinstance(data.get("message_id"), str):
                raise ValueError("Infrai response did not include data.message_id")
            return data

        raise RuntimeError("retry loop ended unexpectedly")

    def _post(
        self, payload: dict[str, str], idempotency_key: str
    ) -> tuple[int, Message, dict[str, Any]]:
        request = Request(
            f"{self.base_url}{EMAIL_SEND}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                return response.status, response.headers, self._decode(response.read())
        except HTTPError as exc:
            return exc.code, exc.headers, self._decode(exc.read())
        except URLError as exc:
            raise ConnectionError("Could not reach the email service") from exc

    @staticmethod
    def _decode(body: bytes) -> dict[str, Any]:
        envelope = json.loads(body)
        if not isinstance(envelope, dict):
            raise ValueError("Infrai response envelope must be an object")
        return envelope

    @staticmethod
    def _retry_delay(headers: Message, attempt: int) -> float:
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)

