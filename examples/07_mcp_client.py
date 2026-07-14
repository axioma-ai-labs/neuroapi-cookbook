"""Call the NeuroAPI agent over MCP.

Connects to the remote NeuroAPI MCP server over Streamable HTTP, authenticates
with your X-API-Key, lists the available tools, and runs a single-turn research
question through `ask_neuroapi` -- the same agent, rate limits, metering, and
billing as POST /agent/ask.

To wire NeuroAPI into an AI client (Claude Code, Cursor, VS Code, ...) instead
of calling it from code, see https://neuroapi.neurobro.ai/docs/mcp/clients.
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
# Trailing slash is intentional: it hits the endpoint directly and avoids a
# redirect that some TLS-terminating proxies answer over http, which would
# turn the POST into a GET.
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
    """Join the text blocks of a tool result."""
    blocks = getattr(result, "content", []) or []
    return "\n".join(b.text for b in blocks if getattr(b, "type", None) == "text")


async def main() -> None:
    # The MCP endpoint takes the same X-API-Key header as the REST API.
    headers = {"X-API-Key": require_api_key()}

    async with streamablehttp_client(MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", ", ".join(tool.name for tool in tools.tools))

            result = await session.call_tool(
                "ask_neuroapi",
                {"prompt": PROMPT, "mode": "smart"},
            )
            if result.isError:
                raise SystemExit(f"ask_neuroapi failed: {result_text(result)}")

            # ask_neuroapi returns the same shape as POST /agent/ask; the
            # structured payload carries `answer` and `usage.cost_units`.
            payload = result.structuredContent or {}
            print("\nAnswer\n" + (payload.get("answer") or result_text(result)))
            print("\ncost_units:", payload.get("usage", {}).get("cost_units"))


if __name__ == "__main__":
    asyncio.run(main())
