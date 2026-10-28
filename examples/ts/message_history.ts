/**
 * Multi-turn POST /agent/ask.
 *
 * The server does not store the conversation. Send prior user and assistant
 * turns in message_history on every follow-up. Roles are "user" and "assistant".
 *
 *   npm install
 *   node --experimental-strip-types message_history.ts
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Turn = {
  role: "user" | "assistant";
  content: string;
};

type AgentAskResponse = {
  answer?: string | null;
  mode: string;
  request_id: string;
};

const PLACEHOLDER_KEY = "neuro_replace_me";

function loadEnvFile(): void {
  const starts = [process.cwd(), dirname(fileURLToPath(import.meta.url))];
  const seen = new Set<string>();
  for (const start of starts) {
    let dir = start;
    for (let depth = 0; depth < 4; depth += 1) {
      const path = resolve(dir, ".env");
      if (!seen.has(path) && existsSync(path)) {
        seen.add(path);
        applyEnvFile(path);
        return;
      }
      const parent = resolve(dir, "..");
      if (parent === dir) break;
      dir = parent;
    }
  }
}

function applyEnvFile(path: string): void {
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

function requireApiKey(): string {
  loadEnvFile();
  const apiKey = process.env.NEUROAPI_KEY;
  if (!apiKey || apiKey === PLACEHOLDER_KEY) {
    throw new Error("Set NEUROAPI_KEY in your environment or .env file.");
  }
  return apiKey;
}

function baseUrl(): string {
  return (process.env.NEUROAPI_BASE_URL ?? "https://api.neurobro.ai/api/v1").replace(/\/$/, "");
}

async function ask(prompt: string, history: Turn[]): Promise<AgentAskResponse> {
  const response = await fetch(`${baseUrl()}/agent/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": requireApiKey(),
    },
    body: JSON.stringify({
      prompt,
      mode: "smart",
      message_history: history,
    }),
    signal: AbortSignal.timeout(90_000),
  });

  const requestId = response.headers.get("x-request-id") ?? "missing";
  if (!response.ok) {
    throw new Error(`NeuroAPI ${response.status} request_id=${requestId}: ${await response.text()}`);
  }

  const data = (await response.json()) as AgentAskResponse;
  if (typeof data.answer !== "string" || data.answer.length === 0) {
    throw new Error(`NeuroAPI returned no answer. request_id=${data.request_id ?? requestId}`);
  }
  console.log(`\nrequest_id=${data.request_id} mode=${data.mode}`);
  console.log(data.answer);
  return data;
}

async function main(): Promise<void> {
  const history: Turn[] = [];
  const firstPrompt = "Compare AAPL and MSFT on FY2024 earnings growth in four bullets.";
  const first = await ask(firstPrompt, history);
  history.push({ role: "user", content: firstPrompt });
  history.push({ role: "assistant", content: first.answer ?? "" });

  await ask("How did their gross margins evolve over the same period?", history);
  console.log(`\nStored history messages: ${history.length}`);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
