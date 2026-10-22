"""Long-term memory subsystem for GDR AI.
Stores user preferences, personal context, project memory, people & relationships,
episodic memories, and temporary notes with relevance retrieval and deduplication.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import List, Dict, Any, Optional

from gdr.tools.registry import tool
from gdr.config import get_gdr_config_dir

MEM_DIR = get_gdr_config_dir()
MEM_DB_PATH = MEM_DIR / "memory.db"


def _resolve_mem_db(path: Optional[Path] = None) -> Path:
    if path:
        return path
    cfg_env = os.environ.get("GDR_CONFIG_DIR")
    if cfg_env:
        return Path(cfg_env) / "memory.db"
    target = get_gdr_config_dir() / "memory.db"
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
        alt = Path("/tmp/gdr/memory.db")
        alt.parent.mkdir(parents=True, exist_ok=True)
        return alt



CATEGORY_MAPPING = {
    "preference": "user_preferences",
    "preferences": "user_preferences",
    "user_preference": "user_preferences",
    "user_preferences": "user_preferences",
    "fact": "personal_context",
    "facts": "personal_context",
    "personal": "personal_context",
    "personal_context": "personal_context",
    "profile": "personal_profile",
    "personal_profile": "personal_profile",
    "project": "project_memory",
    "projects": "project_memory",
    "project_memory": "project_memory",
    "person": "people_relationships",
    "people": "people_relationships",
    "people_relationships": "people_relationships",
    "relationships": "people_relationships",
    "episodic": "episodic",
    "episodic_memory": "episodic_memory",
    "event": "episodic",
    "procedure": "procedural_memory",
    "procedural": "procedural_memory",
    "procedural_memory": "procedural_memory",
    "workflow": "procedural_memory",
    "workflows": "procedural_memory",
    "temporary": "temporary",
    "temp": "temporary",
    "session": "temporary",
    "persona": "user_preferences",
    "style": "user_preferences",
}

CANONICAL_CATEGORIES = [
    "user_preferences",
    "personal_context",
    "project_memory",
    "people_relationships",
    "episodic",
    "temporary",
]

ALL_CATEGORIES = CANONICAL_CATEGORIES + [
    "personal_profile",
    "episodic_memory",
    "procedural_memory",
]


def normalize_category(cat: str) -> str:
    """Normalize input category to one of the canonical/extended categories."""
    clean = (cat or "").strip().lower()
    if clean in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[clean]
    if clean in ALL_CATEGORIES:
        return clean
    return "personal_context"


# Sensitive credentials patterns that MUST NEVER be saved into ordinary memory
SENSITIVE_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{25,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"(?:password|passwd|api_key|token)\s*[:=]\s*['\"]?[a-zA-Z0-9!@#$%^&*()_+=\-`~]{8,}['\"]?", re.IGNORECASE),
    re.compile(r"\b\d{8,11}:[A-Za-z0-9_-]{32,}\b"),  # Telegram bot token
]


def contains_sensitive_credentials(text: str) -> bool:
    """Check if the given text contains private keys, API secrets, or passwords."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in SENSITIVE_SECRET_PATTERNS)



