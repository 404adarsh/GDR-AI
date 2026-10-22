


    #!/usr/bin/env python3

"""
GDR AI - Advanced Personal Computer Agent
==========================================

Designed for:
    Kali Linux
    Ubuntu
    Debian-based Linux
    Android Termux -> SSH/Tailscale -> Linux

Main features:
    - Sarvam AI tool calling
    - Natural language computer control
    - Shell commands
    - Applications
    - Browser / URLs
    - YouTube search
    - Optional Playwright browser automation
    - Keyboard control
    - Mouse control
    - Clipboard
    - Screenshots
    - Fullscreen messages
    - Desktop notifications
    - Files
    - Processes
    - Services (status + restart/stop/start via admin allowlist)
    - System information
    - Network information
    - Git
    - Package information
    - Persistent safe preferences
    - Android-friendly one-shot mode
    - Email (read/send via IMAP/SMTP, app-password based)
    - Live news / custom RSS feeds
    - Generic webpage reading (give it any site's source)
    - "Remembered sites" - name a site once, ask about it by name later
    - Screen vision (screenshot + vision model analysis)
    - Music playback (stream via mpv/yt-dlp, not download)
    - Generic file downloads
    - Gated admin/sudo access via an explicit allowlist
    - System power actions (reboot/shutdown), double-gated behind
      an environment flag AND explicit confirmation

IMPORTANT:
    Never put your SARVAM_API_KEY (or any other secret) in this file.
    Every secret below comes from an environment variable. See the
    "SECRETS" section for the full list of variable names.
"""

import os
import sys
import json
import time
import shlex
import shutil
import socket
import signal
import subprocess
import platform
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
import pathlib
import re
import random
import threading
import queue
import base64
import imaplib
import smtplib
import ssl
import gdr_extras
import email as email_lib
from email.mime.text import MIMEText
from email.header import decode_header
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

MODEL = "sarvam-105b"

AGENT_NAME = "GDR AI"
USER_NAME = "GDR"

MAX_AGENT_STEPS = 24
MAX_OUTPUT = 16000
MEMORY_LIMIT = 30

# Execution resilience
TOOL_MAX_RETRIES = 2
BROWSER_TIMEOUT = 30000
SHELL_RETRY_SAFE_ONLY = True

# Sarvam/API protection
MIN_SARVAM_REQUEST_INTERVAL = 1.5
SARVAM_MAX_RETRIES = 5
SARVAM_BASE_BACKOFF = 5
SARVAM_MAX_BACKOFF = 30

PROFILE_FILE = os.path.join(SCRIPT_DIR, "profile.json")
HISTORY_FILE = os.path.join(SCRIPT_DIR, "history.json")
EVENT_LOG_FILE = os.path.join(SCRIPT_DIR, "gdr_history.jsonl")
HISTORY_CSV_FILE = os.path.join(SCRIPT_DIR, "gdr_history.csv")
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "gdr_checkpoint.json")
TASK_STATE_FILE = os.path.join(SCRIPT_DIR, "gdr_task_state.json")

COMMAND_TIMEOUT = 120

# Persistent execution
# NOTE: auto-resuming a stale task on every launch is what made it feel
# "stuck" after Ctrl+C. We now always ASK before resuming (see interactive()).
AUTO_RESUME = True
ASK_BEFORE_RESUME = True
MAX_CHECKPOINT_MESSAGES = 24
APPROX_TOKEN_BUDGET = 12000

# Token-saving knobs
MAX_TOKENS_PER_STEP = 1500          # was 3500 - most turns don't need that much
TOOL_RESULT_CHAR_LIMIT = 4000       # trims big tool outputs before they re-enter context
QUIET_LOGGING = False                # True = skip the CSV/verbose console spam, saves I/O only

# Cancellation: set by the input-reader thread when the user wants to
# interrupt whatever the agent is currently doing.
STOP_EVENT = threading.Event()
INPUT_QUEUE = queue.Queue()
AGENT_THREAD = {"thread": None, "busy": False}


# ============================================================
# AUTOMATIC VENV
# ============================================================

VENV_PYTHON = os.path.join(
    SCRIPT_DIR,
    ".venv",
    "bin",
    "python"
)

if (
    os.path.exists(VENV_PYTHON)
    and os.path.realpath(sys.executable)
    != os.path.realpath(VENV_PYTHON)
):
    os.execv(
        VENV_PYTHON,
        [VENV_PYTHON] + sys.argv
    )


# ============================================================
# IMPORTS
# ============================================================

try:
    from sarvamai import SarvamAI
except ImportError as e:
    print(f"Sarvam import failed: {e!r}")
    raise


# ============================================================
# CLIENT
# ============================================================

API_KEY = os.environ.get("SARVAM_API_KEY")

if not API_KEY:
    print("\n❌ SARVAM_API_KEY is not set.")
    print("\nSet it on Kali with:")
    print('  export SARVAM_API_KEY="YOUR_KEY"')
    print("\nFor Kali/Zsh, add it to ~/.zshrc.")
    sys.exit(1)

client = SarvamAI(
    api_subscription_key=API_KEY
)


# ============================================================
# SECRETS - everything below comes from environment variables.
# Never hardcode a secret in this file, and never let update_profile
# or any note/file tool persist one to disk.
#
# Required:
#   SARVAM_API_KEY          - already required above
#
# Optional (features quietly disable themselves if these are missing):
#   ANTHROPIC_API_KEY       - powers screen vision (tool_see_screen)
#   EMAIL_ADDRESS            - your email address
#   EMAIL_APP_PASSWORD       - an APP PASSWORD, not your real password
#                              (Gmail: Google Account -> Security ->
#                              2-Step Verification -> App Passwords)
#   EMAIL_IMAP_HOST          - default: imap.gmail.com
#   EMAIL_IMAP_PORT          - default: 993
#   EMAIL_SMTP_HOST          - default: smtp.gmail.com
#   EMAIL_SMTP_PORT          - default: 587
#   GDR_SUDO_ALLOWLIST       - comma-separated command prefixes GDR may
#                              run with sudo (see ADMIN section below)
#   GDR_ALLOW_POWER          - set to "1" to allow reboot/shutdown at all
#
# Example (~/.zshrc):
#   export SARVAM_API_KEY="..."
#   export ANTHROPIC_API_KEY="..."
#   export EMAIL_ADDRESS="you@gmail.com"
#   export EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
# ============================================================

def get_secret(name, default=None):
    """Read a secret from the environment only. Returns default if unset/blank."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value


SECRETS = {
    "SARVAM_API_KEY": API_KEY,
    "ANTHROPIC_API_KEY": get_secret("ANTHROPIC_API_KEY"),
    "EMAIL_ADDRESS": get_secret("EMAIL_ADDRESS"),
    "EMAIL_APP_PASSWORD": get_secret("EMAIL_APP_PASSWORD"),
    "EMAIL_IMAP_HOST": get_secret("EMAIL_IMAP_HOST", "imap.gmail.com"),
    "EMAIL_IMAP_PORT": int(get_secret("EMAIL_IMAP_PORT", "993")),
    "EMAIL_SMTP_HOST": get_secret("EMAIL_SMTP_HOST", "smtp.gmail.com"),
    "EMAIL_SMTP_PORT": int(get_secret("EMAIL_SMTP_PORT", "587")),
}


def _email_configured():
    return bool(SECRETS.get("EMAIL_ADDRESS") and SECRETS.get("EMAIL_APP_PASSWORD"))


# ============================================================
# ROOT / SUDO SAFETY CHECK  ("sudo gdr")
# ============================================================
#
# Running the ENTIRE agent process as root means every tool call -
# including run_shell, browser automation, and anything the LLM does
# after reading a webpage, RSS feed, or email - executes with full
# root privileges. Since fetch_webpage / read_rss / read_site /
# read_email pull text from the open internet and your inbox straight
# into the model's context, a malicious page or email could contain
# text crafted to look like an instruction to the agent (a prompt
# injection). Under the normal (non-root) setup, the worst that gets
# through is capped by run_shell's blocklist and your own user
# permissions. Running the whole process as root removes that ceiling.
#
# For "hardware access" specifically - webcam, mic, USB, serial ports,
# Bluetooth - you almost always want GROUP membership, not root:
#
#   sudo usermod -aG audio,video,plugdev,dialout,netdev,bluetooth $USER
#   (log out and back in for group changes to take effect)
#
# That gives GDR (running as your normal user) direct hardware access
# with nothing needing to be root at all.
#
# For admin actions (restart a service, apt update, etc.) you don't
# need root either - the ADMIN section below already escalates just
# those specific commands through a sudo allowlist while GDR itself
# keeps running as your normal user.
#
# If, having read all that, you still want to run GDR itself as root
# via `sudo gdr` - it's your machine, that's your call - set this in
# your environment first:
#
#   export GDR_I_UNDERSTAND_ROOT_RISK=1
#
# Without it, GDR refuses to start as root and tells you why.
# ============================================================

RUNNING_AS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
ROOT_RISK_ACKNOWLEDGED = get_secret("GDR_I_UNDERSTAND_ROOT_RISK") == "1"

if RUNNING_AS_ROOT and not ROOT_RISK_ACKNOWLEDGED:
    print("\n❌ Refusing to start as root.")
    print("   Running via sudo would make every tool call - including ones")
    print("   triggered by content read from webpages, RSS feeds, or email -")
    print("   execute with full root privileges. See the ROOT / SUDO SAFETY")
    print("   CHECK comment near the top of agent.py for the full reasoning.")
    print("\n   For hardware access (webcam/mic/USB/serial/Bluetooth), use groups instead:")
    print("     sudo usermod -aG audio,video,plugdev,dialout,netdev,bluetooth $USER")
    print("     (then log out and back in)")
    print("\n   For admin actions (restart services, apt update, etc.), run GDR as")
    print("   your normal user - it already escalates through the sudo allowlist")
    print("   (service_restart / service_stop / service_start / run_privileged).")
    print("\n   If you understand the risk and want to proceed anyway:")
    print("     export GDR_I_UNDERSTAND_ROOT_RISK=1")
    sys.exit(1)

if RUNNING_AS_ROOT and ROOT_RISK_ACKNOWLEDGED:
    print("\n⚠️  Running as root (GDR_I_UNDERSTAND_ROOT_RISK=1 is set).")
    print("   Every tool call now has full root access, including anything")
    print("   downstream of read_email / fetch_webpage / read_rss / read_site.")
    print("   Be deliberate about what you ask it to fetch and act on.")

    # Root can write/read anywhere, including credential paths a normal user's
    # own permissions would block. The application-level checks stay active
    # as a second layer even though the OS would otherwise allow the access.
    SENSITIVE_PATH_PARTS_NOTE = (
        "Running as root - is_sensitive_path() blocklist is your only "
        "remaining guard on credential files, since filesystem permissions "
        "no longer apply."
    )


# ============================================================
# PROFILE / MEMORY
# ============================================================

DEFAULT_PROFILE = {
    "name": "GDR",
    "assistant_name": "GDR AI",
    "tone": "friendly, casual, direct",
    "language": "English",
    "style": [
        "talk naturally",
        "be concise",
        "explain technical things simply",
        "don't sound robotic",
        "use light casual language"
    ]
}


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default.copy() if isinstance(default, dict) else default

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default.copy() if isinstance(default, dict) else default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )
        return True

    except Exception:
        return False


profile = load_json(
    PROFILE_FILE,
    DEFAULT_PROFILE
)

conversation = []
_last_sarvam_request_at = 0.0

def _record_sigint(signum, frame):
    log_event(
        "sigint",
        message="Ctrl+C received. Signalling the running task to stop."
    )
    # Tell whatever loop is running (agent step loop, sarvam call, tool call)
    # to bail out at its next safe checkpoint. We do NOT raise KeyboardInterrupt
    # here anymore - that used to unwind unpredictably mid-subprocess. Instead
    # every long-running loop below polls STOP_EVENT.
    STOP_EVENT.set()

signal.signal(signal.SIGINT, _record_sigint)


# ============================================================
# BASIC HELPERS
# ============================================================

def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def trim_output(value, limit=MAX_OUTPUT):
    if value is None:
        return ""

    value = str(value)

    if len(value) <= limit:
        return value

    return value[:limit] + "\n...[output truncated]"


def safe_json(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False
        )
    except Exception:
        return json.dumps(
            {"result": str(value)}
        )



def _safe_json_value(value):
    """Convert SDK/tool objects into JSON-safe values."""
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def log_event(event_type, **data):
    """Append an event immediately so Ctrl+C does not erase the task history."""
    record = {
        "time": now(),
        "event": event_type,
        **{k: _safe_json_value(v) for k, v in data.items()},
    }

    try:
        with open(EVENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Human-readable CSV history.
    try:
        import csv
        exists = os.path.exists(HISTORY_CSV_FILE)
        with open(HISTORY_CSV_FILE, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["time", "event", "tool", "success", "message", "details"],
            )
            if not exists:
                writer.writeheader()

            writer.writerow({
                "time": record["time"],
                "event": event_type,
                "tool": record.get("tool", ""),
                "success": record.get("success", ""),
                "message": record.get("message", ""),
                "details": json.dumps(
                    {k: v for k, v in record.items()
                     if k not in {"time", "event", "tool", "success", "message"}},
                    ensure_ascii=False,
                )[:10000],
            })
    except Exception:
        pass



def command_exists(command):
    return shutil.which(command) is not None


def detect_os():
    try:
        return platform.freedesktop_os_release()
    except Exception:
        return {}


OS_INFO = detect_os()

DISTRO = OS_INFO.get(
    "ID",
    platform.system().lower()
)

DESKTOP = os.environ.get(
    "XDG_CURRENT_DESKTOP",
    ""
)

SESSION_TYPE = os.environ.get(
    "XDG_SESSION_TYPE",
    ""
)

# Startup logging must happen AFTER log_event() is defined.
log_event(
    "startup",
    message=f"{AGENT_NAME} started on {DISTRO}/{DESKTOP or 'unknown'}."
)


def save_checkpoint(messages, user_request, step, status="running"):
    """Persist the exact agent conversation so the task can resume after Ctrl+C."""
    try:
        payload = {
            "saved_at": now(),
            "status": status,
            "user_request": user_request,
            "step": step,
            "messages": messages[-MAX_CHECKPOINT_MESSAGES:],
        }
        tmp = CHECKPOINT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CHECKPOINT_FILE)
    except Exception as e:
        log_event("checkpoint_error", message=str(e))


def load_checkpoint():
    try:
        if not os.path.exists(CHECKPOINT_FILE):
            return None
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("status") != "running":
            return None
        if not data.get("messages"):
            return None
        return data
    except Exception:
        return None


def clear_checkpoint():
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    except Exception:
        pass


def estimate_tokens(messages):
    """Cheap local estimate; no extra API request."""
    try:
        chars = sum(len(str(m.get("content", ""))) for m in messages)
        return max(1, chars // 4)
    except Exception:
        return 0


def compact_messages(messages):
    """Keep the system prompt plus the most recent context to reduce token usage."""
    if estimate_tokens(messages) <= APPROX_TOKEN_BUDGET:
        return messages

    system = [m for m in messages if m.get("role") == "system"][:1]
    recent = [m for m in messages if m.get("role") != "system"][-12:]
    compacted = system + recent
    log_event(
        "context_compacted",
        message="Older conversation context was trimmed to reduce token usage.",
        estimated_tokens=estimate_tokens(compacted),
    )
    return compacted


def record_usage(response):
    """Save provider token usage when the SDK exposes it."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return

    data = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens",
                "input_tokens", "output_tokens"):
        value = getattr(usage, key, None)
        if value is not None:
            data[key] = value

    if data:
        log_event("token_usage", **data)


