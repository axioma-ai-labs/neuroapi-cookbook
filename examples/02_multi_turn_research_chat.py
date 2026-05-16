"""Multi-turn research chat.

NeuroAPI is stateless: every follow-up request must include the prior turns that
should remain in context. This recipe keeps a small local transcript and sends
it as message_history on each call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")

Turn = dict[str, str]


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


@dataclass
class ResearchChat:
    client: httpx.Client
    mode: str = "smart"
    history: list[Turn] = field(default_factory=list)

    def ask(self, prompt: str) -> dict:
        response = self.client.post(
            "/agent/ask",
            json={
                "prompt": prompt,
                "mode": self.mode,
                "message_history": self.history,
            },
        )
        request_id = response.headers.get("x-request-id", "missing")
        response.raise_for_status()

        data = response.json()
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": data["answer"]})

        print(f"\nrequest_id={data.get('request_id', request_id)} mode={data.get('mode')}")
        print(data["answer"])
        return data

    def trim(self, keep_turns: int = 6) -> None:
        """Keep the most recent user/assistant pairs when a conversation grows."""
        self.history = self.history[-keep_turns * 2 :]


def main() -> None:
    headers = {"X-API-Key": require_api_key()}

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=90.0) as client:
        chat = ResearchChat(client=client, mode="smart")

        chat.ask(
            "Compare AAPL and MSFT as quality compounders. Use five bullets: "
            "growth, margins, capital returns, valuation risk, and key catalyst."
        )

        chat.ask(
            "Now turn that into a one-paragraph portfolio-manager takeaway. "
            "Keep the same relative comparison from the previous answer."
        )

        chat.trim()
        print(f"\nStored history messages: {len(chat.history)}")


if __name__ == "__main__":
    main()
