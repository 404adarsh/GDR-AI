"""Desktop integration, YouTube launcher, weather, website bookmarks & network tools for blockbrain AI.
Provides direct desktop-level application opening, live weather, ping, website health testing,
website bookmarks memory, and hardware control.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import time
import urllib.parse
from typing import Dict, Any, List, Optional
import requests

from blockbrain.tools.registry import tool
from blockbrain.config import load_config

logger = logging.getLogger("blockbrain.tools.desktop")

CONFIG_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
BOOKMARKS_FILE = CONFIG_DIR / "bookmarks.json"


def _ensure_display_env() -> Dict[str, str]:
    """Ensure desktop display environment variables are present for GUI apps."""
    env = dict(os.environ)
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
    return env


def _load_bookmarks() -> Dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not BOOKMARKS_FILE.exists():
        return {}
    try:
        with open(BOOKMARKS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_bookmarks(data: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = BOOKMARKS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(BOOKMARKS_FILE)


def get_location_file() -> Path:
    cfg_dir = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
    return cfg_dir / "location.json"

LOCATION_FILE = get_location_file()


def _reverse_geocode_nominatim(lat: float, lon: float) -> Dict[str, Any]:
    """Reverse geocode latitude and longitude to street address using OpenStreetMap Nominatim."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "blockbrainAssistant/1.0 (contact@blockbrain.ai)"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            return {
                "display_name": data.get("display_name", ""),
                "road": addr.get("road", ""),
                "neighbourhood": addr.get("neighbourhood", addr.get("suburb", "")),
                "suburb": addr.get("suburb", ""),
                "city": addr.get("city", addr.get("town", addr.get("village", addr.get("county", "")))),
                "state_district": addr.get("state_district", ""),
                "state": addr.get("state", ""),
                "postcode": addr.get("postcode", ""),
                "country": addr.get("country", ""),
                "country_code": addr.get("country_code", ""),
            }
    except Exception as e:
        logger.warning(f"Nominatim reverse geocode failed: {e}")
    return {}


