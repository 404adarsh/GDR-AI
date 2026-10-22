"""Request database store for GDR AI.
Saves every inbound request with its IP address, method, path, query params, headers,
payload, user-supplied details, and execution duration in SQLite.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
from typing import Optional, Dict, Any, List

from gdr.safety.secrets import sanitize_text

logger = logging.getLogger("gdr.safety.request_db")

DEFAULT_DB_PATH = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "requests.db"


class RequestStore:
    """Thread-safe SQLite persistent store for inbound user & network requests."""

    def __init__(self, db_path: Optional[Path] = None):
        target = db_path or DEFAULT_DB_PATH
        if target.exists() and not os.access(str(target), os.W_OK):
            target = Path("/tmp/gdr_requests.db")
        elif not target.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(str(target.parent), os.W_OK):
                    target = Path("/tmp/gdr_requests.db")
            except Exception:
                target = Path("/tmp/gdr_requests.db")
        self.db_path = target
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self.db_path.exists() and not os.access(str(self.db_path), os.W_OK):
            self.db_path = Path("/tmp/gdr_requests.db")
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        except (sqlite3.OperationalError, OSError, PermissionError):
            fallback = Path("/tmp/gdr_requests.db")
            fallback.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(fallback), timeout=10.0)
            self.db_path = fallback
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    def _init_db(self):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS request_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        ip_address TEXT NOT NULL,
                        method TEXT NOT NULL,
                        path TEXT NOT NULL,
                        query_params TEXT,
                        headers TEXT,
                        body_payload TEXT,
                        user_details TEXT,
                        status_code INTEGER DEFAULT 200,
                        duration_ms REAL DEFAULT 0.0,
                        source TEXT DEFAULT 'http'
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_req_timestamp ON request_logs(timestamp);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_req_ip ON request_logs(ip_address);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_req_path ON request_logs(path);")
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to initialize request_logs table: {e}")

    def log_request(
        self,
        ip_address: str,
        method: str,
        path: str,
        query_params: Optional[Any] = None,
        headers: Optional[Dict[str, Any]] = None,
        body_payload: Optional[Any] = None,
        user_details: Optional[Any] = None,
        status_code: int = 200,
        duration_ms: float = 0.0,
        source: str = "http"
    ) -> int:
        """Record an inbound request with IP address and full user-provided details."""
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            ip = str(ip_address or "127.0.0.1").strip()

            # Sanitize and serialize query params
            q_str = ""
            if query_params:
                if isinstance(query_params, (dict, list)):
                    q_str = sanitize_text(json.dumps(query_params, ensure_ascii=False))
                else:
                    q_str = sanitize_text(str(query_params))

            # Sanitize and serialize headers
            h_str = ""
            if headers:
                safe_headers = {}
                for k, v in headers.items():
                    k_lower = str(k).lower()
                    # Skip sensitive authorization headers
                    if "auth" in k_lower or "token" in k_lower or "cookie" in k_lower or "key" in k_lower:
                        safe_headers[k] = "***"
                    else:
                        safe_headers[k] = sanitize_text(str(v))
                h_str = json.dumps(safe_headers, ensure_ascii=False)

            # Sanitize and serialize body payload
            b_str = ""
            if body_payload is not None:
                if isinstance(body_payload, (dict, list)):
                    b_str = sanitize_text(json.dumps(body_payload, ensure_ascii=False))
                elif isinstance(body_payload, bytes):
                    b_str = f"[Binary data: {len(body_payload)} bytes]"
                else:
                    b_str = sanitize_text(str(body_payload))

            # Sanitize and serialize extracted user details
            u_str = ""
            if user_details is not None:
                if isinstance(user_details, (dict, list)):
                    u_str = sanitize_text(json.dumps(user_details, ensure_ascii=False))
                else:
                    u_str = sanitize_text(str(user_details))

            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO request_logs (
                        timestamp, ip_address, method, path, query_params,
                        headers, body_payload, user_details, status_code,
                        duration_ms, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now_iso, ip, method.upper(), path, q_str,
                    h_str, b_str, u_str, int(status_code),
                    round(float(duration_ms), 2), source
                ))
                conn.commit()
                return cursor.lastrowid or 0
        except Exception as e:
            logger.warning(f"Failed to record request log to database: {e}")
            return 0

    def get_recent_requests(
        self,
        limit: int = 100,
        ip_filter: Optional[str] = None,
        path_filter: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent request logs with optional IP, path, or source filtering."""
        try:
            with self._get_conn() as conn:
                query = "SELECT * FROM request_logs"
                params: List[Any] = []
                clauses = []
                if ip_filter:
                    clauses.append("ip_address LIKE ?")
                    params.append(f"%{ip_filter}%")
                if path_filter:
                    clauses.append("path LIKE ?")
                    params.append(f"%{path_filter}%")
                if source_filter:
                    clauses.append("source LIKE ?")
                    params.append(f"%{source_filter}%")
                if clauses:
                    query += " WHERE " + " AND ".join(clauses)
                query += " ORDER BY id DESC LIMIT ?"
                params.append(max(1, min(1000, limit)))

                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r["id"],
                        "timestamp": r["timestamp"],
                        "ip_address": r["ip_address"],
                        "method": r["method"],
                        "path": r["path"],
                        "query_params": r["query_params"],
                        "headers": r["headers"],
                        "body_payload": r["body_payload"],
                        "user_details": r["user_details"],
                        "status_code": r["status_code"],
                        "duration_ms": r["duration_ms"],
                        "source": r["source"]
                    })
                return results
        except Exception as e:
            logger.warning(f"Failed to query recent request logs: {e}")
            return []

    def get_request_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics on stored requests."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM request_logs")
                total = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM request_logs")
                unique_ips = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT ip_address, COUNT(*) as count
                    FROM request_logs
                    GROUP BY ip_address
                    ORDER BY count DESC
                    LIMIT 5
                """)
                top_ips = [{"ip": r[0], "count": r[1]} for r in cursor.fetchall()]

                cursor.execute("""
                    SELECT path, COUNT(*) as count
                    FROM request_logs
                    GROUP BY path
                    ORDER BY count DESC
                    LIMIT 5
                """)
                top_paths = [{"path": r[0], "count": r[1]} for r in cursor.fetchall()]

                return {
                    "total_requests": total,
                    "unique_ips": unique_ips,
                    "top_ips": top_ips,
                    "top_paths": top_paths
                }
        except Exception as e:
            logger.warning(f"Failed to get request stats: {e}")
            return {"total_requests": 0, "unique_ips": 0, "top_ips": [], "top_paths": []}

    def clear_old_requests(self, days: int = 30) -> int:
        """Purge request logs older than the specified number of days."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM request_logs
                    WHERE datetime(timestamp) < datetime('now', ?)
                """, (f"-{days} days",))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.warning(f"Failed to purge old request logs: {e}")
            return 0


_REQUEST_STORE: Optional[RequestStore] = None


def get_request_store() -> RequestStore:
    """Singleton getter for RequestStore."""
    global _REQUEST_STORE
    if _REQUEST_STORE is None:
        _REQUEST_STORE = RequestStore()
    return _REQUEST_STORE


def log_inbound_request(
    ip_address: str,
    method: str,
    path: str,
    query_params: Optional[Any] = None,
    headers: Optional[Dict[str, Any]] = None,
    body_payload: Optional[Any] = None,
    user_details: Optional[Any] = None,
    status_code: int = 200,
    duration_ms: float = 0.0,
    source: str = "http"
) -> int:
    """Convenience helper to log an inbound request."""
    return get_request_store().log_request(
        ip_address=ip_address,
        method=method,
        path=path,
        query_params=query_params,
        headers=headers,
        body_payload=body_payload,
        user_details=user_details,
        status_code=status_code,
        duration_ms=duration_ms,
        source=source
    )

