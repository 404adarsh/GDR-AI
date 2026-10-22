"""Configurable Integration Registry for User-Provided APIs in Aarushi AI.
Allows users to securely connect arbitrary external APIs (bearer, api_key, basic)
with encrypted secret storage, rate limiting, timeout protection, and on-demand fresh queries.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional

from gdr.safety.secrets import get_secret, _save_env_secret
from gdr.tools.registry import tool

logger = logging.getLogger("gdr.integrations.custom_api")

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
CUSTOM_APIS_FILE = CONFIG_DIR / "custom_apis.json"


class CustomAPIRegistry:
    """Manages user-registered external APIs with secure token encryption."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self.registry_file = self.config_dir / "custom_apis.json"
        self._rate_limit_tracker: Dict[str, List[float]] = {}
        self._ensure_storage()

    def _ensure_storage(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if not self.registry_file.exists():
                with open(self.registry_file, "w") as f:
                    json.dump({}, f)
        except Exception:
            pass

    def _load_registry(self) -> Dict[str, Any]:
        if not self.registry_file.exists():
            return {}
        try:
            with open(self.registry_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_registry(self, data: Dict[str, Any]):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save custom APIs: {e}")

    def register_api(
        self,
        name: str,
        base_url: str,
        description: str,
        auth_type: str = "bearer",
        auth_token: Optional[str] = None,
        auth_header: str = "Authorization",
        rate_limit_per_minute: int = 60,
        timeout_seconds: float = 10.0
    ) -> Dict[str, Any]:
        """Register a user API. Stores tokens securely using secret key references."""
        clean_name = name.strip().lower().replace(" ", "_")
        registry = self._load_registry()

        secret_key_ref = f"CUSTOM_API_{clean_name.upper()}_KEY"
        if auth_token:
            _save_env_secret(secret_key_ref, auth_token)
            os.environ[secret_key_ref] = auth_token

        api_meta = {
            "name": clean_name,
            "title": name.strip(),
            "base_url": base_url.strip().rstrip("/"),
            "description": description.strip(),
            "auth_type": auth_type.strip().lower(),
            "auth_header": auth_header.strip(),
            "secret_key_ref": secret_key_ref if auth_token else None,
            "has_auth": bool(auth_token),
            "rate_limit_per_minute": rate_limit_per_minute,
            "timeout_seconds": timeout_seconds,
            "registered_at": datetime.now().isoformat()
        }

        registry[clean_name] = api_meta
        self._save_registry(registry)
        return {"status": "ok", "message": f"API '{clean_name}' successfully registered.", "meta": api_meta}

    def delete_api(self, name: str) -> bool:
        """Remove an API from the registry."""
        clean_name = name.strip().lower().replace(" ", "_")
        registry = self._load_registry()
        if clean_name in registry:
            del registry[clean_name]
            self._save_registry(registry)
            return True
        return False

    def list_apis(self) -> List[Dict[str, Any]]:
        """List registered APIs without exposing private tokens."""
        registry = self._load_registry()
        res = []
        for meta in registry.values():
            safe_copy = dict(meta)
            # Never return secret tokens or secret key refs
            safe_copy.pop("secret_key_ref", None)
            res.append(safe_copy)
        return res

    def _check_rate_limit(self, name: str, limit_per_minute: int) -> bool:
        now = time.time()
        calls = self._rate_limit_tracker.get(name, [])
        calls = [t for t in calls if (now - t) < 60.0]
        if len(calls) >= limit_per_minute:
            return False
        calls.append(now)
        self._rate_limit_tracker[name] = calls
        return True

    def query(
        self,
        name: str,
        path: str = "",
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetch fresh on-demand information from a connected user API."""
        clean_name = name.strip().lower().replace(" ", "_")
        registry = self._load_registry()

        if clean_name not in registry:
            return {
                "error": True,
                "status_code": 404,
                "message": f"API '{name}' is not registered. Available: {list(registry.keys())}"
            }

        meta = registry[clean_name]
        limit = meta.get("rate_limit_per_minute", 60)
        if not self._check_rate_limit(clean_name, limit):
            return {
                "error": True,
                "status_code": 429,
                "message": f"Rate limit exceeded for '{clean_name}' ({limit} requests/min). Please try again shortly."
            }

        base = meta["base_url"]
        clean_path = path.strip().lstrip("/")
        full_url = f"{base}/{clean_path}" if clean_path else base

        if params:
            query_str = urllib.parse.urlencode(params)
            full_url = f"{full_url}?{query_str}" if "?" not in full_url else f"{full_url}&{query_str}"

        headers = {
            "User-Agent": "Aarushi-Assistant/2.0 (GDR-IDE)",
            "Accept": "application/json"
        }

        # Apply authentication
        auth_type = meta.get("auth_type", "none")
        secret_ref = meta.get("secret_key_ref")
        if secret_ref:
            token = get_secret(secret_ref)
            if token:
                if auth_type == "bearer":
                    headers[meta.get("auth_header", "Authorization")] = f"Bearer {token}"
                elif auth_type == "api_key":
                    headers[meta.get("auth_header", "X-API-Key")] = token
                elif auth_type == "basic":
                    import base64
                    b64 = base64.b64encode(token.encode("utf-8")).decode("utf-8")
                    headers["Authorization"] = f"Basic {b64}"

        req_data = None
        if payload is not None and method.upper() in ("POST", "PUT", "PATCH"):
            req_data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(full_url, data=req_data, headers=headers, method=method.upper())
        timeout = meta.get("timeout_seconds", 10.0)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                raw = resp.read().decode("utf-8")
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"raw_text": raw[:2000]}
                return {
                    "error": False,
                    "status_code": status_code,
                    "data": data,
                    "queried_at": datetime.now().isoformat()
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")[:500]
            if e.code in (401, 403):
                return {
                    "error": True,
                    "status_code": e.code,
                    "message": f"Authentication failed or expired for '{clean_name}'. Please update credentials.",
                    "details": err_body
                }
            return {
                "error": True,
                "status_code": e.code,
                "message": f"HTTP {e.code} error querying '{clean_name}'.",
                "details": err_body
            }
        except Exception as e:
            return {
                "error": True,
                "status_code": 500,
                "message": f"Connection error querying '{clean_name}': {str(e)}"
            }


_GLOBAL_CUSTOM_API_REGISTRY: Optional[CustomAPIRegistry] = None


def get_custom_api_registry() -> CustomAPIRegistry:
    global _GLOBAL_CUSTOM_API_REGISTRY
    if _GLOBAL_CUSTOM_API_REGISTRY is None:
        _GLOBAL_CUSTOM_API_REGISTRY = CustomAPIRegistry()
    return _GLOBAL_CUSTOM_API_REGISTRY


# ==============================================================================
# LLM Accessible Tool
# ==============================================================================

@tool(name="query_custom_api", category="integrations", tier="AUTO")
def query_custom_api_tool(
    api_name: str,
    path: str = "",
    params_json: Optional[str] = None
) -> str:
    """Retrieve fresh on-demand data from a connected user API (deployment status, tasks, monitoring)."""
    reg = get_custom_api_registry()
    params = None
    if params_json:
        try:
            params = json.loads(params_json)
        except Exception:
            pass

    res = reg.query(name=api_name, path=path, params=params)
    return json.dumps(res, indent=2)

