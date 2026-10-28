# Pydantic AI

[10_pydantic_ai_mcp.py](../10_pydantic_ai_mcp.py) attaches NeuroAPI to a Pydantic AI agent through `MCPToolset` (Streamable HTTP, `X-API-Key` header). The recipe uses `FunctionModel` to call `ask_neuroapi` once, so the only secret is `NEUROAPI_KEY`.

Requires Python 3.11+.

```bash
pip install -r examples/pydantic_ai/requirements.txt
python3 examples/10_pydantic_ai_mcp.py
```

Pass your own model to `Agent` instead of `FunctionModel` when that model should choose the tool. Keep the same `MCPToolset`.

The client uses the trailing-slash MCP URL. See [examples/mcp/README.md](../mcp/README.md).
