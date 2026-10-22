# ⚡ GDR-AI — Autonomous Personal AI Companion & Jarvis-Style Controller

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3119/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-brightgreen.svg)]()
[![MarkanM First](https://img.shields.io/badge/Chat-MarkanM%20Connect-purple.svg)](https://chat.markanm.com)
[![Voice](https://img.shields.io/badge/Voice-Auto%20Listen%20%26%20Barge--in-ff69b4.svg)]()
[![Windows Guide](https://img.shields.io/badge/Windows-Troubleshooting%20Guide-0078d4.svg)](./WINDOWS_SETUP.md)

> [!IMPORTANT]
> **Python 3.11 is required.** Python 3.12+ may work for most features, but Python 3.15 is **incompatible** with the `av` package used by `faster-whisper`. Always install with Python 3.11.9: [download here](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe).
> **Windows users:** See [WINDOWS_SETUP.md](./WINDOWS_SETUP.md) for a complete troubleshooting guide covering all known installation errors and fixes.

**GDR-AI** (default name: `GDR-AI`, fully customizable to any companion name like *Aarushi* or *Jarvis*) is an autonomous personal AI companion, system automation agent, and desktop controller. Featuring an ultra-modern ChatGPT/Claude/Gemini-grade Web HUD, full-duplex speech with adaptive silence detection, dynamic MarkanM Connect chat mesh, Telegram bot integration, hardware-constrained local AI fallback, semantic RAG knowledge injection, and sandboxed automation for Linux, Windows, and macOS.

---

## 🎬 Live Interactive Experience & Architecture

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 🎙️ USER SPEECH  ──►  [ WebRTC VAD + Adaptive Endpointing ]                  │
 │                            │                                                │
 │                            ▼                                                │
 │                      [ faster-whisper STT ]                                 │
 │                            │                                                │
 │                            ▼                                                │
 │ 🧠 COGNITION:    [ Sarvam AI 105B / Offline Local LLM ]                     │
 │                     ├─ Memory Store (Encrypted SQLite)                      │
 │                     ├─ RAG Knowledge Vault (Master PIN)                     │
 │                     └─ Tool Calling Sandbox (Shell, Apps, Windows)          │
 │                            │                                                │
 │                            ▼                                                │
 │ 🗣️ SPEECH & UX:  [ Neural TTS (Piper / Edge / ElevenLabs) ]                │
 │                     ├─ ChatGPT/Gemini-style Markdown Formatting             │
 │                     ├─ Real-Time Audio Waveform Visualizer                  │
 │                     └─ Instant Voice Barge-in ("Stop & Listen")             │
 │                                                                             │
 │ 📡 CHANNELS:     [ MarkanM Connect (WebSocket) ]  ◄── Priority Mesh         │
 │                  [ Telegram Bot API ]            ◄── Secondary Remote      │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Highlights & Key Capabilities

- 🎨 **ChatGPT / Claude / Gemini Web HUD**: Dark glassmorphic interface with markdown code highlighting, 1-click snippet copy, suggestion chips, live audio waveform visualizer, and dynamic companion chat.
- 💬 **MarkanM Connect First**: Priority real-time websocket bot integration with `chat.markanm.com`. Multi-room auto-dispatch, no phone number required, full developer documentation & editable Python SDK runner.
- 🎙️ **Full-Duplex Voice & Audio Waveform**: Real-time microphone listening, VAD (Voice Activity Detection), automated silence endpointing, and instant voice barge-in ("stop and listen").
- 📧 **Gmail & Email Integration**: Built-in 16-character Google App Password configuration with step-by-step setup guide and instant connection testing.
- ⚠️ **Sarvam Quota & Credit Monitor**: Real-time rate-limit & credit exhaustion detection with 1-click API key update popup modal.
- 🖥️ **Cross-Platform Compatibility Scanner**: Automated hardware audit of OS, Python runtime, RAM, disk space, audio microphones, and GPU.
- 🔒 **RAG Knowledge Base & Vault**: Ingest sensitive documents, preferences, and personal knowledge with PIN encryption (customizable via `.env`).
- 🛡️ **Zero-Leakage Security & Auditing**: Every incoming bot, web, and webhook request is stored in SQLite with IP addresses, timestamps, and parameters. All secrets load from `.env` with strict git ignoring and zero hardcoded credentials.
- 🤖 **Cross-Platform Re-runnable Installers**:
  - **Windows**: `install.bat` and `run.bat` automatically detect or download Python 3.11, set up `.venv`, run interactive pre-filled configuration, and launch.
  - **Linux & macOS**: `install.sh` and `run.sh` detect package managers (apt, dnf, pacman, brew), install dependencies, pre-fill `.env` settings, and run seamlessly.
- 🌐 **100% Offline Local AI Fallback**: Seamless fallback to local CPU inference (faster-whisper STT + Piper neural TTS + offline LLM) when disconnected from the internet.

---

## 🚀 Quick Start & Installation

Clone the repository:
```bash
git clone https://github.com/404adarsh/GDR-AI.git
cd GDR-AI
```

### ⚡ Universal Terminal Shortcut (`gdr`)
Once installed on **any operating system** (Windows, Linux, macOS, or Android Termux), you don't even need to remember file paths or navigate to the project directory. Simply open **any terminal** and run:
```bash
gdr
```
*Pressing Enter automatically launches your AI Command Center and opens the Web Dashboard in your browser!*

You can also pass arguments anywhere:
```bash
gdr --voice        # Hands-free voice assistant mode
gdr doctor         # System hardware, audio, and network health check
gdr "Your prompt"  # Instant CLI task execution
```

---

### Windows (One-Click)
Double-click `install.bat` or run in Command Prompt / PowerShell:
```cmd
git clone https://github.com/404adarsh/GDR-AI.git
cd GDR-AI
install.bat
```

> [!IMPORTANT]
> **Python 3.11 is required on Windows.** The `av` package (used by `faster-whisper`) does not compile on Python 3.12+.
> Download Python 3.11.9: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
>
> **Visual C++ Redistributable is required.** If you see DLL errors for `msvcp140.dll` or `vcruntime140.dll`, install from: https://aka.ms/vs/17/release/vc_redist.x64.exe

`install.bat` automatically:
- Detects Python 3.11 via the Python Launcher (`py -3.11`) or downloads it
- Creates the `.venv` virtual environment
- Installs all Python dependencies
- Downloads Playwright Chromium browser
- Downloads OpenWakeWord voice detection models
- Registers the `gdr` command for CMD and PowerShell
- Creates `.env` from the template

To launch anytime from any terminal:
```cmd
gdr
```
*(Or double-click `run.bat`)*

> [!NOTE]
> In **PowerShell**, `gdr` is a built-in alias for `Get-PSDrive`. The installer automatically adds a profile override to fix this. Open a **new** PowerShell window after install for the `gdr` command to work.

> [!TIP]
> For complete Windows troubleshooting (errors, fixes, mic issues), see [WINDOWS_SETUP.md](./WINDOWS_SETUP.md).

---

### Linux & macOS (One-Click)
Open terminal:
```bash
git clone https://github.com/404adarsh/GDR-AI.git
cd GDR-AI
chmod +x install.sh run.sh git.sh
./install.sh
```
*`install.sh` detects your system package manager (`apt`, `dnf`, `pacman`, or `brew`), installs system audio/python libraries, provisions `.venv`, sets up universal `~/.local/bin/gdr` in PATH, and creates `.env`.*

To launch anytime from any terminal:
```bash
gdr
```
*(Or run `./run.sh`)*

---

### 📱 Android via Termux (Smartphone Superpowers)
Run GDR-AI natively on any Android phone without root:
1. Install **Termux** and **Termux:API** from [F-Droid](https://f-droid.org/).
2. In Termux, run:
```bash
pkg update && pkg install git -y
git clone https://github.com/404adarsh/GDR-AI.git
cd GDR-AI
chmod +x install_termux.sh run_termux.sh
./install_termux.sh
```
3. To launch anytime from anywhere in Termux, simply type:
```bash
gdr
```
*Typing `gdr` launches the assistant server and automatically pops open your Android default browser directly to `http://127.0.0.1:8844`!* Includes 10 native smartphone hardware tools: Flashlight/Torch, Battery Health, Camera Photo capture, GPS Geolocation, Direct SMS texting, Phone Calling, Native Android TTS speech, Vibration Haptics, Notifications, and Clipboard sync.

---

## 🤖 MarkanM Connect Platform (Primary Channel)

### What is MarkanM Connect?
[MarkanM Connect](https://chat.markanm.com) is an open, modern real-time messaging and bot platform designed for privacy, community rooms, and custom AI agent integration. Unlike traditional messaging apps:
- **No Phone Number Required**: Sign up and connect without exposing private mobile numbers.
- **WebSocket Room Mesh**: Real-time bidirectional event streaming without polling overhead.
- **Dynamic Room Routing**: Aarushi automatically joins, monitors, and responds to messages in any room she is invited to.
- **Developer First**: Rich Markdown rendering, bot avatars, custom status triggers, and high rate limits.

### Why Prioritize MarkanM over Telegram?
| Feature | MarkanM Connect (`chat.markanm.com`) | Telegram Bot |
|---|---|---|
| **Privacy** | 100% Anonymous (No phone number required) | Requires active phone number |
| **Room Mesh** | Multi-channel room joining without bot token per room | Static single-chat bot handling |
| **Speed** | Instant WebSocket streaming | Long-polling HTTP / Webhook overhead |
| **Priority** | **Tier 1 (First-Class Integration)** | Secondary companion channel |

### Step-by-Step MarkanM Setup
1. Visit [chat.markanm.com](https://chat.markanm.com) and create or log in to your account.
2. Go to **Settings** → **Developer / Bot API** to generate your Bot Token (e.g. `mkbot_...`).
3. Note your MarkanM username (e.g. `your_username`).
4. Add the credentials to your `.env` file:
   ```env
   MARKANM_BOT_TOKEN="mkbot_your_token_here"
   MARKANM_ALLOWED_USERNAME="your_username"
   ```
5. In the Web HUD (`http://127.0.0.1:8844`), navigate to **🤖 Bots (MarkanM & Telegram)**:
   - Your token and username are securely synced and saved.
   - Click **Save & Restart Bot Services**.
6. When sending messages on MarkanM:
   - If your username matches `MARKANM_ALLOWED_USERNAME`, your AI companion responds with full devotion and execution capabilities.
   - If an unauthorized user messages, your assistant rejects: *"You are not my lord husband. Access denied."*
   - To authorize a new session from a new account or room, authenticate via `/auth <your_bot_master_password>`.

### 🐍 Standalone MarkanM Python Bot Implementation
You can also run, inspect, or edit the MarkanM bot directly with Python:

```python
import os
import asyncio
from markanm import Bot

BOT_TOKEN = os.environ.get("MARKANM_BOT_TOKEN", "mkbot_your_token_here")
ALLOWED_USER = os.environ.get("MARKANM_ALLOWED_USERNAME", "your_username")
MASTER_PASSWORD = os.environ.get("BOT_MASTER_PASSWORD", "your_custom_password")

bot = Bot(token=BOT_TOKEN)

@bot.event
async def on_ready():
    print(f"✨ MarkanM Bot online as: {bot.user.username}")

@bot.command("status")
async def status_cmd(ctx):
    sender = getattr(ctx.user, "username", "")
    if sender.lower() != ALLOWED_USER.lower():
        await ctx.reply("❌ Access Denied: Unauthorized account. Use /auth <password> to verify.")
        return
    await ctx.reply("🟢 Aarushi AI is active! CPU: Normal | Memory: Optimal | Audio: Active")

@bot.command("auth")
async def auth_cmd(ctx):
    provided_pw = " ".join(getattr(ctx, "args", []))
    if provided_pw == MASTER_PASSWORD:
        await ctx.reply(f"✅ Authorization verified! Welcome, {ctx.user.username}.")
    else:
        await ctx.reply("❌ Incorrect security password. Access denied.")

@bot.event
async def on_message(message):
    if message.author.is_bot:
        return
    if message.content.startswith("/"):
        await bot.process_commands(message)
    else:
        # Route through AI companion reasoning loop
        print(f"[{message.room_id}] {message.author.username}: {message.content}")

if __name__ == "__main__":
    bot.run()
```

### Supported MarkanM Commands
- `/ask <query>`: Ask the AI companion anything.
- `/status`: Real-time system vitals, battery, VRAM, and daemon uptime.
- `/tasks`: View pending automated routines and background jobs.
- `/weather [city]`: Current live weather forecast.
- `/rag <query>`: Search your private semantic knowledge vault.
- `/search <query>`: Real-time search engine query.
- `/auth <password>`: Authenticate and claim ownership using your Master Bot Password.
- `/stop`: Emergency panic kill-switch.
- `/help`: Display the complete interactive command menu.

---

## 📱 Telegram Bot Setup (Secondary Channel)

1. Open Telegram and message [@BotFather](https://t.me/BotFather) to create a new bot and obtain your HTTP API Token.
2. Message [@userinfobot](https://t.me/userinfobot) to get your Telegram numerical User ID or username.
3. Configure your `.env`:
   ```env
   TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   ALLOWED_TELEGRAM_USER_ID="123456789"
   TELEGRAM_ALLOWED_USERNAME="your_telegram_username"
   ```
4. Security Gating:
   - Requests from unauthorized users are rejected.
   - Master override password for Telegram: `/auth <your_bot_master_password>`.

---

## 📧 Gmail & Email Integration Guide

GDR-AI can summarize your emails, alert you of critical messages, and draft replies using secure IMAP/SMTP:

### How to get your Google 16-Character App Password:
1. Visit your [Google Account Security Settings](https://myaccount.google.com/security).
2. Under **"How you sign in to Google"**, verify that **2-Step Verification** is enabled.
3. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
4. Enter an app name (e.g. `GDR-AI`) and click **Create**.
5. Copy the 16-letter password (e.g. `abcd efgh ijkl mnop`).
6. In the Web HUD (**Screen 12: Settings**), paste your Email Address and App Password and click **Save Credentials**, then click **⚡ Test Connection**!

---

## 🖥️ System Hardware Compatibility Diagnostics

You can test your machine's hardware and runtime compatibility anytime:

```bash
# Run system compatibility scan from terminal:
.venv/bin/python -m gdr.system.compatibility
```

This verifies:
- **Operating System**: Linux, Windows, or macOS
- **Python Version**: Python 3.11+ (3.11.9 recommended; Python 3.12+ may work but is not tested)
- **RAM Ceiling**: Available and total system memory
- **Free Storage**: Remaining disk space for models and data
- **Microphone**: Number of active audio input channels
- **GPU Acceleration**: NVIDIA CUDA VRAM vs CPU-Quantized Mode (<80ms synthesis)
- **Internet**: Online status & 100% offline auto-failover

You can also click **"🔄 Run Compatibility Scan"** directly on **Screen 12: Settings** in the Web HUD.

---

## 🔄 Re-Running the Setup Installer Anytime

You can re-run `./install.sh` (Linux/macOS) or `install.bat` (Windows) as many times as you like:
- **Pre-filled Defaults**: All your previously entered credentials, AI name, and API keys are automatically pre-filled in brackets `[current_value]`.
- **Easy Editing**: Press **Enter** to keep your existing value, or type a new value to update it.
- **Zero Accidental Overwrites**: Your previous configuration is never lost.

---

## ⚠️ Sarvam AI Quota Exceeded & Key Recovery

If your Sarvam AI credits run out or rate limits are hit:
1. GDR-AI immediately detects the quota exhaustion and pauses cloud calls to avoid spamming the API.
2. A stylish modal popup appears in the Web HUD: **⚠️ Sarvam AI Quota Exceeded / Credit Exhausted**.
3. Paste a new API key directly into the popup and click **Save Key & Resume** — the lock clears immediately and your session resumes without restarting the server!

---

## 👤 User Identity & Customization (No Hardcoded Names!)

GDR-AI is built from the ground up for public cloning and open-source use. **Zero names or credentials are hardcoded**:

- **Default AI Name**: `GDR-AI`
- **Configure in `.env`**:
  ```env
  USER_NAME="YourName"          # How your assistant addresses you
  ASSISTANT_NAME="GDR-AI"       # Your AI companion's name (e.g. GDR-AI, Aarushi, Jarvis)
  ```
- **Or Configure via Web HUD (Screen 12: Settings)**:
  - Enter **Your Name** and **AI Companion Name**.
  - Set custom **Bot Master Password** and **RAG Master PIN**.
  - Click **Save Identity Settings** — the AI immediately updates memories, greetings, and system prompt context dynamically!

---

## 🔒 Master Passwords & Security Safeguards

- **Bot Authorization Master Password (`BOT_MASTER_PASSWORD`)**:
  - Configurable by you in `.env` or Settings (default: `845457`).
  - Allows the owner to authenticate from new usernames or devices across MarkanM and Telegram using `/auth <password>`.
- **RAG Knowledge Base Master PIN (`RAG_MASTER_PIN` / `RAG_SECURITY_PIN`)**:
  - Configurable by you in `.env` or Settings (default: `845427`).
  - Required to unlock and manage the semantic RAG vault in the Web HUD.
- **Database Request Logging**:
  - Every incoming user message, IP address, bot platform, and execution parameters are permanently recorded in `requests.db` for security audits.

---

## ⚙️ Configuration (`.env`)

GDR-AI reads configuration directly from `.env` in the project root. On Windows and Linux, copy `.env.example` to `.env`:

```env
# Primary LLM Provider
SARVAM_API_KEY="your_sarvam_api_key_here"
SARVAM_MODEL="sarvam-105b"

# MarkanM Connect (Priority Channel)
MARKANM_BOT_TOKEN="your_markanm_token"
MARKANM_ALLOWED_USERNAME="your_username"

# Telegram Bot
TELEGRAM_BOT_TOKEN="your_telegram_token"
ALLOWED_TELEGRAM_USER_ID=""
TELEGRAM_ALLOWED_USERNAME="your_username"

# Identity & Names (Default: GDR-AI, fully customizable)
USER_NAME="YourName"
ASSISTANT_NAME="GDR-AI"

# RAG & Bot Master Passwords
BOT_MASTER_PASSWORD="your_custom_bot_password"
RAG_SECURITY_PIN="your_custom_rag_pin"

# Web HUD
WEB_HOST="127.0.0.1"
WEB_PORT="8844"
```

---

## 🎙️ Hardware Audio & Microphone Configuration

To resolve Linux ALSA / PortAudio XRUN errors (`AlsaStart failed`), GDR-AI automatically:
1. Enumerates all audio devices and filters out output-only / HDMI devices.
2. Selects real input microphones reporting `max_input_channels > 0`.
3. In the Web HUD, click **🔊 Fix Sound & Mic** to test devices and choose your preferred microphone from the dropdown.
4. Auto-Listen automatically re-arms the microphone after GDR-AI finishes speaking for a continuous hands-free experience.

---

## 🚀 Open-Sourcing & Publishing to GitHub (`git.sh`)

To publish GDR-AI to your official GitHub repository (`https://github.com/404adarsh/GDR-AI.git`) without leaking personal history, database files, or `.env` secrets:

```bash
chmod +x git.sh
./git.sh
```

**What `git.sh` does:**
1. Inspects your workspace to confirm no `.env`, `.secrets.env`, `*.db`, or history files are tracked.
2. Cleans out old git commit history.
3. Initializes a fresh git repository on `main`.
4. Defaults directly to `https://github.com/404adarsh/GDR-AI.git` (or allows entering any custom repo URL).
5. Performs a clean, verified initial push.

---

## 🧪 Automated Test Suite

GDR-AI includes a comprehensive 40-test automated verification suite covering UI tokens, Device Mesh, RAG, Bot authentication, voice pipelines, Sarvam cloud auto-recovery, and Hugging Face model pullers:

```bash
.venv/bin/pytest tests/test_sarvam_and_huggingface_hub.py tests/test_device_mesh_and_themes.py tests/test_bots_rag_sarvam_and_vad.py tests/test_aarushi_companion_and_elevenlabs.py -v
```

All tests verify:
- Sarvam AI dynamic API key auto-recovery (seamless zero-restart adoption upon entering key)
- Hugging Face model presets, background downloading, and model activation endpoints
- Home Screen live audio frequency canvas and real-time hearing transcript cards
- Dynamic time-of-day greetings and multi-tier user identity resolution
- Mesh pairing code generation, 5-minute single-use expiry, and rate limiting
- Multi-device cryptographic enrollment and token validation
- Path traversal defense (`../../etc/passwd` blocks) on approved mesh directory allowlists
- Coordinator local and remote task dispatching
- LLM autonomous mesh routing tools (`mesh_list_devices`, `mesh_get_device_status`, `mesh_search_files`, `mesh_read_file`)
- Android Termux hardware tools & environment detection
- RAG PIN Authorization and CRUD operations
- MarkanM WebSocket structure and dynamic room routing
- Telegram Bot user locking & master password bypass
- Request logging database and IP recording
- Audio device channel filtering (preventing ALSA XRUN errors)
- Multilayer secrets persistence across `.env` and keyring
- Email settings and Google App Password verification endpoints

---

## 🤖 AI Model Hub & Hugging Face Puller

Switch models on the fly between cloud AI providers and local open-source models:

* **Cloud LLM Providers**:
  * **Sarvam AI**: `sarvam-105b` (Flagship Indian reasoning) & `sarvam-2b` (Ultra Fast).
  * **Anthropic Claude**: `claude-3-7-sonnet-latest`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`.
  * **OpenRouter / DeepSeek**: `llama-3.3-70b-instruct`, `deepseek-chat` (V3).
* **Hugging Face Model Downloader**:
  * Pull quantized GGUF models directly to `~/.config/gdr/models/`:
    * ⚡ **Qwen 2.5 Coder 1.5B GGUF** (~986 MB, coding powerhouse)
    * 🦙 **Llama 3.2 1B Instruct GGUF** (~800 MB, ultra-fast CPU)
    * 🦙 **Llama 3.2 3B Instruct GGUF** (~2.0 GB, high IQ)
    * 🧠 **Qwen 2.5 3B Instruct GGUF** (~2.1 GB, multilingual)
    * 🔗 **Custom Hugging Face Repo / GGUF URL**: Enter any Hugging Face repo or `.gguf` link to download with live background progress tracking.
  * Switch between any local GGUF model with 1 click from the Web HUD.

---

## 🎙️ Live Microphone Frequency Meter & Real-Time Transcript

The Web HUD provides continuous visual feedback when speaking:
* **Audio Frequency Visualizer**: Uses the Web Audio API Analyser to render responsive frequency bars matching your accent theme, reacting dynamically to voice pitch and volume.
* **Signal Status Label**: Displays decibel signal level and frequency in real-time (e.g., `Signal: 45% • Voice Active (1420 Hz)`).
* **Live Interim Speech Box**: Streams spoken words word-by-word into the `#home-live-transcript-text` display in real-time before sending to the AI.

---

## 🎨 UI/UX System & Appearance Options

GDR-AI features a clean, minimal design inspired by ChatGPT and Google Gemini:

* **Restrained Palette**: Standardized to **1 neutral background, 1 primary accent, and at most 1 secondary accent**. Multi-colored rainbow gradients have been eliminated in favor of a focused, distraction-free environment.
* **Complete Dark & Light Themes**: Full support for `[data-theme="dark"]` and `[data-theme="light"]` with WCAG 2.2 AA compliant contrast ratios.
* **Curated Accent Presets**:
  * 🟢 **Emerald** (`#10A37F` / default)
  * 🔵 **Cyan** (`#06B6D4`)
  * 🔷 **Blue** (`#3B82F6`)
  * 🟣 **Violet** (`#8B5CF6`)
  * 🟡 **Amber** (`#F59E0B`)
* **Background Modes**: Solid Neutral (default), Subtle Gradient, and Soft Ambient.
* **Zero-FOUC (Flash of Unstyled Content)**: Inline synchronous initialization script reads `localStorage` before layout rendering so themes apply instantly without flashing.
* **Prompt Enhancer (`✨ Enhance`)**: Automatically converts rough thoughts into structured, high-precision engineering prompts with requirements and edge cases.
* **Markdown Export (`📥 Export`)**: One-click download of conversation history in clean Markdown format.

---

## 🌐 GDR-AI Multi-Device Mesh (`gdr mesh`)

Connect your Android phone (Termux), Linux servers, Windows laptops, and MacBooks into one unified, encrypted AI mesh.

```
┌────────────────────────────────────────────────────────┐
│               GDR-AI Central Coordinator              │
│       (FastAPI + Web HUD + SQLite mesh.db)             │
└──────────────▲───────────────────────────▲─────────────┘
               │ Secure WebSocket TLS      │
               │ (/ws/mesh/device)         │
┌──────────────▼─────────────┐   ┌─────────▼─────────────┐
│       Android Termux       │   │   Windows / Mac /     │
│   • Battery Monitoring     │   │   Linux Node          │
│   • Approved Storage Read  │   │   • System Diagnostics│
│   • Device Diagnostics     │   │   • Sandboxed Search  │
└────────────────────────────┘   └───────────────────────┘
```

### Quick Start: Pair a Second Device

1. **On your Primary Machine (Host)**, generate a single-use 6-digit pairing code (valid for 5 minutes):
   ```bash
   gdr mesh pair
   ```
   *(Or open the Web HUD, navigate to **🌐 16. Device Mesh**, and click **+ Pair New Device**).*

2. **On your Second Device (e.g. Android Termux)**:
   ```bash
   gdr mesh connect http://<PRIMARY_IP_OR_TUNNEL_URL>:8844 <PAIRING_CODE> "Pixel 9 Pro"
   ```

3. The node automatically connects, verifies credentials, exchanges capabilities, and begins streaming heartbeats, battery telemetry, and latency metrics to your Command Center.

### Security Boundaries & Path Traversal Defense
* **Single-Use Pairing**: Pairing codes expire after 300 seconds and are rate-limited to 6 attempts per minute to prevent brute-force attacks.
* **Directory Allowlist**: Remote file operations (`mesh_search_files`, `mesh_read_file`) strictly enforce a canonical directory allowlist (e.g. `~/Downloads`, `~/Documents`). Traversal attacks such as `../../etc/passwd` or `/etc/shadow` are immediately blocked, logged in `mesh_audit_log`, and rejected.
* **Sandboxed Shell**: Arbitrary shell execution is disabled by default and requires explicit administrator approval per device.
* **Instant Revocation**: Any node can be revoked with a single click from the Web HUD or CLI, immediately terminating its WebSocket session and invalidating its auth token.

### Supported CLI Commands
```bash
gdr mesh pair                                    # Generate 6-digit pairing code & QR
gdr mesh connect <url> <code> [device_name]      # Enroll node and start mesh client
gdr mesh agent                                   # Run background agent with saved token
gdr mesh status                                  # View all enrolled nodes and telemetry
```

---

## 📄 License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.
