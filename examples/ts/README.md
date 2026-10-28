# TypeScript

Two scripts call `POST /agent/ask` with `fetch`. There is no NeuroAPI SDK. Typecheck dependencies live in `package.json`; the scripts have no runtime dependencies.

```bash
cd examples/ts
npm install
npx tsc --noEmit
node --experimental-strip-types agent_ask.ts
node --experimental-strip-types message_history.ts
```

Requires Node 22+. Both scripts read `NEUROAPI_KEY` and optional `NEUROAPI_BASE_URL` from the environment or the repo `.env` file. The default host is `https://api.neurobro.ai/api/v1`. Authentication is the `X-API-Key` header.

| File | What it does |
| --- | --- |
| [agent_ask.ts](agent_ask.ts) | One sync request. `mode` is `smart`. Prints `answer`, `mode`, and `request_id`. |
| [message_history.ts](message_history.ts) | Two turns. The second request sends the first user and assistant messages in `message_history`. |

A non-2xx response throws with the status, `X-Request-Id`, and body. An invalid key returns `401` and `{"detail":"Invalid API key"}`. A missing key returns `401` and `{"detail":"Missing API key"}`.
