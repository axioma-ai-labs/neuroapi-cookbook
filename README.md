<p align="center">
  <img src="assets/neuroapi-cookbook.png" alt="NeuroAPI Cookbook: REST API for Financial Market Intelligence" width="100%">
</p>

<h1 align="center">NeuroAPI Cookbook</h1>

<p align="center">
  Practical, runnable recipes for building with <a href="https://neuroapi.neurobro.ai/docs">NeuroAPI</a>, Neurobro's API for financial market intelligence.
</p>

<p align="center">
  <a href="https://neuroapi.neurobro.ai/docs"><img src="https://img.shields.io/badge/docs-neuroapi-2ea44f" alt="Docs"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT"></a>
</p>

---

Practical examples for building with [NeuroAPI](https://neuroapi.neurobro.ai/docs), Neurobro's paid public API for finance. The cookbook is intentionally small: each recipe focuses on one production pattern and can be run from a terminal or copied into an application.

NeuroAPI has a compact public surface:

- `GET /api/v1/health` verifies your API key without consuming billable units.
- `POST /api/v1/agent/ask` asks the agent and returns either one JSON response or a Server-Sent Events stream.
- Authentication uses `X-API-Key`, not bearer tokens.
- The caller owns conversation state through `message_history`.
- `system_prompt` layers caller instructions on top of the agent persona; `output_schema` (JSON Schema, sync only) returns a validated object in `output`.
- `usage.cost_units` is the billing contract for successful `/agent/ask` calls.
- The same agent is available as the MCP tool `ask_neuroapi`.

## MCP

Point any MCP client at the remote Streamable HTTP server. One tool is exposed: `ask_neuroapi`. It takes the same fields as a non-streaming `POST /agent/ask` (`prompt`, optional `mode`, `message_history`, `system_prompt`, `output_schema`).

```text
https://api.neurobro.ai/api/v1/mcp
```

Send the dashboard key in the `X-API-Key` header. On this endpoint only, `Authorization: Bearer` is also accepted. Do not put the key in the URL.

| Client | Config |
| --- | --- |
| Claude Code | [examples/mcp/claude-code.mcp.json](examples/mcp/claude-code.mcp.json). Or `claude mcp add --transport http neuroapi https://api.neurobro.ai/api/v1/mcp --header "X-API-Key: $NEUROAPI_KEY"`. |
| Cursor | [examples/mcp/cursor.mcp.json](examples/mcp/cursor.mcp.json) as `~/.cursor/mcp.json` or `.cursor/mcp.json`. |
| VS Code | [examples/mcp/vscode.mcp.json](examples/mcp/vscode.mcp.json) as `.vscode/mcp.json`. |

Notes for those files and the Python client are in [examples/mcp/README.md](examples/mcp/README.md). Guide: [Connect a client](https://neuroapi.neurobro.ai/docs/mcp/clients).

## Start Here

1. Create an API key in the [NeuroAPI dashboard](https://neuroapi.neurobro.ai/).
2. Copy `.env.example` to `.env` and set `NEUROAPI_KEY`.
3. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use `uv`:

```bash
uv sync
```

Run the first example:

```bash
python3 examples/01_getting_started.py
```

## Examples

| Example | What it demonstrates |
| --- | --- |
| [01_getting_started.py](examples/01_getting_started.py) | Verify a key with `/health`, make a sync `/agent/ask` call, inspect `usage` and `X-Request-Id`. |
| [02_multi_turn_research_chat.py](examples/02_multi_turn_research_chat.py) | Build a stateless research chat by resending prior turns with `message_history`. |
| [03_streaming_sse.py](examples/03_streaming_sse.py) | Stream an answer over Server-Sent Events and render answer chunks as they arrive. |
| [04_resilient_client.py](examples/04_resilient_client.py) | Wrap `/agent/ask` with retry handling for `429` and `503`, `Retry-After`, idempotency keys, and structured errors. |
| [05_structured_market_report.py](examples/05_structured_market_report.py) | Ask for constrained JSON and validate the answer with Pydantic before using it downstream. |
| [06_scheduled_signal_to_mt5.py](examples/06_scheduled_signal_to_mt5.py) | Run on a CET schedule, combine `system_prompt` + `output_schema` for a validated trade signal, and gate it into a MetaTrader 5 (Fusion Markets) placeholder. |
| [07_fast_and_smart.py](examples/07_fast_and_smart.py) | Send one prompt to `mode=fast` and `mode=smart`. |
| [08_output_schema.py](examples/08_output_schema.py) | Pass a JSON Schema as `output_schema` and validate `output` with Pydantic. |
| [mcp/](examples/mcp/README.md) | Claude Code, Cursor, and VS Code configs for the remote MCP server. |
| [09_mcp_client.py](examples/09_mcp_client.py) | Call `ask_neuroapi` from the Python MCP SDK. Python 3.10+. |

See [examples/README.md](examples/README.md) for usage notes and extension ideas.

## Configuration

All examples read these environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `NEUROAPI_KEY` | required | Your API key, created in the NeuroAPI dashboard. |
| `NEUROAPI_BASE_URL` | `https://api.neurobro.ai/api/v1` | Override for staging, local development, or tests. |

Never hardcode API keys in notebooks, scripts, issue reports, or commits. The full key is shown only once in the dashboard.

## API References

- [NeuroAPI docs](https://neuroapi.neurobro.ai/docs)
- [Quickstart](https://neuroapi.neurobro.ai/docs/quickstart)
- [Authentication](https://neuroapi.neurobro.ai/docs/guides/authentication)
- [Rate limits](https://neuroapi.neurobro.ai/docs/guides/rate-limits)
- [Billing](https://neuroapi.neurobro.ai/docs/guides/billing)
- [Errors](https://neuroapi.neurobro.ai/docs/guides/errors)
- [API reference](https://neuroapi.neurobro.ai/docs/api)
- [MCP](https://neuroapi.neurobro.ai/docs/mcp)
- [MCP clients](https://neuroapi.neurobro.ai/docs/mcp/clients)

## Cookbook Style

This repo follows the same practical pattern as the major API cookbooks:

- Root README as the navigation map.
- Small, runnable examples instead of framework-heavy demos.
- Environment variables for secrets.
- Clear production notes for state, streaming, retries, cost, and validation.
- Contributions focused on complete recipes that developers can run end to end.

## Related

> [!NOTE]
> Looking for pay-per-call crypto intelligence with automatic USDC micropayments?
> See the companion [x402 API Cookbook](https://github.com/axioma-ai-labs/x402-neurobro), an on-ramp to the broader NeuroAPI platform.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). New examples should be self-contained, finance-relevant, and safe to run with a real API key.

## License

Released under the [MIT License](LICENSE).
