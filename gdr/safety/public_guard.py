"""Public URL Security Guard for GDR AI.
Enforces host terminal approval for destructive or high-privilege actions requested over public tunnels.

Rules:
1. Actions requiring Host Terminal Permission when requested via Cloudflare Public URL:
   - Shutting down or rebooting PC / laptop.
   - Deleting any file or folder (e.g. delete_file, rm, unlink, shred).
   - Big administrative / privileged tasks (e.g. sudo, system modifications, process kills).
2. Actions allowed freely without terminal permission:
   - Sharing URLs, links, or bookmarks.
   - Information about the owner/user (from memory store) and agent capabilities.
   - General conversation, study, browsing, reading safe documents, and routine HUD tasks.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import select
import sys
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("gdr.safety.public_guard")

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
APPROVALS_FILE = CONFIG_DIR / "approval_queue.json"


def is_public_request(headers: Dict[str, str], client_ip: str = "127.0.0.1") -> bool:
    """Determine if request originated from Cloudflare Tunnel or external untrusted IP."""
    h_lower = {k.lower(): v for k, v in headers.items()}
    host_header = h_lower.get("host", "").lower()

    # Cloudflare Tunnel specific headers
    is_cf = bool(
        h_lower.get("cf-ray")
        or h_lower.get("cf-connecting-ip")
        or "trycloudflare.com" in host_header
        or "cloudflare" in host_header
    )
    if is_cf:
        return True

    # Check IP origin
    is_localhost = client_ip in ("127.0.0.1", "localhost", "::1", "testclient")
    is_tailscale = client_ip.startswith("100.")
    is_lan = client_ip.startswith("192.168.") or client_ip.startswith("10.") or (
        client_ip.startswith("172.")
        and len(client_ip.split(".")) > 1
        and client_ip.split(".")[1].isdigit()
        and 16 <= int(client_ip.split(".")[1]) <= 31
    )

    return not (is_localhost or is_tailscale or is_lan)


def classify_public_intent(prompt: str) -> Tuple[bool, str, str]:
    """Classify prompt into (is_sensitive, action_type, reason).
    Safe actions: sharing URLs, asking about the user/owner, conversation -> Not sensitive.
    Dangerous actions: shutdown, reboot, delete files, big administrative commands -> Sensitive.
    """
    p = prompt.lower().strip()

    # 1. Check safe whitelist exemptions (sharing URLs, info about user)
    safe_info_patterns = [
        "share url", "share link", "give me the url", "what is the url", "website url",
        "who is gdr", "tell me about gdr", "tell me about yourself", "about the owner",
        "who is the owner", "what does the owner do", "user hobbies", "what are your skills",
        "how are you", "what time is it", "what's the weather", "play music", "open google"
    ]
    if any(k in p for k in safe_info_patterns) and not any(k in p for k in ["delete", "rm ", "shutdown", "reboot", "format"]):
        return False, "safe_query", "Exempted: Safe knowledge, URL sharing, or informational query."

    # 2. Check Shutdown / Poweroff / Reboot
    shutdown_keywords = [
        "shutdown", "power off", "poweroff", "turn off pc", "turn off computer",
        "turn off laptop", "shut down", "halt system", "init 0", "systemctl poweroff"
    ]
    reboot_keywords = [
        "reboot", "restart pc", "restart computer", "restart laptop",
        "init 6", "systemctl reboot"
    ]
    if any(k in p for k in shutdown_keywords):
        return True, "shutdown_pc", "Attempting to shut down the host PC from a public URL."
    if any(k in p for k in reboot_keywords):
        return True, "reboot_pc", "Attempting to reboot the host PC from a public URL."

    # 3. Check File Deletion
    delete_keywords = [
        "delete file", "delete folder", "delete directory", "remove file",
        "remove folder", "rm ", "rm -rf", "unlink ", "shred ", "wipe file"
    ]
    if any(k in p for k in delete_keywords):
        return True, "delete_file", "Attempting to delete files or directories from a public URL."

    # 4. Check Big Administrative / Privileged Tasks
    big_task_keywords = [
        "sudo ", "run_privileged", "run_sudo", "killall", "kill -9",
        "format disk", "wipe disk", "mkfs", "chmod -r 777", "dd if="
    ]
    if any(k in p for k in big_task_keywords):
        return True, "big_task", "Attempting to execute privileged system command from a public URL."

    return False, "normal_action", "Safe non-destructive task."


def request_terminal_approval(action_type: str, prompt: str, timeout_sec: int = 30) -> bool:
    """Prompt the PC owner in the host terminal to authorize a sensitive public request.
    Uses non-blocking select so the request does not hang indefinitely.
    """
    banner = f"""
