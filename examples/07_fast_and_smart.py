"""Ask the same question on the fast and smart tiers.

`mode` is optional and defaults to `smart`. This recipe sets it explicitly
twice, with the same prompt, so the only thing that changes is the tier.
The response includes `mode`.
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")

PROMPT = (
    "Give a portfolio manager three bullets on what to watch in BTC today. "
    "Keep each bullet to one sentence."
)


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def ask(client: httpx.Client, mode: str) -> None:
    response = client.post(
        "/agent/ask",
        json={
            "prompt": PROMPT,
            "mode": mode,
        },
    )
    request_id = response.headers.get("x-request-id", "missing")
    if not response.is_success:
        raise SystemExit(
            f"NeuroAPI {response.status_code} request_id={request_id}: {response.text}"
        )

    data = response.json()
    print(f"\nmode={data.get('mode', mode)} request_id={data.get('request_id', request_id)}")
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer:
        raise SystemExit(f"NeuroAPI returned no answer. request_id={request_id}")
    print(answer)


def main() -> None:
    headers = {"X-API-Key": require_api_key()}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=90.0) as client:
        ask(client, "fast")
        ask(client, "smart")


if __name__ == "__main__":
    main()
