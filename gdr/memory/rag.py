"""RAG (Retrieval Augmented Generation) Knowledge Base for GDR AI.
Secured with customizable Master PIN.
Provides document chunking, semantic keyword/token search, and automatic prompt injection.
"""

from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import List, Dict, Any, Optional

from gdr.tools.registry import tool

RAG_MASTER_PIN = os.environ.get("RAG_SECURITY_PIN", os.environ.get("RAG_MASTER_PIN", ""))
DEFAULT_DB_PATH = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "rag_knowledge.db"

_RAG_PIN_CACHE: Optional[str] = None


def _get_active_rag_pin() -> str:
    """Resolve the RAG master PIN from env, secrets, or config — in priority order."""
    global _RAG_PIN_CACHE

    # 1. Live env var (highest priority — allows runtime override)
    live = os.environ.get("RAG_SECURITY_PIN", os.environ.get("RAG_MASTER_PIN", "")).strip()
    if live:
        _RAG_PIN_CACHE = live
        return live

    # 2. Secrets file (.env / secrets.env) — load fresh
    try:
        from gdr.safety.secrets import _load_env_secrets
        env_secrets = _load_env_secrets()
        for key in ("RAG_SECURITY_PIN", "RAG_MASTER_PIN"):
            v = env_secrets.get(key, "").strip()
            if v:
                os.environ[key] = v
                _RAG_PIN_CACHE = v
                return v
    except Exception:
        pass

    # 3. Config.toml fallback
    try:
        from gdr.config import load_config
        cfg = load_config()
        cfgpin = str(cfg.get("security", {}).get("rag_pin", "") or "").strip()
        if cfgpin:
            _RAG_PIN_CACHE = cfgpin
            return cfgpin
    except Exception:
        pass

    return _RAG_PIN_CACHE or ""


def verify_rag_pin(pin: Optional[str]) -> bool:
    """Verify Master PIN for RAG Knowledge Base access."""
    if not pin:
        return False
    active_pin = _get_active_rag_pin()
    if not active_pin:
        # No PIN configured — deny all access until a PIN is set via Settings
        return False
    return str(pin).strip() == str(active_pin).strip()


