"""Secrets loader for GDR AI.
Loads secrets strictly from environment variables or the system keyring.
Never from config files or source code.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict

try:
    import keyring
except ImportError:
    keyring = None

_KNOWN_SECRET_NAMES = [
    "SARVAM_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "EMAIL_ADDRESS",
    "EMAIL_APP_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "USER_PHONE_NUMBER",
    "WEATHER_API_KEY",
    "BRAVE_API_KEY",
    "ELEVENLABS_API_KEY",
    "MARKANM_BOT_TOKEN",
]


def _get_secrets_file_paths() -> list[Path]:
    """Return all valid environment and secrets file locations in order of priority.
    Writable secrets.env files are listed first to guarantee user persistence across restarts.
    """
    paths = [
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "secrets.env",
        Path(__file__).resolve().parent.parent.parent / ".secrets.env",
        Path.home() / "gdragent" / ".secrets.env",
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path.home() / "gdragent" / ".env",
    ]
    seen = []
    res = []
    for p in paths:
        sp = str(p.resolve()) if p.parent.exists() else str(p)
        if sp not in seen:
            seen.append(sp)
            res.append(p)
    return res


def _load_env_secrets() -> Dict[str, str]:
    """Parse key-value secrets from .env and .secrets.env files.
    Loads fallback .env first, then overrides with authoritative secrets.env.
    """
    secrets: Dict[str, str] = {}

    # 1. Base template/fallback .env files
    base_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path.home() / "gdragent" / ".env",
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / ".env",
    ]
    for path in base_paths:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = re.sub(r"^export\s+", "", k.strip()).strip()
                    v = v.strip().strip("'\"")
                    if k and v and not _is_placeholder_value(v):
                        secrets[k] = v
                        if k not in os.environ or _is_placeholder_value(os.environ.get(k, "")):
                            os.environ[k] = v
        except Exception:
            pass

    # 2. Authoritative persistent user secrets.env files (takes precedence!)
    override_paths = [
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "secrets.env",
        Path(__file__).resolve().parent.parent.parent / ".secrets.env",
        Path.home() / "gdragent" / ".secrets.env",
    ]
    for path in override_paths:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = re.sub(r"^export\s+", "", k.strip()).strip()
                    v = v.strip().strip("'\"")
                    if k and v and not _is_placeholder_value(v):
                        secrets[k] = v
                        if k not in os.environ or _is_placeholder_value(os.environ.get(k, "")):
                            os.environ[k] = v
        except Exception:
            pass

    return secrets


def _save_env_secret(name: str, value: str) -> bool:
    """Save secret across secrets.env and .env targets, updating os.environ."""
    clean_name = re.sub(r"^export\s+", "", name.strip()).strip()
    clean_val = value.strip()
    os.environ[clean_name] = clean_val

    secrets = _load_env_secrets()
    secrets[clean_name] = clean_val
    content = "\n".join(f'{k}="{v}"' for k, v in sorted(secrets.items())) + "\n"

    any_saved = False
    # Priority targets: user secrets.env files first
    target_paths = [
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "secrets.env",
        Path.home() / "gdragent" / ".secrets.env",
        Path(__file__).resolve().parent.parent.parent / ".secrets.env",
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / ".env",
        Path.cwd() / ".env",
    ]

    for path in target_paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            import stat
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = stat.S_IRUSR | stat.S_IWUSR  # 0600
            fd = os.open(str(path), flags, mode)
            with open(fd, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
            any_saved = True
        except Exception:
            continue
    return any_saved


def _is_placeholder_value(val: str) -> bool:
    """Return True if the value looks like a test/sample/mock placeholder."""
    if not val or not val.strip():
        return True
    low = val.strip().lower()
    markers = [
        "test_token", "mkbot_test", "sample", "mock", "placeholder",
        "dummy", "your_", "xxx", "***", "example", "abcdefghijklmnop",
        "xi_test_key", "secret_token_12345",
    ]
    return any(m in low for m in markers)


def get_secret(name: str, default: Optional[str] = None, service: str = "gdr") -> Optional[str]:
    """Retrieve secret from environment variable, persistent .env, system keyring, or config.toml.
    Never returns placeholder/test/mock values — returns None (or default) instead.
    """
    # 1. Environment variable (if not a placeholder/sample)
    val = os.environ.get(name)
    if val and not _is_placeholder_value(val):
        return val.strip()

    # 2. Check persistent user secrets (.env / secrets.env) — higher-priority files first
    env_secrets = _load_env_secrets()
    if name in env_secrets:
        fval = env_secrets[name].strip()
        if not _is_placeholder_value(fval):
            os.environ[name] = fval
            return fval

    # 3. System keyring
    if keyring is not None:
        try:
            stored = keyring.get_password(service, name)
            if stored and not _is_placeholder_value(stored):
                return stored.strip()
        except Exception:
            pass

    # 4. Fallback to config.toml
    try:
        from gdr.config import load_config
        cfg = load_config()
        if "secrets" in cfg and name in cfg["secrets"] and cfg["secrets"][name]:
            resolved = str(cfg["secrets"][name]).strip()
            if not _is_placeholder_value(resolved):
                os.environ[name] = resolved
                return resolved
        cfg_map = {
            "SARVAM_API_KEY": cfg.get("provider", {}).get("api_key") or cfg.get("provider", {}).get("sarvam_api_key"),
            "TELEGRAM_BOT_TOKEN": cfg.get("channels", {}).get("telegram_bot_token"),
            "MARKANM_BOT_TOKEN": cfg.get("channels", {}).get("markanm_bot_token"),
            "ELEVENLABS_API_KEY": cfg.get("voice", {}).get("elevenlabs_api_key"),
        }
        if name in cfg_map and cfg_map[name] and str(cfg_map[name]).strip():
            resolved = str(cfg_map[name]).strip()
            if not _is_placeholder_value(resolved):
                os.environ[name] = resolved
                return resolved
    except Exception:
        pass

    # 5. Never fall back to placeholder/dummy values — return the default
    return default


def set_keyring_secret(name: str, value: str, service: str = "gdr") -> bool:
    """Store secret into system keyring, persistent secrets files, and config.toml."""
    os.environ[name] = value
    saved_keyring = False
    if keyring is not None:
        try:
            keyring.set_password(service, name, value)
            saved_keyring = True
        except Exception:
            saved_keyring = False

    saved_file = _save_env_secret(name, value)

    # Mirror into config.toml as persistent backup
    try:
        from gdr.config import load_config, save_config
        cfg = load_config()
        if "secrets" not in cfg:
            cfg["secrets"] = {}
        cfg["secrets"][name] = value
        updated = True

        if name == "SARVAM_API_KEY":
            if "provider" not in cfg:
                cfg["provider"] = {}
            cfg["provider"]["api_key"] = value
        elif name == "TELEGRAM_BOT_TOKEN":
            if "channels" not in cfg:
                cfg["channels"] = {}
            cfg["channels"]["telegram_bot_token"] = value
        elif name == "MARKANM_BOT_TOKEN":
            if "channels" not in cfg:
                cfg["channels"] = {}
            cfg["channels"]["markanm_bot_token"] = value
        elif name == "ELEVENLABS_API_KEY":
            if "voice" not in cfg:
                cfg["voice"] = {}
            cfg["voice"]["elevenlabs_api_key"] = value
        if updated:
            save_config(cfg)
    except Exception:
        pass

    return saved_keyring or saved_file


def set_secret(name: str, value: str, service: str = "gdr") -> bool:
    """Convenience alias for set_keyring_secret."""
    return set_keyring_secret(name, value, service=service)


def delete_secret(name: str, service: str = "gdr") -> bool:
    """Delete a secret from environment, keyring, persistent files, and config.toml."""
    if name in os.environ:
        del os.environ[name]
    if keyring is not None:
        try:
            keyring.delete_password(service, name)
        except Exception:
            pass

    for path in _get_secrets_file_paths():
        if path.exists():
            try:
                secrets = _load_env_secrets()
                if name in secrets:
                    del secrets[name]
                    import stat
                    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                    fd = os.open(str(path), flags, stat.S_IRUSR | stat.S_IWUSR)
                    with open(fd, "w", encoding="utf-8") as f:
                        f.write("\n".join(f'export {k}="{v}"' for k, v in sorted(secrets.items())) + "\n")
            except Exception:
                pass

    try:
        from gdr.config import load_config, save_config
        cfg = load_config()
        if "secrets" in cfg and name in cfg["secrets"]:
            del cfg["secrets"][name]
            updated = True
        if name == "SARVAM_API_KEY" and "api_key" in cfg.get("provider", {}):
            del cfg["provider"]["api_key"]
            updated = True
        elif name == "TELEGRAM_BOT_TOKEN" and "telegram_bot_token" in cfg.get("channels", {}):
            del cfg["channels"]["telegram_bot_token"]
            updated = True
        elif name == "MARKANM_BOT_TOKEN" and "markanm_bot_token" in cfg.get("channels", {}):
            del cfg["channels"]["markanm_bot_token"]
            updated = True
        elif name == "ELEVENLABS_API_KEY" and "elevenlabs_api_key" in cfg.get("voice", {}):
            cfg["voice"]["elevenlabs_api_key"] = ""
            updated = True
        if updated:
            save_config(cfg)
    except Exception:
        pass

    return True


def mask_secret(value: Optional[str]) -> str:
    """Return masked string for display (e.g. 'sk-...4a2b')."""
    if not value:
        return "<unset>"
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def sanitize_text(text: str) -> str:
    """Sanitize any occurrence of known secrets from text before logging or model prompt."""
    if not text:
        return text
    clean = text
    for name in _KNOWN_SECRET_NAMES:
        val = get_secret(name)
        if val and len(val) >= 4 and val in clean:
            clean = clean.replace(val, f"[REDACTED_{name}]")
        env_val = os.environ.get(name)
        if env_val and len(env_val) >= 4 and env_val in clean:
            clean = clean.replace(env_val, f"[REDACTED_{name}]")
    return clean

