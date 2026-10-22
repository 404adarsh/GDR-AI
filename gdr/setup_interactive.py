"""Interactive Configuration & Credential Setup Wizard for GDR-AI.
Cross-platform interactive CLI for Windows, Linux, and macOS.
Reads existing .env settings, pre-fills current values, and allows re-running
anytime to edit or add credentials without overwriting previously configured keys.
"""

import os
from pathlib import Path
import sys
from typing import Dict, Optional

from gdr.system.compatibility import print_compatibility_report
from gdr.safety.secrets import _load_env_secrets, _save_env_secret, get_secret


def prompt_with_default(prompt_text: str, default_val: str = "", is_secret: bool = False) -> str:
    """Prompt user for input with pre-filled default value in brackets."""
    show_default = "••••••••" if (is_secret and default_val) else default_val
    if show_default:
        display_prompt = f"  {prompt_text} [{show_default}]: "
    else:
        display_prompt = f"  {prompt_text}: "

    try:
        user_input = input(display_prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        return default_val

    if not user_input:
        return default_val
    return user_input


def run_interactive_setup():
    """Run interactive setup wizard with pre-filled values."""
    print("\n" + "=" * 66)
    print("🌸 GDR-AI Interactive Setup & Configuration Wizard")
    print("=" * 66)
    print("Configure your AI companion, credentials, and channels.")
    print("• Press [ENTER] to keep existing / default values.")
    print("• You can re-run this setup anytime to update credentials!")
    print("=" * 66)

    # 1. System Compatibility
    print("\n[Step 1/3] Checking System Compatibility...")
    print_compatibility_report()

    # 2. Read existing .env credentials
    env_secrets = _load_env_secrets()
    project_dir = Path(__file__).resolve().parent.parent
    env_file = project_dir / ".env"

    curr_ai_name = env_secrets.get("ASSISTANT_NAME") or env_secrets.get("AI_NAME") or os.environ.get("ASSISTANT_NAME", "GDR-AI")
    curr_user_name = env_secrets.get("USER_NAME") or os.environ.get("USER_NAME", "User")
    curr_sarvam_key = env_secrets.get("SARVAM_API_KEY", "")
    curr_markanm_token = env_secrets.get("MARKANM_BOT_TOKEN", "")
    curr_markanm_user = env_secrets.get("ALLOWED_MARKANM_USERNAME", "")
    curr_tg_token = env_secrets.get("TELEGRAM_BOT_TOKEN", "")
    curr_tg_user = env_secrets.get("ALLOWED_TELEGRAM_USERNAME", "")
    curr_email = env_secrets.get("EMAIL_ADDRESS", "")
    curr_email_pwd = env_secrets.get("EMAIL_APP_PASSWORD", "")
    curr_bot_pw = env_secrets.get("BOT_MASTER_PASSWORD", "")
    curr_rag_pin = env_secrets.get("RAG_SECURITY_PIN") or env_secrets.get("RAG_MASTER_PIN", "")
    curr_eleven_key = env_secrets.get("ELEVENLABS_API_KEY", "")

    # 3. Interactive Inputs
    print("\n[Step 2/3] Identity & Companion Customization:")
    new_ai_name = prompt_with_default("AI Assistant Name", curr_ai_name)
    new_user_name = prompt_with_default("Your Name (User / Creator)", curr_user_name)

    print("\n[Step 3/3] API Credentials & Bot Platforms:")
    print("  (You can leave API keys blank and configure them later in the Web HUD)")
    new_sarvam_key = prompt_with_default("Sarvam AI API Key", curr_sarvam_key, is_secret=True)
    new_markanm_token = prompt_with_default("MarkanM Bot Token (chat.markanm.com)", curr_markanm_token, is_secret=True)
    new_markanm_user = prompt_with_default("Your MarkanM Username (Security Lock)", curr_markanm_user)
    new_tg_token = prompt_with_default("Telegram Bot Token (Optional)", curr_tg_token, is_secret=True)
    new_tg_user = prompt_with_default("Telegram Username (Security Lock)", curr_tg_user)

    print("\n  📧 Email Integration (Gmail / IMAP):")
    print("     (Requires a 16-character Google App Password from myaccount.google.com/apppasswords)")
    new_email = prompt_with_default("Email Address", curr_email)
    new_email_pwd = prompt_with_default("Google 16-Char App Password", curr_email_pwd, is_secret=True)

    print("\n  🔐 Security Passwords & Master PINs:")
    new_bot_pw = prompt_with_default("Bot Master Password (for /auth)", curr_bot_pw or "845457", is_secret=True)
    new_rag_pin = prompt_with_default("RAG Knowledge Vault PIN", curr_rag_pin or "845427", is_secret=True)

    # Clean app password spaces
    if new_email_pwd:
        new_email_pwd = new_email_pwd.replace(" ", "")

    # Write / Update .env file
    updated_keys = {
        "ASSISTANT_NAME": new_ai_name,
        "USER_NAME": new_user_name,
        "SARVAM_API_KEY": new_sarvam_key,
        "MARKANM_BOT_TOKEN": new_markanm_token,
        "ALLOWED_MARKANM_USERNAME": new_markanm_user,
        "TELEGRAM_BOT_TOKEN": new_tg_token,
        "ALLOWED_TELEGRAM_USERNAME": new_tg_user,
        "EMAIL_ADDRESS": new_email,
        "EMAIL_APP_PASSWORD": new_email_pwd,
        "BOT_MASTER_PASSWORD": new_bot_pw,
        "RAG_MASTER_PIN": new_rag_pin,
        "RAG_SECURITY_PIN": new_rag_pin,
    }

    # Save each secret
    for k, v in updated_keys.items():
        if v:
            _save_env_secret(k, v)
            os.environ[k] = v

    # Also update config.toml
    try:
        from gdr.config import load_config, save_config
        cfg = load_config()
        if "general" not in cfg:
            cfg["general"] = {}
        cfg["general"]["agent_name"] = new_ai_name
        cfg["general"]["user_name"] = new_user_name
        save_config(cfg)
    except Exception:
        pass

    # 4. Autostart Configuration
    print("\n[Step 4/4] Cross-Platform Autostart Configuration:")
    try:
        from gdr.system.autostart import prompt_autostart_configuration
        prompt_autostart_configuration(interactive=True)
    except Exception as e:
        print(f"  Autostart configuration skipped: {e}")

    print("\n" + "=" * 66)
    print("✅ Configuration saved successfully!")
    print(f"  • AI Assistant : {new_ai_name}")
    print(f"  • User Name    : {new_user_name}")
    print(f"  • Configuration: {env_file}")
    print("=" * 66 + "\n")


if __name__ == "__main__":
    run_interactive_setup()

