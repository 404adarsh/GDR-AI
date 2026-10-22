"""Deterministic Channel Authentication and Authorization Module.

Provides secure, deterministic user authorization outside the LLM.
Supports username allowlists, verified platform account IDs, and secure password fallback
with Argon2/scrypt hashing, rate-limiting, and temporary authenticated sessions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple

from gdr.config import load_config, save_config
from gdr.safety.secrets import get_secret

logger = logging.getLogger("gdr.safety.auth")

DEFAULT_MASTER_PASSWORD_ENV = "BOT_MASTER_PASSWORD"
# Default fallback password salt (fixed per installation)
SALT_DEFAULT = b"gdr_ai_aarushi_companion_salt_2026"


def normalize_username(username: Optional[str]) -> str:
    """Normalize username by stripping whitespace and leading '@' and lowercasing."""
    if not username:
        return ""
    return str(username).strip().lstrip("@").lower()


def hash_password(password: str, salt: bytes = SALT_DEFAULT) -> str:
    """Generate secure password hash using scrypt."""
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024
    )
    return key.hex()


@dataclass
class AuthenticatedSession:
    channel: str
    user_id: str
    username: str
    authenticated_at: datetime
    expires_at: datetime

    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < self.expires_at


class ChannelAuthManager:
    """Deterministic channel authentication & authorization manager."""

    _instance: Optional["ChannelAuthManager"] = None

    def __init__(self):
        # In-memory authenticated sessions: (channel, user_id) -> AuthenticatedSession
        self._sessions: Dict[Tuple[str, str], AuthenticatedSession] = {}
        # Failed password attempts tracking for rate-limiting: (channel, user_id) -> [timestamps]
        self._failed_attempts: Dict[Tuple[str, str], List[datetime]] = {}
        # Rate limit parameters
        self.max_attempts = 5
        self.lockout_minutes = 5
        self.session_duration_hours = 24

    @classmethod
    def get_instance(cls) -> "ChannelAuthManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _is_rate_limited(self, channel: str, user_id: str) -> bool:
        """Check if user is currently locked out due to too many failed attempts."""
        key = (channel, str(user_id))
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.lockout_minutes)
        attempts = [ts for ts in self._failed_attempts.get(key, []) if ts > cutoff]
        self._failed_attempts[key] = attempts
        return len(attempts) >= self.max_attempts

    def _record_failed_attempt(self, channel: str, user_id: str):
        """Record a failed authentication attempt."""
        key = (channel, str(user_id))
        now = datetime.now(timezone.utc)
        if key not in self._failed_attempts:
            self._failed_attempts[key] = []
        self._failed_attempts[key].append(now)

    def _clear_failed_attempts(self, channel: str, user_id: str):
        """Clear failed attempts on successful authentication."""
        key = (channel, str(user_id))
        self._failed_attempts.pop(key, None)

    def is_authorized(
        self,
        channel: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        auto_bind_initial: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Deterministically determine if sender is authorized.

        Returns:
            (is_authorized, reason)
        """
        user_id_str = str(user_id).strip() if user_id is not None else ""
        norm_username = normalize_username(username)

        # 1. Check existing authenticated session
        if user_id_str:
            sess = self._sessions.get((channel, user_id_str))
            if sess and sess.is_valid():
                return True, "ACTIVE_SESSION"

        cfg = config if config is not None else load_config()
        c_cfg = cfg.get("channels", {})

        # Parse authorized usernames for this channel
        raw_unames = ""
        allowed_uid_str = ""
        if channel == "telegram":
            raw_unames = c_cfg.get("allowed_telegram_usernames") or c_cfg.get("allowed_telegram_username", "") or get_secret("ALLOWED_TELEGRAM_USERNAME") or os.environ.get("ALLOWED_TELEGRAM_USERNAME", "")
            allowed_uid_str = str(c_cfg.get("allowed_telegram_user_id", "") or get_secret("ALLOWED_TELEGRAM_USER_ID") or os.environ.get("ALLOWED_TELEGRAM_USER_ID", "")).strip()
        elif channel == "markanm":
            raw_unames = c_cfg.get("allowed_markanm_usernames") or c_cfg.get("allowed_markanm_username", "") or get_secret("ALLOWED_MARKANM_USERNAME") or os.environ.get("ALLOWED_MARKANM_USERNAME", "")
            allowed_uid_str = str(c_cfg.get("allowed_markanm_user_id", "") or get_secret("ALLOWED_MARKANM_USER_ID") or os.environ.get("ALLOWED_MARKANM_USER_ID", "")).strip()
        else:
            raw_unames = c_cfg.get("allowed_usernames", "") or get_secret("ALLOWED_USERNAME") or os.environ.get("ALLOWED_USERNAME", "")
            allowed_uid_str = str(c_cfg.get("allowed_user_id", "") or get_secret("ALLOWED_USER_ID") or os.environ.get("ALLOWED_USER_ID", "")).strip()

        allowed_unames: List[str] = []
        if isinstance(raw_unames, list):
            allowed_unames = [normalize_username(x) for x in raw_unames if normalize_username(x)]
        elif raw_unames:
            allowed_unames = [normalize_username(x) for x in re.split(r"[,;\s]+", str(raw_unames)) if normalize_username(x)]

        owner_name = normalize_username(get_secret("USER_NAME") or os.environ.get("USER_NAME", ""))
        if owner_name and owner_name not in ("user", "default", "owner", "admin"):
            if owner_name not in allowed_unames:
                allowed_unames.append(owner_name)

        # 2. Match against configured usernames
        if allowed_unames and norm_username and norm_username in allowed_unames:
            # Securely bind platform account ID so future messages with missing username succeed
            if user_id_str and (not allowed_uid_str or allowed_uid_str != user_id_str):
                self._bind_account(channel, user_id_str, norm_username)
            # Create session
            if user_id_str:
                self._create_session(channel, user_id_str, norm_username)
            return True, "USERNAME_MATCH"

        # 3. Match against configured platform User ID
        if allowed_uid_str and user_id_str and allowed_uid_str == user_id_str:
            if user_id_str:
                self._create_session(channel, user_id_str, norm_username)
            return True, "USER_ID_MATCH"

        # 4. Auto-bind initial user if neither username nor ID is locked yet
        if auto_bind_initial and not allowed_unames and not allowed_uid_str and (user_id_str or norm_username):
            self._bind_account(channel, user_id_str, norm_username)
            if user_id_str:
                self._create_session(channel, user_id_str, norm_username)
            return True, "INITIAL_SETUP_BIND"

        return False, "AUTHENTICATION_REQUIRED"

    def authenticate_password(
        self,
        channel: str,
        user_id: str,
        username: Optional[str],
        candidate_password: str
    ) -> Tuple[bool, str]:
        """Verify candidate master password for fallback authentication.

        Returns:
            (success, message)
        """
        user_id_str = str(user_id).strip()
        norm_username = normalize_username(username)

        if not isinstance(candidate_password, str):
            return False, "Password must be a string."
        if not candidate_password or not candidate_password.strip():
            return False, "Password cannot be empty."

        clean_pw = candidate_password.strip()

        # Check rate limiting
        if self._is_rate_limited(channel, user_id_str):
            logger.warning(f"Auth rate limit triggered for channel '{channel}' user '{user_id_str}'")
            return False, "⏳ Too many failed attempts. Please wait 5 minutes before trying again."

        # Fetch configured master password hash or plaintext env fallback
        expected_hash = (get_secret("BOT_MASTER_PASSWORD_HASH") or "").strip()
        env_pw = (os.environ.get(DEFAULT_MASTER_PASSWORD_ENV) or get_secret("BOT_MASTER_PASSWORD") or "").strip()

        matched = False
        if expected_hash and hmac.compare_digest(hash_password(clean_pw), expected_hash):
            matched = True
        elif env_pw and hmac.compare_digest(clean_pw, env_pw):
            matched = True

        if not matched:
            self._record_failed_attempt(channel, user_id_str)
            logger.warning(f"Failed authentication attempt for channel '{channel}' user '{user_id_str}'")
            return False, "❌ Authentication failed: Invalid password. Please check your credentials."

        # Success: clear failed attempts, bind account, and create active session
        self._clear_failed_attempts(channel, user_id_str)
        self._bind_account(channel, user_id_str, norm_username)
        self._create_session(channel, user_id_str, norm_username)
        logger.info(f"Successfully authenticated session for channel '{channel}' user '{user_id_str}' ({norm_username})")
        return True, "✅ Authentication successful. Your session is now verified and active."

    def _create_session(self, channel: str, user_id: str, username: str):
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.session_duration_hours)
        sess = AuthenticatedSession(
            channel=channel,
            user_id=user_id,
            username=username,
            authenticated_at=now,
            expires_at=expires
        )
        self._sessions[(channel, user_id)] = sess

    def _bind_account(self, channel: str, user_id: str, username: str):
        """Securely bind the verified user ID and username in configuration."""
        try:
            cfg = load_config()
            cfg.setdefault("channels", {})
            if channel == "telegram":
                if user_id:
                    cfg["channels"]["allowed_telegram_user_id"] = int(user_id) if user_id.isdigit() else user_id
                    cfg["channels"]["telegram_chat_id"] = str(user_id)
                if username and not cfg["channels"].get("allowed_telegram_usernames"):
                    cfg["channels"]["allowed_telegram_username"] = username
            elif channel == "markanm":
                if user_id:
                    cfg["channels"]["allowed_markanm_user_id"] = str(user_id)
                if username and not cfg["channels"].get("allowed_markanm_usernames"):
                    cfg["channels"]["allowed_markanm_username"] = username
            save_config(cfg)
        except Exception as e:
            logger.warning(f"Error persisting channel account binding: {e}")

    def revoke_session(self, channel: str, user_id: str):
        """Revoke active authenticated session."""
        self._sessions.pop((channel, str(user_id)), None)


def get_channel_auth_manager() -> ChannelAuthManager:
    return ChannelAuthManager.get_instance()
