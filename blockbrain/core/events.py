"""Signal management, checkpointing, and resume state for blockbrain AI.
Fixes signal trapping bugs and enables reliable task resumption.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import signal
import sys
import threading
from typing import List, Dict, Any, Optional

CHECKPOINT_FILE = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "checkpoint.json"

STOP_EVENT = threading.Event()
_SIGINT_COUNT = 0


def setup_signal_handlers():
    """Register polite-then-forceful SIGINT handler."""
    def handle_sigint(signum, frame):
        global _SIGINT_COUNT
        _SIGINT_COUNT += 1
        if _SIGINT_COUNT == 1:
            print("\n⚠️  [Ctrl+C received] Finishing current step and saving checkpoint... (Press Ctrl+C again to force exit)")
            STOP_EVENT.set()
        else:
            print("\n🚨 [Force Exit] Terminating immediately.")
            sys.exit(130)

    signal.signal(signal.SIGINT, handle_sigint)


def reset_stop_event():
    global _SIGINT_COUNT
    _SIGINT_COUNT = 0
    STOP_EVENT.clear()


def save_checkpoint(conversation: List[Dict[str, Any]], active_task: Optional[str] = None):
    """Save execution state to ~/.config/blockbrain/checkpoint.json."""
    try:
        CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "saved_at": datetime.now().isoformat(),
            "active_task": active_task or "",
            "conversation": conversation[-20:],  # keep last 20 messages
        }
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed to save checkpoint: {e}")


def load_checkpoint() -> Optional[Dict[str, Any]]:
    """Load previous execution state from checkpoint file."""
    if not CHECKPOINT_FILE.exists():
        return None
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load checkpoint: {e}")
        return None


def clear_checkpoint():
    """Remove checkpoint file after successful task completion."""
    if CHECKPOINT_FILE.exists():
        try:
            CHECKPOINT_FILE.unlink()
        except Exception:
            pass

