"""Android & Termux Integration Tools for GDR-AI.
Enables native hardware access when running inside Termux on Android devices:
- Flashlight / Torch control
- Battery status & charging diagnostics
- Native Android TTS speech synthesis
- Haptic vibration feedback
- Heads-up push notifications
- Direct SMS transmission
- Telephony & phone calling
- Front / back camera photo capture
- High-precision GPS geolocation
- Clipboard synchronization
"""

import json
import os
import shutil
import subprocess
from typing import Dict, Any, Optional

from gdr.tools.registry import tool


def is_android_termux() -> bool:
    """Check if currently running inside an Android Termux environment."""
    return bool(
        "TERMUX_VERSION" in os.environ
        or os.path.exists("/data/data/com.termux")
        or shutil.which("termux-battery-status")
    )


def _run_termux_cmd(cmd: list, timeout: int = 15) -> tuple[int, str]:
    """Execute a termux-api CLI command and return exit code and text output."""
    binary = cmd[0]
    if not shutil.which(binary):
        return (
            1,
            f"Command '{binary}' not found. Please install Termux:API (`pkg install termux-api` and install the Termux:API app from F-Droid)."
        )
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = proc.stdout.strip() or proc.stderr.strip()
        return (proc.returncode, out)
    except subprocess.TimeoutExpired:
        return (1, f"Termux command timed out after {timeout}s.")
    except Exception as e:
        return (1, f"Failed to execute Termux command: {e}")


@tool(
    name="android_battery_status",
    description="Get Android device battery percentage, charging state, temperature, and health.",
    category="system",
    tier="AUTO"
)
def android_battery_status() -> str:
    """Retrieve Android battery information via termux-battery-status."""
    code, out = _run_termux_cmd(["termux-battery-status"])
    if code != 0:
        return f"Battery check failed: {out}"
    try:
        data = json.loads(out)
        pct = data.get("percentage", "Unknown")
        status = data.get("status", "Unknown")
        plugged = data.get("plugged", "UNPLUGGED")
        temp = data.get("temperature", 0)
        health = data.get("health", "GOOD")
        return (
            f"📱 Android Battery: {pct}% | Status: {status} ({plugged}) | "
            f"Temp: {temp}°C | Health: {health}"
        )
    except Exception:
        return f"Battery status: {out}"


@tool(
    name="android_toggle_torch",
    description="Turn the Android phone flashlight (torch) ON or OFF.",
    category="hardware",
    tier="AUTO"
)
def android_toggle_torch(enabled: bool = True) -> str:
    """Toggle phone flashlight on Android."""
    arg = "on" if enabled else "off"
    code, out = _run_termux_cmd(["termux-torch", arg])
    if code == 0:
        return f"Flashlight turned {'ON 🔦' if enabled else 'OFF 🌑'}."
    return f"Failed to toggle flashlight: {out}"


@tool(
    name="android_vibrate",
    description="Vibrate the Android phone for a specified duration in milliseconds.",
    category="hardware",
    tier="AUTO"
)
def android_vibrate(duration_ms: int = 500) -> str:
    """Trigger haptic vibration feedback on Android phone."""
    duration = max(50, min(5000, duration_ms))
    code, out = _run_termux_cmd(["termux-vibrate", "-d", str(duration)])
    if code == 0:
        return f"Phone vibrated for {duration}ms. 📳"
    return f"Vibration failed: {out}"


@tool(
    name="android_show_notification",
    description="Display a native Android heads-up notification with title and content.",
    category="notifications",
    tier="AUTO"
)
def android_show_notification(title: str, content: str) -> str:
    """Show heads-up notification on Android."""
    code, out = _run_termux_cmd([
        "termux-notification",
        "--title", title,
        "--content", content,
        "--id", "gdr_ai_notice",
        "--vibrate", "300,200,300"
    ])
    if code == 0:
        return f"Notification posted: '{title}'"
    return f"Failed to post notification: {out}"


