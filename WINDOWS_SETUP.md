# 🪟 GDR-AI Windows Setup & Troubleshooting Guide

> A battle-tested guide for installing and running GDR-AI on Windows 11, documenting every real error encountered and its exact fix.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Fix Checklist](#quick-fix-checklist)
3. [Installation Steps](#installation-steps)
4. [Error Reference](#error-reference)
   - [Error 1: Python Version Incompatibility (av / Cython)](#error-1-python-version-incompatibility)
   - [Error 2: install.bat Crashes with "... was unexpected at this time"](#error-2-installbat-crashes-with--was-unexpected-at-this-time)
   - [Error 3: Missing MSVC Runtime DLLs](#error-3-missing-msvc-runtime-dlls)
   - [Error 4: `gdr` Command Hijacked by PowerShell Alias](#error-4-gdr-command-hijacked-by-powershell-alias)
   - [Error 5: Unicode/Emoji Errors in CMD](#error-5-unicodeemoji-errors-in-cmd)
   - [Error 6: OpenWakeWord ONNX Model Permission Error 13](#error-6-openwakeword-onnx-model-permission-error-13)
   - [Error 7: `gdr.setup_interactive` Module Missing](#error-7-gdrsetup_interactive-module-missing)
   - [Error 8: PowerShell Profile Setup Corrupted by CMD Line Continuation](#error-8-powershell-profile-setup-corrupted-by-cmd-line-continuation)
   - [Error 9: Microphone Recording with Very Low RMS](#error-9-microphone-recording-with-very-low-rms)
   - [Error 10: TTS Check Failing Despite edge-tts Installed](#error-10-tts-check-failing-despite-edge-tts-installed)
5. [Verifying Everything Works](#verifying-everything-works)
6. [Microphone Troubleshooting](#microphone-troubleshooting)
7. [Working Commands Reference](#working-commands-reference)
8. [Files Changed During Setup](#files-changed-during-setup)

---

## Prerequisites

Before running `install.bat`, ensure the following are in place:

### 1. Python 3.11.9 (exact version required)

> [!IMPORTANT]
> GDR-AI requires **Python 3.11.x** specifically. Python 3.12+ and 3.13+ **will not work** because the `av` package (required by `faster-whisper`) uses Cython with `noexcept` syntax that is incompatible with newer Python ABI changes. Python 3.15 was confirmed broken.

Download and install from the official source:

```
https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
```

During installation:
- ✅ Check **"Add Python to PATH"**
- ✅ Check **"Install for all users"** (optional but recommended)
- ✅ Check **"Install pip"**

Verify after installing:

```powershell
py -3.11 --version
# Expected: Python 3.11.9
```

> [!NOTE]
> `winget install Python.Python.3.11 --silent` may fail with exit code 50 (UAC elevation required). Use the direct `.exe` installer instead.

---

### 2. Visual C++ Redistributable 2022

> [!IMPORTANT]
> `ctranslate2` and `onnxruntime` (used by faster-whisper) **require MSVC runtime DLLs** (`msvcp140.dll`, `vcruntime140.dll`, `vcruntime140_1.dll`) installed system-wide. These are not bundled with the Python packages.

Download and install:

```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

Run the installer and reboot if prompted.

---

### 3. PowerShell Execution Policy

To allow PowerShell profiles and scripts to run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

---

### 4. Git (to clone the repo)

```powershell
winget install Git.Git
```

---

## Quick Fix Checklist

Use this table to quickly diagnose your issue:

| # | Symptom | Quick Fix |
|---|---------|-----------|
| 1 | `pip install av` fails during `install.bat` | Install Python 3.11.9 from python.org |
| 2 | `install.bat` shows `... was unexpected at this time` | Fix curly brace f-string in bat file (see Error 2) |
| 3 | `import ctranslate2` → `OSError [WinError 126]` missing DLL | Install VC++ Redistributable x64 2022 |
| 4 | `gdr` in PowerShell opens `Get-PSDrive` instead | Remove PS alias; add `gdr` function to `$PROFILE` |
| 5 | `UnicodeEncodeError` for emoji in CMD | Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` |
| 6 | Wake Word FAIL: ONNX error 13 (permission denied) | `icacls` to grant full permissions on model folder |
| 7 | `No module named gdr.setup_interactive` | Remove that call from `install.bat` |
| 8 | `Missing closing ')'` in PowerShell profile setup | Write PS script to temp `.ps1` file, then execute it |
| 9 | Mic PASS but RMS is `0.0006`, voice not responding | Speak into mic; check Windows mic volume (set to 100%) |
| 10 | TTS FAIL even though `edge-tts` is installed | Add `edge_tts` / `gtts` import checks to `doctor.py` |

---

## Installation Steps

```cmd
REM 1. Clone the repository
git clone https://github.com/your-org/GDR-AI.git
cd GDR-AI-main

REM 2. Run the installer (from CMD, not PowerShell)
install.bat
```

> [!WARNING]
> Run `install.bat` from a **standard CMD window**, not PowerShell. Several fixes in the installer are CMD-specific and behave differently in PowerShell.

After installation completes:

```cmd
REM 3. Verify the setup
gdr doctor
```

---

## Error Reference

---

### Error 1: Python Version Incompatibility

<details>
<summary><strong>❌ Symptom</strong> — <code>install.bat</code> ran but pip failed installing the <code>av</code> package</summary>

**Symptom**

```
error: command 'C:\\...\\cl.exe' failed with exit code 2
...
Cython.Compiler.Errors.CompileError: av/...
noexcept is not supported in this Python version
```

The installer appears to start correctly but crashes when `pip` tries to compile `av` from source.

**Root Cause**

The system had Python 3.15.1. The `av` package (a dependency of `faster-whisper`) compiles Cython extensions using the `noexcept` keyword, which is not compatible with Python 3.15's updated ABI. The package has no pre-built wheel for Python 3.15 either, so pip falls back to source compilation — which also fails.

**Fix**

Install **Python 3.11.9** specifically:

```
https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
```

Then confirm the Python Launcher can find it:

```powershell
py -3.11 --version
# Expected: Python 3.11.9
```

The updated `install.bat` uses `py -3.11` as its preferred Python interpreter.

> [!NOTE]
> You can keep multiple Python versions installed side-by-side using the Windows Python Launcher (`py`). Your system Python remains untouched.

</details>

---

### Error 2: `install.bat` Crashes with "... was unexpected at this time"

<details>
<summary><strong>❌ Symptom</strong> — Double-clicking <code>install.bat</code> immediately shows a parse error</summary>

**Symptom**

```
... was unexpected at this time.
```

The window flashes and closes immediately, or shows this error on line 21.

**Root Cause**

The original `install.bat` used a Python f-string inside a CMD `for /f` loop:

```bat
REM BROKEN — curly braces are CMD variable syntax
for /f "delims=" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VER=%%v
```

CMD's batch parser interprets `{sys.version_info.major}` as a variable expansion attempt, causing an immediate parse error before Python even runs.

**Fix**

Replace the f-string version detection with a simple exit-code check — no curly braces required:

```bat
REM FIXED — no curly braces, uses exit code
python -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.11+ required.
    exit /b 1
)
```

Also, add a Python Launcher check first (most reliable on Windows):

```bat
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py -3.11
) else (
    set PYTHON=python
)
```

> [!TIP]
> Always avoid Python f-strings (which use `{` and `}`) inside CMD batch `for /f` blocks. Use `%`-style string formatting or exit-code tricks instead.

</details>

---

### Error 3: Missing MSVC Runtime DLLs

<details>
<summary><strong>❌ Symptom</strong> — <code>import ctranslate2</code> or <code>import onnxruntime</code> raises <code>OSError [WinError 126]</code></summary>

**Symptom**

```python
>>> import ctranslate2
OSError: [WinError 126] The specified module could not be found.
# Refers to: msvcp140.dll, vcruntime140.dll, or vcruntime140_1.dll
```

Or similarly when importing `onnxruntime`.

**Root Cause**

`ctranslate2` and `onnxruntime` are native C++ libraries that depend on the **Microsoft Visual C++ Runtime** DLLs. On a clean Windows installation without Visual Studio or Office, these DLLs may be absent from `System32`.

**Permanent Fix**

Install the Visual C++ Redistributable:

```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

Run as Administrator. Reboot if prompted.

**Temporary Workaround (no admin required)**

If UAC elevation is unavailable, copy the DLLs from an existing OneDrive installation (which bundles them):

```powershell
Copy-Item "C:\Users\GDR\AppData\Local\Microsoft\OneDrive\25.087.0506.0001\*140*.dll" ".venv\Scripts\"
```

> [!WARNING]
> The OneDrive path contains a version number (`25.087.0506.0001`) that will differ on your system. Check your actual OneDrive folder path:
> ```powershell
> Get-ChildItem "$env:LOCALAPPDATA\Microsoft\OneDrive" -Filter "*140*.dll" -Recurse
> ```

> [!CAUTION]
> The temporary workaround only works for the `.venv` environment. The **permanent fix** (installing VC++ Redistributable) is strongly recommended so DLLs are available system-wide.

</details>

---

### Error 4: `gdr` Command Hijacked by PowerShell Alias

<details>
<summary><strong>❌ Symptom</strong> — Typing <code>gdr</code> in PowerShell launches <code>Get-PSDrive</code> instead of GDR-AI</summary>

**Symptom**

```powershell
PS> gdr
# Shows a table of drive letters — it ran Get-PSDrive, not GDR-AI
```

Or `gdr` simply does nothing / shows an error about drive enumeration.

**Root Cause**

`gdr` is a **built-in PowerShell alias** for the `Get-PSDrive` cmdlet. Even if `gdr.bat` is on your `PATH`, PowerShell's alias resolution takes priority over external executables.

**Fix**

Edit your PowerShell profile to remove the alias and define a `gdr` function:

```powershell
# Open your profile in Notepad
notepad $PROFILE
```

Add these lines:

```powershell
# Remove the built-in Get-PSDrive alias so 'gdr' works as GDR-AI
if (Get-Alias gdr -ErrorAction SilentlyContinue) {
    Remove-Item Alias:gdr -Force
}

# Define gdr as a function that calls run.bat with any arguments
function gdr {
    & 'C:\Users\GDR\Downloads\GDR-AI-main\run.bat' @args
}
```

Save the file, then reload:

```powershell
. $PROFILE
```

> [!NOTE]
> There are **two** PowerShell profile files — one for Windows PowerShell 5.x and one for PowerShell 7+. Apply this fix to both if you use both:
> - `Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` (PS 5.x)
> - `Documents\PowerShell\Microsoft.PowerShell_profile.ps1` (PS 7+)

If profiles don't load at all, first enable execution:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

</details>

---

### Error 5: Unicode/Emoji Errors in CMD

<details>
<summary><strong>❌ Symptom</strong> — <code>gdr doctor</code> in CMD crashes with <code>UnicodeEncodeError</code> on emoji characters</summary>

**Symptom**

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 0: character maps to <undefined>
```

Triggered by emoji like `✅` or `❌` in the output of `gdr doctor`.

**Root Cause**

Windows CMD defaults to code page **cp1252** (Windows-1252), which cannot represent Unicode emoji or many non-Latin characters. Python's `sys.stdout` inherits this encoding.

**Fix**

Set these environment variables before running Python. Add to `run.bat`:

```bat
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
```

And add to your `.env` file:

```env
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
```

> [!TIP]
> You can also switch CMD to UTF-8 interactively for the current session:
> ```cmd
> chcp 65001
> ```
> But the environment variable approach in `run.bat` is more reliable and permanent.

</details>

---

### Error 6: OpenWakeWord ONNX Model Permission Error 13

<details>
<summary><strong>❌ Symptom</strong> — <code>gdr doctor</code> shows Wake Word FAIL with ONNX error 13</summary>

**Symptom**

```
Wake Word  | FAIL  | [ONNXRuntimeError] : 1 : FAIL : Load model from
           |       | ...hey_jarvis_v0.1.onnx failed:system error number 13
```

Error 13 is `EACCES` — permission denied.

**Root Cause**

The ONNX model files for OpenWakeWord were downloaded while another process held a file lock, leaving the files with restrictive permissions. The ONNX Runtime can't read them.

**Fix**

Grant your user account full control over the model directory:

```cmd
icacls ".venv\Lib\site-packages\openwakeword\resources\models" /grant %USERNAME%:F /T /Q
```

- `/grant %USERNAME%:F` — grants Full control to the current user
- `/T` — applies recursively to all files in the directory
- `/Q` — suppresses success messages

Then re-run `gdr doctor` to confirm the fix.

> [!NOTE]
> This typically happens after a partial or interrupted download. If the issue persists, delete the model directory and let OpenWakeWord re-download the models on next startup.

</details>

---

### Error 7: `gdr.setup_interactive` Module Missing

<details>
<summary><strong>❌ Symptom</strong> — <code>install.bat</code> fails at step 4 with <code>No module named gdr.setup_interactive</code></summary>

**Symptom**

```
Step 4: Running interactive setup...
C:\...\python.exe: No module named gdr.setup_interactive
```

**Root Cause**

The original `install.bat` called `python -m gdr.setup_interactive`, but this module **does not exist** in the current version of GDR-AI. It was removed or renamed in a refactor.

**Fix**

Remove the call to `gdr.setup_interactive` from `install.bat`. Interactive setup is now done by editing the `.env` file directly:

```bat
REM REMOVE this line from install.bat:
python -m gdr.setup_interactive

REM REPLACE with a message pointing to .env:
echo.
echo Setup complete! Edit .env to configure your API keys.
echo.
```

After installation, copy `.env.example` to `.env` and fill in your keys:

```cmd
copy .env.example .env
notepad .env
```

</details>

---

### Error 8: PowerShell Profile Setup Corrupted by CMD Line Continuation

<details>
<summary><strong>❌ Symptom</strong> — <code>install.bat</code>'s PowerShell profile setup gives <code>Missing closing ')'</code> error</summary>

**Symptom**

```
Missing closing ')' after expression in 'if' statement.
At line:3 char:1
```

Or the `gdr` command in the generated PowerShell script is parsed as a CMD command, producing `gdr` is not recognized.

**Root Cause**

CMD's `^` line continuation character is unreliable in multi-line PowerShell `-Command` strings. When `install.bat` tried to write a PowerShell script inline using `-Command "..."` with `^` continuation, CMD corrupted the multi-line string. The word `gdr` inside the PS script was interpreted as a CMD call.

**Fix**

Write the PowerShell script content to a **temporary `.ps1` file first**, then execute it:

```bat
REM Write PS script to temp file
(
  echo if (Get-Alias gdr -ErrorAction SilentlyContinue) { Remove-Item Alias:gdr -Force }
  echo function gdr { ^& 'C:\Users\GDR\Downloads\GDR-AI-main\run.bat' @args }
) > "%TEMP%\_gdr_profile_setup.ps1"

REM Execute temp file
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\_gdr_profile_setup.ps1"

REM Clean up
del "%TEMP%\_gdr_profile_setup.ps1"
```

> [!TIP]
> The temp-file approach avoids all CMD-vs-PowerShell escaping conflicts. Any time you need to run non-trivial PowerShell from a `.bat` file, write it to a `.ps1` first.

</details>

---

### Error 9: Microphone Recording with Very Low RMS

<details>
<summary><strong>⚠️ Symptom</strong> — <code>gdr doctor</code> shows Mic PASS but RMS is <code>0.0006</code> and voice mode doesn't respond</summary>

**Symptom**

```
Microphone  | PASS  | RMS: 0.0006 (very low — may not detect speech)
```

Voice mode starts but never responds to speech.

**Root Cause**

An RMS of `0.0006` is **ambient room noise**, not a microphone failure. The health check records audio for a fixed window — if you're not speaking during that window, the RMS is near zero. This is expected behavior, not an error.

The real issue may be:
- Microphone volume set too low in Windows
- Wrong input device selected
- Windows microphone privacy settings blocking access

**Diagnosis**

Check Windows Core Audio levels with `pycaw`:

```python
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL

devices = AudioUtilities.GetMicrophone()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = interface.QueryInterface(IAudioEndpointVolume)
print(f"Volume: {volume.GetMasterVolumeLevelScalar() * 100:.0f}%")
```

**Fix**

1. Speak into the microphone while running `gdr doctor`
2. Set mic volume to 100% in Windows Settings (see [Microphone Troubleshooting](#microphone-troubleshooting))
3. Ensure the correct device is selected

**Expected healthy output:**

```
Microphone  | PASS  | Active (Microphone (Realtek(R) Audio), 48000Hz)
```

RMS values above `0.003` during speech indicate a working microphone.

</details>

---

### Error 10: TTS Check Failing Despite edge-tts Installed

<details>
<summary><strong>❌ Symptom</strong> — <code>gdr doctor</code> shows TTS FAIL even though <code>edge-tts</code> and <code>gtts</code> are installed</summary>

**Symptom**

```
TTS  | FAIL  | No TTS engine found
```

But `pip show edge-tts` and `pip show gtts` both show installed packages.

**Root Cause**

The original `doctor.py` `check_tts()` method only looked for **binary executables**: the `piper` binary and `espeak-ng`. It did not check for Python-based TTS packages (`edge_tts`, `gtts`), which are the primary TTS engines used by GDR-AI on Windows.

**Fix**

Add Python package import checks to `check_tts()` in `gdr/doctor.py`:

```python
def check_tts(self):
    engines = []

    # Check for Python-based TTS engines
    try:
        import edge_tts
        engines.append("Edge-TTS (Neural Studio)")
    except ImportError:
        pass

    try:
        import gtts
        engines.append("gTTS")
    except ImportError:
        pass

    # Check for binary TTS engines
    import shutil
    if shutil.which("piper"):
        engines.append("Piper")
    if shutil.which("espeak-ng"):
        engines.append("eSpeak-NG")

    if engines:
        return CheckResult(
            status=Status.PASS,
            detail=f"Engines available: {', '.join(engines)}"
        )
    else:
        return CheckResult(
            status=Status.FAIL,
            detail="No TTS engine found. Install edge-tts: pip install edge-tts"
        )
```

**Expected healthy output after fix:**

```
TTS  | PASS  | Engines available: Edge-TTS (Neural Studio), gTTS
```

</details>

---

## Verifying Everything Works

After completing installation and applying any relevant fixes, run the health check:

```cmd
gdr doctor
```

**Expected output (all green):**

```
Component          | Status   | Detail
-------------------------------------------------------
Network            | PASS     | HTTPS connectivity to api.sarvam.ai verified
Sarvam API Key     | FAIL     | SARVAM_API_KEY environment variable is missing (add yours)
Anthropic Key      | WARN     | Optional: ANTHROPIC_API_KEY unset
Microphone         | PASS     | Active (Microphone (Realtek(R) Audio), 48000Hz)
Speaker            | PASS     | Speakers (Realtek(R) Audio)
TTS                | PASS     | Engines available: Edge-TTS (Neural Studio), gTTS
STT                | PASS     | Engines active: faster-whisper (local tiny)
Wake Word          | PASS     | OpenWakeWord 'hey_jarvis_v0.1' ready
Browser            | PASS     | Playwright Chromium headless ready
```

> [!NOTE]
> `Sarvam API Key | FAIL` is expected until you add your API key to `.env`. This is the only required key for core functionality.

**Add your Sarvam API key:**

```env
# .env
SARVAM_API_KEY=your_key_here
```

Then launch the dashboard:

```cmd
gdr
```

Navigate to: **http://127.0.0.1:8844**

---

## Microphone Troubleshooting

If `gdr doctor` shows `Mic FAIL` or RMS stays at `0.000x` even while speaking, follow these steps:

### Step 1 — Check Windows Privacy Settings

Windows 11 has per-app microphone privacy controls that can silently block access.

1. Open **Windows Settings** → **Privacy & security** → **Microphone**
2. Ensure **"Microphone access"** is **On**
3. Ensure **"Let apps access your microphone"** is **On**
4. Scroll down and ensure **"Let desktop apps access your microphone"** is **On**

### Step 2 — Check Input Device & Volume

1. Open **Windows Settings** → **System** → **Sound**
2. Under **Input**, select your microphone from the dropdown
3. Click on the microphone → Set **Input volume** to **100%**
4. Use the **"Test your microphone"** button — you should see the bar move when you speak

### Step 3 — Check Default Device in Sound Control Panel

Some apps use the legacy Sound Control Panel device, not the Settings app device.

1. Right-click the speaker icon in the taskbar → **Sound settings** → **More sound settings**
2. Go to the **Recording** tab
3. Right-click your microphone → **Set as Default Device**
4. Right-click your microphone → **Properties** → **Levels** → Set to **100**

### Step 4 — Check for Driver Issues

```powershell
# List audio recording devices
Get-WmiObject Win32_SoundDevice | Select-Object Name, Status
```

If your microphone shows `Status: Error`, update or reinstall the driver from Device Manager.

### Step 5 — Verify with Python Directly

```python
import sounddevice as sd
import numpy as np

duration = 3  # seconds
print("Speak now...")
recording = sd.rec(int(duration * 44100), samplerate=44100, channels=1)
sd.wait()
rms = np.sqrt(np.mean(recording**2))
print(f"RMS: {rms:.4f}")
print("OK" if rms > 0.01 else "Too quiet — check mic volume")
```

> [!TIP]
> RMS above `0.01` during normal speech indicates a healthy microphone. Values between `0.001–0.009` suggest low volume. Values below `0.001` suggest the mic is muted or blocked.

---

## Working Commands Reference

All commands verified working after a complete setup:

| Command | Description |
|---------|-------------|
| `gdr` | Launches web dashboard at http://127.0.0.1:8844 |
| `gdr --help` | Shows all available options |
| `gdr --gui` | Explicitly launches the web dashboard |
| `gdr --gui --restart` | Restarts if already running on port 8844 |
| `gdr --voice` | Starts hands-free voice mode |
| `gdr doctor` | Runs system health check |
| `gdr panic` | Emergency stop — kills all GDR-AI processes |
| `gdr setup` | Launches configuration wizard |
| `gdr tasks` | View scheduled tasks |
| `gdr mesh pair` | Pair a second device to the mesh network |

---

## Files Changed During Setup

The following files were modified to fix the errors documented above:

| File | Changes Made |
|------|-------------|
| `install.bat` | Completely rewritten: fixed f-string/curly brace parse error, added Python Launcher support, fixed PowerShell profile setup, removed `gdr.setup_interactive` call |
| `run.bat` | Added `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` before Python invocation |
| `gdr/doctor.py` | Added `edge_tts` and `gtts` import checks to `check_tts()` method |
| `.env` | Added `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` |

---

*This guide was written based on a real Windows 11 installation of GDR-AI. Every error listed here was actually encountered and resolved. If you hit a new issue not listed here, please open an issue on GitHub with the full error output.*
