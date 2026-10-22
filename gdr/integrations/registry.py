"""Integration Registry for GDR-AI and Aarushi.
Tracks connected workspaces, accounts (Google, Email, Telegram, Mesh),
their sync state, and permissions. Prevents hallucinating unlinked services.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from gdr.safety.secrets import get_secret
from gdr.config import load_config


class IntegrationRegistry:
    """Central registry tracking connected accounts, permissions, and status."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_status(self, service_name: str) -> Dict[str, Any]:
        """Check connection status and permission scopes for a specific service."""
        svc = service_name.lower().strip()

        if svc in ("google", "google_workspace", "gmail", "calendar"):
            return self._check_google_status()
        elif svc in ("email", "imap", "smtp"):
            return self._check_email_status()
        elif svc in ("telegram", "telegram_bot"):
            return self._check_telegram_status()
        elif svc in ("mesh", "android", "device"):
            return self._check_mesh_status()
        elif svc in ("local_files", "system"):
            return {
                "service": "local_files",
                "is_connected": True,
                "status": "connected",
                "permissions": ["read", "write", "execute"],
                "account_label": "Local System Host",
                "last_sync": datetime.now().isoformat(),
            }
        else:
            return {
                "service": svc,
                "is_connected": False,
                "status": "unlinked",
                "permissions": [],
                "account_label": None,
                "message": f"Service '{service_name}' is not recognized or configured.",
            }

    def _check_google_status(self) -> Dict[str, Any]:
        """Check if Google Workspace / OAuth is configured and valid."""
        try:
            from gdr.google.auth import GoogleAuthManager
            auth = GoogleAuthManager()
            accounts = auth.list_accounts()
            if accounts:
                active = [a for a in accounts if a.get("status") == "active"]
                if active:
                    return {
                        "service": "google_workspace",
                        "is_connected": True,
                        "status": "connected",
                        "accounts_count": len(accounts),
                        "primary_email": active[0].get("email") or active[0].get("label"),
                        "permissions": ["read", "draft", "calendar"],
                        "accounts": accounts,
                        "message": f"{len(active)} Google account(s) connected.",
                    }
                else:
                    return {
                        "service": "google_workspace",
                        "is_connected": False,
                        "status": "auth_expired",
                        "permissions": [],
                        "message": "Google accounts configured but tokens need re-authentication.",
                    }
        except Exception as e:
            pass

        return {
            "service": "google_workspace",
            "is_connected": False,
            "status": "unlinked",
            "permissions": [],
            "message": "Google Workspace is not connected. Add credentials via Settings or CLI.",
        }

    def _check_email_status(self) -> Dict[str, Any]:
        """Check if IMAP/SMTP credentials exist in keyring / environment."""
        addr = get_secret("EMAIL_ADDRESS")
        pwd = get_secret("EMAIL_APP_PASSWORD")

        if addr and pwd:
            return {
                "service": "email",
                "is_connected": True,
                "status": "connected",
                "account_email": addr,
                "permissions": ["read", "draft", "send"],
                "message": f"Email inbox connected ({addr}).",
            }

        # Check if Google workspace has email
        g_stat = self._check_google_status()
        if g_stat.get("is_connected"):
            return {
                "service": "email",
                "is_connected": True,
                "status": "connected",
                "account_email": g_stat.get("primary_email"),
                "permissions": ["read", "draft"],
                "message": f"Gmail connected via Google Workspace ({g_stat.get('primary_email')}).",
            }

        return {
            "service": "email",
            "is_connected": False,
            "status": "unlinked",
            "permissions": [],
            "message": "Email is not configured. Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD, or link Google Workspace.",
        }

    def _check_telegram_status(self) -> Dict[str, Any]:
        token = get_secret("TELEGRAM_BOT_TOKEN")
        chat_id = get_secret("TELEGRAM_CHAT_ID")
        if token and chat_id:
            return {
                "service": "telegram",
                "is_connected": True,
                "status": "connected",
                "permissions": ["send_notifications"],
                "chat_id": chat_id,
            }
        return {
            "service": "telegram",
            "is_connected": False,
            "status": "unlinked",
            "permissions": [],
        }

    def _check_mesh_status(self) -> Dict[str, Any]:
        try:
            from gdr.mesh.hub import get_mesh_hub
            hub = get_mesh_hub()
            devices = hub.list_devices()
            online = [d for d in devices if d.get("status") == "online"]
            return {
                "service": "mesh",
                "is_connected": len(online) > 0,
                "status": "connected" if online else "idle",
                "devices_total": len(devices),
                "devices_online": len(online),
                "online_devices": [d.get("name") for d in online],
            }
        except Exception:
            return {
                "service": "mesh",
                "is_connected": False,
                "status": "unlinked",
                "devices_total": 0,
            }

    def list_all_integrations(self) -> Dict[str, Dict[str, Any]]:
        """List statuses of all key system integrations."""
        return {
            "google_workspace": self._check_google_status(),
            "email": self._check_email_status(),
            "telegram": self._check_telegram_status(),
            "mesh": self._check_mesh_status(),
            "local_system": self.get_status("local_files"),
        }

    def get_service_guard_message(self, service_name: str) -> Optional[str]:
        """If a service is unlinked, return a polite natural response for the assistant.
        Returns None if connected.
        """
        stat = self.get_status(service_name)
        if stat.get("is_connected"):
            return None
        
        svc_label = service_name.replace("_", " ").title()
        return (
            f"Aapka {svc_label} account abhi connect nahi hai. "
            f"Maine koi simulated action execute nahi kiya. "
            f"Aap settings ya Command Palette me credentials add karke ise aasani se link kar sakte hain!"
        )


_INTEGRATION_REGISTRY = None


def get_integration_registry() -> IntegrationRegistry:
    global _INTEGRATION_REGISTRY
    if _INTEGRATION_REGISTRY is None:
        _INTEGRATION_REGISTRY = IntegrationRegistry()
    return _INTEGRATION_REGISTRY

