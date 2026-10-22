"""Idempotent event and message deduplication engine for GDR AI.
Guarantees that duplicate webhooks, polling retries, or concurrent handlers
never cause duplicate processing or duplicate replies to the user.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger("gdr.safety.idempotency")

_DEFAULT_EXPIRY_HOURS = 24


class EventDeduplicator:
    """Thread-safe, process-persistent idempotency tracker using SQLite WAL."""

    _instance: Optional["EventDeduplicator"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            candidates = [
                Path(os.environ.get("GDR_DATA_DIR", Path.home() / ".config" / "gdr")),
                Path.home() / ".local" / "share" / "gdr",
                temp_dir / f".gdr_data_{os.getuid() if hasattr(os, 'getuid') else 'user'}",
                temp_dir / ".gdr_data",
            ]
            chosen_dir = None
            for cand in candidates:
                try:
                    cand.mkdir(parents=True, exist_ok=True)
                    test_f = cand / ".test_write"
                    test_f.touch(exist_ok=True)
                    test_f.unlink(missing_ok=True)
                    chosen_dir = cand
                    break
                except Exception:
                    continue
            if chosen_dir is None:
                chosen_dir = Path("/tmp")
            db_path = chosen_dir / "idempotency.db"
        self.db_path = db_path
        self._local_cache: Dict[str, float] = {}  # In-memory fast cache
        self._local_lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS processed_events (
                        channel TEXT NOT NULL,
                        event_id TEXT NOT NULL,
                        payload_hash TEXT,
                        status TEXT NOT NULL,  -- 'processing', 'completed', 'failed'
                        reply_text TEXT,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (channel, event_id)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON processed_events(created_at)")
                # Purge expired entries older than 24h
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=_DEFAULT_EXPIRY_HOURS)).timestamp()
                conn.execute("DELETE FROM processed_events WHERE created_at < ?", (cutoff,))
        except Exception as e:
            logger.debug(f"Idempotency DB init note: {e}")

    def claim_event(self, channel: str, event_id: str, payload: Optional[Any] = None) -> bool:
        """Atomically claim an event for processing.
        Returns:
            True if this event was successfully claimed (first time seen).
            False if this event was already claimed or processed (duplicate delivery).
        """
        if not event_id or not str(event_id).strip():
            # If no event ID is provided, treat as unique to avoid blocking legitimate messages
            return True

        ev_key = f"{channel}:{event_id}"
        now = datetime.now(timezone.utc).timestamp()

        # Fast in-memory check first
        with self._local_lock:
            if ev_key in self._local_cache:
                if now - self._local_cache[ev_key] < (_DEFAULT_EXPIRY_HOURS * 3600):
                    logger.info(f"Duplicate event rejected by fast cache: {ev_key}")
                    return False
            self._local_cache[ev_key] = now

        p_hash = ""
        if payload:
            try:
                raw_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
                p_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
            except Exception:
                pass

        try:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT status FROM processed_events WHERE channel = ? AND event_id = ?",
                    (channel, str(event_id))
                )
                row = cur.fetchone()
                if row:
                    logger.info(f"Duplicate event rejected by persistent DB: channel={channel} id={event_id} status={row[0]}")
                    return False

                cur.execute(
                    "INSERT INTO processed_events (channel, event_id, payload_hash, status, created_at) VALUES (?, ?, ?, 'processing', ?)",
                    (channel, str(event_id), p_hash, now)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            logger.info(f"Duplicate event collision on INSERT: channel={channel} id={event_id}")
            return False
        except Exception as e:
            logger.debug(f"Error checking event idempotency: {e}")
            return True

    def mark_completed(self, channel: str, event_id: str, reply_text: Optional[str] = None):
        """Mark event as completed with optional reply text."""
        if not event_id:
            return
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE processed_events SET status = 'completed', reply_text = ? WHERE channel = ? AND event_id = ?",
                    (reply_text or "", channel, str(event_id))
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Error marking event completed: {e}")

    def get_completed_reply(self, channel: str, event_id: str) -> Optional[str]:
        """Retrieve stored reply if event was already completed."""
        if not event_id:
            return None
        try:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT reply_text FROM processed_events WHERE channel = ? AND event_id = ? AND status = 'completed'",
                    (channel, str(event_id))
                )
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception:
            pass
        return None


_DEDUP: Optional[EventDeduplicator] = None

def get_event_deduplicator() -> EventDeduplicator:
    global _DEDUP
    if _DEDUP is None:
        _DEDUP = EventDeduplicator()
    return _DEDUP

