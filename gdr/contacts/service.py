"""Contacts and relationships database service for Aarushi / GDR-AI.
Stores structured contacts, family, friends, colleagues, preferred channels,
and trusted contacts with privacy controls.
"""

from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import Dict, Any, List, Optional

from gdr.config import get_gdr_config_dir

CONTACTS_DIR = get_gdr_config_dir()
CONTACTS_DB_PATH = CONTACTS_DIR / "contacts.db"

def _resolve_contacts_db(path: Optional[Path] = None) -> Path:
    if path:
        return path
    cfg_env = os.environ.get("GDR_CONFIG_DIR")
    if cfg_env:
        return Path(cfg_env) / "contacts.db"
    target = get_gdr_config_dir() / "contacts.db"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            with open(target, "a"):
                pass
        else:
            with open(target, "w"):
                pass
        return target
    except Exception:
        alt = Path("/tmp/gdr/contacts.db")
        alt.parent.mkdir(parents=True, exist_ok=True)
        return alt


VALID_RELATIONSHIPS = [
    "Trusted Family",
    "Family member",
    "Best Friend",
    "Friend",
    "Partner",
    "Colleague",
    "Classmate",
    "Teacher",
    "Professional contact",
    "Enemy / Rival / Untrusted",
    "Acquaintance",
    "Other"
]


