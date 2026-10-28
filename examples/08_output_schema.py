"""Ask for a JSON object with output_schema.

`output_schema` is a JSON Schema with an object root. The object comes back
on `output`, and `answer` is null. This recipe sends `stream: false`, which
`output_schema` requires.

Validate `output` locally before using it. Structured calls usually take
10-60 seconds, so the client timeout is 120 seconds.
"""

from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")

# Object root, every property required, additionalProperties false.
# Descriptions guide the agent. They are not checked.
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "asset": {"type": "string"},
        "stance": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "conviction": {"type": "number", "description": "0-1 confidence"},
        "summary": {"type": "string"},
    },
    "required": ["asset", "stance", "conviction", "summary"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are a concise crypto analyst. Fill only the schema fields. "
    "conviction is a number from 0 to 1."
)


class MarketRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset: str = Field(min_length=1)
    stance: Literal["bullish", "bearish", "neutral"]
    conviction: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1)


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def main() -> None:
    headers = {"X-API-Key": require_api_key()}
    body = {
        "prompt": "Give me a structured read on Bitcoin right now.",
        "mode": "smart",
        "stream": False,
        "system_prompt": SYSTEM_PROMPT,
        "output_schema": OUTPUT_SCHEMA,
    }

    # Structured calls usually return in 10-60 seconds. Allow 120.
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=120.0) as client:
        response = client.post("/agent/ask", json=body)
        request_id = response.headers.get("x-request-id", "missing")
        if not response.is_success:
            raise SystemExit(
                f"NeuroAPI {response.status_code} request_id={request_id}: {response.text}"
            )

        data = response.json()
        request_id = data.get("request_id", request_id)
        output = data.get("output")
        if not isinstance(output, dict):
            raise SystemExit(f"Expected an output object. request_id={request_id}")

    try:
        report = MarketRead.model_validate(output)
    except ValidationError as exc:
        raise SystemExit(f"Output failed local validation. request_id={request_id}\n{exc}") from exc

    print(f"request_id={request_id} mode={data.get('mode')}")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
