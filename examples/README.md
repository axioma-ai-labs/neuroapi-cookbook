# Examples

Each file is a complete, runnable recipe. Set `NEUROAPI_KEY` before running any example:

```bash
cp .env.example .env
# edit .env
python3 examples/01_getting_started.py
```

The examples target `https://api.neurobro.ai/api/v1` by default. Set `NEUROAPI_BASE_URL` when testing against staging or a local NeuroAPI server.

## Recipe Map

| File | Use when you need to |
| --- | --- |
| [01_getting_started.py](01_getting_started.py) | Smoke-test auth and make the first sync request. |
| [02_multi_turn_research_chat.py](02_multi_turn_research_chat.py) | Keep a conversation coherent while the server stays stateless. |
| [03_streaming_sse.py](03_streaming_sse.py) | Show long answers incrementally in a terminal or UI. |
| [04_resilient_client.py](04_resilient_client.py) | Put retry, error, and idempotency behavior behind a small client wrapper. |
| [05_structured_market_report.py](05_structured_market_report.py) | Convert natural-language analysis into validated application data. |
| [06_scheduled_signal_to_mt5.py](06_scheduled_signal_to_mt5.py) | Run unattended on a CET schedule, get a schema-validated trade signal, and hand it to a broker placeholder. |
| [07_fast_and_smart.py](07_fast_and_smart.py) | Compare `fast` and `smart` on one prompt. Two `/agent/ask` calls. |
| [08_output_schema.py](08_output_schema.py) | Return a validated object in `output` from a JSON Schema. `stream` is false. |
| [mcp/](mcp/README.md) | Paste the Claude Code, Cursor, or VS Code config. |
| [09_mcp_client.py](09_mcp_client.py) | Call `ask_neuroapi` from Python. `pip install -r mcp/requirements.txt` (Python 3.10+). |

## Production Notes

- `/health` is free and is the right deploy-time smoke test.
- `/agent/ask` defaults to `mode="smart"` and `stream=false`.
- `fast`, `smart`, and `max` trade off capability and `usage.cost_units`; `max` requires Pro or Enterprise access.
- The server does not store chat state for you. Send `message_history` on every follow-up request.
- Retry only `429` and `503` by default. Honor `Retry-After` and cap attempts.
- Use `Idempotency-Key` for sync `/agent/ask` retries representing the same logical operation. Streaming responses are not cached.
- Treat model-formatted JSON as untrusted until your code validates it.
- `output_schema` requires `stream=false`. The validated object is returned in `output` (and `answer` is `null`). `mode="max"` gives provider-enforced conformance; `fast`/`smart` are best-effort with retries.
- `system_prompt` augments the agent; it cannot override its persona or safety guardrails.
- Re-validate structured output locally before acting on it, especially before anything that moves money. Keep real-money side effects opt-in and off by default.
- MCP tool calls are non-streaming. `ask_neuroapi` accepts `prompt`, `mode`, `message_history`, `system_prompt`, and `output_schema`.
- Programmatic MCP clients should use `https://api.neurobro.ai/api/v1/mcp/` (trailing slash). The URL without the slash answers with `307 Location: http://api.neurobro.ai/api/v1/mcp/`.
