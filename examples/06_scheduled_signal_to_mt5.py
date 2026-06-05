"""Run scheduled trade-signal checks and optionally send them to MetaTrader 5.

The example uses two NeuroAPI request fields:

- system_prompt: adds a fixed trading playbook to every run.
- output_schema: asks the agent for one structured signal object.

The script validates the returned `output` with Pydantic before any MT5 handoff.
It stays in dry-run mode unless MT5_LIVE=1 is set.

Default Europe/Berlin run times:

    08:30  Daily Bias
    12:00  Signal Scan
    16:00  Signal Scan
    20:00  Signal Scan

    # one immediate run, no waiting, dry-run:
    python3 examples/06_scheduled_signal_to_mt5.py --once scan

    # run the scheduler (blocks; Ctrl-C to stop):
    python3 examples/06_scheduled_signal_to_mt5.py

Optional settings:

    SIGNAL_SYMBOL=XAUUSD
    NEUROAPI_MODE=max
    MT5_LIVE=0

Live MT5 settings:

    MT5_LOGIN=<your_mt5_account_id>
    MT5_PASSWORD=<your_mt5_password>
    MT5_SERVER=FusionMarkets-Live
    MT5_VOLUME=0.10
"""

from __future__ import annotations

import argparse
import logging
import os
import time as time_module
from datetime import datetime, time, timedelta
from typing import Any, Literal, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

try:
    from zoneinfo import ZoneInfo
except ImportError as exc:  # pragma: no cover - zoneinfo ships with Python 3.9+
    raise SystemExit("Python 3.9+ with zoneinfo is required.") from exc

load_dotenv()

BASE_URL = os.getenv("NEUROAPI_BASE_URL", "https://api.neurobro.ai/api/v1").rstrip("/")
API_KEY = os.getenv("NEUROAPI_KEY")

DEFAULT_SIGNAL_SYMBOL = "XAUUSD"
DEFAULT_NEUROAPI_MODE = "max"
DEFAULT_MT5_LIVE = "0"
DEFAULT_MT5_VOLUME = "0.10"
MT5_SERVER_PLACEHOLDER = "FusionMarkets-Live"

SYMBOL = os.getenv("SIGNAL_SYMBOL", DEFAULT_SIGNAL_SYMBOL)
MODE = os.getenv("NEUROAPI_MODE", DEFAULT_NEUROAPI_MODE)
MT5_LIVE = os.getenv("MT5_LIVE", DEFAULT_MT5_LIVE) == "1"

TZ = ZoneInfo("Europe/Berlin")
RUN_TIMES: list[tuple[int, int, str]] = [
    (8, 30, "bias"),
    (12, 0, "scan"),
    (16, 0, "scan"),
    (20, 0, "scan"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S%z",
)
log = logging.getLogger("signal-bot")


def require_api_key() -> str:
    if not API_KEY or API_KEY == "neuro_replace_me":
        raise SystemExit("Set NEUROAPI_KEY in your environment or .env file.")
    return API_KEY


PLAYBOOK = """
You are an intraday trading assistant for liquid CFDs. Use these rules:

- Trade only with a clear higher-timeframe trend. Otherwise return DIRECTION=FLAT.
- Risk:reward to TP1 must be at least 1.5:1.
- CONFLUENCE_SCORE is 0-100.
- Set PASSES_PLAYBOOK=true only when CONFLUENCE_SCORE >= 65 and the setup agrees.
- For LONG: SL < ENTRY_IDEAL < TP1 < TP2. For SHORT: SL > ENTRY_IDEAL > TP1 > TP2.
- For FLAT: ENTRY_IDEAL, SL, TP1, and TP2 must all be null.
- Use FINAL_INSTRUCTION=EXECUTE only when PASSES_PLAYBOOK=true and entry is valid now.
- Use WAIT for a forming setup and SKIP when there is no edge.
- For Daily Bias, prefer WAIT unless price is already at a clean entry.
- Be conservative. A missed trade is cheaper than a bad one.
""".strip()

PRICE_OR_NULL_SCHEMA: dict[str, Any] = {
    "type": ["number", "null"],
    "description": "Numeric for LONG/SHORT signals; null when DIRECTION is FLAT.",
}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "DIRECTION": {"type": "string", "enum": ["LONG", "SHORT", "FLAT"]},
        "ENTRY_IDEAL": PRICE_OR_NULL_SCHEMA,
        "SL": PRICE_OR_NULL_SCHEMA,
        "TP1": PRICE_OR_NULL_SCHEMA,
        "TP2": PRICE_OR_NULL_SCHEMA,
        "CONFLUENCE_SCORE": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "0-100 strength of the confluence behind the idea.",
        },
        "PASSES_PLAYBOOK": {"type": "boolean"},
        "FINAL_INSTRUCTION": {"type": "string", "enum": ["EXECUTE", "WAIT", "SKIP"]},
    },
    "required": [
        "DIRECTION",
        "ENTRY_IDEAL",
        "SL",
        "TP1",
        "TP2",
        "CONFLUENCE_SCORE",
        "PASSES_PLAYBOOK",
        "FINAL_INSTRUCTION",
    ],
    "additionalProperties": False,
}