def show_recent_history(limit=20):
    try:
        if not os.path.exists(EVENT_LOG_FILE):
            print("\n📜 No history yet.")
            return

        with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]

        print("\n📜 Recent GDR AI activity:")
        for line in lines:
            try:
                item = json.loads(line)
                tool = f" [{item.get('tool')}]" if item.get("tool") else ""
                msg = item.get("message", "")
                print(f"  {item.get('time')} | {item.get('event')}{tool} | {msg}")
            except Exception:
                continue
    except Exception as e:
        print(f"\n❌ Could not read history: {e}")


def show_last_task():
    checkpoint = load_checkpoint()
    if not checkpoint:
        print("\n✓ No interrupted task waiting to resume.")
        return
    print(
        f"\n⏯️ Interrupted task waiting:\n"
        f"   {checkpoint.get('user_request', '')}\n"
        f"   Last step: {checkpoint.get('step', '?')}"
    )



# ============================================================
# FRIENDLY UI
# ============================================================

THINKING_PHRASES = [
    "Hmm...",
    "Alright...",
    "Got you...",
    "Give me a sec...",
    "Okay...",
    "Let me handle that...",
    "On it...",
    "Yep...",
]


def thinking():
    phrase = random.choice(
        THINKING_PHRASES
    )

    print(
        f"\n🤖 {phrase}"
    )


def print_tool(name):
    print(
        f"\n   🔧 {name}"
    )


def print_result(success=True):
    if success:
        print("   ✓ done")
    else:
        print("   ✗ failed")


# ============================================================
# GUI ENVIRONMENT
# ============================================================

def find_xauthority():
    runtime = (
        os.environ.get("XDG_RUNTIME_DIR")
        or f"/run/user/{os.getuid()}"
    )

    if not os.path.isdir(runtime):
        return None

    candidates = []

    try:
        for name in os.listdir(runtime):

            if name.startswith(
                ".mutter-Xwaylandauth."
            ):
                candidates.append(
                    os.path.join(runtime, name)
                )

            elif name.startswith(
                ".Xauthority"
            ):
                candidates.append(
                    os.path.join(runtime, name)
                )

    except Exception:
        pass

    if not candidates:
        return None

    candidates.sort(
        key=lambda p: os.path.getmtime(p),
        reverse=True
    )

    return candidates[0]


def gui_environment():
    """
    Build an environment usable by GUI applications.

    Works with:
        X11
        Xwayland
        GNOME/Wayland
        common Kali desktop environments
    """

    env = os.environ.copy()

    if not env.get("DISPLAY"):

        # Common local Linux display.
        env["DISPLAY"] = ":0"

    if not env.get("XDG_RUNTIME_DIR"):

        env["XDG_RUNTIME_DIR"] = (
            f"/run/user/{os.getuid()}"
        )

    auth = env.get("XAUTHORITY")

    if not auth or not os.path.exists(auth):

        found = find_xauthority()

        if found:
            env["XAUTHORITY"] = found

    return env


# ============================================================
# PATH SECURITY
# ============================================================

SENSITIVE_PATH_PARTS = [
    "/.ssh/",
    "/.gnupg/",
    "/.aws/",
    "/.config/gcloud/",
    "/.kube/",
    "/.docker/",
    "/.npmrc",
    "/.pypirc",
    "/.netrc",
]


def is_sensitive_path(path):

    expanded = os.path.abspath(
        os.path.expanduser(path)
    )

    normalized = expanded.replace(
        "\\",
        "/"
    )

    for part in SENSITIVE_PATH_PARTS:
        if part in normalized:
            return True

    if normalized.endswith(".env"):
        return True

    if "/.env." in normalized:
        return True

    if normalized.endswith(
        "id_rsa"
    ):
        return True

    if normalized.endswith(
        "id_ed25519"
    ):
        return True

    return False


# ============================================================
# COMMAND SAFETY
# ============================================================

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\brm\s+-rf\s+\*",
    r"\bmkfs(\.| )",
    r"\bdd\s+if=",
    r"\bfdisk\b",
    r"\bparted\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r":\(\)\s*\{.*\}",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-fd\b",
]


def dangerous_command(command):

    lower = command.lower()

    for pattern in DANGEROUS_PATTERNS:

        if re.search(
            pattern,
            lower
        ):
            return True

    return False


def privileged_command(command):

    lower = command.lower().strip()

    prefixes = [
        "sudo ",
        "su ",
        "doas ",
        "pkexec ",
    ]

    return any(
        lower.startswith(x)
        for x in prefixes
    )


# ============================================================
# SHELL
# ============================================================

def _shell_command_is_safe_to_retry(command):
    """Only retry commands that are clearly read-only/idempotent."""
    c = command.strip().lower()
    blocked_words = [
        " rm ", "mv ", "cp ", "mkdir", "touch ", "tee ", ">", ">>",
        "sed -i", "perl -i", "python -c", "pip ", "apt ", "git commit",
        "git push", "curl -x", "wget -o", "kill ", "pkill ", "systemctl start",
        "systemctl stop", "systemctl restart"
    ]
    padded = f" {c} "
    return not any(word in padded for word in blocked_words)