class RAGStore:
    """High-performance RAG knowledge store with SQLite and BM25-style lexical scoring."""

    def __init__(self, db_path: Optional[Path] = None):
        target = db_path or DEFAULT_DB_PATH
        if target.exists() and not os.access(str(target), os.W_OK):
            target = Path("/tmp/gdr_rag_knowledge.db")
        elif not target.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(str(target.parent), os.W_OK):
                    target = Path("/tmp/gdr_rag_knowledge.db")
            except Exception:
                target = Path("/tmp/gdr_rag_knowledge.db")
        self.db_path = target
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self.db_path.exists() and not os.access(str(self.db_path), os.W_OK):
            self.db_path = Path("/tmp/gdr_rag_knowledge.db")
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path))
        except (sqlite3.OperationalError, OSError, PermissionError):
            fallback = Path("/tmp/gdr_rag_knowledge.db")
            fallback.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(fallback))
            self.db_path = fallback
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'notes',  -- 'notes', 'docs', 'facts', 'rules', 'code', 'secrets'
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                source TEXT DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_category ON rag_documents(category);")
            conn.commit()

    def add_document(
        self,
        title: str,
        content: str,
        category: str = "notes",
        tags: str = "",
        source: str = "manual"
    ) -> Dict[str, Any]:
        """Add a knowledge document or note into RAG knowledge base."""
        now = datetime.now().isoformat()
        clean_title = (title or "Untitled Document").strip()
        clean_content = (content or "").strip()
        clean_cat = (category or "notes").strip().lower()
        clean_tags = (tags or "").strip()

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO rag_documents (title, category, content, tags, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (clean_title, clean_cat, clean_content, clean_tags, source, now, now))
            doc_id = cur.lastrowid
            conn.commit()

        return {
            "id": doc_id,
            "title": clean_title,
            "category": clean_cat,
            "tags": clean_tags,
            "word_count": len(clean_content.split()),
            "created_at": now
        }

    def update_document(
        self,
        doc_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None
    ) -> bool:
        """Update an existing RAG document."""
        now = datetime.now().isoformat()
        fields = ["updated_at = ?"]
        params: List[Any] = [now]

        if title is not None:
            fields.append("title = ?")
            params.append(title.strip())
        if content is not None:
            fields.append("content = ?")
            params.append(content.strip())
        if category is not None:
            fields.append("category = ?")
            params.append(category.strip().lower())
        if tags is not None:
            fields.append("tags = ?")
            params.append(tags.strip())

        params.append(doc_id)
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE rag_documents SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
            return cur.rowcount > 0

    def delete_document(self, doc_id: int) -> bool:
        """Delete document from knowledge base."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM rag_documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM rag_documents WHERE id = ?", (doc_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_documents(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List documents with optional filtering."""
        query = "SELECT * FROM rag_documents WHERE 1=1"
        params: List[Any] = []

        if category and category.lower() != "all":
            query += " AND category = ?"
            params.append(category.lower().strip())

        if search and search.strip():
            s = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            params.extend([s, s, s])

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            docs = []
            for r in cur.fetchall():
                d = dict(r)
                d["word_count"] = len(d.get("content", "").split())
                docs.append(d)
            return docs

    def search_rag(self, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Score and retrieve top relevant knowledge chunks using BM25-style term weighting."""
        if not query_text or not query_text.strip():
            return []

        clean_q = query_text.lower().strip()
        tokens = [t for t in re.findall(r"\b[a-zA-Z0-9_\u0900-\u097F]{2,}\b", clean_q) if len(t) >= 2]
        if not tokens:
            return []

        all_docs = self.list_documents(limit=300)
        if not all_docs:
            return []

        scored_docs = []
        for doc in all_docs:
            score = 0.0
            title_low = doc.get("title", "").lower()
            content_low = doc.get("content", "").lower()
            tags_low = doc.get("tags", "").lower()

            for t in tokens:
                # Title match is heavily weighted (4x)
                if t in title_low:
                    score += 4.0
                # Tags match is weighted (3x)
                if t in tags_low:
                    score += 3.0
                # Content frequency count
                c_count = content_low.count(t)
                if c_count > 0:
                    score += 1.0 + math.log1p(c_count)

            # Exact phrase match bonus
            if clean_q in content_low or clean_q in title_low:
                score += 8.0

            if score > 0:
                doc_copy = dict(doc)
                doc_copy["relevance_score"] = round(score, 2)
                scored_docs.append(doc_copy)

        scored_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_docs[:top_k]

    def format_rag_context(self, query_text: str, max_chars: int = 2500) -> str:
        """Format matching RAG knowledge into structured system prompt context."""
        results = self.search_rag(query_text, top_k=3)
        if not results:
            return ""

        chunks = []
        total_len = 0
        for r in results:
            content_snippet = r.get("content", "").strip()
            if len(content_snippet) > 800:
                content_snippet = content_snippet[:800] + "..."
            entry = f"【Knowledge Document: {r.get('title')} ({r.get('category')})】\n{content_snippet}"
            if total_len + len(entry) > max_chars:
                break
            chunks.append(entry)
            total_len += len(entry)

        if not chunks:
            return ""

        return "\n\n".join(chunks)

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG knowledge base statistics."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), SUM(LENGTH(content)) FROM rag_documents")
            row = cur.fetchone()
            total_docs = row[0] if row else 0
            total_chars = row[1] if row and row[1] else 0

            cur.execute("SELECT category, COUNT(*) FROM rag_documents GROUP BY category")
            categories = {r[0]: r[1] for r in cur.fetchall()}

        return {
            "total_documents": total_docs,
            "total_characters": total_chars,
            "estimated_words": total_chars // 5,
            "categories": categories,
            "pin_protected": True
        }


# Global singleton instance
_GLOBAL_RAG_STORE: Optional[RAGStore] = None


def get_rag_store() -> RAGStore:
    global _GLOBAL_RAG_STORE
    if _GLOBAL_RAG_STORE is None:
        _GLOBAL_RAG_STORE = RAGStore()
    return _GLOBAL_RAG_STORE


# -------------------------------------------------------------
# Agent Tools for RAG
# -------------------------------------------------------------
@tool(
    name="search_knowledge_base",
    description="Search the user's private RAG knowledge base for specific documents, notes, facts, and project details.",
    category="memory"
)
def search_knowledge_base(query: str) -> str:
    store = get_rag_store()
    results = store.search_rag(query, top_k=4)
    if not results:
        return f"No matching documents found in knowledge base for query: '{query}'."

    lines = [f"Found {len(results)} relevant knowledge documents:"]
    for r in results:
        lines.append(f"\n--- {r['title']} [{r['category']}] (Score: {r['relevance_score']}) ---")
        lines.append(r['content'][:600])
    return "\n".join(lines)


@tool(
    name="add_to_knowledge_base",
    description="Save a new document, note, or reference guide into the user's private RAG knowledge base.",
    category="memory"
)
def add_to_knowledge_base(title: str, content: str, category: str = "notes", tags: str = "") -> str:
    store = get_rag_store()
    res = store.add_document(title=title, content=content, category=category, tags=tags)
    return f"✅ Saved to Knowledge Base: '{res['title']}' (ID #{res['id']}, Category: {res['category']})."

