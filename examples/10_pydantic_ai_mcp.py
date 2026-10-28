"""Give a Pydantic AI agent the NeuroAPI MCP tool.

MCPToolset connects to the remote Streamable HTTP server and exposes
ask_neuroapi. FunctionModel issues that one tool call and returns the
answer, so this recipe needs only NEUROAPI_KEY.

To let a hosted model decide when to call the tool, pass that model to
Agent instead of FunctionModel and keep the same toolset.

Install on Python 3.11+:

    pip install -r examples/pydantic_ai/requirements.txt
    python3 examples/10_pydantic_ai_mcp.py
"""

from __future__ import annotations

import json
import os

# The library prints an observability banner on the first run. Silence it
# before import so the recipe output is only the tool result.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from fastmcp.exceptions import ToolError
from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
# See examples/09_mcp_client.py: call the trailing-slash URL so the client
# does not follow the https-to-http redirect.
MCP_URL = f"{BASE_URL}/mcp/"
API_KEY = os.getenv("NEUROAPI_KEY")

PROMPT = "What is the macro setup for the euro this week? Answer in four short bullets."


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


def latest_user_text(messages: list[ModelMessage]) -> str:
    for message in reversed(messages):
        for part in getattr(message, "parts", []):
            if not isinstance(part, UserPromptPart):
                continue
            if isinstance(part.content, str):
                return part.content
            texts = [item for item in part.content if isinstance(item, str)]
            if texts:
                return "\n".join(texts)
    raise RuntimeError("The agent run had no user prompt.")


def format_tool_content(content: object) -> str:
    if isinstance(content, dict):
        request_id = content.get("request_id", "missing")
        mode = content.get("mode")
        answer = content.get("answer")
        if isinstance(answer, str) and answer:
            return f"request_id={request_id} mode={mode}\n\n{answer}"
        output = content.get("output")
        if isinstance(output, dict):
            rendered = json.dumps(output, indent=2)
            return f"request_id={request_id} mode={mode}\n\n{rendered}"
    if isinstance(content, str) and content:
        return content
    return json.dumps(content, indent=2, default=str)


def route(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Call ask_neuroapi once, then turn its result into the agent answer."""
    names = [tool.name for tool in info.function_tools]
    if names and "ask_neuroapi" not in names:
        raise RuntimeError(f"ask_neuroapi is not available. Tools: {', '.join(names)}")

    for message in reversed(messages):
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolReturnPart) and part.tool_name == "ask_neuroapi":
                return ModelResponse(parts=[TextPart(format_tool_content(part.content))])

    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="ask_neuroapi",
                args={"prompt": latest_user_text(messages), "mode": "smart"},
            )
        ]
    )


async def main() -> None:
    toolset = MCPToolset(
        MCP_URL,
        headers={"X-API-Key": require_api_key()},
        tool_error_behavior="error",
        id="neuroapi",
    )
    agent = Agent(FunctionModel(route), toolsets=[toolset])

    try:
        async with toolset:
            result = await agent.run(PROMPT)
    except ToolError as exc:
        raise SystemExit(f"ask_neuroapi failed: {exc}") from exc

    print(result.output)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
