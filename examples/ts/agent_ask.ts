/**
 * Sync POST /agent/ask.
 *
 *   npm install
 *   node --experimental-strip-types agent_ask.ts
 *
 * Requires Node 22+. Reads NEUROAPI_KEY and optional NEUROAPI_BASE_URL from
 * the environment or the cookbook .env file.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Usage = {
  prompt_tokens?: number;
  completion_tokens?: number;
  cached_tokens?: number;
  cost_units: number;
};

type AgentAskResponse = {
  answer?: string | null;
  output?: Record<string, unknown> | null;
  mode: string;
  request_id: string;
  usage: Usage;
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

async function main(): Promise<void> {
  const response = await fetch(`${baseUrl()}/agent/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": requireApiKey(),
    },
    body: JSON.stringify({
      prompt: "Summarise the latest macroeconomic outlook for the eurozone.",
      mode: "smart",
    }),
    signal: AbortSignal.timeout(60_000),
  });

  const requestId = response.headers.get("x-request-id") ?? "missing";
  if (!response.ok) {
    throw new Error(`NeuroAPI ${response.status} request_id=${requestId}: ${await response.text()}`);
  }

  const data = (await response.json()) as AgentAskResponse;
  if (typeof data.answer !== "string" || data.answer.length === 0) {
    throw new Error(`NeuroAPI returned no answer. request_id=${data.request_id ?? requestId}`);
  }

  console.log(`mode=${data.mode} request_id=${data.request_id}`);
  console.log(data.answer);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
