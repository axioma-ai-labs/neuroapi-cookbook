"""Validate structured JSON returned by NeuroAPI.

The agent is prompted to return only JSON, but application code still validates
the result before trusting it. This pattern is useful for dashboards, alerts,
and pipelines that need typed data rather than prose.
"""

from __future__ import annotations

import json
import os
import re
from typing import Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")


class MarketReport(BaseModel):
    asset: str
    stance: Literal["bullish", "neutral", "bearish"]
    confidence: int = Field(ge=0, le=100)
    horizon: str
    thesis: str = Field(min_length=20, max_length=600)
    drivers: list[str] = Field(min_length=2, max_length=5)
    risks: list[str] = Field(min_length=2, max_length=5)
    invalidation: str = Field(min_length=10, max_length=300)


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in NeuroAPI answer.")
    return json.loads(cleaned[start : end + 1])


def main() -> None:
    prompt = """
Return only a JSON object for this schema:
{
  "asset": "string",
  "stance": "bullish | neutral | bearish",
  "confidence": "integer from 0 to 100",
  "horizon": "string",
  "thesis": "string, <= 600 characters",
  "drivers": ["2 to 5 short strings"],
  "risks": ["2 to 5 short strings"],
  "invalidation": "string"
}

Create a market report for NVDA written for a public-equities analyst.
Do not include markdown, comments, or trailing text.
""".strip()

    headers = {"X-API-Key": require_api_key()}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=90.0) as client:
        response = client.post(
            "/agent/ask",
            json={
                "prompt": prompt,
                "mode": "smart",
            },
        )
        request_id = response.headers.get("x-request-id", "missing")
        response.raise_for_status()
        answer = response.json()["answer"]

    try:
        report = MarketReport.model_validate(extract_json_object(answer))
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise RuntimeError(
            f"Could not validate NeuroAPI response. request_id={request_id}"
        ) from exc

    print(f"request_id={request_id}")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