@tool(
    name="android_send_sms",
    description="Send an SMS text message to a phone number from your Android phone.",
    category="communication",
    tier="APPROVAL"
)
def android_send_sms(phone_number: str, message: str) -> str:
    """Send SMS text message via Termux."""
    clean_num = "".join(c for c in phone_number if c.isdigit() or c == "+")
    if not clean_num:
        return "Invalid phone number."
    code, out = _run_termux_cmd(["termux-sms-send", "-n", clean_num, message])
    if code == 0:
        return f"SMS successfully sent to {clean_num}: '{message}'"
    return f"Failed to send SMS: {out}"


@tool(
    name="android_make_call",
    description="Dial a phone number directly on your Android phone.",
    category="communication",
    tier="APPROVAL"
)
def android_make_call(phone_number: str) -> str:
    """Initiate a phone call via Termux telephony."""
    clean_num = "".join(c for c in phone_number if c.isdigit() or c == "+")
    if not clean_num:
        return "Invalid phone number."
    code, out = _run_termux_cmd(["termux-telephony-call", clean_num])
    if code == 0:
        return f"Calling {clean_num}... 📞"
    return f"Failed to initiate phone call: {out}"


@tool(
    name="android_take_photo",
    description="Take a photo with the Android phone front or back camera.",
    category="vision",
    tier="AUTO"
)
def android_take_photo(camera: str = "back", output_path: str = "/tmp/android_photo.jpg") -> str:
    """Snap a photo using termux-camera-photo. camera can be 'back' (0) or 'front' (1)."""
    cam_id = "1" if camera.lower().startswith("front") else "0"
    target_path = output_path or "/tmp/android_photo.jpg"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    except Exception:
        target_path = "/tmp/android_photo.jpg"

    code, out = _run_termux_cmd(["termux-camera-photo", "-c", cam_id, target_path], timeout=20)
    if code == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        return f"Photo captured successfully from {camera} camera and saved to {target_path}."
    return f"Failed to take photo: {out}"


@tool(
    name="android_get_gps_location",
    description="Get precise GPS coordinates (latitude, longitude, altitude) from Android hardware.",
    category="system",
    tier="AUTO"
)
def android_get_gps_location() -> str:
    """Acquire real-time GPS coordinates via termux-location."""
    code, out = _run_termux_cmd(["termux-location", "-p", "gps", "-r", "last"], timeout=15)
    if code != 0:
        code, out = _run_termux_cmd(["termux-location", "-p", "network", "-r", "last"], timeout=10)
    if code != 0:
        return f"Location check failed: {out}. Ensure GPS location permission is granted to Termux:API."

    try:
        loc = json.loads(out)
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        acc = loc.get("accuracy", "Unknown")
        speed = loc.get("speed", 0)
        return (
            f"📍 Android GPS Location: Latitude {lat}, Longitude {lon} "
            f"(Accuracy: ±{acc}m, Speed: {speed} m/s)"
        )
    except Exception:
        return f"Location: {out}"


@tool(
    name="android_tts_speak",
    description="Speak text aloud using Android's native high-quality speech engine (Google/Samsung TTS).",
    category="voice",
    tier="AUTO"
)
def android_tts_speak(text: str) -> str:
    """Synthesize speech using termux-tts-speak."""
    if not text:
        return "No text to speak."
    code, out = _run_termux_cmd(["termux-tts-speak", text])
    if code == 0:
        return f"Spoken via Android TTS: '{text}'"
    return f"Android TTS failed: {out}"


@tool(
    name="android_clipboard",
    description="Get or set text in Android system clipboard.",
    category="system",
    tier="AUTO"
)
def android_clipboard(action: str = "get", text: str = "") -> str:
    """Read or write Android clipboard."""
    if action.lower() == "set":
        code, out = _run_termux_cmd(["termux-clipboard-set", text])
        if code == 0:
            return f"Copied to clipboard: '{text}'"
        return f"Failed to set clipboard: {out}"
    else:
        code, out = _run_termux_cmd(["termux-clipboard-get"])
        if code == 0:
            return f"Clipboard contents: '{out}'"
        return f"Failed to read clipboard: {out}"

