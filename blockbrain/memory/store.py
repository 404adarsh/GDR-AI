"""Long-term memory subsystem for blockbrain AI.
Stores facts, user preferences, people, and projects in SQLite with semantic search.
Exposes remember, recall, and forget tools to the agent.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional

from blockbrain.tools.registry import tool

MEM_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
MEM_DB_PATH = MEM_DIR / "memory.db"


class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or MEM_DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,       -- 'fact', 'preference', 'person', 'project'
                key TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            conn.commit()

    def remember(self, key: str, content: str, category: str = "fact") -> str:
        now_str = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute("""
            INSERT INTO memories (category, key, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                category = excluded.category,
                updated_at = excluded.updated_at
            """, (category, key.lower().strip(), content, now_str, now_str))
            conn.commit()
        return f"Stored memory for '{key}' in category '{category}'."

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]
        with self._get_conn() as conn:
            cur = conn.cursor()
            if not terms:
                cur.execute("SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?", (limit,))
            else:
                # Basic token matching rank
                where_clauses = " OR ".join(["key LIKE ? OR content LIKE ?" for _ in terms])
                params = []
                for t in terms:
                    params.extend([f"%{t}%", f"%{t}%"])
                params.append(limit)
                cur.execute(f"SELECT * FROM memories WHERE {where_clauses} ORDER BY updated_at DESC LIMIT ?", params)

            return [dict(r) for r in cur.fetchall()]

    def forget(self, key: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE key = ?", (key.lower().strip(),))
            conn.commit()
            return cur.rowcount > 0

    def list_all(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM memories ORDER BY category, key ASC")
            return [dict(r) for r in cur.fetchall()]

    def auto_learn_from_user(self, text: str) -> List[Dict[str, str]]:
        """Intelligently and automatically learns preferences, facts, style, and personal details
        from user speech like a child learning from their parent.
        """
        if not text or len(text.strip()) < 3:
            return []

        import re
        learned = []
        low = text.lower().strip()

        # 1. Parent/Child Relationship anchor:
        if any(k in low for k in ["you are my child", "like my child", "child learning from me", "mera baccha", "learn from me"]):
            self.remember(
                key="relationship_role",
                content="Looks up to user as a loving parent and teacher. Learns and grows from user's wisdom, tone, and guidance with warmth and respect.",
                category="persona"
            )
            learned.append({"key": "relationship_role", "content": "Parent-Child learning bond established."})

        # 2. Name / Identity:
        m = re.search(r"(?:my name is|call me|i am called|naam hai mera|mera naam)\s+([a-zA-Z\u0900-\u097F]+)", low)
        if m:
            name = m.group(1).capitalize()
            self.remember(key="user_name", content=f"Creator's name is {name}.", category="fact")
            learned.append({"key": "user_name", "content": f"User's name is {name}"})

        # 3. Profession / Work:
        m = re.search(r"(?:i am an?|i work as an?|i do|mera kaam|main ek)\s+([a-zA-Z0-9\s\-]+?)(?:\.|\band\b|\bwith\b|\bfor\b|$)", low)
        if m and any(w in m.group(1) for w in ["developer", "engineer", "researcher", "student", "hacker", "designer", "coder", "analyst", "founder", "manager"]):
            role = m.group(1).strip()
            self.remember(key="profession", content=f"Works as: {role}.", category="fact")
            learned.append({"key": "profession", "content": role})

        # 4. Likes & Preferences:
        # English: "I love black coffee", "I prefer python"
        # Hindi: "mujhe chai pasand hai", "mujhe music accha lagta hai"
        m = re.search(r"(?:i love|i really like|i like|i prefer|mujhe pasand hai|mujhe accha lagta hai)\s+([^,\.\?!]+)", low)
        m_hi = re.search(r"(?:mujhe|humein)\s+([^,\.\?!]+?)\s+(?:pasand hai|bahut pasand|acchi? lagti? hai)", low)
        item = None
        if m:
            item = m.group(1).strip()
        elif m_hi:
            item = m_hi.group(1).strip()

        if item and len(item) > 2 and item not in ("you", "it", "that", "this", "listening", "speaking", "to", "the"):
            key = f"likes_{re.sub(r'[^a-z0-9]', '_', item[:20]).strip('_')}"
            self.remember(key=key, content=f"Loves/prefers: {item}.", category="preference")
            learned.append({"key": key, "content": item})

        # 5. Dislikes & Displeasures:
        # English: "I hate cold tea", "I don't like bugs"
        # Hindi: "mujhe cold pizza pasand nahi", "mujhe bura lagta hai noise"
        m = re.search(r"(?:i hate|i dislike|i don't like|i do not like|mujhe pasand nahi|mujhe bura lagta hai)\s+([^,\.\?!]+)", low)
        m_hi_dis = re.search(r"(?:mujhe|humein)\s+([^,\.\?!]+?)\s+(?:pasand nahi|buri? lagti? hai)", low)
        item_dis = None
        if m:
            item_dis = m.group(1).strip()
        elif m_hi_dis:
            item_dis = m_hi_dis.group(1).strip()

        if item_dis and len(item_dis) > 2 and item_dis not in ("you", "it", "that", "this"):
            key = f"dislikes_{re.sub(r'[^a-z0-9]', '_', item_dis[:20]).strip('_')}"
            self.remember(key=key, content=f"Dislikes: {item_dis}.", category="preference")
            learned.append({"key": key, "content": item_dis})

        # 6. Explicit instructions to remember:
        m = re.search(r"(?:remember that|always remember|don't forget that|yaad rakhna ki|yaad rakh)\s+([^,\.\?!]+)", low)
        if m:
            fact = m.group(1).strip()
            if fact:
                key = f"fact_{re.sub(r'[^a-z0-9]', '_', fact[:20]).strip('_')}"
                self.remember(key=key, content=f"Remembered fact: {fact}.", category="fact")
                learned.append({"key": key, "content": fact})

        # 7. Family / Friends / People:
        m = re.search(r"(?:my (?:brother|sister|friend|mom|mother|dad|father|boss|colleague|wife|husband|dog|cat))\s+(?:is|name is|called)?\s*([a-zA-Z\u0900-\u097F]+)", low)
        if m:
            person = m.group(0).strip()
            key = f"person_{re.sub(r'[^a-z0-9]', '_', person[:20]).strip('_')}"
            self.remember(key=key, content=f"Personal connection: {person}.", category="person")
            learned.append({"key": key, "content": person})

        # 8. Speaking style & Language cues:
        hindi_cues = ["bhai", "yaar", "kya", "kaise", "nahi", "accha", "haan", "theek", "shukriya", "dhanyawad", "namaste", "chup", "ruko"]
        if any(h in low.split() for h in hindi_cues):
            self.remember(
                key="style_language",
                content="User naturally uses Hindi/Hinglish phrasing. Appreciates warm, culturally attuned, respectful conversational replies.",
                category="style"
            )

        return learned

    def get_formatted_knowledge(self, query: str = "") -> str:
        """Get formatted knowledge block for prompt injection."""
        all_mems = self.list_all()
        if not all_mems:
            return "No prior memories recorded yet. Actively listen and learn from the user."

        lines = ["=== WHAT YOU HAVE LEARNED FROM YOUR CREATOR (PARENT/TEACHER) ==="]
        for m in all_mems:
            cat = m["category"].upper()
            lines.append(f"• [{cat}] {m['key']}: {m['content']}")
        lines.append("==================================================================")
        return "\n".join(lines)


_MEMORY_STORE = None


def get_memory_store() -> MemoryStore:
    global _MEMORY_STORE
    if _MEMORY_STORE is None:
        _MEMORY_STORE = MemoryStore()
    return _MEMORY_STORE


@tool(name="remember_fact", description="Save a long-term memory about user preferences, people, projects, or facts.", category="memory", tier="AUTO")
def remember_fact(key: str, content: str, category: str = "preference") -> str:
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

