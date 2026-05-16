# Contributing

Thanks for improving the NeuroAPI Cookbook. The goal is to keep every recipe useful, runnable, and safe for developers using real API keys.

## Recipe Checklist

Before opening a pull request:

- Keep the example focused on one pattern.
- Use `NEUROAPI_KEY` and `NEUROAPI_BASE_URL`; never hardcode secrets.
- Include a short explanation of when to use the pattern.
- Capture or print `X-Request-Id` when requests fail.
- Handle non-2xx responses intentionally.
- Avoid expensive loops or unbounded retries.
- Prefer finance-relevant prompts and outputs.
- Run the file with a real or test key before submitting when possible.

## Local Setup

```bash
uv sync
cp .env.example .env
```

Then set `NEUROAPI_KEY` in `.env`.

If you do not use `uv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Formatting & Linting

The cookbook is formatted and linted with [Ruff](https://docs.astral.sh/ruff/).
Run both before opening a pull request. CI runs the same checks:

```bash
uv run ruff format examples/   # apply formatting
uv run ruff check examples/    # report lint issues (add --fix to auto-fix)
```

Configuration lives in `pyproject.toml` under `[tool.ruff]`.

## Adding an Example

Place new examples in `examples/` with a numbered filename:

```text
examples/06_my_pattern.py
```

Also update:

- `README.md`
- `examples/README.md`

Examples should be self-contained. A developer should be able to read one file and understand the complete flow.

## Security

If you accidentally commit a real API key, revoke it in the dashboard immediately and create a new one. Do not include prompts with customer PII, private trading data, or internal credentials in examples.