def _run_shell_once(command, timeout):
    """Run a command in its own process group so hung children can be killed."""
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        try:
            stdout, stderr = proc.communicate(timeout=int(timeout))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                time.sleep(0.5)
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass

            try:
                stdout, stderr = proc.communicate(timeout=2)
            except Exception:
                stdout, stderr = "", ""

            return {
                "success": False,
                "timeout": True,
                "returncode": -9,
                "stdout": trim_output(stdout),
                "stderr": trim_output(stderr),
                "error": f"Command timed out after {timeout}s and the process group was stopped."
            }

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": trim_output(stdout),
            "stderr": trim_output(stderr),
        }

    except KeyboardInterrupt:
        # Ctrl+C should not kill GDR AI itself.
        try:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            pass

        return {
            "success": False,
            "interrupted": True,
            "error": "The shell operation was interrupted."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def tool_run_shell(command, timeout=COMMAND_TIMEOUT):
    if not command:
        return {"success": False, "error": "Empty command."}

    if dangerous_command(command):
        return {
            "success": False,
            "blocked": True,
            "error": "Potentially destructive command blocked."
        }

    if privileged_command(command):
        return {
            "success": False,
            "confirmation_required": True,
            "error": (
                "Privileged command requires the dedicated admin tools "
                "(run_privileged, service_restart, service_stop, service_start, "
                "system_power) which go through the sudo allowlist instead."
            )
        }

    if re.search(
        r"(cat|less|more|head|tail|grep|sed|awk).*"
        r"(\.ssh|id_rsa|id_ed25519|SARVAM_API_KEY|\.env)",
        command,
        re.I
    ):
        return {
            "success": False,
            "blocked": True,
            "error": "Potential credential/secret access blocked."
        }

    attempts = 2 if (
        SHELL_RETRY_SAFE_ONLY and
        _shell_command_is_safe_to_retry(command)
    ) else 1

    last = None

    for attempt in range(attempts):
        result = _run_shell_once(command, timeout)
        last = result

        if result.get("success"):
            return result

        if not result.get("timeout"):
            return result

        if attempt + 1 < attempts:
            print(
                f"\n   ↻ Shell timed out. Retrying "
                f"({attempt + 2}/{attempts})..."
            )
            time.sleep(1)

    return last


# ============================================================
# APPLICATIONS
# ============================================================

COMMON_APPS = {
    "browser": [
        "google-chrome",
        "chromium",
        "chromium-browser",
        "firefox",
    ],

    "chrome": [
        "google-chrome",
        "chromium",
    ],

    "firefox": [
        "firefox",
    ],

    "terminal": [
        "xfce4-terminal",
        "konsole",
        "gnome-terminal",
        "qterminal",
    ],

    "code": [
        "code",
    ],

    "vscode": [
        "code",
    ],

    "file manager": [
        "thunar",
        "nautilus",
        "dolphin",
        "pcmanfm",
    ],
}


def find_application(name):

    if command_exists(name):
        return name

    key = name.lower().strip()

    candidates = COMMON_APPS.get(
        key,
        []
    )

    for app in candidates:

        if command_exists(app):
            return app

    return None


def tool_open_application(
    application,
    arguments=None
):

    app = find_application(
        application
    )

    if not app:

        return {
            "success": False,
            "error":
                f"Application not found: {application}"
        }

    args = arguments or []

    if isinstance(args, str):
        args = shlex.split(args)

    try:

        subprocess.Popen(
            [app] + args,
            env=gui_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return {
            "success": True,
            "application": app
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_close_application(
    application
):

    app = find_application(
        application
    )

    if not app:

        return {
            "success": False,
            "error": "Application not found."
        }

    return tool_run_shell(
        f"pkill -TERM -x {shlex.quote(app)}"
    )


# ============================================================
# URL / BROWSER
# ============================================================

def tool_open_url(url):

    if not re.match(
        r"^https?://",
        url,
        re.I
    ):
        url = "https://" + url

    try:

        subprocess.Popen(
            [
                "xdg-open",
                url
            ],
            env=gui_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return {
            "success": True,
            "url": url
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_google_search(query):

    url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote_plus(query)
    )

    return tool_open_url(url)


def tool_youtube_search(query):

    url = (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
    )

    result = tool_open_url(url)

    result["query"] = query

    return result


# ============================================================
# BROWSER AUTOMATION
# ============================================================

_BROWSER = {
    "playwright": None,
    "browser": None,
    "context": None,
    "page": None,
    "console_errors": [],
    "failed_requests": [],
}


def _browser_normalize_url(url):
    if not re.match(r"^https?://", url, re.I):
        return "https://" + url
    return url


def _browser_require():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None


def _browser_start():
    sync_playwright = _browser_require()
    if sync_playwright is None:
        return None, {
            "success": False,
            "error": (
                "Playwright is not installed. Run inside .venv:\n"
                "python -m pip install playwright\n"
                "python -m playwright install chromium"
            )
        }

    if _BROWSER["page"] is not None:
        try:
            _ = _BROWSER["page"].url
            return _BROWSER["page"], None
        except Exception:
            _BROWSER["page"] = None

    try:
        log_event("browser_start", message="Starting Playwright Chromium.")

        pw = sync_playwright().start()

        launch_attempts = [
            {"headless": False},
            {"headless": False, "args": ["--disable-gpu", "--disable-dev-shm-usage"]},
        ]

        last_error = None
        browser = None

        for launch_options in launch_attempts:
            try:
                browser = pw.chromium.launch(**launch_options)
                break
            except Exception as launch_error:
                last_error = launch_error
                log_event(
                    "browser_launch_failed",
                    message=str(launch_error),
                )

        if browser is None:
            # Keep the failure detailed instead of hiding it behind "browser failed".
            try:
                pw.stop()
            except Exception:
                pass

            return None, {
                "success": False,
                "error": (
                    "Playwright Chromium could not start. "
                    f"Detailed error: {last_error}. "
                    "Run: python -m playwright install chromium "
                    "and verify DISPLAY/X11 access."
                ),
                "troubleshoot": [
                    "python -m playwright install chromium",
                    "echo $DISPLAY",
                    "echo $XDG_SESSION_TYPE",
                    "which chromium",
                    "which google-chrome",
                ],
            }

        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=False,
        )
        page = context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)
        page.set_default_navigation_timeout(BROWSER_TIMEOUT)

        _BROWSER["playwright"] = pw
        _BROWSER["browser"] = browser
        _BROWSER["context"] = context
        _BROWSER["page"] = page
        _BROWSER["console_errors"] = []
        _BROWSER["failed_requests"] = []

        def on_console(msg):
            if msg.type == "error":
                _BROWSER["console_errors"].append(msg.text)
                _BROWSER["console_errors"] = _BROWSER["console_errors"][-30:]

        def on_request_failed(req):
            _BROWSER["failed_requests"].append({
                "url": req.url,
                "method": req.method,
                "failure": req.failure,
            })
            _BROWSER["failed_requests"] = _BROWSER["failed_requests"][-30:]

        page.on("console", on_console)
        page.on("requestfailed", on_request_failed)

        return page, None

    except Exception as e:
        return None, {"success": False, "error": str(e)}


def _browser_page():
    page, error = _browser_start()
    if error:
        return None, error
    return page, None


def tool_browser_open(url):
    url = _browser_normalize_url(url)

    for attempt in range(2):
        page, error = _browser_page()
        if error:
            return error

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=BROWSER_TIMEOUT,
            )
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            result = {
                "success": True,
                "title": page.title(),
                "url": page.url,
                "status": response.status if response else None,
            }
            log_event(
                "browser_open_success",
                tool="browser_open",
                success=True,
                message=f"Opened {page.url}",
            )
            return result

        except Exception as e:
            log_event(
                "browser_open_failed",
                tool="browser_open",
                success=False,
                message=str(e),
                details=f"url={url}; attempt={attempt + 1}",
            )
            if attempt == 0:
                print("\n   ↻ Browser navigation failed. Retrying...")
                time.sleep(1)
                continue
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Browser navigation failed."}


def tool_browser_click(selector="", text="", button="left"):
    page, error = _browser_page()
    if error:
        return error

    try:
        if text:
            locator = page.get_by_text(text, exact=False).first
        elif selector:
            locator = page.locator(selector).first
        else:
            return {"success": False, "error": "Provide selector or text."}

        locator.click(button=button, timeout=BROWSER_TIMEOUT)

        return {
            "success": True,
            "selector": selector,
            "text": text,
            "url": page.url,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_fill(selector, text):
    page, error = _browser_page()
    if error:
        return error

    try:
        page.locator(selector).first.fill(text, timeout=BROWSER_TIMEOUT)
        return {"success": True, "selector": selector}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_type(selector, text, press_enter=False):
    page, error = _browser_page()
    if error:
        return error

    try:
        locator = page.locator(selector).first
        locator.click(timeout=BROWSER_TIMEOUT)
        locator.fill(text, timeout=BROWSER_TIMEOUT)
        if press_enter:
            locator.press("Enter")
        return {"success": True, "selector": selector}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_press(key):
    page, error = _browser_page()
    if error:
        return error

    try:
        page.keyboard.press(key)
        return {"success": True, "key": key}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_wait(milliseconds=1000):
    page, error = _browser_page()
    if error:
        return error

    try:
        page.wait_for_timeout(max(0, min(int(milliseconds), 30000)))
        return {"success": True, "milliseconds": milliseconds}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_back():
    page, error = _browser_page()
    if error:
        return error

    try:
        page.go_back(wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT)
        return {"success": True, "url": page.url, "title": page.title()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_read(selector="body", max_chars=12000):
    page, error = _browser_page()
    if error:
        return error

    try:
        locator = page.locator(selector).first
        text_content = locator.inner_text(timeout=BROWSER_TIMEOUT)
        return {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "text": trim_output(text_content, int(max_chars)),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_inspect():
    """Inspect page structure, stylesheets, console errors and failed requests."""
    page, error = _browser_page()
    if error:
        return error

    try:
        data = page.evaluate("""
        () => {
          const links = [...document.querySelectorAll('link[rel="stylesheet"]')]
            .map(x => x.href);
          const styles = [...document.querySelectorAll('style')]
            .map(x => ({chars: x.textContent?.length || 0}));
          const scripts = [...document.scripts].map(x => x.src).filter(Boolean);
          const body = document.body?.innerText || "";
          const sample = [...document.querySelectorAll('a,button,input,textarea,select')]
            .slice(0, 80)
            .map((x, i) => ({
              i,
              tag: x.tagName,
              text: (x.innerText || x.getAttribute('aria-label') || x.getAttribute('placeholder') || "").trim().slice(0,120),
              id: x.id || "",
              cls: typeof x.className === "string" ? x.className.slice(0,160) : ""
            }));
          return {
            title: document.title,
            url: location.href,
            readyState: document.readyState,
            stylesheetLinks: links,
            inlineStyles: styles,
            scripts,
            elements: sample,
            bodyText: body.slice(0, 8000)
          };
        }
        """)

        data["consoleErrors"] = _BROWSER["console_errors"][-30:]
        data["failedRequests"] = _BROWSER["failed_requests"][-30:]
        data["success"] = True
        return data

    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_screenshot(path=""):
    page, error = _browser_page()
    if error:
        return error

    if not path:
        path = os.path.join(
            HOME,
            "Pictures",
            f"gdr_browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )

    path = os.path.abspath(os.path.expanduser(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        page.screenshot(path=path, full_page=True)
        return {"success": True, "path": path, "url": page.url}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_browser_close():
    try:
        if _BROWSER["context"]:
            _BROWSER["context"].close()
    except Exception:
        pass
    try:
        if _BROWSER["browser"]:
            _BROWSER["browser"].close()
    except Exception:
        pass
    try:
        if _BROWSER["playwright"]:
            _BROWSER["playwright"].stop()
    except Exception:
        pass

    for key in _BROWSER:
        if key not in {"console_errors", "failed_requests"}:
            _BROWSER[key] = None

    _BROWSER["console_errors"] = []
    _BROWSER["failed_requests"] = []

    return {"success": True}


# ============================================================
# KEYBOARD / MOUSE
# ============================================================

def tool_type_text(text):

    if not command_exists("xdotool"):

        return {
            "success": False,
            "error":
                "xdotool is not installed."
        }

    try:

        subprocess.run(
            [
                "xdotool",
                "type",
                "--delay",
                "20",
                text
            ],
            env=gui_environment(),
            timeout=20
        )

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_keypress(key):

    if not command_exists("xdotool"):

        return {
            "success": False,
            "error":
                "xdotool is not installed."
        }

    allowed = {
        "enter",
        "escape",
        "tab",
        "space",
        "backspace",
        "delete",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "pageup",
        "pagedown",
        "ctrl+c",
        "ctrl+v",
        "ctrl+x",
        "ctrl+a",
        "ctrl+l",
        "alt+tab",
        "alt+f4",
        "super",
    }

    normalized = key.lower()

    if normalized not in allowed:

        return {
            "success": False,
            "error":
                "Key combination not allowed."
        }

    try:

        subprocess.run(
            [
                "xdotool",
                "key",
                key
            ],
            env=gui_environment(),
            timeout=10
        )

        return {
            "success": True,
            "key": key
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_mouse_click(
    x,
    y,
    button=1
):

    if not command_exists("xdotool"):

        return {
            "success": False,
            "error":
                "xdotool is not installed."
        }

    try:

        subprocess.run(
            [
                "xdotool",
                "mousemove",
                str(int(x)),
                str(int(y))
            ],
            env=gui_environment(),
            timeout=10
        )

        subprocess.run(
            [
                "xdotool",
                "click",
                str(int(button))
            ],
            env=gui_environment(),
            timeout=10
        )

        return {
            "success": True,
            "x": x,
            "y": y
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# CLIPBOARD
# ============================================================

def tool_clipboard_get():

    try:

        if command_exists("xclip"):

            r = subprocess.run(
                [
                    "xclip",
                    "-selection",
                    "clipboard",
                    "-o"
                ],
                env=gui_environment(),
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "success": True,
                "text": trim_output(
                    r.stdout,
                    10000
                )
            }

        if command_exists("xsel"):

            r = subprocess.run(
                [
                    "xsel",
                    "--clipboard",
                    "--output"
                ],
                env=gui_environment(),
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "success": True,
                "text": trim_output(
                    r.stdout,
                    10000
                )
            }

        return {
            "success": False,
            "error":
                "Install xclip or xsel."
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_clipboard_set(text):

    try:

        if command_exists("xclip"):

            p = subprocess.Popen(
                [
                    "xclip",
                    "-selection",
                    "clipboard"
                ],
                stdin=subprocess.PIPE,
                env=gui_environment(),
                text=True
            )

            p.communicate(text)

            return {
                "success": p.returncode == 0
            }

        if command_exists("xsel"):

            p = subprocess.Popen(
                [
                    "xsel",
                    "--clipboard",
                    "--input"
                ],
                stdin=subprocess.PIPE,
                env=gui_environment(),
                text=True
            )

            p.communicate(text)

            return {
                "success": p.returncode == 0
            }

        return {
            "success": False,
            "error":
                "Install xclip or xsel."
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# SCREEN
# ============================================================

def tool_show_screen(
    message,
    title="GDR AI",
    duration=5
):

    try:

        import tkinter as tk

        env = gui_environment()

        os.environ.update(env)

        root = tk.Tk()

        root.title(title)

        root.attributes(
            "-fullscreen",
            True
        )

        root.attributes(
            "-topmost",
            True
        )

        root.configure(
            bg="#080808"
        )

        root.bind(
            "<Escape>",
            lambda event: root.destroy()
        )

        title_label = tk.Label(
            root,
            text=title,
            font=("DejaVu Sans", 28, "bold"),
            fg="white",
            bg="#080808"
        )

        title_label.pack(
            pady=(100, 20)
        )

        label = tk.Label(
            root,
            text=str(message),
            font=("DejaVu Sans", 48, "bold"),
            fg="white",
            bg="#080808",
            wraplength=1200,
            justify="center"
        )

        label.pack(
            expand=True
        )

        hint = tk.Label(
            root,
            text="Press ESC to close",
            font=("DejaVu Sans", 14),
            fg="#888888",
            bg="#080808"
        )

        hint.pack(
            pady=40
        )

        root.update()

        root.after(
            int(float(duration) * 1000),
            root.destroy
        )

        root.mainloop()

        return {
            "success": True,
            "duration": duration
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# NOTIFICATIONS
# ============================================================

def tool_notify(
    title,
    message
):

    if not command_exists(
        "notify-send"
    ):

        return {
            "success": False,
            "error":
                "notify-send is not installed."
        }

    try:

        subprocess.run(
            [
                "notify-send",
                title,
                message
            ],
            env=gui_environment(),
            timeout=10
        )

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# SYSTEM INFO
# ============================================================

def tool_system_info():

    data = {
        "hostname": socket.gethostname(),
        "user": os.getenv("USER"),
        "home": HOME,
        "os": DISTRO,
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "desktop": DESKTOP,
        "session": SESSION_TYPE,
        "display": os.environ.get("DISPLAY"),
        "python": platform.python_version(),
    }

    try:

        data["uptime"] = (
            open(
                "/proc/uptime"
            ).read().split()[0]
        )

    except Exception:
        pass

    return {
        "success": True,
        "system": data
    }


def tool_system_health():

    commands = [
        "uptime",
        "free -h",
        "df -h /",
        "ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 12",
        "ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 12",
    ]

    results = {}

    for command in commands:

        result = tool_run_shell(
            command
        )

        results[command] = result

    return {
        "success": True,
        "results": results
    }


# ============================================================
# PROCESSES
# ============================================================

def tool_processes():

    return tool_run_shell(
        "ps -eo pid,ppid,user,%cpu,%mem,stat,comm --sort=-%cpu | head -n 40"
    )


def tool_kill_process(
    pid
):

    return {
        "success": False,
        "confirmation_required": True,
        "error":
            f"Killing process {pid} requires confirmation."
    }


# ============================================================
# FILES
# ============================================================

def tool_list_directory(
    path=HOME
):

    path = os.path.abspath(
        os.path.expanduser(path)
    )

    try:

        entries = []

        for item in sorted(
            os.listdir(path)
        ):

            full = os.path.join(
                path,
                item
            )

            entries.append({
                "name": item,
                "type":
                    "directory"
                    if os.path.isdir(full)
                    else "file"
            })

        return {
            "success": True,
            "path": path,
            "entries": entries[:300]
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_find_files(
    pattern,
    path=HOME,
    max_results=100
):

    root = os.path.abspath(
        os.path.expanduser(path)
    )

    matches = []

    try:

        for base, dirs, files in os.walk(root):

            dirs[:] = [
                d for d in dirs
                if d not in {
                    ".git",
                    "node_modules",
                    ".cache"
                }
            ]

            for filename in files:

                if pattern.lower() in filename.lower():

                    full = os.path.join(
                        base,
                        filename
                    )

                    if not is_sensitive_path(full):

                        matches.append(full)

                    if len(matches) >= int(
                        max_results
                    ):
                        return {
                            "success": True,
                            "matches": matches
                        }

        return {
            "success": True,
            "matches": matches
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_read_file(
    path,
    max_chars=20000
):

    path = os.path.abspath(
        os.path.expanduser(path)
    )

    if is_sensitive_path(path):

        return {
            "success": False,
            "blocked": True,
            "error":
                "Sensitive file access blocked."
        }

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:

            content = f.read(
                int(max_chars)
            )

        return {
            "success": True,
            "path": path,
            "content": content
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_write_file(
    path,
    content,
    append=False
):

    path = os.path.abspath(
        os.path.expanduser(path)
    )

    if is_sensitive_path(path):

        return {
            "success": False,
            "blocked": True,
            "error":
                "Sensitive file access blocked."
        }

    try:

        os.makedirs(
            os.path.dirname(path),
            exist_ok=True
        )

        mode = "a" if append else "w"

        with open(
            path,
            mode,
            encoding="utf-8"
        ) as f:

            f.write(content)

        return {
            "success": True,
            "path": path
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_create_directory(path):

    path = os.path.abspath(
        os.path.expanduser(path)
    )

    try:

        os.makedirs(
            path,
            exist_ok=True
        )

        return {
            "success": True,
            "path": path
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def tool_disk_usage(
    path=HOME
):

    return tool_run_shell(
        f"du -sh {shlex.quote(os.path.expanduser(path))}"
    )


# ============================================================
# ADMIN / PRIVILEGED COMMANDS
# ============================================================
#
# GDR AI never guesses at admin access. For any of this to actually run,
# you must add a NOPASSWD sudoers rule that matches these exact prefixes.
#
#   sudo visudo -f /etc/sudoers.d/gdr-ai
#
# then add lines like (replace "yourusername"):
#
#   yourusername ALL=(root) NOPASSWD: /usr/bin/systemctl restart *
#   yourusername ALL=(root) NOPASSWD: /usr/bin/systemctl stop *
#   yourusername ALL=(root) NOPASSWD: /usr/bin/systemctl start *
#   yourusername ALL=(root) NOPASSWD: /usr/bin/apt update
#
# Only add prefixes you're genuinely comfortable with GDR running
# unattended. We deliberately do NOT ship (or suggest) a blanket
# "NOPASSWD: ALL" rule - that would mean any bug, bad tool call, or
# leaked API key could run arbitrary commands as root on your machine.
#
# Want to allow more? Set GDR_SUDO_ALLOWLIST as a comma-separated list
# of prefixes in your environment, e.g.:
#   export GDR_SUDO_ALLOWLIST="systemctl restart ,systemctl stop ,systemctl start ,apt update,apt upgrade -y"
#
# NOTE: none of this sudoers setup is needed if GDR itself is already
# running as root (`sudo gdr` with GDR_I_UNDERSTAND_ROOT_RISK=1 set -
# see the ROOT / SUDO SAFETY CHECK section above). In that mode,
# run_privileged/service_restart/service_stop/service_start/system_power
# run the command directly instead of re-invoking sudo. The allowlist
# below still applies either way - it's the same gate regardless of
# whether GDR is escalating via sudo or already root.
# ============================================================

DEFAULT_SUDO_ALLOWLIST = [
    "systemctl restart ",
    "systemctl stop ",
    "systemctl start ",
    "apt update",
]

_env_allowlist = get_secret("GDR_SUDO_ALLOWLIST")
SUDO_ALLOWLIST = (
    [p.strip() for p in _env_allowlist.split(",") if p.strip()]
    if _env_allowlist
    else DEFAULT_SUDO_ALLOWLIST
)

# Power actions (reboot/shutdown) are off by default even if sudo works.
ALLOW_POWER_ACTIONS = get_secret("GDR_ALLOW_POWER", "0") == "1"


def _sudo_command_allowed(command):
    stripped = command.strip()
    return any(stripped.startswith(prefix) for prefix in SUDO_ALLOWLIST)


def tool_run_privileged(command):
    """Run a command as root via `sudo -n` (non-interactive). Only commands
    matching SUDO_ALLOWLIST are permitted. sudo -n fails cleanly and
    immediately (rather than hanging waiting for a password) if the
    NOPASSWD sudoers rule isn't configured yet."""
    if not command:
        return {"success": False, "error": "Empty command."}

    if not _sudo_command_allowed(command):
        return {
            "success": False,
            "blocked": True,
            "error": (
                f"'{command}' is not in the admin allowlist. "
                f"Allowed prefixes: {SUDO_ALLOWLIST}. "
                "Add more via the GDR_SUDO_ALLOWLIST environment variable."
            ),
        }

    # If GDR itself is already running as root (sudo gdr, with the risk
    # acknowledged above), there's no need to sudo again - just run it.
    full_command = command if RUNNING_AS_ROOT else f"sudo -n {command}"
    result = _run_shell_once(full_command, COMMAND_TIMEOUT)

    stderr_lower = (result.get("stderr") or "").lower()
    if not result.get("success") and ("password is required" in stderr_lower or "a password is required" in stderr_lower):
        result["error"] = (
            "sudo needs a NOPASSWD rule for this exact command. "
            "Run `sudo visudo -f /etc/sudoers.d/gdr-ai` and add a matching line "
            "(see the ADMIN section at the top of agent.py for examples)."
        )

    return result


def tool_service_restart(service):
    if not re.match(r"^[a-zA-Z0-9_.@-]+$", service or ""):
        return {"success": False, "error": "Invalid service name."}
    return tool_run_privileged(f"systemctl restart {shlex.quote(service)}")


def tool_service_stop(service):
    if not re.match(r"^[a-zA-Z0-9_.@-]+$", service or ""):
        return {"success": False, "error": "Invalid service name."}
    return tool_run_privileged(f"systemctl stop {shlex.quote(service)}")


def tool_service_start(service):
    if not re.match(r"^[a-zA-Z0-9_.@-]+$", service or ""):
        return {"success": False, "error": "Invalid service name."}
    return tool_run_privileged(f"systemctl start {shlex.quote(service)}")


def tool_system_power(action, confirm=False):
    """Reboot / shutdown / power off. Double-gated: needs GDR_ALLOW_POWER=1
    in the environment AND an explicit confirm=True on the call, so a
    stray or hallucinated tool call can't take the machine down."""
    action = (action or "").lower()
    commands = {
        "reboot": "systemctl reboot",
        "shutdown": "systemctl poweroff",
        "poweroff": "systemctl poweroff",
    }

    if action not in commands:
        return {"success": False, "error": f"Unsupported power action: {action}"}

    if not ALLOW_POWER_ACTIONS:
        return {
            "success": False,
            "confirmation_required": True,
            "error": "Power actions are disabled. Set GDR_ALLOW_POWER=1 in the environment to enable them.",
        }

    if not confirm:
        return {
            "success": False,
            "confirmation_required": True,
            "error": f"Ask the user to explicitly confirm '{action}' out loud, then call this tool again with confirm=true.",
        }

    power_command = commands[action] if RUNNING_AS_ROOT else f"sudo -n {commands[action]}"
    return _run_shell_once(power_command, 15)


# ============================================================
# SERVICES (read-only status - unchanged from before)
# ============================================================

def tool_service_status(
    service
):

    if not re.match(
        r"^[a-zA-Z0-9_.@-]+$",
        service
    ):

        return {
            "success": False,
            "error":
                "Invalid service name."
        }

    return tool_run_shell(
        f"systemctl status "
        f"{shlex.quote(service)} "
        f"--no-pager -l"
    )


# ============================================================
# NETWORK
# ============================================================

def tool_network_info():

    commands = [
        "ip -brief address",
        "ip route",
        "ss -tuln",
        "tailscale status 2>/dev/null || true",
    ]

    output = {}

    for cmd in commands:
        output[cmd] = tool_run_shell(cmd)

    return {
        "success": True,
        "network": output
    }


def tool_ping(
    host
):

    if not re.match(
        r"^[a-zA-Z0-9_.:-]+$",
        host
    ):

        return {
            "success": False,
            "error": "Invalid host."
        }

    return tool_run_shell(
        f"ping -c 4 {shlex.quote(host)}"
    )


# ============================================================
# GIT
# ============================================================

def tool_git_status(
    path=HOME
):

    path = os.path.abspath(
        os.path.expanduser(path)
    )

    return tool_run_shell(
        f"cd {shlex.quote(path)} && git status --short --branch"
    )


# ============================================================
# SCREENSHOT
# ============================================================

def tool_screenshot(
    path=""
):

    if not path:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        path = os.path.join(
            HOME,
            "Pictures",
            f"gdr_{timestamp}.png"
        )

    path = os.path.abspath(
        os.path.expanduser(path)
    )

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    commands = []

    if command_exists(
        "gnome-screenshot"
    ):
        commands.append(
            [
                "gnome-screenshot",
                "-f",
                path
            ]
        )

    if command_exists("scrot"):
        commands.append(
            [
                "scrot",
                path
            ]
        )

    if command_exists("xfce4-screenshooter"):
        commands.append(
            [
                "xfce4-screenshooter",
                "-f",
                "-s",
                path
            ]
        )

    for command in commands:

        try:

            r = subprocess.run(
                command,
                env=gui_environment(),
                capture_output=True,
                text=True,
                timeout=30
            )

            if r.returncode == 0:

                return {
                    "success": True,
                    "path": path
                }

        except Exception:
            continue

    return {
        "success": False,
        "error":
            "No working screenshot utility found."
    }


# ============================================================
# SCREEN VISION - "can you see my screen?"
# ============================================================
#
# Takes a screenshot, then sends it to a vision-capable model so GDR can
# actually describe/diagnose what's on the screen instead of just saving
# an image nobody looks at. Requires ANTHROPIC_API_KEY. Swap the endpoint
# below for any other vision-capable API you have access to if you'd
# rather not use that one.
# ============================================================

VISION_MODEL = "claude-sonnet-4-6"


def tool_see_screen(question="What's on my screen right now? Point out anything that looks broken or wrong."):
    if not SECRETS.get("ANTHROPIC_API_KEY"):
        return {
            "success": False,
            "error": (
                "Screen vision needs an ANTHROPIC_API_KEY environment variable. "
                "Set it, or swap tool_see_screen() to another vision-capable API you have."
            ),
        }

    shot = tool_screenshot()
    if not shot.get("success"):
        return shot

    try:
        with open(shot["path"], "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        payload = json.dumps({
            "model": VISION_MODEL,
            "max_tokens": 1024,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                    {"type": "text", "text": question},
                ],
            }],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": SECRETS["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        text_blocks = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        analysis = "\n".join(text_blocks).strip() or "No analysis returned."

        return {"success": True, "screenshot": shot["path"], "analysis": analysis}

    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"Vision API HTTP {e.code}: {e.read().decode(errors='replace')[:500]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# PACKAGE INFORMATION
# ============================================================

def tool_package_info(
    package
):

    if not re.match(
        r"^[a-zA-Z0-9_.+:-]+$",
        package
    ):

        return {
            "success": False,
            "error": "Invalid package name."
        }

    if command_exists("apt"):

        return tool_run_shell(
            f"apt-cache policy "
            f"{shlex.quote(package)}"
        )

    if command_exists("pacman"):

        return tool_run_shell(
            f"pacman -Si "
            f"{shlex.quote(package)}"
        )

    return {
        "success": False,
        "error":
            "No supported package manager found."
    }


# ============================================================
# PROFILE
# ============================================================

def tool_get_profile():

    return {
        "success": True,
        "profile": profile
    }


def tool_update_profile(
    key,
    value
):

    allowed = {
        "name",
        "assistant_name",
        "tone",
        "language",
        "style"
    }

    if key not in allowed:

        return {
            "success": False,
            "error":
                "Profile field not allowed."
        }

    profile[key] = value

    save_json(
        PROFILE_FILE,
        profile
    )

    return {
        "success": True,
        "profile": profile
    }


# ============================================================
# NEW: VOLUME / BRIGHTNESS / MEDIA
# ============================================================

def tool_volume(action="get", level=None):
    """action: get | set | mute | unmute | up | down"""
    action = (action or "get").lower()

    if command_exists("pactl"):
        if action == "get":
            return tool_run_shell(
                "pactl get-sink-volume @DEFAULT_SINK@ && pactl get-sink-mute @DEFAULT_SINK@"
            )
        if action == "set" and level is not None:
            lvl = max(0, min(int(level), 150))
            return tool_run_shell(f"pactl set-sink-volume @DEFAULT_SINK@ {lvl}%")
        if action == "mute":
            return tool_run_shell("pactl set-sink-mute @DEFAULT_SINK@ 1")
        if action == "unmute":
            return tool_run_shell("pactl set-sink-mute @DEFAULT_SINK@ 0")
        if action == "up":
            return tool_run_shell("pactl set-sink-volume @DEFAULT_SINK@ +10%")
        if action == "down":
            return tool_run_shell("pactl set-sink-volume @DEFAULT_SINK@ -10%")

    if command_exists("amixer"):
        if action == "get":
            return tool_run_shell("amixer get Master")
        if action == "set" and level is not None:
            lvl = max(0, min(int(level), 100))
            return tool_run_shell(f"amixer set Master {lvl}%")
        if action == "mute":
            return tool_run_shell("amixer set Master mute")
        if action == "unmute":
            return tool_run_shell("amixer set Master unmute")
        if action == "up":
            return tool_run_shell("amixer set Master 10%+")
        if action == "down":
            return tool_run_shell("amixer set Master 10%-")

    return {"success": False, "error": "Neither pactl nor amixer is available."}


def tool_brightness(action="get", level=None):
    """action: get | set | up | down. Needs brightnessctl (preferred) or xrandr fallback."""
    action = (action or "get").lower()

    if command_exists("brightnessctl"):
        if action == "get":
            return tool_run_shell("brightnessctl get && brightnessctl max")
        if action == "set" and level is not None:
            lvl = max(1, min(int(level), 100))
            return tool_run_shell(f"brightnessctl set {lvl}%")
        if action == "up":
            return tool_run_shell("brightnessctl set +10%")
        if action == "down":
            return tool_run_shell("brightnessctl set 10%-")

    return {
        "success": False,
        "error": "brightnessctl is not installed. Install it with: sudo apt install brightnessctl"
    }


def tool_battery_status():
    if command_exists("upower"):
        battery = tool_run_shell(
            "upower -e | grep -i battery | head -n1"
        )
        path = battery.get("stdout", "").strip()
        if path:
            return tool_run_shell(f"upower -i {shlex.quote(path)}")

    sys_power = "/sys/class/power_supply"
    if os.path.isdir(sys_power):
        for entry in os.listdir(sys_power):
            if entry.upper().startswith("BAT"):
                return tool_run_shell(
                    f"cat {sys_power}/{shlex.quote(entry)}/capacity "
                    f"{sys_power}/{shlex.quote(entry)}/status"
                )

    return {"success": False, "error": "No battery found (likely a desktop machine)."}


def tool_media_control(action):
    """action: play_pause | play | pause | next | previous | stop"""
    if not command_exists("playerctl"):
        return {
            "success": False,
            "error": "playerctl is not installed. Install it with: sudo apt install playerctl"
        }

    allowed = {"play-pause", "play", "pause", "next", "previous", "stop"}
    normalized = (action or "").lower().replace("_", "-")

    if normalized not in allowed:
        return {"success": False, "error": f"Unsupported media action: {action}"}

    return tool_run_shell(f"playerctl {normalized}")


def tool_lock_screen():
    for cmd in [
        "loginctl lock-session",
        "xdg-screensaver lock",
        "gnome-screensaver-command --lock",
        "xflock4",
    ]:
        binary = cmd.split()[0]
        if command_exists(binary):
            return tool_run_shell(cmd)

    return {"success": False, "error": "No screen-lock utility found."}


# ============================================================
# NEW: MUSIC PLAYBACK (streaming, not downloading)
# ============================================================
#
# Downloading copyrighted music/video from YouTube etc. generally
# violates its Terms of Service and copyright law in most places, even
# for personal use. These tools stream and play through mpv instead of
# saving a file - use media_control (above) to pause/skip/stop.
# ============================================================

def tool_play_music(query):
    if not command_exists("mpv"):
        return {"success": False, "error": "mpv is not installed. Install it with: sudo apt install mpv"}
    if not command_exists("yt-dlp"):
        return {
            "success": False,
            "error": "yt-dlp is not installed. Install it with: sudo apt install yt-dlp (or: pip install yt-dlp)",
        }

    try:
        subprocess.Popen(
            ["mpv", "--no-video", "--really-quiet", f"ytdl://ytsearch:{query}"],
            env=gui_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "success": True,
            "playing": query,
            "note": "Streaming via mpv, nothing saved to disk. Use media_control to pause/skip/stop.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_stop_music():
    result = tool_media_control("stop")
    if result.get("success"):
        return result
    return tool_run_shell("pkill -f 'mpv --no-video'")


# ============================================================
# NEW: GENERIC FILE DOWNLOAD
# ============================================================

MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024  # 200MB cap


def tool_download_file(url, dest_path):
    if not re.match(r"^https?://", url or "", re.I):
        return {"success": False, "error": "URL must start with http:// or https://"}

    dest_path = os.path.abspath(os.path.expanduser(dest_path))

    if is_sensitive_path(dest_path):
        return {"success": False, "blocked": True, "error": "Refusing to write to a sensitive path."}

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GDR AI personal assistant)"})
        total = 0
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("File exceeds the 200MB download cap.")
                    f.write(chunk)

        return {"success": True, "path": dest_path, "bytes": total}

    except Exception as e:
        try:
            if os.path.exists(dest_path):
                os.remove(dest_path)
        except Exception:
            pass
        return {"success": False, "error": str(e)}


# ============================================================
# NEW: WINDOW MANAGEMENT
# ============================================================

def tool_list_windows():
    if not command_exists("wmctrl"):
        return {"success": False, "error": "wmctrl is not installed. Install it with: sudo apt install wmctrl"}
    return tool_run_shell("wmctrl -l")


def tool_focus_window(name):
    if not command_exists("wmctrl"):
        return {"success": False, "error": "wmctrl is not installed. Install it with: sudo apt install wmctrl"}
    if not name:
        return {"success": False, "error": "Provide a window name to focus."}
    return tool_run_shell(f"wmctrl -a {shlex.quote(name)}")


# ============================================================
# NEW: REMINDERS / TIMERS
# ============================================================

def tool_set_reminder(message, seconds):
    """Fires a desktop notification after `seconds`, without blocking the agent."""
    try:
        seconds = max(1, min(int(seconds), 24 * 60 * 60))
    except (TypeError, ValueError):
        return {"success": False, "error": "seconds must be a number."}

    def _fire():
        tool_notify("⏰ GDR AI reminder", str(message))
        log_event("reminder_fired", message=str(message))

    timer = threading.Timer(seconds, _fire)
    timer.daemon = True
    timer.start()

    log_event("reminder_set", message=str(message), details=f"in {seconds}s")

    return {
        "success": True,
        "message": message,
        "fires_in_seconds": seconds,
        "note": "This runs in the background - you can keep using GDR AI normally."
    }


# ============================================================
# NEW: NOTES
# ============================================================

NOTES_FILE = os.path.join(SCRIPT_DIR, "gdr_notes.txt")


def tool_add_note(text):
    if not text:
        return {"success": False, "error": "Note text is empty."}
    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now()}] {text}\n")
        return {"success": True, "saved": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_list_notes(limit=20):
    try:
        if not os.path.exists(NOTES_FILE):
            return {"success": True, "notes": []}
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-int(limit):]
        return {"success": True, "notes": [l.strip() for l in lines]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# NEW: EMAIL (IMAP read / SMTP send, app-password based)
# ============================================================
#
# Set EMAIL_ADDRESS + EMAIL_APP_PASSWORD in the environment.
# For Gmail: turn on 2-Step Verification, then create an "App Password"
# at https://myaccount.google.com/apppasswords - use THAT, never your
# real account password.
# ============================================================

def _decode_mime_words(value):
    if not value:
        return ""
    parts = decode_header(value)
    decoded = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            decoded += text.decode(enc or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded


def tool_read_email(max_results=10, unread_only=True):
    if not _email_configured():
        return {
            "success": False,
            "error": "Email is not configured. Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in the environment.",
        }

    try:
        conn = imaplib.IMAP4_SSL(SECRETS["EMAIL_IMAP_HOST"], SECRETS["EMAIL_IMAP_PORT"])
        conn.login(SECRETS["EMAIL_ADDRESS"], SECRETS["EMAIL_APP_PASSWORD"])
        conn.select("INBOX")

        criterion = "UNSEEN" if unread_only else "ALL"
        status, data = conn.search(None, criterion)

        if status != "OK":
            conn.logout()
            return {"success": False, "error": "IMAP search failed."}

        ids = data[0].split()
        ids = ids[-int(max_results):]
        ids.reverse()

        messages = []
        for msg_id in ids:
            status, msg_data = conn.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            messages.append({
                "from": _decode_mime_words(msg.get("From")),
                "subject": _decode_mime_words(msg.get("Subject")),
                "date": msg.get("Date"),
            })

        conn.logout()
        return {"success": True, "count": len(messages), "emails": messages}

    except imaplib.IMAP4.error as e:
        return {"success": False, "error": f"IMAP error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_send_email(to, subject, body):
    if not _email_configured():
        return {
            "success": False,
            "error": "Email is not configured. Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in the environment.",
        }

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to or ""):
        return {"success": False, "error": "Invalid recipient address."}

    try:
        msg = MIMEText(body or "", "plain", "utf-8")
        msg["Subject"] = subject or "(no subject)"
        msg["From"] = SECRETS["EMAIL_ADDRESS"]
        msg["To"] = to

        context = ssl.create_default_context()
        with smtplib.SMTP(SECRETS["EMAIL_SMTP_HOST"], SECRETS["EMAIL_SMTP_PORT"]) as server:
            server.starttls(context=context)
            server.login(SECRETS["EMAIL_ADDRESS"], SECRETS["EMAIL_APP_PASSWORD"])
            server.sendmail(SECRETS["EMAIL_ADDRESS"], [to], msg.as_string())

        return {"success": True, "to": to, "subject": subject}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# NEW: LIVE NEWS / RSS + GENERIC WEBPAGE READING
# ============================================================

class _TextExtractor(HTMLParser):
    """Minimal stdlib-only HTML -> readable text extractor. No bs4 needed."""

    def __init__(self):
        super().__init__()
        self.chunks = []
        self.skip = False
        self.title_chunks = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip = True
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_chunks.append(data)
            return
        if not self.skip:
            text = data.strip()
            if text:
                self.chunks.append(text)

    def get_text(self):
        return "\n".join(self.chunks)

    def get_title(self):
        return "".join(self.title_chunks).strip()


def tool_fetch_webpage(url, max_chars=8000):
    """Fetch any URL and return its readable title + text. This is the
    generic 'give it the source of a website' tool."""
    if not re.match(r"^https?://", url or "", re.I):
        url = "https://" + (url or "")

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (GDR AI personal assistant)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(2_000_000)  # cap at ~2MB
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw.decode(charset, errors="replace")

        parser = _TextExtractor()
        parser.feed(html)

        return {
            "success": True,
            "url": url,
            "title": parser.get_title(),
            "text": trim_output(parser.get_text(), int(max_chars)),
        }

    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code} for {url}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


NEWS_FEEDS = {
    "top": "https://news.google.com/rss",
    "tech": "https://feeds.arstechnica.com/arstechnica/index",
    "india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "world": "https://news.google.com/rss/headlines/section/topic/WORLD",
    "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS",
}


def _parse_rss(xml_bytes, limit):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub = item.findtext("pubDate") or ""
        items.append({"title": title.strip(), "link": link.strip(), "published": pub.strip()})
        if len(items) >= limit:
            break
    return items


def tool_read_rss(feed_url, limit=8):
    """Read any RSS feed URL, not just the built-in topics."""
    try:
        req = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "Mozilla/5.0 (GDR AI personal assistant)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(2_000_000)

        items = _parse_rss(raw, int(limit))
        return {"success": True, "feed": feed_url, "items": items}

    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_news(topic="top", limit=8):
    """Read one of the built-in news topics: top, tech, india, world, business."""
    feed_url = NEWS_FEEDS.get((topic or "top").lower(), NEWS_FEEDS["top"])
    return tool_read_rss(feed_url, limit)


# ============================================================
# NEW: REMEMBERED SITES
# ============================================================
#
# "Give it the source of a specific website" - save a URL under a short
# name once, then just ask about it by name from then on, e.g.:
#   gdr "remember my college site as https://college.edu/notices"
#   gdr "check my college site for anything new"
# ============================================================

SITES_FILE = os.path.join(SCRIPT_DIR, "gdr_sites.json")


def _load_sites():
    return load_json(SITES_FILE, {})


def tool_remember_site(name, url):
    if not name or not url:
        return {"success": False, "error": "Both name and url are required."}
    sites = _load_sites()
    sites[name.lower().strip()] = url
    save_json(SITES_FILE, sites)
    return {"success": True, "name": name, "url": url}


def tool_forget_site(name):
    sites = _load_sites()
    key = (name or "").lower().strip()
    if key not in sites:
        return {"success": False, "error": f"No saved site named '{name}'."}
    del sites[key]
    save_json(SITES_FILE, sites)
    return {"success": True, "removed": name}


def tool_list_sites():
    return {"success": True, "sites": _load_sites()}


def tool_read_site(name, max_chars=8000):
    sites = _load_sites()
    key = (name or "").lower().strip()
    url = sites.get(key)
    if not url:
        return {"success": False, "error": f"No saved site named '{name}'. Use remember_site first."}
    return tool_fetch_webpage(url, max_chars)


# ============================================================
# NEW: SAFE CALCULATOR (no eval of arbitrary code)
# ============================================================

import ast
import operator as _op

_CALC_OPS = {
    ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
    ast.Div: _op.truediv, ast.Pow: _op.pow, ast.Mod: _op.mod,
    ast.USub: _op.neg, ast.UAdd: _op.pos, ast.FloorDiv: _op.floordiv,
}


def _safe_eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_OPS:
        return _CALC_OPS[type(node.op)](_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _CALC_OPS:
        return _CALC_OPS[type(node.op)](_safe_eval_node(node.operand))
    raise ValueError("Only plain arithmetic (+ - * / // % **) is allowed.")


def tool_calculate(expression):
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval_node(tree.body)
        return {"success": True, "expression": expression, "result": result}
    except Exception as e:
        return {"success": False, "error": f"Could not evaluate: {e}"}


# ============================================================
# NEW: OPEN A SPECIFIC FILE
# ============================================================

def tool_open_file(path):
    path = os.path.abspath(os.path.expanduser(path))

    if is_sensitive_path(path):
        return {"success": False, "blocked": True, "error": "Sensitive file access blocked."}

    if not os.path.exists(path):
        return {"success": False, "error": f"File not found: {path}"}

    try:
        subprocess.Popen(
            ["xdg-open", path],
            env=gui_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"success": True, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description":
                "Run a non-destructive, non-privileged Linux shell command. "
                "For anything needing root, use run_privileged / service_restart / "
                "service_stop / service_start / system_power instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string"
                    },
                    "timeout": {
                        "type": "integer"
                    }
                },
                "required": ["command"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description":
                "Open an installed Linux application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string"
                    },
                    "arguments": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["application"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description":
                "Close a named application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string"
                    }
                },
                "required": ["application"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description":
                "Open a website URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string"
                    }
                },
                "required": ["url"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "google_search",
            "description":
                "Search Google.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    }
                },
                "required": ["query"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description":
                "Search YouTube for a song, video, movie or topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    }
                },
                "required": ["query"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_open",
            "description":
                "Open a URL using optional Playwright browser automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string"
                    }
                },
                "required": ["url"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click a web page element by CSS selector or visible text in the persistent browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                    "button": {"type": "string"}
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_fill",
            "description": "Fill a web form field using a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["selector", "text"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Click and fill a web field; optionally press Enter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                    "press_enter": {"type": "boolean"}
                },
                "required": ["selector", "text"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_press",
            "description": "Press a keyboard key in the persistent browser.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_wait",
            "description": "Wait briefly for a web page to update.",
            "parameters": {
                "type": "object",
                "properties": {"milliseconds": {"type": "integer"}}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_back",
            "description": "Go back one page in the persistent browser.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": "Read visible text from the current web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "max_chars": {"type": "integer"}
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_inspect",
            "description": "Inspect the current page for title, URL, CSS stylesheets, scripts, controls, console errors and failed network requests. Use this for diagnosing website problems such as CSS not loading.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current browser page.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "browser_close",
            "description": "Close the persistent browser session.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description":
                "Type text into the currently focused desktop application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string"
                    }
                },
                "required": ["text"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "keypress",
            "description":
                "Press an allowed keyboard key or combination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string"
                    }
                },
                "required": ["key"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "mouse_click",
            "description":
                "Click a screen coordinate using xdotool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer"
                    },
                    "y": {
                        "type": "integer"
                    },
                    "button": {
                        "type": "integer"
                    }
                },
                "required": ["x", "y"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "clipboard_get",
            "description":
                "Read the current desktop clipboard.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "clipboard_set",
            "description":
                "Set desktop clipboard text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string"
                    }
                },
                "required": ["text"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "show_screen",
            "description":
                "Display a fullscreen message on the Linux desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string"
                    },
                    "title": {
                        "type": "string"
                    },
                    "duration": {
                        "type": "number"
                    }
                },
                "required": ["message"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "notify",
            "description":
                "Show a Linux desktop notification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string"
                    },
                    "message": {
                        "type": "string"
                    }
                },
                "required": ["title", "message"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description":
                "Get Linux system and desktop information.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "system_health",
            "description":
                "Check CPU, memory, disk, uptime and processes.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "processes",
            "description":
                "Show running processes.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description":
                "List files and directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    }
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description":
                "Find files by filename.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string"
                    },
                    "path": {
                        "type": "string"
                    },
                    "max_results": {
                        "type": "integer"
                    }
                },
                "required": ["pattern"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description":
                "Read a normal text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "max_chars": {
                        "type": "integer"
                    }
                },
                "required": ["path"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description":
                "Write a normal text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string"
                    },
                    "append": {
                        "type": "boolean"
                    }
                },
                "required": [
                    "path",
                    "content"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description":
                "Create a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    }
                },
                "required": ["path"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "disk_usage",
            "description":
                "Check disk usage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    }
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "service_status",
            "description":
                "Check a Linux systemd service (read-only, no admin needed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string"
                    }
                },
                "required": ["service"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "service_restart",
            "description": "Restart a systemd service. Requires sudo NOPASSWD rule (see ADMIN section in agent.py).",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string"}},
                "required": ["service"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "service_stop",
            "description": "Stop a systemd service. Requires sudo NOPASSWD rule (see ADMIN section in agent.py).",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string"}},
                "required": ["service"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "service_start",
            "description": "Start a systemd service. Requires sudo NOPASSWD rule (see ADMIN section in agent.py).",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string"}},
                "required": ["service"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "run_privileged",
            "description":
                "Run a root command via sudo, but ONLY if it matches the admin allowlist "
                "(see ADMIN section in agent.py / GDR_SUDO_ALLOWLIST env var). "
                "Use service_restart/service_stop/service_start for services instead of this directly when possible.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "system_power",
            "description":
                "Reboot or shut down the machine. Disabled unless GDR_ALLOW_POWER=1 is set in the "
                "environment. Always ask the user to explicitly confirm out loud before calling this "
                "with confirm=true - never call it with confirm=true on the first try.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["reboot", "shutdown", "poweroff"]},
                    "confirm": {"type": "boolean"}
                },
                "required": ["action"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "network_info",
            "description":
                "Show interfaces, routes, ports and Tailscale information.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "ping",
            "description":
                "Ping a host.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string"
                    }
                },
                "required": ["host"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description":
                "Check Git status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    }
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description":
                "Take a screenshot of the Linux desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    }
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "see_screen",
            "description":
                "Take a screenshot and have a vision model actually look at it and describe or "
                "diagnose what's on screen. Use this whenever the user asks 'can you see my screen', "
                "'what's wrong with my screen', or similar. Requires ANTHROPIC_API_KEY.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "What to ask about the screenshot."}
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "package_info",
            "description":
                "Show information about a Linux package without installing it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package": {
                        "type": "string"
                    }
                },
                "required": ["package"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_profile",
            "description":
                "Get the user's safe assistant preferences.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description":
                "Remember a safe assistant preference such as tone or language. Never store secrets/passwords here.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string"
                    },
                    "value": {}
                },
                "required": [
                    "key",
                    "value"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "volume",
            "description": "Get or change system audio volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["get", "set", "mute", "unmute", "up", "down"]},
                    "level": {"type": "integer", "description": "0-150, only used with action=set"}
                },
                "required": ["action"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "brightness",
            "description": "Get or change screen brightness (requires brightnessctl).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["get", "set", "up", "down"]},
                    "level": {"type": "integer", "description": "1-100, only used with action=set"}
                },
                "required": ["action"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "battery_status",
            "description": "Show battery charge and status, if a battery is present.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "media_control",
            "description": "Control the currently playing media (requires playerctl).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["play_pause", "play", "pause", "next", "previous", "stop"]}
                },
                "required": ["action"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Stream and play a song/artist/playlist by search query (via mpv + yt-dlp). Does not download anything.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "stop_music",
            "description": "Stop whatever music is currently streaming.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "download_file",
            "description": "Download a file from a direct URL to a local path (200MB cap). Not for streaming media - use play_music for that.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "dest_path": {"type": "string"}
                },
                "required": ["url", "dest_path"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Lock the desktop screen.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "list_windows",
            "description": "List open desktop windows (requires wmctrl).",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Bring a window to the front by (partial) title match.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Fire a desktop notification after a delay, without blocking the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "seconds": {"type": "integer", "description": "Delay before the reminder fires"}
                },
                "required": ["message", "seconds"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Save a quick timestamped text note for the user.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "Show the user's most recent saved notes.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}}
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read recent emails from the configured inbox (unread by default). Requires EMAIL_ADDRESS + EMAIL_APP_PASSWORD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer"},
                    "unread_only": {"type": "boolean"}
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email from the configured account. Requires EMAIL_ADDRESS + EMAIL_APP_PASSWORD. Always confirm recipient and content with the user before sending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get recent headlines for a built-in topic: top, tech, india, world, business.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "limit": {"type": "integer"}
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_rss",
            "description": "Read any RSS/Atom feed URL, not just the built-in news topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feed_url": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["feed_url"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "Fetch any website URL and return its readable title and text. Use this to 'read the source' of a specific site the user gives you.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "max_chars": {"type": "integer"}
                },
                "required": ["url"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "remember_site",
            "description": "Save a website URL under a short name so the user can refer to it later by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"}
                },
                "required": ["name", "url"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "forget_site",
            "description": "Remove a previously remembered website.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "list_sites",
            "description": "List all remembered website names and URLs.",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_site",
            "description": "Read the current content of a previously remembered website by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "max_chars": {"type": "integer"}
                },
                "required": ["name"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Safely evaluate a plain arithmetic expression (+ - * / // % **). No code execution.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Open a specific local file with its default application.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    }
]

gdr_extras.init(globals())
TOOLS.extend(gdr_extras.TOOLS)
# ============================================================
# TOOL DISPATCH
# ============================================================

def execute_tool(
    name,
    arguments
):

    try:
        if name in gdr_extras.HANDLERS:
            return gdr_extras.HANDLERS[name](**arguments)

        if name == "run_shell":
            return tool_run_shell(
                arguments.get("command"),
                arguments.get(
                    "timeout",
                    COMMAND_TIMEOUT
                )
            )

        if name == "open_application":
            return tool_open_application(
                arguments.get("application"),
                arguments.get("arguments")
            )

        if name == "close_application":
            return tool_close_application(
                arguments.get("application")
            )

        if name == "open_url":
            return tool_open_url(
                arguments.get("url")
            )

        if name == "google_search":
            return tool_google_search(
                arguments.get("query")
            )

        if name == "youtube_search":
            return tool_youtube_search(
                arguments.get("query")
            )

        if name == "browser_open":
            return tool_browser_open(
                arguments.get("url")
            )

        if name == "browser_click":
            return tool_browser_click(
                arguments.get("selector", ""),
                arguments.get("text", ""),
                arguments.get("button", "left")
            )

        if name == "browser_fill":
            return tool_browser_fill(
                arguments.get("selector"),
                arguments.get("text")
            )

        if name == "browser_type":
            return tool_browser_type(
                arguments.get("selector"),
                arguments.get("text"),
                arguments.get("press_enter", False)
            )

        if name == "browser_press":
            return tool_browser_press(arguments.get("key"))

        if name == "browser_wait":
            return tool_browser_wait(
                arguments.get("milliseconds", 1000)
            )

        if name == "browser_back":
            return tool_browser_back()

        if name == "browser_read":
            return tool_browser_read(
                arguments.get("selector", "body"),
                arguments.get("max_chars", 12000)
            )

        if name == "browser_inspect":
            return tool_browser_inspect()

        if name == "browser_screenshot":
            return tool_browser_screenshot(
                arguments.get("path", "")
            )

        if name == "browser_close":
            return tool_browser_close()

        if name == "type_text":
            return tool_type_text(
                arguments.get("text")
            )

        if name == "keypress":
            return tool_keypress(
                arguments.get("key")
            )

        if name == "mouse_click":
            return tool_mouse_click(
                arguments.get("x"),
                arguments.get("y"),
                arguments.get(
                    "button",
                    1
                )
            )

        if name == "clipboard_get":
            return tool_clipboard_get()

        if name == "clipboard_set":
            return tool_clipboard_set(
                arguments.get("text")
            )

        if name == "show_screen":
            return tool_show_screen(
                arguments.get("message"),
                arguments.get(
                    "title",
                    "GDR AI"
                ),
                arguments.get(
                    "duration",
                    5
                )
            )

        if name == "notify":
            return tool_notify(
                arguments.get("title"),
                arguments.get("message")
            )

        if name == "system_info":
            return tool_system_info()

        if name == "system_health":
            return tool_system_health()

        if name == "processes":
            return tool_processes()

        if name == "list_directory":
            return tool_list_directory(
                arguments.get(
                    "path",
                    HOME
                )
            )

        if name == "find_files":
            return tool_find_files(
                arguments.get("pattern"),
                arguments.get(
                    "path",
                    HOME
                ),
                arguments.get(
                    "max_results",
                    100
                )
            )

        if name == "read_file":
            return tool_read_file(
                arguments.get("path"),
                arguments.get(
                    "max_chars",
                    20000
                )
            )

        if name == "write_file":
            return tool_write_file(
                arguments.get("path"),
                arguments.get("content"),
                arguments.get(
                    "append",
                    False
                )
            )

        if name == "create_directory":
            return tool_create_directory(
                arguments.get("path")
            )

        if name == "disk_usage":
            return tool_disk_usage(
                arguments.get(
                    "path",
                    HOME
                )
            )

        if name == "service_status":
            return tool_service_status(
                arguments.get("service")
            )

        if name == "service_restart":
            return tool_service_restart(arguments.get("service"))

        if name == "service_stop":
            return tool_service_stop(arguments.get("service"))

        if name == "service_start":
            return tool_service_start(arguments.get("service"))

        if name == "run_privileged":
            return tool_run_privileged(arguments.get("command"))

        if name == "system_power":
            return tool_system_power(
                arguments.get("action"),
                arguments.get("confirm", False)
            )

        if name == "network_info":
            return tool_network_info()

        if name == "ping":
            return tool_ping(
                arguments.get("host")
            )

        if name == "git_status":
            return tool_git_status(
                arguments.get(
                    "path",
                    HOME
                )
            )

        if name == "screenshot":
            return tool_screenshot(
                arguments.get("path", "")
            )

        if name == "see_screen":
            return tool_see_screen(
                arguments.get(
                    "question",
                    "What's on my screen right now? Point out anything that looks broken or wrong."
                )
            )

        if name == "package_info":
            return tool_package_info(
                arguments.get("package")
            )

        if name == "get_profile":
            return tool_get_profile()

        if name == "update_profile":
            return tool_update_profile(
                arguments.get("key"),
                arguments.get("value")
            )

        if name == "volume":
            return tool_volume(
                arguments.get("action", "get"),
                arguments.get("level")
            )

        if name == "brightness":
            return tool_brightness(
                arguments.get("action", "get"),
                arguments.get("level")
            )

        if name == "battery_status":
            return tool_battery_status()

        if name == "media_control":
            return tool_media_control(arguments.get("action"))

        if name == "play_music":
            return tool_play_music(arguments.get("query"))

        if name == "stop_music":
            return tool_stop_music()

        if name == "download_file":
            return tool_download_file(
                arguments.get("url"),
                arguments.get("dest_path")
            )

        if name == "lock_screen":
            return tool_lock_screen()

        if name == "list_windows":
            return tool_list_windows()

        if name == "focus_window":
            return tool_focus_window(arguments.get("name"))

        if name == "set_reminder":
            return tool_set_reminder(
                arguments.get("message"),
                arguments.get("seconds")
            )

        if name == "add_note":
            return tool_add_note(arguments.get("text"))

        if name == "list_notes":
            return tool_list_notes(arguments.get("limit", 20))

        if name == "read_email":
            return tool_read_email(
                arguments.get("max_results", 10),
                arguments.get("unread_only", True)
            )

        if name == "send_email":
            return tool_send_email(
                arguments.get("to"),
                arguments.get("subject"),
                arguments.get("body")
            )

        if name == "get_news":
            return tool_get_news(
                arguments.get("topic", "top"),
                arguments.get("limit", 8)
            )

        if name == "read_rss":
            return tool_read_rss(
                arguments.get("feed_url"),
                arguments.get("limit", 8)
            )

        if name == "fetch_webpage":
            return tool_fetch_webpage(
                arguments.get("url"),
                arguments.get("max_chars", 8000)
            )

        if name == "remember_site":
            return tool_remember_site(
                arguments.get("name"),
                arguments.get("url")
            )

        if name == "forget_site":
            return tool_forget_site(arguments.get("name"))

        if name == "list_sites":
            return tool_list_sites()

        if name == "read_site":
            return tool_read_site(
                arguments.get("name"),
                arguments.get("max_chars", 8000)
            )

        if name == "calculate":
            return tool_calculate(arguments.get("expression"))

        if name == "open_file":
            return tool_open_file(arguments.get("path"))

        return {
            "success": False,
            "error":
                f"Unknown tool: {name}"
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = f"""
You are {AGENT_NAME}, a personal Linux computer assistant.

The user is {profile.get("name", USER_NAME)}.

You are running directly on the user's Linux computer.

Current environment:
- Linux distribution: {DISTRO}
- Desktop: {DESKTOP or "unknown"}
- Session: {SESSION_TYPE or "unknown"}
- Hostname: {socket.gethostname()}

PERSONALITY:
- Friendly.
- Natural.
- Direct.
- Casual but useful.
- Talk like a capable friend.
- Do not constantly repeat technical details.
- Do not say you are "just an AI".
- Do not unnecessarily explain simple actions.

IMPORTANT BEHAVIOR:
1. Use tools when the user asks you to actually do something.
2. Do not merely tell the user how to do an action when you can perform it.
3. After a successful tool call, briefly report what happened.
4. If a tool fails, explain the real reason.
5. Never pretend that an action succeeded if the tool says it failed.
6. You may chain several tools when necessary.
7. For GUI tasks, use GUI tools.
8. For files, use file tools.
9. For websites, use browser/URL tools for interaction; use fetch_webpage/read_site for just reading content.
10. For YouTube, use youtube_search first. Direct video selection requires browser automation.
11. Remember safe user preferences using update_profile when explicitly asked. NEVER store passwords,
    API keys or other secrets via update_profile, add_note, write_file or any other persistence tool -
    those only ever come from environment variables.
12. Never reveal API keys, passwords, private keys or credentials, even partially.
13. Do not access sensitive credential files.
14. Do not perform destructive operations automatically without explicit confirmation.
15. If a tool says confirmation is required, tell the user exactly what needs confirming and wait for
    them to say yes before calling it again.
16. Do not repeatedly call the same tool after a clear failure. Change strategy.
17. Prefer one well-chosen tool call over exploratory/redundant calls.
18. Do not use multiple shell commands when one command can accomplish the task.
19. When a task requires multiple steps, continue automatically until the requested task is complete or a real blocker requires the user.
20. If a tool times out or has a transient failure, retry it with the same state when safe; if unsafe to repeat, change strategy instead.
21. Do not stop merely because one tool failed. Use the failure result to choose the next tool or recovery step.
22. For browser tasks, prefer the persistent browser tools over xdotool. Open the site, inspect it, then click/fill/read as needed.
23. For website debugging, use browser_inspect after browser_open. Check stylesheet URLs, failed requests and console errors before concluding why CSS is broken.
24. After every successful step, immediately use the result as input to the next required step.
25. Avoid repeating an identical failed tool call more than once; recover or try a different method.
26. For long-running work, keep the current task state in the tool-call conversation and continue from the last successful step.
27. When a tool fails, first explain/use the exact error. Do not hide the failure.
28. If browser_open fails, troubleshoot Playwright/browser startup before falling back to unrelated shell commands.
29. Browser troubleshooting may check Playwright installation, browser availability, DISPLAY/session variables, and the browser's detailed exception.
30. When a browser task succeeds, continue using the same browser session for subsequent actions.
31. Never silently abandon a task because one tool failed.
32. Prefer the browser tools for website interaction and browser_inspect for website diagnostics.

ADMIN / PRIVILEGED ACTIONS:
33. For restarting, stopping, or starting a systemd service, use service_restart/service_stop/service_start,
    not run_shell. These go through a sudo allowlist that must be configured on the machine; if they fail
    with a sudoers error, tell the user exactly what to add (they'll find the instructions in agent.py).
34. For any other root-level command, use run_privileged, and only if it is safe and something the user
    clearly wants. It will refuse anything outside the configured allowlist - report that refusal plainly.
35. NEVER call system_power with confirm=true unless the user has explicitly and unambiguously confirmed
    they want to reboot/shut down THIS session, after you've asked them directly. Always ask first.

EMAIL / NEWS / WEB READING:
36. Use read_email to check the inbox and send_email to send messages. Always read back the recipient,
    subject and a summary of the body to the user before calling send_email, unless they've already
    given you the exact content and told you to send it.
37. Use get_news for the built-in topics (top, tech, india, world, business) and read_rss for any other
    feed URL the user gives you.
38. Use fetch_webpage to read the text of any URL the user gives you directly. Use remember_site once to
    save a URL under a name, then read_site by that name afterward - this is what to do when the user
    wants you to "know about" a specific site so they can just ask about it by name later.
39. When summarizing news or web content, keep it conversational and give the gist - don't dump raw
    RSS/HTML back at the user.

SCREEN VISION:
40. If the user asks "can you see my screen", "what's wrong with my screen", or similar, use see_screen.
    Report exactly what the model saw - don't guess about it yourself first.

MUSIC:
41. For playing music, use play_music (this streams, it does not download or save anything - never call
    download_file for songs/videos, since that would generally violate copyright).

ANDROID/REMOTE CONTEXT:
The user may be controlling this agent from Android Termux through SSH/Tailscale.
Do not assume the phone itself is the computer.
The Linux laptop is the execution machine.

GUI:
The user may be using Kali XFCE, GNOME, KDE or another desktop.
Do not assume Ubuntu.
"""
SYSTEM_PROMPT += gdr_extras.PROMPT_ADDITIONS



# ============================================================
# MESSAGE HANDLING
# ============================================================

def assistant_message_dict(
    message,
    tool_calls
):

    data = {
        "role": "assistant",
        "content":
            getattr(
                message,
                "content",
                None
            )
    }

    if tool_calls:

        data["tool_calls"] = []

        for tc in tool_calls:

            data["tool_calls"].append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name":
                        tc.function.name,
                    "arguments":
                        tc.function.arguments
                }
            })

    return data



def _extract_http_status(error):
    """Best-effort extraction of an HTTP status from a Sarvam SDK exception."""
    for attr in ("status_code", "status", "http_status"):
        value = getattr(error, attr, None)
        if isinstance(value, int):
            return value

    response = getattr(error, "response", None)
    if response is not None:
        for attr in ("status_code", "status"):
            value = getattr(response, attr, None)
            if isinstance(value, int):
                return value

    match = re.search(r"status_code[=:]\s*(\d+)", str(error))
    if match:
        return int(match.group(1))

    match = re.search(r"\b(429|500|502|503|504)\b", str(error))
    if match:
        return int(match.group(1))

    return None


def _extract_retry_after(error):
    """Read Retry-After when the SDK exposes response headers."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None

    if headers:
        value = headers.get("retry-after") or headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except (TypeError, ValueError):
                pass

    return None


def sarvam_chat_with_retry(**kwargs):
    """
    Throttle Sarvam requests and retry only temporary 429/5xx errors.
    Authentication/validation errors are not retried.
    """
    global _last_sarvam_request_at

    for attempt in range(SARVAM_MAX_RETRIES + 1):
        elapsed = time.monotonic() - _last_sarvam_request_at

        if elapsed < MIN_SARVAM_REQUEST_INTERVAL:
            time.sleep(MIN_SARVAM_REQUEST_INTERVAL - elapsed)

        try:
            response = client.chat.completions(**kwargs)
            _last_sarvam_request_at = time.monotonic()
            return response

        except Exception as error:
            _last_sarvam_request_at = time.monotonic()
            status = _extract_http_status(error)

            if status not in {429, 500, 502, 503, 504}:
                raise

            if attempt >= SARVAM_MAX_RETRIES:
                raise

            retry_after = _extract_retry_after(error)

            if retry_after is not None:
                delay = min(retry_after, SARVAM_MAX_BACKOFF)
            else:
                delay = min(
                    SARVAM_BASE_BACKOFF * (2 ** attempt),
                    SARVAM_MAX_BACKOFF
                )

            delay += random.uniform(0, 1.0)

            if status == 429:
                print(
                    f"\n⏳ Sarvam rate limit reached. "
                    f"Retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{SARVAM_MAX_RETRIES})..."
                )
            else:
                print(
                    f"\n⏳ Sarvam temporary server error ({status}). "
                    f"Retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{SARVAM_MAX_RETRIES})..."
                )

            time.sleep(delay)

    raise RuntimeError("Sarvam request failed after all retries.")


def run_agent(user_request, resume_messages=None, resume_step=0, resumed=False):
    global conversation

    if resume_messages is None:
        conversation.append({
            "role": "user",
            "content": user_request
        })
        conversation = conversation[-MEMORY_LIMIT:]

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]
        messages.extend(conversation)
    else:
        messages = resume_messages
        user_request = user_request or "resume interrupted task"

    messages = compact_messages(messages)

    thinking()

    log_event(
        "task_start" if not resumed else "task_resume",
        message=user_request,
        details=f"resume_step={resume_step}",
    )

    save_checkpoint(
        messages,
        user_request,
        resume_step,
        "running"
    )

    for step in range(resume_step, MAX_AGENT_STEPS):

        if STOP_EVENT.is_set():
            print("\n\n⏹️  Task stopped.")
            print("   Nothing further will run until you ask for it again.")
            log_event(
                "task_stopped",
                message="Stopped by user before the next agent step.",
            )
            save_checkpoint(messages, user_request, step, "cancelled")
            return False

        print(f"   ↳ agent step {step + 1}/{MAX_AGENT_STEPS}")
        if not QUIET_LOGGING:
            log_event(
                "agent_step",
                message=f"Agent step {step + 1}/{MAX_AGENT_STEPS}",
            )

        try:
            messages = compact_messages(messages)

            response = sarvam_chat_with_retry(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.25,
                max_tokens=MAX_TOKENS_PER_STEP
            )

            record_usage(response)

        except KeyboardInterrupt:
            print("\n\n⏸️ Paused safely.")
            print("   Your task state has been saved.")
            print("   Start GDR again to resume automatically.")
            log_event(
                "task_paused",
                message="User interrupted the agent. Checkpoint saved.",
            )
            save_checkpoint(messages, user_request, step, "running")
            return False

        except Exception as e:
            status = _extract_http_status(e)

            log_event(
                "sarvam_error",
                message=str(e),
                details=f"status={status}",
            )

            if status == 429:
                print(
                    "\n❌ Sarvam rate limit is still active."
                    "\n   Automatic backoff was exhausted."
                )
            elif status in {401, 403}:
                print(
                    "\n❌ Sarvam authentication/permission error."
                    "\n   Check SARVAM_API_KEY and account access."
                )
            else:
                print(f"\n❌ Sarvam error: {e}")

            save_checkpoint(messages, user_request, step, "running")
            return False

        if not response.choices:
            print("\n❌ No response received.")
            save_checkpoint(messages, user_request, step, "running")
            return False

        message = response.choices[0].message
        content = getattr(message, "content", None)
        tool_calls = getattr(message, "tool_calls", None)

        if tool_calls:
            messages.append(
                assistant_message_dict(message, tool_calls)
            )

            for tool_call in tool_calls:

                if STOP_EVENT.is_set():
                    print("\n\n⏹️  Task stopped mid-step.")
                    log_event(
                        "task_stopped",
                        message="Stopped by user between tool calls.",
                    )
                    save_checkpoint(messages, user_request, step, "cancelled")
                    return False

                name = tool_call.function.name
                raw_arguments = tool_call.function.arguments

                try:
                    arguments = json.loads(raw_arguments)
                except Exception:
                    arguments = {}

                print_tool(name)
                print(
                    f"      args: "
                    f"{trim_output(json.dumps(arguments, ensure_ascii=False), 700)}"
                )

                log_event(
                    "tool_start",
                    tool=name,
                    message="Tool started.",
                    details=json.dumps(arguments, ensure_ascii=False)[:5000],
                )

                tool_started = time.monotonic()

                try:
                    result = execute_tool(name, arguments)
                except KeyboardInterrupt:
                    result = {
                        "success": False,
                        "interrupted": True,
                        "error": "User interrupted this tool with Ctrl+C."
                    }

                elapsed = time.monotonic() - tool_started

                success = bool(result.get("success", False))

                print_result(success)
                print(f"      time: {elapsed:.2f}s")

                if not success:
                    print(
                        f"      error: "
                        f"{trim_output(result.get('error', 'Unknown failure'), 2500)}"
                    )

                log_event(
                    "tool_result",
                    tool=name,
                    success=success,
                    message=(
                        "Tool completed successfully."
                        if success
                        else result.get("error", "Tool failed.")
                    ),
                    details=f"elapsed={elapsed:.2f}s; result={safe_json(result)[:8000]}",
                )

                tool_payload = dict(result)

                if not success:
                    tool_payload["_agent_hint"] = (
                        "Tool failed. Do not pretend it worked. "
                        "Use the exact error to troubleshoot. "
                        "Try a different method or retry once if safe. "
                        "Continue the original task if possible."
                    )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": trim_output(
                        safe_json(tool_payload),
                        TOOL_RESULT_CHAR_LIMIT
                    )
                })

                # Save immediately after EVERY tool, so Ctrl+C loses at most the
                # current model call rather than the completed work.
                save_checkpoint(
                    messages,
                    user_request,
                    step,
                    "running"
                )

            continue

        if content:
            content = content.strip()

            print(f"\n🤖 {content}")

            conversation.append({
                "role": "assistant",
                "content": content
            })
            conversation = conversation[-MEMORY_LIMIT:]

            clear_checkpoint()

            log_event(
                "task_complete",
                message=content[:4000],
            )

            return True

        print(
            "\n🤖 I completed the request, "
            "but there was no text response."
        )

        clear_checkpoint()
        log_event(
            "task_complete",
            message="No text response returned.",
        )
        return True

    print(
        f"\n⚠️ I reached the {MAX_AGENT_STEPS}-step limit."
        "\n   The current task state has been saved."
        "\n   Start GDR again to continue it."
    )

    log_event(
        "step_limit",
        message=f"Reached {MAX_AGENT_STEPS} agent steps.",
    )
    save_checkpoint(messages, user_request, MAX_AGENT_STEPS, "running")
    return False


# ============================================================
# COMMAND LINE MODES
# ============================================================

def print_help():

    print("""
GDR AI commands:

  gdr
      Start interactive mode.

  gdr "open Firefox"
      Run one request and exit.

  gdr --system
      Show system information.

  gdr --network
      Show network information.

  gdr --health
      Show system health.

  gdr --help
      Show this help.

  gdr --history
      Show recent activity.

  gdr --resume
      Resume the last interrupted task without asking.

  gdr --gui
      Open the Tkinter chat window instead of the terminal.

In interactive mode:

  stop / cancel
      Cancel whatever task is currently running, without exiting.

  <anything else while a task is running>
      Stops the current task and immediately starts your new request.
      You never have to wait for one task to finish before giving the next.

Examples:

  gdr "open VS Code"

  gdr "open YouTube"

  gdr "search Google for Python decorators"

  gdr "play Hanuman Chalisa on YouTube"

  gdr "play some lofi music"

  gdr "show hello GDR on screen for 5 seconds"

  gdr "take a screenshot"

  gdr "can you see my screen? anything wrong with it?"

  gdr "check my disk usage"

  gdr "find agent.py in my home directory"

  gdr "check if SSH is running"

  gdr "restart the nginx service"

  gdr "check my unread emails"

  gdr "email John saying I'll be 10 minutes late"

  gdr "what's the top news today"

  gdr "remember my college site as https://college.edu/notices"

  gdr "check my college site for anything new"

  gdr "open my project folder"

  gdr "open snapcourse.in and check why CSS is not loading"

  gdr "open example.com, click the login button, fill the email field and submit"

  gdr "remember that I prefer casual explanations"

SETUP FOR NEW FEATURES (all via environment variables, never in this file):

  Email (Gmail app password):
    export EMAIL_ADDRESS="you@gmail.com"
    export EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

  Screen vision:
    export ANTHROPIC_API_KEY="..."

  Admin actions (restart/stop/start services):
    sudo visudo -f /etc/sudoers.d/gdr-ai
    (add NOPASSWD rules - see the ADMIN section at the top of agent.py)

  Reboot/shutdown (off by default):
    export GDR_ALLOW_POWER=1

  Hardware access (webcam/mic/USB/serial/Bluetooth) - use groups, not root:
    sudo usermod -aG audio,video,plugdev,dialout,netdev,bluetooth $USER
    (then log out and back in)

  Running GDR itself as root (sudo gdr) - only if you've read the
  ROOT / SUDO SAFETY CHECK comment near the top of agent.py:
    export GDR_I_UNDERSTAND_ROOT_RISK=1
    sudo -E env HOME="$HOME" gdr
    (sudo normally resets $HOME and drops most env vars for the root
    user - this form preserves your API keys and profile/notes files,
    which live under your own home directory, not root's)
""")


def _stdin_reader():
    """
    Runs on its own thread for the whole life of the program.
    Its only job is to read a line and push it onto INPUT_QUEUE - it never
    blocks on anything the agent is doing, so you can type at ANY time,
    including while a task is mid-run.
    """
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            INPUT_QUEUE.put(None)  # sentinel: stdin closed / ctrl+d
            return
        INPUT_QUEUE.put(line)


def _run_agent_in_background(request, resume_messages=None, resume_step=0, resumed=False):
    """Starts run_agent() on a worker thread and returns immediately."""
    STOP_EVENT.clear()

    def _worker():
        AGENT_THREAD["busy"] = True
        try:
            run_agent(
                request,
                resume_messages=resume_messages,
                resume_step=resume_step,
                resumed=resumed,
            )
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        finally:
            AGENT_THREAD["busy"] = False
            print("\nGDR > ", end="", flush=True)

    t = threading.Thread(target=_worker, daemon=True)
    AGENT_THREAD["thread"] = t
    t.start()


def _stop_current_task(wait_seconds=15):
    """Signals the running task to stop and waits briefly for it to unwind."""
    if not AGENT_THREAD["busy"]:
        return False

    STOP_EVENT.set()
    thread = AGENT_THREAD["thread"]

    if thread is not None:
        thread.join(timeout=wait_seconds)

    return True


def interactive():

    print("""
👋 Hey bro, I'm here.

   Kali edition 😎

   What are we doing?

   Type 'exit' whenever you're done, or 'stop' to cancel whatever's running.
   You can type a new request at any time - even while I'm mid-task - and
   I'll stop what I'm doing and switch to it.
""")

    checkpoint = load_checkpoint()

    if checkpoint:
        print(
            "\n⏯️  There's an unfinished task from last time:"
            f"\n   \"{checkpoint.get('user_request', '')}\""
            f"\n   (stopped at step {checkpoint.get('step', '?')})"
        )

        if ASK_BEFORE_RESUME:
            answer = input(
                "   Resume it? [y/N] "
            ).strip().lower()

            if answer in {"y", "yes"}:
                _run_agent_in_background(
                    checkpoint.get("user_request", ""),
                    resume_messages=checkpoint.get("messages"),
                    resume_step=int(checkpoint.get("step", 0)),
                    resumed=True,
                )
            else:
                clear_checkpoint()
                print("   Okay - starting fresh. That old task is discarded.\n")
        elif AUTO_RESUME:
            print("   Resuming from the last saved step...")
            _run_agent_in_background(
                checkpoint.get("user_request", ""),
                resume_messages=checkpoint.get("messages"),
                resume_step=int(checkpoint.get("step", 0)),
                resumed=True,
            )

    reader = threading.Thread(target=_stdin_reader, daemon=True)
    reader.start()

    print("GDR > ", end="", flush=True)

    while True:

        line = INPUT_QUEUE.get()

        if line is None:
            _stop_current_task()
            print("\n\n👋 Bye bro.")
            break

        request = line.strip()

        if not request:
            print("GDR > ", end="", flush=True)
            continue

        low = request.lower()

        if low in {"exit", "quit", "bye"}:
            if AGENT_THREAD["busy"]:
                print("\n⏹️  Stopping the current task first...")
                _stop_current_task()
            print("\n👋 See you bro.")
            break

        if low in {"stop", "cancel"}:
            if AGENT_THREAD["busy"]:
                print("\n⏹️  Stopping...")
                _stop_current_task()
                print("Stopped. What's next?")
            else:
                print("\n(nothing is running right now)")
            print("\nGDR > ", end="", flush=True)
            continue

        if low in {"help", "/help"}:
            print_help()
            print("\nGDR > ", end="", flush=True)
            continue

        if AGENT_THREAD["busy"]:
            print("\n↪️  Got it - stopping the current task and switching to your new request...")
            _stop_current_task()

        _run_agent_in_background(request)


def gui():
    """
    A minimal desktop chat window. Runs each request on a background thread
    so the window stays responsive, and the Stop button sets STOP_EVENT the
    same way the terminal 'stop' command does.
    """
    try:
        import tkinter as tk
        from tkinter import scrolledtext
    except ImportError:
        print("\n❌ Tkinter is not available. Install it with: sudo apt install python3-tk")
        return

    os.environ.update(gui_environment())

    root = tk.Tk()
    root.title(f"{AGENT_NAME}")
    root.geometry("760x560")
    root.configure(bg="#111111")

    output = scrolledtext.ScrolledText(
        root, wrap="word", bg="#111111", fg="#e6e6e6",
        insertbackground="#e6e6e6", font=("DejaVu Sans Mono", 11), state="disabled"
    )
    output.pack(fill="both", expand=True, padx=10, pady=(10, 6))

    bottom = tk.Frame(root, bg="#111111")
    bottom.pack(fill="x", padx=10, pady=(0, 10))

    entry = tk.Entry(bottom, bg="#1c1c1c", fg="#e6e6e6", insertbackground="#e6e6e6",
                      font=("DejaVu Sans Mono", 11))
    entry.pack(side="left", fill="x", expand=True, ipady=6)

    status_var = tk.StringVar(value="idle")

    def log(text):
        def _write():
            output.configure(state="normal")
            output.insert("end", text + "\n")
            output.see("end")
            output.configure(state="disabled")
        root.after(0, _write)

    def set_status(text):
        status_var.set(text)

    def run_request(request):
        set_status("thinking...")
        # Redirect this call's console prints into the chat window.
        import io
        import contextlib
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                run_agent(request)
        finally:
            text = buf.getvalue().strip()
            if text:
                log(text)
            set_status("idle")
            AGENT_THREAD["busy"] = False

    def on_send(event=None):
        request = entry.get().strip()
        if not request:
            return
        entry.delete(0, "end")
        log(f"\nYou: {request}")

        low = request.lower()
        if low in {"stop", "cancel"}:
            if AGENT_THREAD["busy"]:
                STOP_EVENT.set()
                log("(stopping current task...)")
            else:
                log("(nothing is running)")
            return

        if AGENT_THREAD["busy"]:
            log("(stopping current task and switching to your new request...)")
            STOP_EVENT.set()
            if AGENT_THREAD["thread"] is not None:
                AGENT_THREAD["thread"].join(timeout=15)

        STOP_EVENT.clear()
        AGENT_THREAD["busy"] = True
        t = threading.Thread(target=run_request, args=(request,), daemon=True)
        AGENT_THREAD["thread"] = t
        t.start()

    def on_stop():
        if AGENT_THREAD["busy"]:
            STOP_EVENT.set()
            log("(stop requested)")
        else:
            log("(nothing is running)")

    entry.bind("<Return>", on_send)

    button_row = tk.Frame(root, bg="#111111")
    button_row.pack(fill="x", padx=10, pady=(0, 10))

    send_btn = tk.Button(button_row, text="Send", command=on_send, bg="#2563eb", fg="white", relief="flat")
    send_btn.pack(side="right", padx=(6, 0))

    stop_btn = tk.Button(button_row, text="Stop", command=on_stop, bg="#dc2626", fg="white", relief="flat")
    stop_btn.pack(side="right")

    status_label = tk.Label(button_row, textvariable=status_var, bg="#111111", fg="#888888")
    status_label.pack(side="left")

    log(f"👋 {AGENT_NAME} GUI mode. Type a request and hit Enter or Send.")
    log("Type 'stop' or press Stop at any time to cancel the current task.")

    entry.focus_set()
    root.mainloop()


def main():

    if len(sys.argv) > 1:

        if sys.argv[1] == "--voice":
            gdr_extras.voice_mode(run_agent)
            return

        if sys.argv[1] == "--gui":
            gui()
            return

        if sys.argv[1] in {
            "--help",
            "-h"
        }:

            print_help()
            return

        if sys.argv[1] == "--system":

            print(
                json.dumps(
                    tool_system_info(),
                    indent=2
                )
            )

            return

        if sys.argv[1] == "--network":

            print(
                json.dumps(
                    tool_network_info(),
                    indent=2
                )
            )

            return

        if sys.argv[1] == "--health":

            print(
                json.dumps(
                    tool_system_health(),
                    indent=2
                )
            )

            return

        if sys.argv[1] == "--history":
            show_recent_history(30)
            return

        if sys.argv[1] == "--resume":
            checkpoint = load_checkpoint()
            if not checkpoint:
                print("\n✓ No interrupted task to resume.")
                return

            run_agent(
                checkpoint.get("user_request", ""),
                resume_messages=checkpoint.get("messages"),
                resume_step=int(checkpoint.get("step", 0)),
                resumed=True,
            )
            return

        request = " ".join(
            sys.argv[1:]
        )

        run_agent(
            request
        )

        return

    interactive()


def _cleanup_browser():
    try:
        tool_browser_close()
    except Exception:
        pass


import atexit
atexit.register(_cleanup_browser)


if __name__ == "__main__":
    main()
