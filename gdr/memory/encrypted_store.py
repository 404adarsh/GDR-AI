"""Permanent Encrypted Long-Term Memory Subsystem for GDR AI (Phase 7).
Features:
- Encrypted SQLite storage with key managed via system keyring.
- Categorized memory: pinned facts (verbatim), preferences, people, projects, episodic events, auto-summaries.
- Contradiction handling: old memories marked 'superseded' with full version history.
- Inferred vs verbatim tracking.
- Hybrid search (keyword, semantic tokens, date range filters).
- Export, import, and integrity verification.
"""

import base64
from datetime import datetime, date
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from gdr.safety.secrets import get_secret, set_keyring_secret

MEM_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
ENCRYPTED_DB_PATH = MEM_DIR / "secure_memory.db"
KEYRING_KEY_NAME = "GDR_MEMORY_ENCRYPTION_KEY"


def _get_or_create_encryption_key() -> bytes:
    """Retrieve encryption key from keyring or generate and persist it."""
    stored = get_secret(KEYRING_KEY_NAME)
    if stored:
        return stored.encode("utf-8")

    # Generate new 32-byte urlsafe key
    new_key = Fernet.generate_key().decode("utf-8")
    set_keyring_secret(KEYRING_KEY_NAME, new_key)
    # Also set in env for session
    os.environ[KEYRING_KEY_NAME] = new_key
    return new_key.encode("utf-8")