class TradeSignal(BaseModel):
    """Validated signal returned by NeuroAPI."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    direction: Literal["LONG", "SHORT", "FLAT"] = Field(alias="DIRECTION")
    entry_ideal: Optional[float] = Field(alias="ENTRY_IDEAL")  # noqa: UP045
    sl: Optional[float] = Field(alias="SL")  # noqa: UP045
    tp1: Optional[float] = Field(alias="TP1")  # noqa: UP045
    tp2: Optional[float] = Field(alias="TP2")  # noqa: UP045
    confluence_score: int = Field(alias="CONFLUENCE_SCORE", ge=0, le=100)
    passes_playbook: bool = Field(alias="PASSES_PLAYBOOK")
    final_instruction: Literal["EXECUTE", "WAIT", "SKIP"] = Field(alias="FINAL_INSTRUCTION")

    @model_validator(mode="after")
    def _check_level_geometry(self) -> TradeSignal:
        """Check level order and execution requirements."""
        levels = (self.entry_ideal, self.sl, self.tp1, self.tp2)

        if self.direction == "FLAT":
            if any(level is not None for level in levels):
                raise ValueError("FLAT requires ENTRY_IDEAL, SL, TP1, and TP2 to be null.")
            if self.passes_playbook:
                raise ValueError("FLAT cannot pass the playbook.")
            if self.final_instruction == "EXECUTE":
                raise ValueError("FLAT cannot have FINAL_INSTRUCTION=EXECUTE.")
            return self

        if any(level is None for level in levels):
            raise ValueError("LONG/SHORT signals require numeric ENTRY_IDEAL, SL, TP1, and TP2.")

        entry_ideal = self.entry_ideal
        sl = self.sl
        tp1 = self.tp1
        tp2 = self.tp2

        if self.direction == "LONG" and not (sl < entry_ideal < tp1 < tp2):
            raise ValueError("LONG requires SL < ENTRY_IDEAL < TP1 < TP2.")
        if self.direction == "SHORT" and not (sl > entry_ideal > tp1 > tp2):
            raise ValueError("SHORT requires SL > ENTRY_IDEAL > TP1 > TP2.")

        if self.passes_playbook and self.confluence_score < 65:
            raise ValueError("PASSES_PLAYBOOK=true requires CONFLUENCE_SCORE >= 65.")
        if self.final_instruction == "EXECUTE" and not self.passes_playbook:
            raise ValueError("EXECUTE requires PASSES_PLAYBOOK=true.")

        if self.passes_playbook or self.final_instruction == "EXECUTE":
            risk = abs(entry_ideal - sl)
            reward = abs(tp1 - entry_ideal)
            if risk == 0 or reward / risk < 1.5:
                raise ValueError("Playbook-passing signals require at least 1.5:1 to TP1.")
        return self


def build_prompt(kind: str, symbol: str) -> str:
    if kind == "bias":
        return (
            f"Daily Bias for {symbol}. Read the higher-timeframe structure and momentum "
            f"for the session ahead. Return the playbook signal object."
        )
    return (
        f"Signal Scan for {symbol}. Look for an actionable intraday entry now. "
        f"Return DIRECTION=FLAT with null price levels when there is no clean setup."
    )


def ask_structured(
    client: httpx.Client,
    prompt: str,
    *,
    max_attempts: int = 3,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Call /agent/ask and return the structured output."""
    body = {
        "prompt": prompt,
        "mode": MODE,
        "stream": False,
        "system_prompt": PLAYBOOK,
        "output_schema": OUTPUT_SCHEMA,
    }

    for attempt in range(max_attempts):
        response = client.post("/agent/ask", json=body)
        request_id = response.headers.get("x-request-id", "missing")

        if response.status_code in (429, 503) and attempt < max_attempts - 1:
            retry_after = response.headers.get("retry-after")
            delay = float(retry_after) if retry_after else float(2**attempt)
            log.warning("Throttled (%s); retrying in %.1fs", response.status_code, delay)
            time_module.sleep(delay)
            continue

        response.raise_for_status()
        data = response.json()
        output = data.get("output")
        if output is None:
            raise RuntimeError(f"No structured output returned. request_id={request_id}")
        return output, data.get("request_id", request_id), data.get("usage", {})

    raise RuntimeError("Retry loop exited unexpectedly.")


