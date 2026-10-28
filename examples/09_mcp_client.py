"""Call ask_neuroapi from the Python MCP SDK.

NeuroAPI exposes one remote MCP tool, ask_neuroapi, over Streamable HTTP.
Its arguments mirror a non-streaming POST /agent/ask body: prompt, and
optionally mode, message_history, system_prompt, and output_schema.

Install on Python 3.10+:

    pip install -r examples/mcp/requirements.txt
    python3 examples/09_mcp_client.py
"""

from __future__ import annotations

import os

import httpx2
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
# Documented URL: https://api.neurobro.ai/api/v1/mcp
# A POST to that URL returns 307 Location: http://api.neurobro.ai/api/v1/mcp/
# (the scheme drops to http). This SDK does not follow a cross-scheme redirect,
# so the client calls the trailing-slash URL directly.
MCP_URL = f"{BASE_URL}/mcp/"
API_KEY = os.getenv("NEUROAPI_KEY")

PROMPT = (
    "Give me a concise three-bullet market brief for BTC. Focus on what a "
    "portfolio manager should watch today."
)


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def result_text(result: object) -> str:
    blocks = getattr(result, "content", []) or []
    lines = [block.text for block in blocks if getattr(block, "type", None) == "text"]
    return "\n".join(lines)


async def main() -> None:
    # Same header as the REST API. Do not put the key in the URL.
    # 30s for connect/write, 300s read: a research call can sit quiet until the answer.
    timeout = httpx2.Timeout(30.0, read=300.0)
    headers = {"X-API-Key": require_api_key()}

    async with httpx2.AsyncClient(headers=headers, timeout=timeout) as http_client:
        async with streamable_http_client(MCP_URL, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                names = [tool.name for tool in listed.tools]
                print("Tools:", ", ".join(names))
                if "ask_neuroapi" not in names:
                    raise SystemExit(f"ask_neuroapi was not listed. Tools: {', '.join(names)}")

                result = await session.call_tool(
                    "ask_neuroapi",
                    {"prompt": PROMPT, "mode": "smart"},
                    read_timeout_seconds=180,
                )

    if result.is_error:
        raise SystemExit(f"ask_neuroapi failed: {result_text(result)}")

    payload = result.structured_content if isinstance(result.structured_content, dict) else {}
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer:
        answer = result_text(result)
    print(f"\nmode={payload.get('mode')} request_id={payload.get('request_id')}")
    print(answer)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