class ContactService:
    """Manages friends, family, professional contacts, and enemy/untrusted relations with trust ratings."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = _resolve_contacts_db(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id TEXT NOT NULL DEFAULT 'primary_user',
                display_name TEXT NOT NULL,
                relationship_type TEXT NOT NULL DEFAULT 'Friend',
                category TEXT DEFAULT 'Friend',
                trust_level INTEGER DEFAULT 50, -- 0 to 100% trust level
                email TEXT,
                phone_number TEXT,
                preferred_contact_method TEXT DEFAULT 'any', -- 'email', 'phone', 'whatsapp', 'telegram', 'any'
                preferred_language TEXT DEFAULT 'English',
                timezone TEXT DEFAULT 'Asia/Kolkata',
                notes TEXT DEFAULT '',
                is_trusted_contact INTEGER DEFAULT 0, -- 1 for trusted contact (support/emergencies)
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            # Migration: add trust_level and category to existing databases if missing
            try:
                conn.execute("ALTER TABLE contacts ADD COLUMN trust_level INTEGER DEFAULT 50;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE contacts ADD COLUMN category TEXT DEFAULT 'Friend';")
            except Exception:
                pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_contact_name ON contacts(display_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contact_rel ON contacts(relationship_type);")
            conn.commit()

    def add_contact(
        self,
        display_name: str,
        relationship_type: str = "Friend",
        trust_level: int = 50,
        category: str = "Friend",
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        preferred_contact_method: str = "any",
        preferred_language: str = "English",
        timezone: str = "Asia/Kolkata",
        notes: str = "",
        is_trusted_contact: Optional[bool] = None,
        owner_user_id: str = "primary_user"
    ) -> Dict[str, Any]:
        """Add a new contact to the database with trust rating and relationship safety."""
        now = datetime.now().isoformat()
        rel = relationship_type.strip()
        rel_match = next((r for r in VALID_RELATIONSHIPS if r.lower() == rel.lower()), rel)

        # Enforce trust bounds 0 to 100
        tl = max(0, min(100, int(trust_level)))
        # Enemy relationships have 0% trust by default
        if "enemy" in rel.lower() or "rival" in rel.lower() or "untrusted" in rel.lower():
            if trust_level == 50:  # User didn't customize it
                tl = 0
            is_trusted = False
        elif is_trusted_contact is not None:
            is_trusted = bool(is_trusted_contact)
        else:
            is_trusted = bool(tl >= 80 or "trusted" in rel.lower() or "family" in rel.lower() or "best friend" in rel.lower())

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO contacts (
                owner_user_id, display_name, relationship_type, category,
                trust_level, email, phone_number, preferred_contact_method,
                preferred_language, timezone, notes, is_trusted_contact,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                owner_user_id, display_name.strip(), rel_match,
                category.strip() or rel_match, tl,
                email.strip() if email else None,
                phone_number.strip() if phone_number else None,
                preferred_contact_method.strip(),
                preferred_language.strip(),
                timezone.strip(),
                notes.strip(),
                1 if is_trusted else 0,
                now, now
            ))
            conn.commit()
            contact_id = cur.lastrowid

        return self.get_contact(contact_id)  # type: ignore

    def get_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a contact by ID."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_trusted_contact"] = bool(d["is_trusted_contact"])
            return d

    def search_contacts(
        self,
        query: str = "",
        relationship_type: Optional[str] = None,
        trusted_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search contacts by name, email, phone, or notes."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            conditions = []
            params = []

            if query.strip():
                q = f"%{query.strip().lower()}%"
                conditions.append("(LOWER(display_name) LIKE ? OR LOWER(email) LIKE ? OR phone_number LIKE ? OR LOWER(notes) LIKE ?)")
                params.extend([q, q, q, q])

            if relationship_type:
                conditions.append("LOWER(relationship_type) = ?")
                params.append(relationship_type.strip().lower())

            if trusted_only:
                conditions.append("is_trusted_contact = 1")

            where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(limit)

            sql = f"SELECT * FROM contacts {where_sql} ORDER BY is_trusted_contact DESC, display_name ASC LIMIT ?"
            cur.execute(sql, params)
            results = []
            for r in cur.fetchall():
                d = dict(r)
                d["is_trusted_contact"] = bool(d["is_trusted_contact"])
                results.append(d)
            return results

    def get_contact_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find contact by exact or near name match."""
        res = self.search_contacts(query=name, limit=1)
        return res[0] if res else None

    def get_trusted_contacts(self) -> List[Dict[str, Any]]:
        """Return contacts marked as trusted (e.g. for emergency outreach or emotional check-ins)."""
        return self.search_contacts(trusted_only=True)

    def update_contact(self, contact_id: int, **fields) -> Optional[Dict[str, Any]]:
        """Update allowed fields of a contact."""
        allowed = {
            "display_name", "relationship_type", "category", "trust_level",
            "email", "phone_number", "preferred_contact_method",
            "preferred_language", "timezone", "notes", "is_trusted_contact"
        }
        updates = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                if k == "is_trusted_contact":
                    params.append(1 if v else 0)
                elif k == "trust_level":
                    params.append(max(0, min(100, int(v))))
                else:
                    params.append(v)

        if not updates:
            return self.get_contact(contact_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(contact_id)

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE contacts SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        return self.get_contact(contact_id)

    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact by ID."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_contact_summary_for_prompt(self, limit: int = 50) -> str:
        """Format contacts with trust levels and notes into structured context for AI reasoning."""
        all_contacts = self.search_contacts(limit=limit)
        if not all_contacts:
            return "No contacts recorded yet in your personal network."

        lines = ["USER'S PERSONAL NETWORK & TRUSTED RELATIONS:"]
        for c in all_contacts:
            t_score = c.get("trust_level", 50)
            if t_score >= 80:
                badge = f"⭐ TRUSTED ({t_score}%)"
            elif t_score <= 25:
                badge = f"⚠️ UNTRUSTED / ENEMY ({t_score}%)"
            else:
                badge = f"NEUTRAL ({t_score}%)"

            info = [f"Name: {c['display_name']}", f"Relation: {c['relationship_type']}", f"Trust: {badge}"]
            if c.get("email"):
                info.append(f"Email: {c['email']}")
            if c.get("phone_number"):
                info.append(f"Phone: {c['phone_number']}")
            if c.get("notes"):
                info.append(f"Safety/Notes: {c['notes']}")
            lines.append("• " + " | ".join(info))

        return "\n".join(lines)


_CONTACT_SERVICE = None


def get_contact_service() -> ContactService:
    global _CONTACT_SERVICE
    if _CONTACT_SERVICE is None:
        _CONTACT_SERVICE = ContactService()
    return _CONTACT_SERVICE
