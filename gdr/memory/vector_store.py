"""Vector Store and Local RAG Index for GDR AI.
Provides dense vector retrieval using FAISS + SentenceTransformers when installed,
with automatic fallback to TF-IDF cosine similarity for offline/zero-dependency environments.
"""

from __future__ import annotations

import collections
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Try optional heavy dependencies
try:
    import faiss
    _FAISS_AVAILABLE = True
except Exception:
    faiss = None
    _FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    _ST_AVAILABLE = False


def _tokenize(text: str) -> List[str]:
    """Simple lowercase alphanumeric word tokenizer."""
    return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())


class KeywordIndex:
    """TF-IDF Cosine Similarity index for offline environments without FAISS."""

    def __init__(self):
        self.docs: List[str] = []
        self.metadata: List[Dict[str, Any]] = []
        self.doc_freqs: collections.Counter = collections.Counter()
        self.doc_vectors: List[Dict[str, float]] = []

    def clear(self):
        self.docs.clear()
        self.metadata.clear()
        self.doc_freqs.clear()
        self.doc_vectors.clear()

    def add(self, doc: str, meta: Optional[Dict[str, Any]] = None):
        tokens = _tokenize(doc)
        if not tokens:
            return
        self.docs.append(doc)
        self.metadata.append(meta or {})

        tf = collections.Counter(tokens)
        for w in set(tokens):
            self.doc_freqs[w] += 1

        # Store term frequency
        self.doc_vectors.append(dict(tf))

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.docs:
            return []

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        n_docs = len(self.docs)
        q_tf = collections.Counter(q_tokens)

        # Calculate query vector with IDF
        q_vec = {}
        for w, count in q_tf.items():
            idf = math.log((n_docs + 1) / (self.doc_freqs.get(w, 0) + 1)) + 1.0
            q_vec[w] = count * idf

        q_norm = math.sqrt(sum(v ** 2 for v in q_vec.values())) or 1.0

        scores = []
        for idx, d_tf in enumerate(self.doc_vectors):
            dot = 0.0
            d_norm_sq = 0.0
            for w, count in d_tf.items():
                idf = math.log((n_docs + 1) / (self.doc_freqs.get(w, 0) + 1)) + 1.0
                d_val = count * idf
                d_norm_sq += d_val ** 2
                if w in q_vec:
                    dot += q_vec[w] * d_val

            d_norm = math.sqrt(d_norm_sq) or 1.0
            sim = dot / (q_norm * d_norm)
            if sim > 0:
                scores.append((sim, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, idx in scores[:top_k]:
            results.append({
                "text": self.docs[idx],
                "score": round(sim, 4),
                "metadata": self.metadata[idx]
            })
        return results


class VectorStore:
    """Hybrid Vector Store with FAISS/SentenceTransformers and TF-IDF fallback."""

    def __init__(self, index_path: Optional[Path] = None, model_name: str = "all-MiniLM-L6-v2"):
        self.index_path = index_path
        self.model_name = model_name
        self.is_semantic = _FAISS_AVAILABLE and _ST_AVAILABLE
        self._st_model = None
        self._faiss_index = None

        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self._keyword_index = KeywordIndex()

        if self.is_semantic:
            try:
                self._st_model = SentenceTransformer(model_name)
            except Exception:
                self.is_semantic = False

    @property
    def count(self) -> int:
        return len(self.documents)

    @property
    def doc_count(self) -> int:
        return len(self.documents)

    def clear(self):
        """Reset index and document collection."""
        self.documents.clear()
        self.metadatas.clear()
        self._keyword_index.clear()
        self._faiss_index = None

    def add_documents(self, docs: List[str], metadata: Optional[List[Dict[str, Any]]] = None) -> int:
        """Add and embed a batch of documents."""
        if not docs:
            return 0

        metas = metadata or [{} for _ in docs]
        added = 0

        for d, m in zip(docs, metas):
            if not d.strip():
                continue
            self.documents.append(d)
            self.metadatas.append(m)
            self._keyword_index.add(d, m)
            added += 1

        if self.is_semantic and self._st_model is not None:
            try:
                embeddings = self._st_model.encode(docs, convert_to_numpy=True, normalize_embeddings=True)
                dim = embeddings.shape[1]
                if self._faiss_index is None:
                    self._faiss_index = faiss.IndexFlatIP(dim)
                self._faiss_index.add(embeddings)
            except Exception as e:
                print(f"FAISS embedding failed, relying on keyword fallback: {e}")

        return added

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve most relevant document chunks for the query."""
        if not self.documents:
            return []

        # Try semantic search first
        if self.is_semantic and self._faiss_index is not None and self._st_model is not None:
            try:
                q_emb = self._st_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
                scores, indices = self._faiss_index.search(q_emb, min(top_k, len(self.documents)))
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx >= 0 and idx < len(self.documents):
                        results.append({
                            "text": self.documents[idx],
                            "score": round(float(score), 4),
                            "metadata": self.metadatas[idx]
                        })
                if results:
                    return results
            except Exception:
                pass

        # Fallback to TF-IDF keyword search
        return self._keyword_index.search(query, top_k=top_k)

    def index_directory(
        self,
        dir_path: Path,
        extensions: Optional[List[str]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> int:
        """Recursively walk directory, chunk text/code files, and index them."""
        exts = set(extensions or [".py", ".md", ".txt", ".sh", ".json", ".js", ".ts", ".html", ".css", ".yaml", ".yml"])
        p = Path(dir_path)
        if not p.exists() or not p.is_dir():
            return 0

        chunks = []
        metas = []

        for item in p.rglob("*"):
            if item.is_file() and item.suffix.lower() in exts:
                # Skip hidden/venv/git directories
                if any(part.startswith(".") or part in ("node_modules", "venv", ".venv", "__pycache__") for part in item.parts):
                    continue
                try:
                    text = item.read_text(encoding="utf-8", errors="ignore")
                    if not text.strip():
                        continue

                    # Chunk by lines or character window
                    lines = text.splitlines(keepends=True)
                    current_chunk = []
                    current_len = 0
                    line_start = 1

                    for l_idx, line in enumerate(lines, start=1):
                        current_chunk.append(line)
                        current_len += len(line)
                        if current_len >= chunk_size:
                            chunk_text = "".join(current_chunk)
                            chunks.append(chunk_text)
                            metas.append({
                                "file_path": str(item.resolve()),
                                "file_name": item.name,
                                "line_start": line_start,
                                "line_end": l_idx,
                            })
                            # Overlap
                            overlap_lines = current_chunk[-max(1, len(current_chunk) // 5):]
                            current_chunk = list(overlap_lines)
                            current_len = sum(len(l) for l in current_chunk)
                            line_start = l_idx - len(overlap_lines) + 1

                    if current_chunk:
                        chunks.append("".join(current_chunk))
                        metas.append({
                            "file_path": str(item.resolve()),
                            "file_name": item.name,
                            "line_start": line_start,
                            "line_end": len(lines),
                        })

                except Exception:
                    continue

        return self.add_documents(chunks, metas)

    def save(self, path: Optional[Path] = None):
        """Save documents, metadata and FAISS index."""
        p = path or self.index_path
        if not p:
            return
        p.mkdir(parents=True, exist_ok=True)
        meta_file = p / "vector_store.json"
        meta_data = {
            "documents": self.documents,
            "metadatas": self.metadatas,
            "is_semantic": self.is_semantic,
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))

        if self.is_semantic and self._faiss_index is not None:
            faiss_file = str(p / "index.faiss")
            faiss.write_index(self._faiss_index, faiss_file)

    def load(self, path: Optional[Path] = None):
        """Load documents, metadata and FAISS index."""
        p = path or self.index_path
        if not p or not p.exists():
            return
        meta_file = p / "vector_store.json"
        if meta_file.exists():
            data = json.loads(meta_file.read_text())
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            self.clear()
            self.add_documents(docs, metas)

        faiss_file = p / "index.faiss"
        if self.is_semantic and faiss_file.exists() and faiss is not None:
            try:
                self._faiss_index = faiss.read_index(str(faiss_file))
            except Exception:
                pass
