"""Multi-Account Google OAuth 2.0 Manager for blockbrain AI.
Supports multiple accounts (personal, college, work).
Tokens are stored securely in system keyring, never in plain config files.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional
import urllib.parse

from blockbrain.safety.secrets import get_secret, set_secret

logger = logging.getLogger("blockbrain.google.auth")

DEFAULT_CONFIG_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
ACCOUNTS_FILE = DEFAULT_CONFIG_DIR / "google_accounts.json"

DEFAULT_READONLY_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
]

WRITE_SCOPES = {
    "gmail_send": "https://www.googleapis.com/auth/gmail.send",
    "gmail_compose": "https://www.googleapis.com/auth/gmail.compose",
    "calendar_write": "https://www.googleapis.com/auth/calendar.events",
}

KEYRING_SERVICE = "blockbrain_google_oauth"


class GoogleAuthManager:
    """Manages multi-account OAuth 2.0 credentials and token lifecycles."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.accounts_file = self.config_dir / "google_accounts.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.accounts_file.exists():
            self._save_accounts_meta({})

    def _load_accounts_meta(self) -> Dict[str, Any]:
        if not self.accounts_file.exists():
            return {}
        try:
            with open(self.accounts_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read google_accounts.json: {e}")
            return {}

    def _save_accounts_meta(self, data: Dict[str, Any]) -> None:
        tmp_file = self.accounts_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(data, f, indent=2)
        tmp_file.replace(self.accounts_file)

    def list_accounts(self) -> List[Dict[str, Any]]:
        """List all registered accounts with status and warning info."""
        accounts = self._load_accounts_meta()
        result = []
        now = time.time()
        for acc_id, meta in accounts.items():
            account_info = dict(meta)
            account_info["id"] = acc_id

            # Check 7-day refresh token testing mode warning
            created_at = meta.get("created_at_epoch", now)
            days_active = (now - created_at) / 86400.0
            account_info["days_active"] = round(days_active, 1)

            if meta.get("testing_mode", True) and days_active >= 6.0:
                account_info["warning"] = (
                    f"Account '{meta.get('label', acc_id)}' refresh token expires in ~"
                    f"{max(0, round(7.0 - days_active, 1))} days due to Google OAuth Testing mode limit. "
                    "Re-authorization recommended."
                )
            result.append(account_info)
        return result

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        accounts = self._load_accounts_meta()
        return accounts.get(account_id)

    def add_account(
        self,
        account_id: str,
        label: str,
        email: str,
        client_id: str = "mock_client_id",
        client_secret: str = "mock_client_secret",
        scopes: Optional[List[str]] = None,
        can_send: bool = False,
        can_write_calendar: bool = False,
        refresh_token: str = "mock_refresh_token",
        access_token: str = "mock_access_token",
        expires_in: int = 3600,
        is_mock: bool = False,
        testing_mode: bool = True,
    ) -> Dict[str, Any]:
        """Register a new Google account and store secret tokens in keyring."""
        accounts = self._load_accounts_meta()
        now = time.time()

        assigned_scopes = list(scopes or DEFAULT_READONLY_SCOPES)
        if can_send and WRITE_SCOPES["gmail_send"] not in assigned_scopes:
            assigned_scopes.append(WRITE_SCOPES["gmail_send"])
        if can_write_calendar and WRITE_SCOPES["calendar_write"] not in assigned_scopes:
            assigned_scopes.append(WRITE_SCOPES["calendar_write"])

        meta = {
            "label": label,
            "email": email,
            "scopes": assigned_scopes,
            "can_send": can_send,
            "can_write_calendar": can_write_calendar,
            "is_mock": is_mock,
            "testing_mode": testing_mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_at_epoch": now,
            "expires_at": now + expires_in,
            "status": "active",
        }

        # Store tokens securely in keyring
        token_payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "access_token": access_token,
        }
        set_secret(account_id, json.dumps(token_payload), service=KEYRING_SERVICE)

        accounts[account_id] = meta
        self._save_accounts_meta(accounts)
        logger.info(f"Registered Google account '{label}' ({email}) [{account_id}]")
        return {"id": account_id, **meta}

    def remove_account(self, account_id: str) -> bool:
        accounts = self._load_accounts_meta()
        if account_id in accounts:
            del accounts[account_id]
            self._save_accounts_meta(accounts)
            try:
                set_secret(account_id, "", service=KEYRING_SERVICE)
            except Exception:
                pass
            return True
        return False

    def get_token(self, account_id: str) -> Optional[str]:
        """Get valid access token, auto-refreshing if expired."""
        account = self.get_account(account_id)
        if not account:
            return None

        # If mock mode, return mock access token directly
        if account.get("is_mock", False):
            return "mock_access_token_" + account_id

        token_raw = get_secret(account_id, service=KEYRING_SERVICE)
        if not token_raw:
            logger.warning(f"No keyring credentials found for {account_id}")
            return None

        try:
            tokens = json.loads(token_raw)
        except Exception:
            return None

        now = time.time()
        # If expired or expiring in < 300s, refresh
        if now >= account.get("expires_at", 0) - 300:
            refreshed = self._refresh_access_token(account_id, tokens)
            if refreshed:
                return refreshed
            else:
                account["status"] = "expired"
                accounts = self._load_accounts_meta()
                accounts[account_id] = account
                self._save_accounts_meta(accounts)
                return None

        return tokens.get("access_token")

    def _refresh_access_token(self, account_id: str, tokens: Dict[str, str]) -> Optional[str]:
        """Refresh OAuth2 access token with Google token endpoint."""
        import urllib.request
        import urllib.error

        refresh_token = tokens.get("refresh_token")
        client_id = tokens.get("client_id")
        client_secret = tokens.get("client_secret")

        if not refresh_token or not client_id or not client_secret:
            return None

        data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                new_token = res.get("access_token")
                expires_in = res.get("expires_in", 3600)
                tokens["access_token"] = new_token
                set_secret(f"{KEYRING_SERVICE}_{account_id}", json.dumps(tokens))

                accounts = self._load_accounts_meta()
                if account_id in accounts:
                    accounts[account_id]["expires_at"] = time.time() + expires_in
                    accounts[account_id]["status"] = "active"
                    self._save_accounts_meta(accounts)
                return new_token
        except Exception as e:
            logger.error(f"Failed to refresh token for {account_id}: {e}")
            return None
