"""First NeuroAPI request.

This recipe verifies an API key with /health, asks the agent once through the
sync JSON path, and prints the response usage and request id.
"""

from __future__ import annotations

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def print_json(title: str, payload: object) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    headers = {"X-API-Key": require_api_key()}

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=60.0) as client:
        health = client.get("/health")
        health.raise_for_status()
        print_json("Health check", health.json())

        response = client.post(
            "/agent/ask",
            json={
                "prompt": (
                    "Give me a concise three-bullet market brief for BTC, ETH, "
                    "and SOL. Focus on what a portfolio manager should watch today."
                ),
                "mode": "smart",
            },
        )
        request_id = response.headers.get("x-request-id", "missing")
        response.raise_for_status()

        data = response.json()
        print("\nAnswer")
        print(data["answer"])
        print_json(
            "Request metadata",
            {
                "request_id": data.get("request_id", request_id),
                "mode": data.get("mode"),
                "usage": data.get("usage"),
            },
        )


if __name__ == "__main__":
    main()
