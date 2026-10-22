"""Spending caps, rate-limit handling, and token tracker for blockbrain AI.
Maintains daily expenditure and halts paid calls when spending exceeds limit.
"""

from datetime import datetime, date
import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple

from blockbrain.config import load_config

USAGE_FILE = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "usage.json"

# Approximate costs per 1K tokens / calls (USD)
COSTS = {
    "sarvam-105b-prompt": 0.0002,
    "sarvam-105b-completion": 0.0006,
    "claude-3-5-sonnet": 0.003,
    "twilio-call-minute": 0.015,
}


def _load_usage() -> Dict[str, Any]:
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_usage(data: Dict[str, Any]):
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Usage save failed: {e}")


def record_cost(model_or_service: str, amount_usd: float, tokens: int = 0):
    """Record a spending transaction for today."""
    today = date.today().isoformat()
    data = _load_usage()
    if today not in data:
        data[today] = {"total_usd": 0.0, "tokens": 0, "breakdown": {}}

    day_record = data[today]
    day_record["total_usd"] += amount_usd
    day_record["tokens"] += tokens
    day_record["breakdown"][model_or_service] = day_record["breakdown"].get(model_or_service, 0.0) + amount_usd

    _save_usage(data)


def check_spending_cap() -> Tuple[bool, str]:
    """Check if daily spending cap has been reached. Returns (is_allowed, reason)."""
    cfg = load_config()
    cap = float(cfg.get("safety", {}).get("spending_cap_daily_usd", 5.0))

    today = date.today().isoformat()
    data = _load_usage()
    spent = data.get(today, {}).get("total_usd", 0.0)

    if spent >= cap:
        return False, f"Daily spending cap of ${cap:.2f} reached (currently ${spent:.2f})."
    return True, f"Spent ${spent:.4f} of ${cap:.2f} daily limit."

