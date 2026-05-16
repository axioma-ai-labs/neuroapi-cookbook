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

## Production Notes

- `/health` is free and is the right deploy-time smoke test.
- `/agent/ask` defaults to `mode="smart"` and `stream=false`.
- `fast`, `smart`, and `max` trade off capability and `usage.cost_units`; `max` requires Pro or Enterprise access.
- The server does not store chat state for you. Send `message_history` on every follow-up request.
- Retry only `429` and `503` by default. Honor `Retry-After` and cap attempts.
- Use `Idempotency-Key` for sync `/agent/ask` retries representing the same logical operation. Streaming responses are not cached.
- Treat model-formatted JSON as untrusted until your code validates it.
