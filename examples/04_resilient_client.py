"""A small resilient NeuroAPI client.

This recipe wraps sync /agent/ask calls with:
- bounded retries for 429 rate limits and 503 capacity errors,
- Retry-After handling,
- Idempotency-Key for safe retry of the same logical operation,
- structured exceptions that include X-Request-Id.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from uuid import uuid4

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


@dataclass
class AskResult:
    data: dict
    request_id: str
    replayed: bool


class NeuroAPIError(RuntimeError):
    def __init__(self, status_code: int, request_id: str, detail: str) -> None:
        super().__init__(f"NeuroAPI {status_code} request_id={request_id}: {detail}")
        self.status_code = status_code
        self.request_id = request_id
        self.detail = detail

    @classmethod
    def from_response(cls, response: httpx.Response) -> NeuroAPIError:
        request_id = response.headers.get("x-request-id", "missing")
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return cls(response.status_code, request_id, str(detail))


class NeuroAPI:
    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        self.client = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=90.0,
        )

    def close(self) -> None:
        self.client.close()

    def ask(
        self,
        prompt: str,
        *,
        mode: str = "smart",
        message_history: list[dict[str, str]] | None = None,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
    ) -> AskResult:
        body = {
            "prompt": prompt,
            "mode": mode,
            "message_history": message_history or [],
            "stream": False,
        }
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None

        for attempt in range(max_attempts):
            try:
                response = self.client.post("/agent/ask", json=body, headers=headers)
            except httpx.TransportError:
                if attempt == max_attempts - 1:
                    raise
                time.sleep(2**attempt)
                continue

            if response.status_code in (429, 503) and attempt < max_attempts - 1:
                time.sleep(self._retry_delay(response, attempt))
                continue

            if not response.is_success:
                raise NeuroAPIError.from_response(response)

            return AskResult(
                data=response.json(),
                request_id=response.headers.get("x-request-id", "missing"),
                replayed=response.headers.get("idempotent-replayed", "").lower() == "true",
            )

        raise RuntimeError("Retry loop exited unexpectedly.")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt)


def main() -> None:
    api = NeuroAPI(require_api_key())
    try:
        logical_operation_id = f"daily-market-brief-{uuid4()}"
        result = api.ask(
            "Write a concise daily market brief for BTC, ETH, US equities, and rates. "
            "End with three risk checks for the next trading session.",
            mode="smart",
            idempotency_key=logical_operation_id,
        )
    finally:
        api.close()

    print(f"request_id={result.request_id} replayed={result.replayed}")
    print(result.data["answer"])
    print(result.data["usage"])


if __name__ == "__main__":
    main()