def place_trade_mt5(signal: TradeSignal, symbol: str) -> None:
    """Send an executable signal to MT5, or log the dry-run order."""
    actionable = (
        signal.passes_playbook
        and signal.final_instruction == "EXECUTE"
        and signal.direction in ("LONG", "SHORT")
    )
    if not actionable:
        log.info(
            "No order: direction=%s passes_playbook=%s instruction=%s",
            signal.direction,
            signal.passes_playbook,
            signal.final_instruction,
        )
        return

    order = {
        "symbol": symbol,
        "side": signal.direction,
        "entry": signal.entry_ideal,
        "sl": signal.sl,
        "tp1": signal.tp1,
        "tp2": signal.tp2,
    }

    if not MT5_LIVE:
        log.info("[DRY-RUN] Would send MT5 order: %s (set MT5_LIVE=1 to arm)", order)
        return

    if None in (signal.entry_ideal, signal.sl, signal.tp1):
        raise RuntimeError("Validated directional signal is missing entry, SL, or TP1.")

    login_raw = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")
    if not login_raw or not password or not server:
        raise RuntimeError(
            "Set MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER before MT5_LIVE=1 "
            f"(server example: {MT5_SERVER_PLACEHOLDER})."
        )

    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError(
            "Install the MetaTrader5 package on a supported Windows MT5 host before "
            "setting MT5_LIVE=1."
        ) from exc

    try:
        login = int(login_raw)
    except ValueError as exc:
        raise RuntimeError("MT5_LOGIN must be an integer account id.") from exc

    try:
        volume = float(os.getenv("MT5_VOLUME", DEFAULT_MT5_VOLUME))
    except ValueError as exc:
        raise RuntimeError("MT5_VOLUME must be numeric.") from exc
    if volume <= 0:
        raise RuntimeError("MT5_VOLUME must be greater than zero.")

    if not mt5.initialize(login=login, password=password, server=server):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise RuntimeError(f"MT5 symbol not found: {symbol}")
        if not symbol_info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 could not select symbol: {symbol}")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"MT5 has no current tick for symbol: {symbol}")

        order_type = mt5.ORDER_TYPE_BUY if signal.direction == "LONG" else mt5.ORDER_TYPE_SELL
        price = tick.ask if signal.direction == "LONG" else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": signal.sl,
            "tp": signal.tp1,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": "neuroapi-signal",
        }
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"MT5 order_send failed: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 order rejected: {result.retcode} {result.comment}")
        log.info("MT5 order filled: ticket=%s", result.order)
    finally:
        mt5.shutdown()


def run_scan(client: httpx.Client, kind: str) -> None:
    label = "Daily Bias" if kind == "bias" else "Signal Scan"
    log.info("%s for %s (mode=%s)", label, SYMBOL, MODE)

    try:
        output, request_id, usage = ask_structured(client, build_prompt(kind, SYMBOL))
    except (httpx.HTTPError, RuntimeError) as exc:
        log.error("NeuroAPI request failed: %s", exc)
        return

    try:
        signal = TradeSignal.model_validate(output)
    except ValidationError as exc:
        log.error("Signal failed validation; not trading. request_id=%s\n%s", request_id, exc)
        return

    log.info(
        "request_id=%s cost_units=%s signal=%s",
        request_id,
        usage.get("cost_units"),
        signal.model_dump(by_alias=True),
    )
    place_trade_mt5(signal, SYMBOL)


def seconds_until_next_run(now: datetime) -> tuple[datetime, str]:
    """Return the next scheduled run."""
    candidates: list[tuple[datetime, str]] = []
    for day_offset in (0, 1):
        day = (now + timedelta(days=day_offset)).date()
        for hour, minute, kind in RUN_TIMES:
            run_at = datetime.combine(day, time(hour, minute), tzinfo=TZ)
            if run_at > now:
                candidates.append((run_at, kind))
    return min(candidates, key=lambda c: c[0])


def run_scheduler(client: httpx.Client) -> None:
    log.info(
        "Scheduler started for %s. Runs at %s Europe/Berlin. live=%s",
        SYMBOL,
        ", ".join(f"{h:02d}:{m:02d}" for h, m, _ in RUN_TIMES),
        MT5_LIVE,
    )
    while True:
        now = datetime.now(TZ)
        run_at, kind = seconds_until_next_run(now)
        delay = (run_at - now).total_seconds()
        log.info("Next run: %s (%s) in %.0fs", run_at.isoformat(), kind, delay)
        time_module.sleep(delay)
        run_scan(client, kind)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        choices=["bias", "scan"],
        help="Run a single bias/scan immediately and exit, instead of scheduling.",
    )
    args = parser.parse_args()

    headers = {"X-API-Key": require_api_key()}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=120.0) as client:
        if args.once:
            run_scan(client, args.once)
        else:
            run_scheduler(client)


if __name__ == "__main__":
    main()
