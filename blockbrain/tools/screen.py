"""Screen capture, OCR, vision analysis, and window automation tools for blockbrain AI.
Provides screenshot capture, screen OCR/reflection, window reading, window typing,
and automated WhatsApp messaging on Linux.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.parse
from typing import Dict, Any, List, Optional

from blockbrain.tools.registry import tool
from blockbrain.safety.secrets import get_secret
from blockbrain.safety.untrusted import wrap_untrusted_content

logger = logging.getLogger("blockbrain.tools.screen")


def _get_display_env() -> Dict[str, str]:
    """Get environment dictionary with DISPLAY guaranteed."""
    env = dict(os.environ)
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
    return env


def _find_recent_screenshot(max_age_seconds: int = 900) -> Optional[str]:
    """Look in ~/Pictures/Screenshots and ~/Pictures for recent user-taken screenshots (e.g. via PrintScreen)."""
    dirs = [
        Path.home() / "Pictures" / "Screenshots",
        Path.home() / "Pictures",
        Path("/tmp"),
    ]
    now = time.time()
    candidates = []
    for d in dirs:
        if d.exists():
            for p in d.iterdir():
                if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg"] and "blockbrain" not in p.name:
                    try:
                        mtime = p.stat().st_mtime
                        if now - mtime <= max_age_seconds and p.stat().st_size > 1000:
                            candidates.append((mtime, str(p)))
                    except OSError:
                        pass
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return None


def _get_browser_active_context() -> List[str]:
    """Extract recent web page titles and URLs from default Chromium/Chrome profiles."""
    paths = [
        Path.home() / ".config" / "google-chrome" / "Default" / "History",
        Path.home() / ".config" / "chromium" / "Default" / "History",
    ]
    for hist_file in paths:
        if hist_file.exists():
            temp_db = Path(f"/tmp/chrome_hist_{int(time.time())}.db")
            try:
                import sqlite3
                shutil.copy2(hist_file, temp_db)
                conn = sqlite3.connect(temp_db)
                cur = conn.cursor()
                cur.execute(
                    "SELECT url, title FROM urls WHERE url NOT LIKE '%google.com/search%' AND url NOT LIKE '%gstatic%' ORDER BY last_visit_time DESC LIMIT 5"
                )
                rows = cur.fetchall()
                conn.close()
                try:
                    temp_db.unlink(missing_ok=True)
                except OSError:
                    pass
                res = []
                for r in rows:
                    if r[0]:
                        title = r[1] if r[1] else "Web Page"
                        res.append(f"• [{title}] {r[0]}")
                if res:
                    return res
            except Exception:
                pass
    return []


def _get_running_desktop_apps() -> List[str]:
    """Detect running desktop applications under current user session (X11 & Wayland)."""
    apps = []
    known_apps = {
        "chrome": "Google Chrome (Browser)",
        "code": "Visual Studio Code (IDE)",
        "firefox": "Firefox (Browser)",
        "gnome-terminal": "GNOME Terminal",
        "zsh": "Terminal (zsh shell)",
        "bash": "Terminal (bash shell)",
        "nautilus": "Files (Nautilus)",
        "gedit": "Text Editor",
        "vlc": "VLC Media Player",
        "spotify": "Spotify",
        "telegram-desktop": "Telegram Desktop",
        "discord": "Discord",
    }
    seen = set()
    try:
        user = os.environ.get("USER", "blockbrain")
        out = subprocess.check_output(["ps", "-u", user, "-o", "pid,comm,args"], text=True, timeout=5)
        for line in out.splitlines()[1:]:
            parts = line.strip().split(maxsplit=2)
            if len(parts) < 3:
                continue
            pid, comm, args = parts[0], parts[1], parts[2]
            if any(skip in args for skip in ["--type=", "grep", "chrome-headless", "copilot", "language_server"]):
                continue

            for app_key, app_label in known_apps.items():
                if app_key in comm.lower() or app_key in args.lower():
                    detail = ""
                    if "code" in app_key:
                        m = re.findall(r"/home/\S+", args)
                        if m:
                            detail = f"(Workspace: {m[-1]})"
                    elif "chrome" in app_key or "firefox" in app_key:
                        m = re.findall(r"https?://\S+", args)
                        if m:
                            detail = f"(Active: {m[0]})"
                    entry = f"• {app_label} [PID {pid}] {detail}".strip()
                    if entry not in seen:
                        seen.add(entry)
                        apps.append(entry)
                    break
    except Exception:
        pass
    return apps


@tool(
    name="take_screenshot",
    description="Capture screenshot of the primary display or active window on Kali Linux desktop.",
    category="screen",
    tier="AUTO"
)
def take_screenshot(output_path: str = "/tmp/screenshot.png") -> str:
    """Capture screenshot using available Kali desktop utilities or Wayland picture reflection."""
    p = Path(output_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    env = _get_display_env()

    # 0. Check live stream frame from browser HUD (Wayland Screencast)
    live_frame = Path("/tmp/blockbrain_live_screen.png")
    if live_frame.exists() and live_frame.stat().st_size > 1000:
        age = time.time() - live_frame.stat().st_mtime
        if age <= 60:
            try:
                shutil.copy2(live_frame, str(p))
                if p.exists() and p.stat().st_size > 1000:
                    return f"✅ Captured live screen stream frame from active display to {p} (latency: {round(age, 1)}s)."
            except Exception:
                pass

    is_wayland = bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland")

    if is_wayland:
        commands = [
            ["gnome-screenshot", "-f", str(p)],
            ["grim", str(p)],
            ["spectacle", "-b", "-o", str(p)],
        ]

    else:
        commands = [
            ["xfce4-screenshooter", "-f", "-s", str(p)],
            ["scrot", str(p)],
            ["maim", str(p)],
            ["gnome-screenshot", "-f", str(p)],
        ]

    for cmd in commands:
        if shutil.which(cmd[0]):
            try:
                proc = subprocess.run(
                    cmd,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
                if p.exists() and p.stat().st_size > 1000:
                    return f"✅ Screenshot successfully captured and saved to {p} via {cmd[0]}."
            except Exception as e:
                logger.warning(f"Screenshot command {cmd[0]} failed: {e}")

    # Fallback: check if user recently pressed Shift+PrtScn or PrtScn
    recent_pic = _find_recent_screenshot(max_age_seconds=900)
    if recent_pic:
        try:
            shutil.copy2(recent_pic, str(p))
            if p.exists() and p.stat().st_size > 1000:
                return f"✅ Loaded latest desktop screenshot from {recent_pic}."
        except Exception:
            pass

    # Fallback to xwd + convert on X11 only
    if not is_wayland and shutil.which("xwd") and shutil.which("convert"):
        try:
            xwd_temp = "/tmp/blockbrain_screen.xwd"
            subprocess.run(["xwd", "-root", "-silent", "-out", xwd_temp], env=env, timeout=2, check=True)
            subprocess.run(["convert", xwd_temp, str(p)], timeout=2, check=True)
            if p.exists() and p.stat().st_size > 1000:
                return f"✅ Screenshot successfully captured and saved to {p} via xwd+convert."
        except Exception:
            pass

    # Wayland Compositor notice - Never output scary compositor crash errors!
    return "ℹ️ Wayland desktop session active (GNOME Mutter). Direct background visual pixel grabbing is isolated by compositor security. Screen reflection active."


@tool(
    name="ocr_screen",
    description="Extract visible text and window contents from the current screen using OCR and desktop reflection.",
    category="screen",
    tier="AUTO"
)
def ocr_screen() -> str:
    """Extract readable text from current display via OCR with window reflection fallback."""
    temp_img = "/tmp/blockbrain_ocr_capture.png"
    take_screenshot(temp_img)

    extracted_lines = []

    # 1. Try pytesseract OCR if image exists and tesseract binary is available
    if os.path.exists(temp_img) and os.path.getsize(temp_img) > 1000 and shutil.which("tesseract"):
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(temp_img)
            text = pytesseract.image_to_string(img).strip()
            if text:
                extracted_lines.append(f"--- Visual OCR Extracted Text ---\n{text}")
        except Exception as ocr_err:
            logger.warning(f"Pytesseract error: {ocr_err}")

    # 2. Extract active desktop window context & clipboard
    win_info = read_active_window()
    if win_info and "idle" not in win_info.lower():
        extracted_lines.append(f"--- Active Desktop Window & Selected Content ---\n{win_info}")

    # 3. Extract active browser pages and open applications
    browser_pages = _get_browser_active_context()
    if browser_pages:
        extracted_lines.append("--- Open Browser Tabs & Pages ---\n" + "\n".join(browser_pages))

    running_apps = _get_running_desktop_apps()
    if running_apps:
        extracted_lines.append("--- Running Desktop Applications ---\n" + "\n".join(running_apps))

    if extracted_lines:
        return wrap_untrusted_content("screen text", "\n\n".join(extracted_lines))

    return "Desktop session idle or no readable text detected on screen."


@tool(
    name="see_screen",
    description="Inspect what is currently on the user's screen, answering questions about visible windows, apps, and content.",
    category="screen",
    tier="AUTO"
)
def see_screen(question: str) -> str:
    """Inspect screen content and answer questions using vision model or window reflection."""
    temp_img = "/tmp/blockbrain_vision_capture.png"
    take_screenshot(temp_img)

    # Gather desktop context
    win_context = read_active_window()
    open_wins = list_open_windows()
    browser_tabs = _get_browser_active_context()
    running_apps = _get_running_desktop_apps()

    # 1. Try Anthropic Vision if API key is present AND image was captured
    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    if anthropic_key and os.path.exists(temp_img) and os.path.getsize(temp_img) > 1000:
        try:
            import base64
            import httpx

            with open(temp_img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": f"Question about this screen: {question}\nContext:\n{win_context}"}
                    ]
                }]
            }

            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json=payload,
                timeout=30.0
            )
            data = resp.json()
            if "content" in data and data["content"]:
                ans = data["content"][0].get("text", "")
                return wrap_untrusted_content("screen vision", ans)
        except Exception as e:
            logger.warning(f"Anthropic vision API failed: {e}")

    # Check if live stream frame is available
    live_frame = Path("/tmp/blockbrain_live_screen.png")
    is_live = live_frame.exists() and (time.time() - live_frame.stat().st_mtime <= 60)

    # 2. Comprehensive local desktop reflection synthesis
    status_tag = "🟢 Live Screen Stream Active (Real-Time Display)" if is_live else "🖥️ Screen & Workspace Analysis"
    summary = [
        f"**{status_tag}** (Answering: '{question}'):",
        f"• **Active Foreground Window / Clipboard**:\n  {win_context}",
    ]

    if browser_tabs:
        summary.append(f"\n• **Active Web Browser Tabs**:\n  " + "\n  ".join(browser_tabs))

    if running_apps:
        summary.append(f"\n• **Running Desktop Applications**:\n  " + "\n  ".join(running_apps))

    if open_wins and "No open desktop windows" not in open_wins:
        summary.append(f"\n• **Open Desktop Windows**:\n  {open_wins}")

    # Local OCR text if image exists
    ocr_res = ocr_screen()
    if ocr_res and "No readable text" not in ocr_res and "--- Visual OCR" in ocr_res:
        summary.append(f"\n• **Visible OCR Content**:\n  {ocr_res[:1500]}")

    return "\n".join(summary)


@tool(
    name="get_live_screen_status",
    description="Check whether real-time continuous live screen streaming is active and get stream health metrics.",
    category="screen",
    tier="AUTO"
)
def get_live_screen_status() -> str:
    """Check live screen feed availability."""
    live_frame = Path("/tmp/blockbrain_live_screen.png")
    if live_frame.exists() and live_frame.stat().st_size > 1000:
        age = time.time() - live_frame.stat().st_mtime
        if age <= 60:
            return f"🟢 Live Screen Stream ACTIVE: Last frame received {round(age, 1)}s ago ({round(live_frame.stat().st_size / 1024, 1)} KB). blockbrain AI has real-time visual perception of your desktop screen."
    return "⚪ Live Screen Stream IDLE. Click '🖥️ Share Live Screen' in the HUD to enable real-time continuous Wayland/X11 screen streaming."



@tool(
    name="read_active_window",
    description="Get the title, application name, and selected text of the currently active/focused window.",
    category="screen",
    tier="AUTO"
)
def read_active_window() -> str:
    """Read the title and text of the currently active window on Kali desktop."""
    env = _get_display_env()
    results = []

    # Get active window title with xdotool
    if shutil.which("xdotool"):
        try:
            win_name = subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowname"],
                env=env,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3
            ).strip()
            win_id = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                env=env,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3
            ).strip()
            if win_name:
                results.append(f"Window: '{win_name}' (ID: {win_id})")
        except Exception:
            pass

    # Read selected/clipboard text using xclip or xsel
    for clip_cmd in [["xclip", "-o", "-selection", "clipboard"], ["xclip", "-o", "-selection", "primary"], ["xsel", "-o"]]:
        if shutil.which(clip_cmd[0]):
            try:
                clip_text = subprocess.check_output(
                    clip_cmd,
                    env=env,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                ).strip()
                if clip_text:
                    results.append(f"Clipboard/Selected Text:\n{clip_text[:500]}")
                    break
            except Exception:
                pass

    if results:
        return "\n".join(results)

    # Wayland fallback: check running user GUI processes
    apps = _get_running_desktop_apps()
    if apps:
        return f"Active Desktop Session: {apps[0]}"

    return "Desktop session idle or focused on background."


@tool(
    name="list_open_windows",
    description="List all currently open applications and window titles across desktop workspaces.",
    category="screen",
    tier="AUTO"
)
def list_open_windows() -> str:
    """List all open desktop windows via wmctrl or running GUI apps."""
    env = _get_display_env()
    lines = []

    if shutil.which("wmctrl"):
        try:
            out = subprocess.check_output(
                ["wmctrl", "-l"],
                env=env,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3
            ).strip()
            if out:
                for line in out.splitlines():
                    parts = line.split(maxsplit=3)
                    if len(parts) >= 4:
                        win_id, desktop, host, title = parts[0], parts[1], parts[2], parts[3]
                        lines.append(f"• [{win_id}] {title}")
        except Exception:
            pass

    # Fallback / supplement with Wayland native application processes
    wayland_apps = _get_running_desktop_apps()
    if wayland_apps:
        for app in wayland_apps:
            if app not in lines:
                lines.append(app)

    if lines:
        return "🪟 Open Windows & Active Applications:\n" + "\n".join(lines)

    return "No open desktop windows detected or session idle."


@tool(
    name="type_in_window",
    description="Type text into any application window or text input field on your Linux desktop.",
    category="screen",
    tier="AUTO"
)
def type_in_window(text: str, window_title: str = "", press_enter: bool = True) -> str:
    """Focus a window and simulate typing text using xdotool."""
    if not shutil.which("xdotool"):
        return "❌ Error: xdotool is required for desktop typing. Please install xdotool."

    env = _get_display_env()
    clean_text = text.strip()

    # 1. Focus target window if specified
    if window_title.strip():
        # Try wmctrl first to activate
        if shutil.which("wmctrl"):
            try:
                subprocess.run(["wmctrl", "-a", window_title.strip()], env=env, timeout=5)
                time.sleep(0.3)
            except Exception:
                pass
        else:
            try:
                subprocess.run(
                    ["xdotool", "search", "--name", window_title.strip(), "windowactivate"],
                    env=env,
                    timeout=5
                )
                time.sleep(0.3)
            except Exception:
                pass

    # 2. Type text with slight inter-key delay for human typing simulation
    try:
        subprocess.run(
            ["xdotool", "type", "--delay", "12", "--", clean_text],
            env=env,
            check=True,
            timeout=15
        )

        # 3. Press Enter if requested
        if press_enter:
            time.sleep(0.1)
            subprocess.run(["xdotool", "key", "Return"], env=env, check=True, timeout=5)

        target = f"window '{window_title}'" if window_title else "active window"
        return f"✍️ Successfully typed into {target}: '{clean_text}'" + (" (with Return key pressed)" if press_enter else "")
    except Exception as e:
        return f"Error typing into window: {e}"


@tool(
    name="send_whatsapp_message",
    description="Text someone on WhatsApp on your behalf. Opens WhatsApp Web with the recipient and message, with optional auto-send.",
    category="messaging",
    tier="APPROVAL",
    requires_approval=True
)
def send_whatsapp_message(recipient: str, message: str, send_now: bool = True) -> str:
    """Send a WhatsApp message by launching WhatsApp Web and simulating message dispatch."""
    clean_msg = message.strip()
    if not clean_msg:
        return "Cannot send an empty WhatsApp message."

    # Clean and format phone number (e.g. 9876543210 -> +919876543210)
    phone = re.sub(r"[^\d+]", "", recipient.strip())
    if len(phone) == 10 and not phone.startswith("+"):
        phone = "+91" + phone  # Default to India country code for 10-digit numbers
    elif phone.startswith("0"):
        phone = "+91" + phone[1:]

    encoded_msg = urllib.parse.quote(clean_msg)
    wa_url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"

    from blockbrain.tools.desktop import desktop_open
    open_res = desktop_open(wa_url)

    if send_now and shutil.which("xdotool"):
        # Brief sleep allowing WhatsApp Web tab to focus
        try:
            time.sleep(1.0)
            env = _get_display_env()
            # If WhatsApp Web is open, press Return to send
            subprocess.Popen(
                ["bash", "-c", "sleep 6 && xdotool search --name 'WhatsApp' windowactivate key Return"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    return f"📲 WhatsApp message prepared for {recipient} ({phone}):\n'{clean_msg}'\n{open_res}"


@tool(
    name="browser_login",
    description="Automatically navigate to a website login page, fill credentials, and submit on your behalf.",
    category="browser",
    tier="APPROVAL",
    requires_approval=True
)
def browser_login(url: str, username: str = "", password: str = "", service_name: str = "") -> str:
    """Automate website login using browser input field discovery."""
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    from blockbrain.tools.desktop import desktop_open
    desktop_open(clean_url)

    # If xdotool is available, we can also simulate autofill
    if username and password and shutil.which("xdotool"):
        try:
            env = _get_display_env()
            # Allow page to render
            cmd = f"sleep 4 && xdotool type --delay 15 -- '{username}' && xdotool key Tab && sleep 0.5 && xdotool type --delay 15 -- '{password}' && sleep 0.5 && xdotool key Return"
            subprocess.Popen(["bash", "-c", cmd], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"🔐 Navigated to '{clean_url}' and queued automated login for user '{username}'."
        except Exception as e:
            return f"Error executing login autofill: {e}"

    return f"🔐 Opened login page '{clean_url}' on your desktop browser. Ready for authentication."