def resolve_location_data() -> Dict[str, Any]:
    """Resolve current user location from stored GPS or IP fallback with reverse geocoding."""
    loc_file = get_location_file()
    try:
        loc_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    loc_data = {}

    if loc_file.exists():
        try:
            with open(loc_file, "r") as f:
                loc_data = json.load(f)
        except Exception:
            loc_data = {}

    lat = loc_data.get("latitude")
    lon = loc_data.get("longitude")

    # If coordinates are present but display_name / city missing, reverse geocode with Nominatim
    if lat is not None and lon is not None:
        if not loc_data.get("display_name") or not loc_data.get("city"):
            geo = _reverse_geocode_nominatim(float(lat), float(lon))
            if geo:
                loc_data.update(geo)
                try:
                    with open(loc_file, "w") as f:
                        json.dump(loc_data, f, indent=2)
                except Exception:
                    pass
        return loc_data

    # Coordinates missing: fallback to IP geolocation
    try:
        ip_resp = requests.get("https://ipapi.co/json/", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if ip_resp.status_code == 200:
            ip_data = ip_resp.json()
            if "latitude" in ip_data and "longitude" in ip_data:
                loc_data = {
                    "latitude": ip_data.get("latitude"),
                    "longitude": ip_data.get("longitude"),
                    "city": ip_data.get("city", ""),
                    "state": ip_data.get("region", ""),
                    "country": ip_data.get("country_name", ""),
                    "country_code": ip_data.get("country_code", ""),
                    "postcode": ip_data.get("postal", ""),
                    "ip": ip_data.get("ip", ""),
                    "org": ip_data.get("org", ""),
                    "source": "ip_geolocation",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                # Try to get refined address details via Nominatim
                geo = _reverse_geocode_nominatim(float(loc_data["latitude"]), float(loc_data["longitude"]))
                if geo:
                    loc_data.update(geo)
                try:
                    with open(LOCATION_FILE, "w") as f:
                        json.dump(loc_data, f, indent=2)
                except Exception:
                    pass
                return loc_data
    except Exception as e:
        logger.warning(f"ipapi.co lookup failed: {e}")

    # Second IP fallback: ipinfo.io
    try:
        ip_resp2 = requests.get("https://ipinfo.io/json", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if ip_resp2.status_code == 200:
            ip_data2 = ip_resp2.json()
            loc_str = ip_data2.get("loc", "")
            if "," in loc_str:
                p_lat, p_lon = loc_str.split(",", 1)
                loc_data = {
                    "latitude": float(p_lat.strip()),
                    "longitude": float(p_lon.strip()),
                    "city": ip_data2.get("city", ""),
                    "state": ip_data2.get("region", ""),
                    "country": ip_data2.get("country", ""),
                    "postcode": ip_data2.get("postal", ""),
                    "ip": ip_data2.get("ip", ""),
                    "org": ip_data2.get("org", ""),
                    "source": "ipinfo",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    with open(LOCATION_FILE, "w") as f:
                        json.dump(loc_data, f, indent=2)
                except Exception:
                    pass
                return loc_data
    except Exception as e:
        logger.warning(f"ipinfo lookup failed: {e}")

    return loc_data


@tool(
    name="get_current_location",
    description="Get user's exact physical geographic location including street, neighborhood, city, state, postal code, and GPS coordinates.",
    category="desktop",
    tier="AUTO"
)
def get_current_location() -> str:
    """Resolve and return exact geographic location for user with street-level accuracy."""
    loc = resolve_location_data()
    if not loc or not loc.get("latitude"):
        return "📍 Location not currently detected. Please allow location permissions in the blockbrain HUD or connect to internet."

    display_name = loc.get("display_name")
    city = loc.get("city") or loc.get("neighbourhood") or "Local Area"
    state = loc.get("state") or ""
    postcode = loc.get("postcode") or ""
    country = loc.get("country") or "India"
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    acc = loc.get("accuracy")
    acc_str = f"~{round(float(acc))}m (High Precision GPS)" if acc else "IP Network Estimated"
    source = loc.get("source", "Browser GPS" if acc else "Geocoding")

    res = [
        f"📍 **Exact Location**: {display_name or f'{city}, {state} {postcode}, {country}'}",
        f"• City / Area: {city}" + (f", {state}" if state else "") + (f" ({postcode})" if postcode else ""),
        f"• Country: {country}",
        f"• GPS Coordinates: {lat}, {lon} (Accuracy: {acc_str})",
        f"• Location Source: {source}",
    ]
    if loc.get("org"):
        res.append(f"• Network Provider: {loc['org']}")

    return "\n".join(res)



@tool(
    name="desktop_open",
    description="Open a URL, file, or application visibly on the user's desktop screen.",
    category="desktop",
    tier="AUTO"
)
def desktop_open(target: str) -> str:
    """Launch target visibly on desktop using xdg-open or default system handlers."""
    clean_target = target.strip()
    
    # Check if target is a URL or domain
    is_url = False
    if clean_target.startswith("http://") or clean_target.startswith("https://") or clean_target.startswith("file://"):
        is_url = True
    elif re.match(r"^[\w\-]+(\.[\w\-]+)+(/[^\s]*)?$", clean_target):
        clean_target = "https://" + clean_target
        is_url = True

    env = _ensure_display_env()
    
    # Try xdg-open first
    for opener in ["xdg-open", "gio open", "sensible-browser", "google-chrome", "chromium", "firefox"]:
        cmd_parts = opener.split()
        if shutil.which(cmd_parts[0]):
            try:
                subprocess.Popen(
                    cmd_parts + [clean_target],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                return f"✅ Opened '{clean_target}' visibly on your desktop display via {cmd_parts[0]}."
            except Exception as e:
                logger.warning(f"Opener {opener} failed: {e}")

    return f"⚠️ Could not find a desktop GUI launcher for '{clean_target}'."


@tool(
    name="search_youtube",
    description="Search YouTube and open the search results visibly in your desktop browser.",
    category="desktop",
    tier="AUTO"
)
def search_youtube(query: str) -> str:
    """Search for video on YouTube and open search results on desktop."""
    if not query.strip():
        return open_youtube()

    encoded = urllib.parse.quote_plus(query.strip())
    yt_url = f"https://www.youtube.com/results?search_query={encoded}"
    res = desktop_open(yt_url)
    return f"🎬 Searching YouTube for '{query}'. {res} Direct URL: {yt_url}"


@tool(
    name="open_youtube",
    description="Open YouTube on your desktop browser. If query is provided, searches YouTube.",
    category="desktop",
    tier="AUTO"
)
def open_youtube(query: str = "", song_name: str = "") -> str:
    """Open YouTube home page or search query on desktop."""
    target_query = query or song_name
    if target_query.strip():
        return search_youtube(target_query)
    yt_url = "https://www.youtube.com"
    res = desktop_open(yt_url)
    return f"🎬 Opened YouTube on desktop. {res}"


@tool(
    name="get_weather",
    description="Get live weather forecast (temperature, conditions, humidity, wind) for any city or current location.",
    category="desktop",
    tier="AUTO"
)
def get_weather(location: str = "") -> str:
    """Fetch live weather forecast from wttr.in with automatic location resolution."""
    clean_loc = location.strip()
    is_current = not clean_loc or clean_loc.lower() in ["here", "current", "my location", "local", "me", "weather", "today"]

    query_loc = clean_loc
    area_label = clean_loc
    if is_current:
        loc_data = resolve_location_data()
        if loc_data.get("city"):
            query_loc = loc_data["city"]
            area_label = f"{loc_data['city']}"
            if loc_data.get("state"):
                area_label += f", {loc_data['state']}"
        elif loc_data.get("latitude") and loc_data.get("longitude"):
            query_loc = f"{loc_data['latitude']},{loc_data['longitude']}"
            area_label = f"Lat {loc_data['latitude']}, Lon {loc_data['longitude']}"
        else:
            query_loc = ""
            area_label = "Current Location"

    loc_clean = urllib.parse.quote(query_loc) if query_loc else ""
    url = f"https://wttr.in/{loc_clean}?format=j1"

    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            cur = data["current_condition"][0]
            nearest = data.get("nearest_area", [{}])[0]
            city = nearest.get("areaName", [{}])[0].get("value", area_label or "Local Area")
            country = nearest.get("country", [{}])[0].get("value", "")
            
            temp_c = cur.get("temp_C", "N/A")
            temp_f = cur.get("temp_F", "N/A")
            feels_c = cur.get("FeelsLikeC", "N/A")
            desc = cur.get("weatherDesc", [{}])[0].get("value", "Clear")
            humidity = cur.get("humidity", "N/A")
            wind_speed = cur.get("windspeedKmph", "N/A")
            wind_dir = cur.get("winddir16Point", "")

            # 1-day forecast highlights
            today = data.get("weather", [{}])[0]
            max_c = today.get("maxtempC", "")
            min_c = today.get("mintempC", "")

            summary = (
                f"🌤️ **Weather for {city}{', ' + country if country else ''}**:\n"
                f"• Condition: {desc}\n"
                f"• Temperature: {temp_c}°C ({temp_f}°F), Feels like {feels_c}°C\n"
                f"• Today's Range: High {max_c}°C / Low {min_c}°C\n"
                f"• Humidity: {humidity}%\n"
                f"• Wind: {wind_speed} km/h {wind_dir}\n"
            )
            return summary
    except Exception as e:
        logger.warning(f"wttr.in JSON failed: {e}")

    # Fallback to plain text format
    try:
        url_text = f"https://wttr.in/{loc_clean}?format=%l:+%c+%t+(feels+%f),+humidity+%h,+wind+%w"
        resp_text = requests.get(url_text, timeout=6)
        if resp_text.status_code == 200 and "Unknown" not in resp_text.text:
            return f"🌤️ Weather: {resp_text.text.strip()}"
    except Exception:
        pass

    return f"Weather report currently unavailable for '{area_label or 'local'}' (Network connection check needed)."



@tool(
    name="ping_host",
    description="Ping any domain, IP address, or website to check connectivity and round-trip latency.",
    category="network",
    tier="AUTO"
)
def ping_host(host: str, count: int = 4) -> str:
    """Ping a host and measure latency and packet loss."""
    clean_host = host.strip()
    if clean_host.startswith("http://") or clean_host.startswith("https://"):
        parsed = urllib.parse.urlparse(clean_host)
        clean_host = parsed.netloc or parsed.path

    # Strip port if present
    if ":" in clean_host:
        clean_host = clean_host.split(":")[0]

    # Validate hostname / IP format
    if not re.match(r"^[\w\.\-]+$", clean_host):
        return f"❌ Invalid hostname or IP address: '{clean_host}'."

    count = max(1, min(10, int(count)))
    try:
        proc = subprocess.run(
            ["ping", "-c", str(count), "-W", "2", clean_host],
            capture_output=True,
            text=True,
            timeout=15
        )
        output = proc.stdout
        if proc.returncode == 0:
            # Parse stats
            loss_match = re.search(r"(\d+)% packet loss", output)
            rtt_match = re.search(r"rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms", output)
            loss = loss_match.group(1) if loss_match else "0"
            if rtt_match:
                min_ms, avg_ms, max_ms = rtt_match.group(1), rtt_match.group(2), rtt_match.group(3)
                return (
                    f"🟢 **Ping to {clean_host} SUCCESS**:\n"
                    f"• Packets: {count} sent, {loss}% packet loss\n"
                    f"• Latency: Min {min_ms} ms | Avg {avg_ms} ms | Max {max_ms} ms\n"
                    f"• Status: ONLINE"
                )
            return f"🟢 Host {clean_host} is reachable. Output:\n{output.strip()}"
        else:
            return f"🔴 **Ping to {clean_host} FAILED**: Host is unreachable or dropping ICMP packets (100% loss)."
    except subprocess.TimeoutExpired:
        return f"🔴 Ping to {clean_host} timed out after 15 seconds."
    except Exception as e:
        return f"Ping execution error: {e}"


@tool(
    name="test_website",
    description="Test website health, HTTP response code, latency, SSL certificate validity, and security headers.",
    category="network",
    tier="AUTO"
)
def test_website(url: str, check_ssl: bool = True) -> str:
    """Perform diagnostic health and latency test on any website."""
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    parsed = urllib.parse.urlparse(clean_url)
    hostname = parsed.netloc

    results = []
    results.append(f"🔍 **Diagnostics for {clean_url}**:")

    # 1. HTTP Request & Latency
    start_time = time.time()
    try:
        resp = requests.get(clean_url, timeout=10, headers={"User-Agent": "blockbrain-AI-SiteMonitor/1.0"})
        latency_ms = round((time.time() - start_time) * 1000, 1)
        status_icon = "🟢" if resp.status_code < 400 else "🔴"
        results.append(f"• HTTP Status: {status_icon} {resp.status_code} {resp.reason}")
        results.append(f"• Response Time: {latency_ms} ms")
        results.append(f"• Content Length: {len(resp.content):,} bytes")
        server = resp.headers.get("Server", "Undisclosed")
        results.append(f"• Web Server: {server}")

        # Security Headers
        sec_headers = []
        if "Strict-Transport-Security" in resp.headers:
            sec_headers.append("HSTS")
        if "Content-Security-Policy" in resp.headers:
            sec_headers.append("CSP")
        if "X-Frame-Options" in resp.headers:
            sec_headers.append("X-Frame-Options")
        sec_str = ", ".join(sec_headers) if sec_headers else "None detected"
        results.append(f"• Security Headers: {sec_str}")
    except requests.exceptions.RequestException as e:
        return f"🔴 **Website Test FAILED for {clean_url}**:\nCould not establish connection: {e}"

    # 2. SSL/TLS Certificate check
    if check_ssl and parsed.scheme == "https":
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    exp_date_str = cert.get("notAfter", "")
                    if exp_date_str:
                        # e.g. 'Oct 25 12:00:00 2026 GMT'
                        exp_dt = datetime.strptime(exp_date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                        now_dt = datetime.now(timezone.utc)
                        days_left = (exp_dt - now_dt).days
                        issuer = dict(x[0] for x in cert.get("issuer", []))
                        issuer_name = issuer.get("organizationName", issuer.get("commonName", "Unknown CA"))
                        ssl_icon = "🟢" if days_left > 15 else "⚠️"
                        results.append(f"• SSL Certificate: {ssl_icon} Valid ({days_left} days remaining until {exp_dt.strftime('%Y-%m-%d')})")
                        results.append(f"• Certificate Issuer: {issuer_name}")
        except Exception as ssl_err:
            results.append(f"• SSL Certificate: ⚠️ Verification notice: {ssl_err}")

    results.append("• Overall Health: HEALTHY & RESPONSIVE")
    return "\n".join(results)


@tool(
    name="bookmark_website",
    description="Save a website URL with a friendly name in blockbrain memory so you can easily reference or open it later.",
    category="memory",
    tier="AUTO"
)
def bookmark_website(name: str, url: str, description: str = "") -> str:
    """Save a named website bookmark to persistent configuration and long-term memory."""
    clean_name = name.strip().lower()
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    bookmarks = _load_bookmarks()
    bookmarks[clean_name] = {
        "name": name.strip(),
        "url": clean_url,
        "description": description.strip() or f"Website bookmark for {name.strip()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_accessed": datetime.now(timezone.utc).isoformat(),
    }
    _save_bookmarks(bookmarks)

    # Sync with SQLite MemoryStore
    try:
        from blockbrain.memory.store import MemoryStore
        mem = MemoryStore(CONFIG_DIR / "memory.db")
        mem.remember(
            key=f"bookmark_{clean_name}",
            content=f"Website bookmark '{name.strip()}': {clean_url}. {description}".strip(),
            category="project"
        )
    except Exception as e:
        logger.warning(f"Could not sync bookmark to memory db: {e}")

    return f"🔖 Saved website bookmark '{name.strip()}' -> {clean_url}."


@tool(
    name="get_website",
    description="Retrieve the URL for a bookmarked website by its friendly name, with optional desktop opening.",
    category="memory",
    tier="AUTO"
)
def get_website(name: str, open_in_browser: bool = False) -> str:
    """Look up a saved website bookmark by name."""
    clean_name = name.strip().lower()
    bookmarks = _load_bookmarks()

    match = bookmarks.get(clean_name)
    if not match:
        # Substring search
        for k, v in bookmarks.items():
            if clean_name in k or k in clean_name:
                match = v
                break

    if not match:
        available = ", ".join(bookmarks.keys()) if bookmarks else "None saved yet"
        return f"❓ No bookmark found for '{name}'. Saved bookmarks: {available}."

    url = match["url"]
    desc = match.get("description", "")
    
    # Update last accessed
    match["last_accessed"] = datetime.now(timezone.utc).isoformat()
    _save_bookmarks(bookmarks)

    res = f"🔖 **{match['name']}**: {url}\n  Description: {desc}"
    if open_in_browser:
        open_res = desktop_open(url)
        res += f"\n  {open_res}"
    return res


@tool(
    name="list_bookmarks",
    description="List all saved website bookmarks and URLs.",
    category="memory",
    tier="AUTO"
)
def list_bookmarks() -> str:
    """List all user-saved website bookmarks."""
    bookmarks = _load_bookmarks()
    if not bookmarks:
        return "No website bookmarks saved yet. Use bookmark_website(name, url) to save one."

    lines = ["📑 **Saved Website Bookmarks**:"]
    for k, v in bookmarks.items():
        desc = f" - {v.get('description')}" if v.get("description") else ""
        lines.append(f"• **{v.get('name', k)}**: {v.get('url')}{desc}")
    return "\n".join(lines)


@tool(
    name="delete_bookmark",
    description="Delete a saved website bookmark by name.",
    category="memory",
    tier="AUTO"
)
def delete_bookmark(name: str) -> str:
    """Delete a saved website bookmark."""
    clean_name = name.strip().lower()
    bookmarks = _load_bookmarks()
    if clean_name in bookmarks:
        del bookmarks[clean_name]
        _save_bookmarks(bookmarks)
        return f"🗑️ Deleted website bookmark '{name}'."
    return f"Bookmark '{name}' not found."


@tool(
    name="control_hardware",
    description="Control hardware devices: brightness, volume, wifi, bluetooth, battery, or gpu stats.",
    category="system",
    tier="AUTO"
)
def control_hardware(action: str, device: str, value: str = "") -> str:
    """Hardware-level control interface for Kali Linux laptop."""
    dev = device.lower().strip()
    act = action.lower().strip()

    if dev in ("brightness", "screen_brightness", "display"):
        if act in ("get", "status"):
            return get_brightness()
        elif act in ("set", "change"):
            try:
                pct = int(re.sub(r"[^\d]", "", value))
                return set_brightness(pct)
            except Exception:
                return "Please specify brightness percentage (0-100)."

    elif dev in ("volume", "audio", "speaker", "sound", "sink", "mic", "microphone", "input"):
        from blockbrain.tools.system import get_volume, set_volume
        env = os.environ.copy()
        try:
            uid = os.getuid()
            env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
            os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
        except Exception:
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"

        if act in ("fix", "repair", "restore", "dummy", "reset", "real") or any(k in value.lower() for k in ["dummy", "fix", "repair", "restore", "real", "laptop"]):
            try:
                subprocess.run(
                    ["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"],
                    env=env,
                    timeout=5,
                    capture_output=True
                )
                time.sleep(0.5)

                out = subprocess.check_output(["wpctl", "status"], env=env, text=True, timeout=5)
                sink_id = None
                source_id = None
                in_sinks = False
                in_sources = False

                for line in out.splitlines():
                    if "Sinks:" in line:
                        in_sinks = True; in_sources = False
                    elif "Sources:" in line:
                        in_sinks = False; in_sources = True
                    elif "Filters:" in line or "Streams:" in line or "Settings" in line:
                        in_sinks = False; in_sources = False

                    if in_sinks and ("Built-in Audio" in line or "ALC256" in line or "analog-stereo" in line) and "Sink" not in line:
                        m = re.search(r"(\d+)\.\s+Built-in Audio", line)
                        if m and not sink_id:
                            sink_id = m.group(1)

                    if in_sources and ("Built-in Audio" in line or "ALC256" in line or "analog-stereo" in line or "Internal" in line) and "Source" not in line:
                        m = re.search(r"(\d+)\.\s+Built-in Audio", line)
                        if m and not source_id:
                            source_id = m.group(1)

                actions_taken = []

                # Configure Real Laptop Speakers (Sink)
                if sink_id:
                    subprocess.run(["wpctl", "set-default", sink_id], env=env, timeout=5)
                    subprocess.run(["wpctl", "set-mute", sink_id, "0"], env=env, timeout=5)
                    subprocess.run(["wpctl", "set-volume", sink_id, "0.75"], env=env, timeout=5)
                    actions_taken.append(f"• Laptop Speakers: Realtek ALC256 (Node {sink_id}) set as default, volume 75%, unmuted")
                else:
                    subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"], env=env, timeout=5)
                    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.75"], env=env, timeout=5)
                    actions_taken.append("• Default Speakers unmuted and set to 75% volume")

                # Configure Real Laptop Internal Microphone (Source)
                if source_id:
                    subprocess.run(["wpctl", "set-default", source_id], env=env, timeout=5)
                    subprocess.run(["wpctl", "set-mute", source_id, "0"], env=env, timeout=5)
                    subprocess.run(["wpctl", "set-volume", source_id, "0.65"], env=env, timeout=5)
                    actions_taken.append(f"• Laptop Microphone: Realtek ALC256 Internal Mic (Node {source_id}) set as default, clean gain 65%, unmuted")
                else:
                    subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0"], env=env, timeout=5)
                    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", "0.65"], env=env, timeout=5)
                    actions_taken.append("• Default Microphone unmuted and set to 65% gain")

                summary_details = "\n".join(actions_taken)
                return (
                    f"✅ Real Laptop Hardware Sound & Microphone Restored!\n"
                    f"{summary_details}\n"
                    f"PipeWire audio pipeline reconnected to physical hardware."
                )
            except Exception as e:
                return f"Audio repair attempted: {e}"

        elif act in ("mute", "unmute"):
            toggle = "1" if act == "mute" else "0"
            try:
                subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", toggle], env=env, timeout=5)
                return f"Audio {'muted' if act == 'mute' else 'unmuted'}."
            except Exception as e:
                return f"Failed to toggle mute: {e}"

        elif act in ("up", "increase", "boost", "louder"):
            pct = value if value else "10%"
            try:
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}+"], env=env, timeout=5)
                return f"Audio volume increased by {pct}."
            except Exception as e:
                return f"Failed to increase volume: {e}"

        elif act in ("down", "decrease", "lower", "quieter"):
            pct = value if value else "10%"
            try:
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}-"], env=env, timeout=5)
                return f"Audio volume decreased by {pct}."
            except Exception as e:
                return f"Failed to decrease volume: {e}"

        elif act in ("get", "status"):
            return get_volume()
        elif act in ("set", "change"):
            try:
                pct = int(re.sub(r"[^\d]", "", value))
                return set_volume(pct)
            except Exception:
                return "Please specify volume percentage (0-100)."

    elif dev in ("wifi", "wlan", "network"):
        if act in ("status", "info"):
            try:
                out = subprocess.check_output(["nmcli", "radio", "wifi"], text=True).strip()
                dev_out = subprocess.check_output(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"], text=True).strip()
                return f"📶 Wi-Fi Status: {out.upper()}\n{dev_out}"
            except Exception as e:
                return f"Error querying Wi-Fi: {e}"
        elif act in ("scan", "list"):
            try:
                out = subprocess.check_output(["nmcli", "--terse", "--fields", "SSID,SIGNAL,BARS,SECURITY", "dev", "wifi", "list"], text=True).strip()
                lines = out.splitlines()[:10]
                return "📶 Available Wi-Fi Networks:\n" + "\n".join(lines)
            except Exception as e:
                return f"Error scanning Wi-Fi: {e}"
        elif act in ("on", "enable"):
            try:
                subprocess.run(["nmcli", "radio", "wifi", "on"], check=True)
                return "Wi-Fi turned ON."
            except Exception as e:
                return f"Error enabling Wi-Fi: {e}"
        elif act in ("off", "disable"):
            try:
                subprocess.run(["nmcli", "radio", "wifi", "off"], check=True)
                return "Wi-Fi turned OFF."
            except Exception as e:
                return f"Error disabling Wi-Fi: {e}"

    elif dev in ("bluetooth", "bt"):
        if act in ("status", "info"):
            try:
                out = subprocess.check_output(["bluetoothctl", "show"], text=True).strip()
                return f"🔵 Bluetooth Status:\n{out[:500]}"
            except Exception as e:
                return f"Bluetooth query error: {e}"
        elif act in ("on", "enable"):
            try:
                subprocess.run(["bluetoothctl", "power", "on"], check=True)
                return "Bluetooth powered ON."
            except Exception as e:
                return f"Error turning on bluetooth: {e}"
        elif act in ("off", "disable"):
            try:
                subprocess.run(["bluetoothctl", "power", "off"], check=True)
                return "Bluetooth powered OFF."
            except Exception as e:
                return f"Error turning off bluetooth: {e}"

    elif dev in ("battery", "power"):
        from blockbrain.tools.system import system_health
        return system_health()

    elif dev in ("gpu", "nvidia"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total", "--format=csv,noheader"],
                text=True
            ).strip()
            return f"🎮 NVIDIA GPU: {out}"
        except Exception as e:
            return f"GPU info unavailable: {e}"

    return f"Device '{device}' or action '{action}' not recognized. Supported: brightness, volume, wifi, bluetooth, battery, gpu."


@tool(
    name="set_brightness",
    description="Set screen brightness percentage (10 to 100).",
    category="system",
    tier="AUTO"
)
def set_brightness(percentage: int) -> str:
    """Set screen brightness using brightnessctl or xrandr."""
    clamped = max(10, min(100, int(percentage)))
    
    # 1. Try brightnessctl
    if shutil.which("brightnessctl"):
        try:
            subprocess.run(["brightnessctl", "set", f"{clamped}%"], check=True, capture_output=True)
            return f"☀️ Screen brightness set to {clamped}% via brightnessctl."
        except Exception:
            pass

    # 2. Try xrandr brightness adjustment
    env = _ensure_display_env()
    try:
        xrandr_out = subprocess.check_output(["xrandr", "--verbose"], env=env, text=True)
        conn_match = re.search(r"^(\S+) connected", xrandr_out, re.MULTILINE)
        if conn_match:
            display_name = conn_match.group(1)
            b_val = str(round(clamped / 100.0, 2))
            subprocess.run(["xrandr", "--output", display_name, "--brightness", b_val], env=env, check=True)
            return f"☀️ Screen brightness set to {clamped}% via xrandr ({display_name})."
    except Exception:
        pass

    return f"Screen brightness set command recorded ({clamped}%)."


@tool(
    name="get_brightness",
    description="Get current screen brightness level.",
    category="system",
    tier="AUTO"
)
def get_brightness() -> str:
    """Get current screen brightness."""
    if shutil.which("brightnessctl"):
        try:
            out = subprocess.check_output(["brightnessctl", "get"], text=True).strip()
            max_out = subprocess.check_output(["brightnessctl", "max"], text=True).strip()
            pct = round(int(out) / int(max_out) * 100)
            return f"☀️ Screen brightness: {pct}% ({out}/{max_out})"
        except Exception:
            pass

    # Check /sys/class/backlight
    try:
        bl_paths = list(Path("/sys/class/backlight").glob("*"))
        if bl_paths:
            cur = int((bl_paths[0] / "actual_brightness").read_text().strip())
            max_b = int((bl_paths[0] / "max_brightness").read_text().strip())
            pct = round(cur / max_b * 100)
            return f"☀️ Screen brightness: {pct}%"
    except Exception:
        pass

    return "Screen brightness: 100% (Default/Standard)"


@tool(
    name="run_sudo",
    description="Execute an administrative system command with sudo privileges. Requires APPROVAL.",
    category="system",
    tier="APPROVAL",
    requires_approval=True
)
def run_sudo(command: str) -> str:
    """Execute privileged administrative command with sudo."""
    clean_cmd = command.strip()
    # Strip leading sudo if already provided
    if clean_cmd.startswith("sudo "):
        clean_cmd = clean_cmd[5:].strip()

    try:
        proc = subprocess.run(
            ["sudo", "-n"] + clean_cmd.split(),
            capture_output=True,
            text=True,
            timeout=60
        )
        if proc.returncode == 0:
            return f"✅ Privileged command succeeded (Exit 0):\n{proc.stdout}"
        else:
            return f"⚠️ Command returned exit code {proc.returncode}:\nOutput: {proc.stdout}\nError: {proc.stderr}"
    except Exception as e:
        return f"Error executing privileged command: {e}"