class EncryptedMemoryStore:
    def __init__(self, db_path: Optional[Path] = None, encryption_key: Optional[bytes] = None):
        self.db_path = db_path or ENCRYPTED_DB_PATH
        self.key = encryption_key or _get_or_create_encryption_key()
        self.cipher = Fernet(self.key)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _encrypt(self, text: str) -> str:
        return self.cipher.encrypt(text.encode("utf-8")).decode("utf-8")

    def _decrypt(self, cipher_text: str) -> str:
        try:
            return self.cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception:
            return "[Decryption Error]"

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,         -- 'pinned_fact', 'preference', 'person', 'project', 'episodic', 'summary'
                subject TEXT NOT NULL,          -- normalized subject/entity/key
                content_encrypted TEXT NOT NULL, -- encrypted verbatim content
                is_inferred INTEGER NOT NULL DEFAULT 0, -- 0 = verbatim user, 1 = model inferred
                status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'superseded', 'deleted'
                superseded_by_id INTEGER,
                event_date TEXT NOT NULL,       -- ISO timestamp of when event/fact relates to
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_subject ON memories(subject);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_status ON memories(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_event_date ON memories(event_date);")
            conn.commit()

    def remember(
        self,
        subject: str,
        content: str,
        category: str = "pinned_fact",
        is_inferred: bool = False,
        event_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Store a new memory. If an active memory with the same subject exists,
        supersede the old memory rather than silently overwriting.
        """
        clean_subj = subject.strip().lower()
        now = datetime.now()
        event_dt = event_date or now
        now_str = now.isoformat()
        event_str = event_dt.isoformat()

        with self._get_conn() as conn:
            cur = conn.cursor()

            # Check if active memory with same subject exists
            cur.execute("""
            SELECT id, content_encrypted FROM memories
            WHERE subject = ? AND status = 'active'
            """, (clean_subj,))
            existing = cur.fetchone()

            old_id = None
            if existing:
                old_id = existing["id"]

            # Insert new memory
            encrypted_val = self._encrypt(content)
            cur.execute("""
            INSERT INTO memories (category, subject, content_encrypted, is_inferred, status, event_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
            """, (category, clean_subj, encrypted_val, 1 if is_inferred else 0, event_str, now_str, now_str))
            new_id = cur.lastrowid

            # Mark old memory as superseded
            if old_id:
                cur.execute("""
                UPDATE memories
                SET status = 'superseded', superseded_by_id = ?, updated_at = ?
                WHERE id = ?
                """, (new_id, now_str, old_id))

            conn.commit()

            return {
                "id": new_id,
                "subject": clean_subj,
                "superseded_old_id": old_id,
                "status": "superseded_old" if old_id else "stored_new"
            }

    def recall(
        self,
        query: str,
        category: Optional[str] = None,
        include_superseded: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Hybrid recall searching decrypted content, normalized subject, and date filters."""
        with self._get_conn() as conn:
            cur = conn.cursor()

            status_cond = "status != 'deleted'" if include_superseded else "status = 'active'"
            sql = f"SELECT * FROM memories WHERE {status_cond}"
            params: List[Any] = []

            if category:
                sql += " AND category = ?"
                params.append(category)

            if start_date:
                sql += " AND event_date >= ?"
                params.append(start_date.isoformat())

            if end_date:
                sql += " AND event_date <= ?"
                params.append(end_date.isoformat())

            sql += " ORDER BY event_date DESC"
            cur.execute(sql, params)
            rows = cur.fetchall()

        # Decrypt and filter/rank matches
        tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) >= 2]
        matches = []

        for r in rows:
            decrypted = self._decrypt(r["content_encrypted"])
            subj = r["subject"]

            # Score relevance
            score = 0
            haystack = (subj + " " + decrypted).lower()
            if query.lower() in haystack:
                score += 10
            for t in tokens:
                if t in haystack:
                    score += 2

            if not tokens or score > 0:
                matches.append({
                    "id": r["id"],
                    "category": r["category"],
                    "subject": subj,
                    "content": decrypted,
                    "is_inferred": bool(r["is_inferred"]),
                    "status": r["status"],
                    "superseded_by_id": r["superseded_by_id"],
                    "event_date": r["event_date"],
                    "created_at": r["created_at"],
                    "score": score
                })

        # Sort by relevance score then date
        matches.sort(key=lambda m: (m["score"], m["event_date"]), reverse=True)
        return matches[:limit]

    def forget(self, memory_id_or_subject: str) -> bool:
        """Mark a memory as deleted."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            if str(memory_id_or_subject).isdigit():
                cur.execute("UPDATE memories SET status = 'deleted' WHERE id = ?", (int(memory_id_or_subject),))
            else:
                cur.execute("UPDATE memories SET status = 'deleted' WHERE subject = ?", (memory_id_or_subject.lower().strip(),))
            conn.commit()
            return cur.rowcount > 0

    def export_data(self) -> Dict[str, Any]:
        """Export all memories as decrypted JSON payload for portability and backup."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM memories ORDER BY id ASC")
            rows = cur.fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "category": r["category"],
                "subject": r["subject"],
                "content": self._decrypt(r["content_encrypted"]),
                "is_inferred": r["is_inferred"],
                "status": r["status"],
                "superseded_by_id": r["superseded_by_id"],
                "event_date": r["event_date"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            })
        return {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "count": len(items),
            "memories": items
        }

    def import_data(self, data: Dict[str, Any]) -> int:
        """Import memories from exported payload."""
        items = data.get("memories", [])
        imported = 0
        with self._get_conn() as conn:
            for item in items:
                enc = self._encrypt(item["content"])
                conn.execute("""
                INSERT OR REPLACE INTO memories (id, category, subject, content_encrypted, is_inferred, status, superseded_by_id, event_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("id"),
                    item.get("category", "pinned_fact"),
                    item.get("subject", ""),
                    enc,
                    item.get("is_inferred", 0),
                    item.get("status", "active"),
                    item.get("superseded_by_id"),
                    item.get("event_date", datetime.now().isoformat()),
                    item.get("created_at", datetime.now().isoformat()),
                    item.get("updated_at", datetime.now().isoformat())
                ))
                imported += 1
            conn.commit()
        return imported

    def verify_integrity(self) -> Tuple[bool, str]:
        """Verify database integrity and decryption of all records."""
        try:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                res = cur.fetchone()[0]
                if res != "ok":
                    return False, f"SQLite integrity check failed: {res}"

                cur.execute("SELECT COUNT(*) FROM memories;")
                total = cur.fetchone()[0]

                cur.execute("SELECT id, content_encrypted FROM memories;")
                for r in cur.fetchall():
                    dec = self._decrypt(r["content_encrypted"])
                    if dec == "[Decryption Error]":
                        return False, f"Decryption failed for memory record #{r['id']}."

            return True, f"Integrity verified. {total} secure records validated."
        except Exception as e:
            return False, f"Verification error: {e}"


_SECURE_STORE = None


def get_secure_memory() -> EncryptedMemoryStore:
    global _SECURE_STORE
    if _SECURE_STORE is None:
        _SECURE_STORE = EncryptedMemoryStore()
    return _SECURE_STORE