class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._shared_conn = None
        if db_path and str(db_path) == ":memory:":
            self.db_path = Path(":memory:")
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self.db_path = _resolve_mem_db(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 3,
                    confidence REAL DEFAULT 1.0,
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """)
                # Automatic column migrations for existing databases
                for col, defn in [
                    ("importance", "INTEGER DEFAULT 3"),
                    ("confidence", "REAL DEFAULT 1.0"),
                    ("expires_at", "TEXT"),
                    ("source_type", "TEXT DEFAULT 'explicit_fact'"),
                    ("project_path", "TEXT"),
                    ("superseded_by", "INTEGER"),
                    ("quality_score", "REAL DEFAULT 1.0"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE memories ADD COLUMN {col} {defn};")
                    except Exception:
                        pass

                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_cat ON memories(category);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(key);")

                # Persistent Conversation History
                conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    engine_info TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conversation_history(session_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_created ON conversation_history(created_at);")

                conn.commit()
        except Exception:
            pass

    def save_chat_message(
        self,
        role: str,
        content: str,
        session_id: str = "default",
        engine_info: Optional[Dict[str, Any]] = None
    ) -> int:
        """Persist a conversation message into database."""
        now_str = datetime.now().isoformat()
        eng_json = json.dumps(engine_info or {})
        try:
            with self._get_conn() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO conversation_history (session_id, role, content, engine_info, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, role, content, eng_json, now_str)
                )
                conn.commit()
                return cur.lastrowid
        except Exception:
            return -1

    def get_chat_history(self, session_id: str = "default", limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent chronological conversation history."""
        try:
            with self._get_conn() as conn:
                cur = conn.execute(
                    """
                    SELECT id, session_id, role, content, engine_info, created_at
                    FROM conversation_history
                    WHERE session_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (session_id, limit)
                )
                rows = cur.fetchall()
                out = []
                for r in rows:
                    try:
                        einfo = json.loads(r["engine_info"]) if r["engine_info"] else {}
                    except Exception:
                        einfo = {}
                    out.append({
                        "id": r["id"],
                        "session_id": r["session_id"],
                        "role": r["role"],
                        "content": r["content"],
                        "engine_info": einfo,
                        "created_at": r["created_at"]
                    })
                return out
        except Exception:
            return []

    def clear_chat_history(self, session_id: Optional[str] = None) -> int:
        """Clear conversation history, optionally for a specific session."""
        try:
            with self._get_conn() as conn:
                if session_id:
                    cur = conn.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))
                else:
                    cur = conn.execute("DELETE FROM conversation_history")
                conn.commit()
                return cur.rowcount
        except Exception:
            return 0


    def remember(
        self,
        key: str,
        content: str,
        category: str = "fact",
        importance: int = 3,
        confidence: float = 1.0,
        expires_at: Optional[str] = None,
        source_type: str = "explicit_fact",
        project_path: Optional[str] = None,
        quality_score: float = 1.0
    ) -> str:
        """Store or update a memory with category normalization, credential filtering, and metadata."""
        # 1. Security Check: Never store credentials in ordinary memory
        if contains_sensitive_credentials(content) or contains_sensitive_credentials(key):
            return "Security violation: Credentials or private tokens cannot be saved in ordinary memory. Use secure vault storage."

        now_str = datetime.now().isoformat()
        norm_cat = normalize_category(category)
        clean_key = key.lower().strip()

        try:
            with self._get_conn() as conn:
                # Check for existing memory with this key to track superseding/updates
                cur = conn.cursor()
                cur.execute("SELECT id, content FROM memories WHERE key = ?", (clean_key,))
                existing = cur.fetchone()

                if existing:
                    old_id = existing["id"]
                    # Update existing record and update quality/source
                    conn.execute("""
                    UPDATE memories SET
                        content = ?,
                        category = ?,
                        importance = ?,
                        confidence = ?,
                        expires_at = ?,
                        source_type = ?,
                        project_path = COALESCE(?, project_path),
                        quality_score = ?,
                        updated_at = ?
                    WHERE id = ?
                    """, (
                        content.strip(),
                        norm_cat,
                        importance,
                        confidence,
                        expires_at,
                        source_type,
                        project_path,
                        quality_score,
                        now_str,
                        old_id
                    ))
                else:
                    conn.execute("""
                    INSERT INTO memories (category, key, content, importance, confidence, expires_at, source_type, project_path, quality_score, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        norm_cat,
                        clean_key,
                        content.strip(),
                        importance,
                        confidence,
                        expires_at,
                        source_type,
                        project_path,
                        quality_score,
                        now_str,
                        now_str
                    ))
                conn.commit()
        except Exception as e:
            return f"Could not store memory: {e}"
        return f"Stored memory for '{clean_key}' in category '{norm_cat}'."

    def recall(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recall memories matching query or category, filtering out expired items."""
        now_str = datetime.now().isoformat()
        terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]

        with self._get_conn() as conn:
            cur = conn.cursor()
            conditions = ["(expires_at IS NULL OR expires_at > ?)"]
            params: List[Any] = [now_str]

            if category:
                conditions.append("category = ?")
                params.append(normalize_category(category))

            if terms:
                term_clauses = " OR ".join(["key LIKE ? OR content LIKE ?" for _ in terms])
                conditions.append(f"({term_clauses})")
                for t in terms:
                    params.extend([f"%{t}%", f"%{t}%"])

            where_sql = f"WHERE {' AND '.join(conditions)}"
            params.append(limit)

            sql = f"SELECT * FROM memories {where_sql} ORDER BY importance DESC, updated_at DESC LIMIT ?"
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def forget(self, key: str) -> bool:
        """Delete memory by exact key."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE key = ?", (key.lower().strip(),))
            conn.commit()
            return cur.rowcount > 0

    def delete(self, category: str, key: str) -> bool:
        """Delete memory by category and key for backwards compatibility."""
        norm_cat = normalize_category(category)
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE (category = ? OR category = ?) AND key = ?", (category, norm_cat, key.lower().strip()))
            conn.commit()
            if cur.rowcount > 0:
                return True
            # Fallback to key only
            return self.forget(key)

    def delete_by_id(self, memory_id: int) -> bool:
        """Delete memory by database ID."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cur.rowcount > 0

    def list_all(self, include_expired: bool = False) -> List[Dict[str, Any]]:
        """List all memories ordered by category and key."""
        now_str = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            if include_expired:
                cur.execute("SELECT * FROM memories ORDER BY category, key ASC")
            else:
                cur.execute("SELECT * FROM memories WHERE (expires_at IS NULL OR expires_at > ?) ORDER BY category, key ASC", (now_str,))
            return [dict(r) for r in cur.fetchall()]

    def list_by_category(self, category: str) -> List[Dict[str, Any]]:
        """List all memories for a specific canonical category."""
        norm_cat = normalize_category(category)
        now_str = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM memories WHERE category = ? AND (expires_at IS NULL OR expires_at > ?) ORDER BY updated_at DESC",
                (norm_cat, now_str)
            )
            return [dict(r) for r in cur.fetchall()]

    def save_personal_profile(self, key: str, content: str, source_type: str = "user_confirmed") -> str:
        """Save a long-term personal profile fact (name, style, interests, goals)."""
        return self.remember(
            key=f"profile_{key}",
            content=content,
            category="personal_profile",
            importance=5,
            confidence=1.0,
            source_type=source_type,
            quality_score=1.0
        )

    def get_personal_profile(self) -> Dict[str, Any]:
        """Retrieve all active personal profile facts."""
        items = self.list_by_category("personal_profile")
        profile: Dict[str, Any] = {}
        for it in items:
            clean_key = it["key"].replace("profile_", "")
            profile[clean_key] = it["content"]
        return profile

    def save_project_context(
        self,
        project_name: str,
        purpose: str = "",
        tech_stack: str = "",
        state: str = "",
        completed_features: Optional[List[str]] = None,
        bugs: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None,
        blockers: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        project_path: Optional[str] = None
    ) -> str:
        """Save structured lifelong memory for a project."""
        p_name_clean = project_name.strip().lower()
        data = {
            "name": project_name.strip(),
            "purpose": purpose,
            "tech_stack": tech_stack,
            "state": state,
            "completed_features": completed_features or [],
            "known_bugs": bugs or [],
            "decisions": decisions or [],
            "blockers": blockers or [],
            "next_steps": next_steps or [],
            "project_path": project_path or "",
            "last_updated": datetime.now().isoformat()
        }
        json_blob = json.dumps(data)
        return self.remember(
            key=f"proj_{p_name_clean}",
            content=json_blob,
            category="project_memory",
            importance=4,
            source_type="user_confirmed",
            project_path=project_path,
            quality_score=1.0
        )

    def get_project_context(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve verified current context and state for a project."""
        clean_key = f"proj_{project_name.strip().lower()}"
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM memories WHERE key = ? AND category = 'project_memory'", (clean_key,))
            row = cur.fetchone()
            if row:
                try:
                    return json.loads(row["content"])
                except Exception:
                    return {"name": project_name, "raw_content": row["content"]}
        return None

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all tracked projects in project_memory."""
        items = self.list_by_category("project_memory")
        projects = []
        for it in items:
            try:
                projects.append(json.loads(it["content"]))
            except Exception:
                projects.append({"key": it["key"], "content": it["content"]})
        return projects

    def save_procedure(
        self,
        workflow_name: str,
        steps: List[str],
        commands: Optional[List[str]] = None,
        context: str = ""
    ) -> str:
        """Store verified procedural memory for a workflow or recurring task."""
        clean_name = workflow_name.strip().lower().replace(" ", "_")
        data = {
            "workflow": workflow_name.strip(),
            "steps": steps,
            "commands": commands or [],
            "context": context,
            "verified": True,
            "updated_at": datetime.now().isoformat()
        }
        return self.remember(
            key=f"proc_{clean_name}",
            content=json.dumps(data),
            category="procedural_memory",
            importance=4,
            source_type="user_confirmed"
        )

    def get_procedure(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored procedural workflow by name."""
        clean_key = f"proc_{workflow_name.strip().lower().replace(' ', '_')}"
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM memories WHERE key = ?", (clean_key,))
            row = cur.fetchone()
            if row:
                try:
                    return json.loads(row["content"])
                except Exception:
                    return {"raw": row["content"]}
        return None

    def resolve_contradiction(self, key: str, new_content: str, reason: str = "User updated fact") -> str:
        """Resolve a conflicting fact by updating content and preserving lineage."""
        clean_key = key.lower().strip()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, content FROM memories WHERE key = ?", (clean_key,))
            row = cur.fetchone()
            if row:
                old_id = row["id"]
                now_str = datetime.now().isoformat()
                conn.execute("""
                UPDATE memories SET
                    content = ?,
                    source_type = 'user_confirmed',
                    updated_at = ?
                WHERE id = ?
                """, (new_content.strip(), now_str, old_id))
                conn.commit()
                return f"Resolved contradiction for '{clean_key}': updated fact (reason: {reason})."
        return self.remember(key, new_content, source_type="user_confirmed")

    def export_memories(self, export_format: str = "json") -> str:
        """Export all memories as JSON for inspection or backup."""
        all_mems = self.list_all(include_expired=True)
        if export_format.lower() == "json":
            return json.dumps(all_mems, indent=2, default=str)
        # Default text dump
        lines = [f"[{m.get('category')}] {m.get('key')}: {m.get('content')}" for m in all_mems]
        return "\n".join(lines)


    def auto_learn_from_user(self, text: str) -> List[Dict[str, str]]:
        """Automatically extracts facts, preferences, styles, and context from conversation."""
        if not text or len(text.strip()) < 3:
            return []

        learned = []
        low = text.lower().strip()

        uname = os.environ.get("USER_NAME", "User")
        aname = os.environ.get("ASSISTANT_NAME", "Aarushi")

        # 1. Persona confirmation / Assistant role:
        if any(k in low for k in [
            "you are my child", "like my child", "child learning from me", "mera baccha",
            "learn from me like a child", "child", "you are my assistant", "act as aarushi",
            "be my companion", "naam aarushi", "your name is aarushi"
        ]):
            self.remember(
                key="relationship_role",
                content=f"{aname} is {uname}'s context-aware, emotionally intelligent personal assistant and companion.",
                category="user_preferences",
                importance=5
            )
            learned.append({"key": "relationship_role", "content": f"{aname} personal assistant and companion."})

        # 2. Name / Identity:
        m = re.search(r"(?:my name is|call me|i am called|naam hai mera|mera naam)\s+([a-zA-Z\u0900-\u097F]+)", low)
        if m:
            name = m.group(1).capitalize()
            self.remember(key="user_name", content=f"Creator's name is {name}.", category="personal_context", importance=5)
            learned.append({"key": "user_name", "content": f"User's name is {name}"})

        # 3. Profession / Role:
        m = re.search(r"(?:i am an?|i work as an?|i do|mera kaam|main ek)\s+([a-zA-Z0-9\s\-]+?)(?:\.|\band\b|\bwith\b|\bfor\b|$)", low)
        if m and any(w in m.group(1) for w in ["developer", "engineer", "researcher", "student", "hacker", "designer", "coder", "analyst", "founder", "manager"]):
            role = m.group(1).strip()
            self.remember(key="profession", content=f"Works as: {role}.", category="personal_context", importance=4)
            learned.append({"key": "profession", "content": role})

        # 4. Likes & Preferences:
        m = re.search(r"(?:i love|i really like|i like|i prefer|mujhe pasand hai|mujhe accha lagta hai)\s+([^,\.\?!]+)", low)
        m_hi = re.search(r"(?:mujhe|humein)\s+([^,\.\?!]+?)\s+(?:pasand hai|bahut pasand|acchi? lagti? hai)", low)
        item = None
        if m:
            item = m.group(1).strip()
        elif m_hi:
            item = m_hi.group(1).strip()

        if item and len(item) > 2 and item not in ("you", "it", "that", "this", "listening", "speaking", "to", "the"):
            key = f"likes_{re.sub(r'[^a-z0-9]', '_', item[:20]).strip('_')}"
            self.remember(key=key, content=f"Loves/prefers: {item}.", category="user_preferences", importance=3)
            learned.append({"key": key, "content": item})

        # 5. Dislikes:
        m = re.search(r"(?:i hate|i dislike|i don't like|i do not like|mujhe pasand nahi|mujhe bura lagta hai)\s+([^,\.\?!]+)", low)
        m_hi_dis = re.search(r"(?:mujhe|humein)\s+([^,\.\?!]+?)\s+(?:pasand nahi|buri? lagti? hai)", low)
        item_dis = None
        if m:
            item_dis = m.group(1).strip()
        elif m_hi_dis:
            item_dis = m_hi_dis.group(1).strip()

        if item_dis and len(item_dis) > 2 and item_dis not in ("you", "it", "that", "this"):
            key = f"dislikes_{re.sub(r'[^a-z0-9]', '_', item_dis[:20]).strip('_')}"
            self.remember(key=key, content=f"Dislikes: {item_dis}.", category="user_preferences", importance=3)
            learned.append({"key": key, "content": item_dis})

        # 6. Explicit instructions to remember:
        m = re.search(r"(?:remember that|always remember|don't forget that|yaad rakhna ki|yaad rakh)\s+([^,\.\?!]+)", low)
        if m:
            fact = m.group(1).strip()
            if fact:
                key = f"fact_{re.sub(r'[^a-z0-9]', '_', fact[:20]).strip('_')}"
                self.remember(key=key, content=f"Remembered fact: {fact}.", category="personal_context", importance=4)
                learned.append({"key": key, "content": fact})

        # 7. Family / Friends / Girlfriend / Partner:
        m = re.search(r"(?:my (?:girlfriend|boyfriend|partner|brother|sister|friend|mom|mother|dad|father|boss|colleague|wife|husband|dog|cat))\s+(?:is|name is|called)?\s*([a-zA-Z\u0900-\u097F]+)", low)
        if m:
            person = m.group(0).strip()
            name_part = m.group(1).capitalize()
            rel_label = m.group(0).split()[1] if len(m.group(0).split()) > 1 else "contact"
            key = f"person_{re.sub(r'[^a-z0-9]', '_', name_part[:20]).strip('_').lower()}"
            self.remember(
                key=key,
                content=f"Personal connection: {rel_label} is {name_part} (Source: user_confirmed).",
                category="people_relationships",
                importance=5
            )
            learned.append({"key": key, "content": f"{rel_label} is {name_part}"})

        # 8. Name suppression & address preferences:
        if any(k in low for k in ["don't use my name", "don't call me by name", "stop using my name", "naam mat lo", "naam se mat bulao"]):
            self.remember(key="suppress_user_name", content="User explicitly prefers NOT to be called by their name.", category="user_preferences", importance=5)
            learned.append({"key": "suppress_user_name", "content": "Suppress user name in conversation"})
        elif any(k in low for k in ["you can use my name", "call me by my name", "naam le sakte ho"]):
            self.forget("suppress_user_name")

        # 9. Language preference overrides:
        if any(k in low for k in ["speak in english only", "speak english", "only english", "english me baat karo", "reply in english", "english please"]):
            self.remember(key="language_override", content="English only. User explicitly instructed to respond exclusively in English.", category="user_preferences", importance=5)
            learned.append({"key": "language_override", "content": "Language set to English"})
        elif any(k in low for k in ["speak in hindi", "hindi me baat karo", "hindi bolo"]):
            self.remember(key="language_override", content="Hindi/Hinglish. User explicitly requested Hindi.", category="user_preferences", importance=5)
            learned.append({"key": "language_override", "content": "Language set to Hindi"})

        # 8. Project notes:
        m_proj = re.search(r"(?:working on|building|developing|project is|repo is)\s+([^,\.\?!]+)", low)
        if m_proj:
            proj = m_proj.group(1).strip()
            if len(proj) > 2 and proj not in ("it", "this", "that", "code"):
                key = f"proj_{re.sub(r'[^a-z0-9]', '_', proj[:20]).strip('_')}"
                self.remember(key=key, content=f"Active project: {proj}.", category="project_memory", importance=4)
                learned.append({"key": key, "content": proj})

        return learned

    def set_preference(self, key: str, value: Any) -> str:
        """Store a typed user preference in user_preferences category."""
        content = json.dumps(value) if isinstance(value, (dict, list, bool, int, float)) else str(value)
        return self.remember(key=key, content=content, category="user_preferences", importance=5)

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a user preference from user_preferences category."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT content FROM memories
                WHERE category = 'user_preferences' AND key = ?
                ORDER BY updated_at DESC LIMIT 1
            """, (key,))
            row = cur.fetchone()
            if row:
                raw = row["content"]
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
        return default

    def get_personal_relationship(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve relationship details for a contact name."""
        clean = name.lower().strip()
        key = f"person_{re.sub(r'[^a-z0-9]', '_', clean[:20]).strip('_')}"
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT category, key, content, confidence, importance FROM memories
                WHERE key = ? OR LOWER(key) = ? OR LOWER(content) LIKE ?
                ORDER BY updated_at DESC LIMIT 1
            """, (key, f"person_{clean}", f"%{clean}%"))
            row = cur.fetchone()
            if row:
                content = row["content"]
                rel_label = "contact"
                for word in ["girlfriend", "boyfriend", "partner", "wife", "husband", "friend", "sister", "brother", "mother", "father"]:
                    if word in content.lower():
                        rel_label = word
                        break
                return {
                    "name": name,
                    "relationship": rel_label,
                    "verified": "user_confirmed" in content.lower(),
                    "content": content
                }
        return None

    def purge_unverified_contact_claims(self, contact_name: str) -> int:
        """Purge or clean any unverified external biographical claims associated with a contact name."""
        clean = contact_name.lower().strip()
        count = 0
        with self._get_conn() as conn:
            cur = conn.cursor()
            # Delete memories that contain unverified/public web claims for this name
            cur.execute("""
                DELETE FROM memories
                WHERE (category IN ('people_relationships', 'personal_context'))
                  AND LOWER(content) LIKE ?
                  AND LOWER(content) NOT LIKE '%user_confirmed%'
            """, (f"%{clean}%",))
            conn.commit()
            count = cur.rowcount
        return count

    def correct_personal_fact(self, key: str, corrected_content: str, category: str = "people_relationships") -> str:
        """Allow user to explicitly correct a mistaken personal fact or association."""
        return self.remember(key=key, content=f"{corrected_content} (Source: user_confirmed)", category=category, importance=5)

    def get_formatted_knowledge(self, query: str = "") -> str:
        """Get formatted knowledge block organized by canonical categories."""
        all_mems = self.list_all()
        uname = os.environ.get("USER_NAME", "User")
        aname = os.environ.get("ASSISTANT_NAME", "Aarushi")
        if not all_mems:
            return f"No prior memories recorded yet. Actively learn preferences and project context for {uname}."

        lines = [f"=== WHAT YOU HAVE LEARNED FROM YOUR CREATOR & PERSISTENT MEMORY FOR {uname.upper()} ==="]
        # Group by category
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for m in all_mems:
            cat = m["category"]
            by_cat.setdefault(cat, []).append(m)

        category_headers = {
            "user_preferences": "USER PREFERENCES & HABITS",
            "personal_context": "PERSONAL CONTEXT & FACTS",
            "project_memory": "PROJECT & WORKSPACE MEMORY",
            "people_relationships": "PEOPLE & RELATIONSHIPS",
            "episodic": "EPISODIC & PAST INTERACTIONS",
            "temporary": "CURRENT SESSION NOTES",
        }

        for cat_key, header in category_headers.items():
            if cat_key in by_cat:
                lines.append(f"[{header}]:")
                for item in by_cat[cat_key]:
                    lines.append(f"• {item['key']}: {item['content']}")

        lines.append("===================================================")
        return "\n".join(lines)

    def get_proactive_context(self) -> Dict[str, Any]:
        """Extract key memories and context for proactive idle conversation."""
        all_mems = self.list_all()
        likes = [m["content"] for m in all_mems if m["category"] in ("user_preferences", "preference") and "dislike" not in m["key"]]
        dislikes = [m["content"] for m in all_mems if "dislike" in m["key"]]
        facts = [m["content"] for m in all_mems if m["category"] in ("personal_context", "fact", "project_memory", "people_relationships")]
        user_name = None
        for m in all_mems:
            if m["key"] == "user_name":
                content = m["content"]
                if "is " in content:
                    candidate = content.split("is ")[-1].strip(". ")
                    if candidate and candidate.lower() not in ("adarsh", "user", "gdr"):
                        user_name = candidate
                        break

        if not user_name:
            user_name = os.environ.get("USER_NAME")
            if not user_name:
                try:
                    from gdr.config import load_config
                    cfg_u = load_config().get("general", {}).get("user_name")
                    if cfg_u and cfg_u.lower() not in ("adarsh", "user", "gdr"):
                        user_name = cfg_u
                except Exception:
                    pass

        if not user_name or str(user_name).strip().lower() in ("adarsh", "user", "gdr"):
            import getpass
            try:
                sys_u = getpass.getuser()
                user_name = sys_u.capitalize() if sys_u.lower() not in ("root", "kali", "gdr", "runner") else "Commander"
            except Exception:
                user_name = "Commander"

        now = datetime.now()
        hour = now.hour
        time_phase = "late night" if (hour >= 23 or hour < 5) else ("morning" if hour < 12 else ("afternoon" if hour < 17 else "evening"))

        return {
            "user_name": user_name,
            "likes": likes[:3],
            "dislikes": dislikes[:2],
            "facts": facts[:5],
            "current_hour": hour,
            "time_phase": time_phase,
        }


_MEMORY_STORE = None


def get_memory_store() -> MemoryStore:
    global _MEMORY_STORE
    expected_path = _resolve_mem_db()
    if _MEMORY_STORE is None or _MEMORY_STORE.db_path != expected_path:
        _MEMORY_STORE = MemoryStore(db_path=expected_path)
    return _MEMORY_STORE



@tool(name="remember_fact", description="Save a long-term memory in categories: user_preferences, personal_context, project_memory, people_relationships, episodic, temporary.", category="memory", tier="AUTO")
def remember_fact(key: str, content: str, category: str = "personal_context") -> str:
    store = get_memory_store()
    return store.remember(key=key, content=content, category=category)


@tool(name="recall_memory", description="Search long-term memory for saved facts, preferences, or project details.", category="memory", tier="AUTO")
def recall_memory(query: str) -> str:
    store = get_memory_store()
    recalled = store.recall(query=query)
    if not recalled:
        return f"No memories found matching '{query}'."
    lines = [f"Found {len(recalled)} memories:"]
    for m in recalled:
        lines.append(f"• [{m['category'].upper()}] {m['key']}: {m['content']}")
    return "\n".join(lines)


@tool(name="forget_fact", description="Delete a stored memory by key.", category="memory", tier="AUTO")
def forget_fact(key: str) -> str:
    store = get_memory_store()
    deleted = store.forget(key)
    if deleted:
        return f"Removed memory for '{key}'."
    return f"No memory found with key '{key}'."
