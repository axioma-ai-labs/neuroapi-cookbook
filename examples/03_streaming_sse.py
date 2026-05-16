"""Stream a NeuroAPI answer over Server-Sent Events.

Pass stream=true to /agent/ask and render answer chunks as they arrive. The
stream finishes with `data: [DONE]`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def iter_sse_payloads(response: httpx.Response) -> Iterator[str]:
    buffer = ""
    for chunk in response.iter_text():
        buffer += chunk

        while "\n\n" in buffer:
            event, buffer = buffer.split("\n\n", 1)
            for line in event.splitlines():
                if not line.startswith("data:"):
                    continue

                payload = line.removeprefix("data:").strip()
                if payload == "[DONE]":
                    return
                yield payload


def extract_answer_text(payload: str) -> str:
    """Extract answer text from the current TaskResponseMessage shape.

    If the event shape changes, fall back to printing the raw payload so the
    caller still sees useful stream data.
    """
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    if event.get("type") == "error":
        raise RuntimeError(event.get("message", "NeuroAPI stream error"))

    answer = event.get("data", {}).get("answer") or {}
    chunk = answer.get("chunk") or {}
    return chunk.get("content", "")


def main() -> None:
    headers = {"X-API-Key": require_api_key()}

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=None) as client:
        with client.stream(
            "POST",
            "/agent/ask",
            json={
                "prompt": (
                    "Stream a top-down macro brief for a crypto portfolio manager. "
                    "Start with the conclusion, then list the main risks."
                ),
                "mode": "smart",
                "stream": True,
            },
        ) as response:
            request_id = response.headers.get("x-request-id", "missing")
            response.raise_for_status()

            print(f"request_id={request_id}\n")
            for payload in iter_sse_payloads(response):
                text = extract_answer_text(payload)
                if text:
                    print(text, end="", flush=True)
            print()


if __name__ == "__main__":
    main()
