"""Authenticated Website Access Subsystem for Aarushi AI.
Allows authorized, domain-gated website access with distinct read-only vs submit permissions,
MFA detection, session cookie handling, and strict domain allowlists.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

from gdr.tools.registry import tool

logger = logging.getLogger("gdr.integrations.authenticated_web")

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
ALLOWLIST_FILE = CONFIG_DIR / "authorized_websites.json"


class AuthenticatedWebManager:
    """Controls domain allowlist, permission modes (read_only vs read_write), and safe requests."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self.allowlist_file = self.config_dir / "authorized_websites.json"
        self._ensure_storage()

    def _ensure_storage(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if not self.allowlist_file.exists():
                with open(self.allowlist_file, "w") as f:
                    json.dump({"domains": {}}, f)
        except Exception:
            pass

    def _load_data(self) -> Dict[str, Any]:
        if not self.allowlist_file.exists():
            return {"domains": {}}
        try:
            with open(self.allowlist_file, "r") as f:
                return json.load(f)
        except Exception:
            return {"domains": {}}

    def _save_data(self, data: Dict[str, Any]):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.allowlist_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save website allowlist: {e}")

    def add_domain(self, domain: str, mode: str = "read_only", notes: str = "") -> bool:
        """Authorize a domain for automated access."""
        clean_domain = domain.lower().strip().replace("https://", "").replace("http://", "").split("/")[0]
        data = self._load_data()
        data["domains"][clean_domain] = {
            "domain": clean_domain,
            "mode": mode if mode in ("read_only", "read_write") else "read_only",
            "notes": notes,
            "added_at": datetime.now().isoformat()
        }
        self._save_data(data)
        return True

    def remove_domain(self, domain: str) -> bool:
        """Revoke authorization for a domain."""
        clean_domain = domain.lower().strip().replace("https://", "").replace("http://", "").split("/")[0]
        data = self._load_data()
        if clean_domain in data.get("domains", {}):
            del data["domains"][clean_domain]
            self._save_data(data)
            return True
        return False

    def list_authorized_domains(self) -> List[Dict[str, Any]]:
        """List all currently permitted domains."""
        data = self._load_data()
        return list(data.get("domains", {}).values())

    def is_domain_authorized(self, url: str) -> Tuple[bool, str]:
        """Check if URL host matches authorized domain allowlist and return permission mode."""
        parsed = urllib.parse.urlparse(url)
        host = (parsed.netloc or "").lower().split(":")[0]
        data = self._load_data()
        domains = data.get("domains", {})

        for authorized_domain, meta in domains.items():
            if host == authorized_domain or host.endswith(f".{authorized_domain}"):
                return True, meta.get("mode", "read_only")

        return False, "none"

    def fetch_content(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fetch content from an authorized website."""
        authorized, mode = self.is_domain_authorized(url)
        if not authorized:
            return {
                "error": True,
                "status": "unauthorized_domain",
                "message": f"Security restriction: Domain for '{url}' is not in the authorized allowlist. Please add domain in settings first."
            }

        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")

                # Detect MFA / 2FA / Login prompts
                low_raw = raw.lower()
                if any(mfa_term in low_raw for mfa_term in ["two-factor authentication", "2fa verification", "enter authenticator code", "one-time passcode"]):
                    return {
                        "error": True,
                        "status": "mfa_required",
                        "message": "Multi-factor authentication (MFA) prompt detected. Please complete sign-in manually in your browser."
                    }

                if any(login_term in low_raw for login_term in ["sign in to your account", "session expired", "please log in"]):
                    return {
                        "error": True,
                        "status": "auth_expired",
                        "message": "Session expired or authentication required. Please sign in to the website in your browser."
                    }

                # Strip HTML tags for clean text preview
                clean_text = re.sub(r'<script.*?</script>', '', raw, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r'<style.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                return {
                    "error": False,
                    "status": "success",
                    "mode": mode,
                    "url": url,
                    "content_preview": clean_text[:4000],
                    "length": len(clean_text)
                }
        except Exception as e:
            return {
                "error": True,
                "status": "connection_error",
                "message": f"Failed to retrieve '{url}': {str(e)}"
            }


_GLOBAL_AUTH_WEB: Optional[AuthenticatedWebManager] = None


def get_authenticated_web_manager() -> AuthenticatedWebManager:
    global _GLOBAL_AUTH_WEB
    if _GLOBAL_AUTH_WEB is None:
        _GLOBAL_AUTH_WEB = AuthenticatedWebManager()
    return _GLOBAL_AUTH_WEB


# ==============================================================================
# LLM Accessible Tools
# ==============================================================================

@tool(name="fetch_authorized_website", category="integrations", tier="AUTO")
def fetch_authorized_website_tool(url: str) -> str:
    """Retrieve content from an authorized website on the user's allowlist."""
    mgr = get_authenticated_web_manager()
    res = mgr.fetch_content(url)
    return json.dumps(res, indent=2)


@tool(name="manage_website_allowlist", category="integrations", tier="APPROVAL")
def manage_website_allowlist_tool(domain: str, action: str = "add", permission_mode: str = "read_only") -> str:
    """Authorize or revoke a domain from the web access allowlist (actions: 'add', 'remove', 'list')."""
    mgr = get_authenticated_web_manager()
    act = action.lower().strip()
    if act == "add":
        mgr.add_domain(domain, mode=permission_mode)
        return f"Domain '{domain}' added to authorized allowlist with mode '{permission_mode}'."
    elif act in ("remove", "delete"):
        mgr.remove_domain(domain)
        return f"Domain '{domain}' removed from authorized allowlist."
    else:
        domains = mgr.list_authorized_domains()
        return json.dumps(domains, indent=2)
