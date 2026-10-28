# MCP setup

NeuroAPI's remote MCP server speaks Streamable HTTP. It exposes one tool, `ask_neuroapi`. Inputs match a non-streaming `POST /agent/ask`: `prompt` (required), plus optional `mode`, `message_history`, `system_prompt`, and `output_schema`.

```text
https://api.neurobro.ai/api/v1/mcp
```

Send the dashboard key in the `X-API-Key` header. Clients that only have a bearer-token field can send `Authorization: Bearer` on this endpoint. The REST API does not accept that header. Do not put the key in the URL.

Copy a file below into the path for that client. Each one reads `NEUROAPI_KEY` from the environment, or prompts for it.

## Claude Code

```bash
claude mcp add --transport http neuroapi https://api.neurobro.ai/api/v1/mcp \
  --header "X-API-Key: $NEUROAPI_KEY"
```

Or save [claude-code.mcp.json](claude-code.mcp.json) as `.mcp.json` at the project root. Claude Code expands `${NEUROAPI_KEY}`.

## Cursor

Copy [cursor.mcp.json](cursor.mcp.json) to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (this project). Cursor expands `${env:NEUROAPI_KEY}`.

## VS Code

Copy [vscode.mcp.json](vscode.mcp.json) to `.vscode/mcp.json`. `type` must be `"http"`. The `inputs` block prompts for the key and stores it in VS Code's secret storage.

Guide: [Connect a client](https://neuroapi.neurobro.ai/docs/mcp/clients).