======================================================================
🚨 [GDR SECURITY ALERT: REMOTE ACTION FROM PUBLIC CLOUDFLARE URL]
Action Category: {action_type.upper().replace('_', ' ')}
Requested Prompt: "{prompt}"
A remote user on your public Cloudflare Tunnel requested this action!
👉 Authorize this action on your PC? [y/N] ({timeout_sec}s timeout): 
======================================================================
"""
    try:
        sys.stderr.write(banner)
        sys.stderr.flush()
    except Exception:
        pass

    # Record into approval queue file so user can also approve via 'gdr approve'
    appr_id = _record_pending_approval(action_type, prompt)

    # Check if stdin is interactive
    if not sys.stdin or not hasattr(sys.stdin, "fileno"):
        logger.warning("No interactive TTY attached. Requiring manual 'gdr approve' or auto-denying.")
        return False

    try:
        if not os.isatty(sys.stdin.fileno()):
            logger.warning("stdin is not a TTY. Auto-denying sensitive action.")
            return False

        r, _, _ = select.select([sys.stdin], [], [], timeout_sec)
        if r:
            line = sys.stdin.readline().strip().lower()
            if line in ("y", "yes"):
                sys.stderr.write("✅ Remote public action APPROVED by PC owner.\n\n")
                sys.stderr.flush()
                _resolve_recorded_approval(appr_id, approved=True)
                return True
            else:
                sys.stderr.write("❌ Remote public action DENIED by PC owner.\n\n")
                sys.stderr.flush()
                _resolve_recorded_approval(appr_id, approved=False)
                return False
        else:
            sys.stderr.write(f"\n⏰ Approval prompt timed out ({timeout_sec}s). Action DENIED.\n\n")
            sys.stderr.flush()
            _resolve_recorded_approval(appr_id, approved=False)
            return False
    except Exception as e:
        logger.error(f"Terminal approval error: {e}")
        return False


def _record_pending_approval(action_type: str, prompt: str) -> str:
    """Record pending approval in approval_queue.json for HUD and CLI."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        items = []
        if APPROVALS_FILE.exists():
            try:
                items = json.loads(APPROVALS_FILE.read_text(encoding="utf-8"))
            except Exception:
                items = []

        appr_id = f"pub_{int(datetime.now().timestamp())}_{len(items)+1}"
        items.append({
            "id": appr_id,
            "tool": action_type,
            "args": {"prompt": prompt},
            "source": "cloudflare_public_url",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        })
        APPROVALS_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return appr_id
    except Exception as e:
        logger.debug(f"Error recording approval: {e}")
        return "unknown"


def _resolve_recorded_approval(appr_id: str, approved: bool):
    """Mark recorded approval as approved or denied."""
    try:
        if not APPROVALS_FILE.exists():
            return
        items = json.loads(APPROVALS_FILE.read_text(encoding="utf-8"))
        for i in items:
            if i.get("id") == appr_id and i.get("status") == "pending":
                i["status"] = "approved" if approved else "denied"
                break
        APPROVALS_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")
    except Exception:
        pass


def check_public_permission(headers: Dict[str, str], prompt: str, client_ip: str = "127.0.0.1") -> Tuple[bool, str]:
    """Top-level check for requests arriving at /api/chat.
    Returns: (is_allowed: bool, rejection_message: str)
    """
    if not is_public_request(headers, client_ip):
        return True, ""

    is_sensitive, action_type, reason = classify_public_intent(prompt)
    if not is_sensitive:
        return True, ""

    # Sensitive action requested from public URL: request terminal approval from owner
    approved = request_terminal_approval(action_type, prompt, timeout_sec=25)
    if approved:
        return True, ""

    err_msg = (
        f"🔒 Security Alert: Action '{action_type.replace('_', ' ').title()}' requested via the public Cloudflare URL "
        f"requires host terminal authorization. The PC owner did not approve this action in the terminal."
    )
    return False, err_msg

