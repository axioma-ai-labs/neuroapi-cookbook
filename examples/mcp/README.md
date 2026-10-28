# MCP setup

NeuroAPI's remote MCP server speaks Streamable HTTP. It exposes one tool, `ask_neuroapi`. Arguments match a non-streaming `POST /agent/ask` body: `prompt` (required), plus optional `mode`, `message_history`, `system_prompt`, and `output_schema`.

```text
https://api.neurobro.ai/api/v1/mcp
```

Send the dashboard key on `X-API-Key`. Clients that only have a bearer-token field can send `Authorization: Bearer` on this endpoint. The REST API does not accept that header. Do not put the key in the query string (`400 api_key_in_query`).

The snippets below are the documented project configs. They read `NEUROAPI_KEY` from the environment, or prompt for it. Copy the file into the path noted for that client.

## Claude Code

One command:

```bash
claude mcp add --transport http neuroapi https://api.neurobro.ai/api/v1/mcp \
  --header "X-API-Key: $NEUROAPI_KEY"
```

Or commit [claude-code.mcp.json](claude-code.mcp.json) as `.mcp.json` at the project root. Claude Code expands `${NEUROAPI_KEY}`.

## Cursor

Copy [cursor.mcp.json](cursor.mcp.json) to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (this project). Cursor expands `${env:NEUROAPI_KEY}`.

## VS Code

Copy [vscode.mcp.json](vscode.mcp.json) to `.vscode/mcp.json`. `type` must be `"http"`. The `inputs` block prompts for the key and stores it in VS Code's secret storage.

## Python client

[09_mcp_client.py](../09_mcp_client.py) calls `ask_neuroapi` with the MCP Python SDK (3.10+):

```bash
pip install -r examples/mcp/requirements.txt
python3 examples/09_mcp_client.py
```

Programmatic clients should request `https://api.neurobro.ai/api/v1/mcp/` with the trailing slash. A POST to the URL without the slash returns `307` with `Location: http://api.neurobro.ai/api/v1/mcp/`, and the MCP Python SDK will not follow a redirect that changes `https` to `http`.

Tool calls with a missing or invalid key come back as an MCP tool error whose text includes `HTTP 401` and `Invalid API key` or `Missing API key`. `tools/list` still returns `ask_neuroapi` before that check.

Reference: [Connect a client](https://neuroapi.neurobro.ai/docs/mcp/clients).
