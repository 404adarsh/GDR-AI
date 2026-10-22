## What `gdr` actually is

The `gdr` command is a **symlink** in `~/.local/bin/` that points to a small wrapper script:

```bash
# ~/.local/bin/gdr
exec "$HOME/gdr-agent/.venv/bin/python" "$HOME/gdr-agent/agent.py" "$@"
```

So typing `gdr` launches `python` from the project's virtual environment (`.venv/bin/python`) and passes it the main `agent.py`.

---

## Key settings that determine how "me" (the agent) works

### 1. **Virtual environment auto-enforcement**
Around line 149 of `agent.py`:
```python
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.executable) != os.path.realpath(VENV_PYTHON):
    os.execv(VENV_PYTHON, sys.argv)
```
If `gdr` is run outside the venv (which it isn't from the symlink), it **replaces itself** with the venv Python. This is a hard security boundary — it refuses to run without the isolated venv.

### 2. **Secrets from environment variables only**
All credentials come from `os.environ.get()`, never from files. For example:
- `SARVAM_API_KEY` → SARVAM API
- `ANTHROPIC_API_KEY` → (optional) Anthropic fallback
- `EMAIL_ADDRESS` / `EMAIL_APP_PASSWORD` → Gmail IMAP/SMTP
- `GDR_SUDO_ALLOWLIST` → sudo prefix config
- `GDR_I_UNDERSTAND_ROOT_RISK` → root acceptance gate
- `GDR_ALLOW_POWER` → power action toggle

### 3. **Role / personality**
- `MODEL = "sarvam-105b"`
- `AGENT_NAME = "GDR AI"`
- `USER_NAME = "GDR"`
- Default tone: `"friendly, casual, direct"`

### 4. **Tools available (the "what I can do" list)**
The `TOOLS` dict in `agent.py` defines ~40+ capabilities:
- Shell: `run_shell`, `run_privileged`
- Browser: `browser_open`, `browser_click`, `browser_fill`, etc.
- Files: `list_directory`, `read_file`, `write_file`, etc.
- System: `system_info`, `system_health`, `processes`, `service_status/start/stop/restart`
- Media: `play_music`, `stop_music`, `volume`, `brightness`
- Power: `lock_screen` (and reboot/shutdown behind `GDR_ALLOW_POWER=1`)
- Screenshot: `screenshot`, `see_screen`
- Email: `read_email`, `send_email`
- News / RSS: `get_news`, `read_rss`
- Git, package info, YouTube search, etc.

### 5. **Sudo / admin safety gate**
`DEFAULT_SUDO_ALLOWLIST = ["systemctl restart ", "systemctl stop ", "systemctl start ", "apt update"]`

Any command-prefix not in this list is **blocked**. Even root-mode can't override the allowlist.

### 6. **No root by default**
If you type `sudo gdr`, `agent.py` checks `os.geteuid() == 0`. Unless `GDR_I_UNDERSTAND_ROOT_RISK=1` is exported, it **refuses to start** with a hard-coded error explaining prompt-injection and credential risks.

### 7. **Checkpoint / resume on Ctrl+C**
- `AUTO_RESUME = True`
- `CHECKPOINT_FILE = ~/gdr-agent/gdr_checkpoint.json`
- If you Ctrl+C mid-task, the state is saved. Run `gdr --resume` to pick up where you left off.

### 8. **Max steps & memory**
- `MAX_AGENT_STEPS = 24`
- `MEMORY_LIMIT = 30` (last 30 messages retained)
- `MAX_TOKENS_PER_STEP = 1500`

---

## What happens when you type `gdr`

| Step | What happens |
|------|-------------|
| 1. `~/.local/bin/gdr` symlink | Executed |
| 2. Wrapper runs `.venv/bin/python agent.py` | Isolated Python env |
| 3. `agent.py` starts, checks venv ownership | Hard gate enforced |
| 4. `interactive()` starts | Reads from `sys.stdin` or Tk GUI |
| 5. Your text → `sarvam-105b` → tool calls | LLM plans and calls tools |
| 6. Tools run (shell, browser, file, etc.) | Under your user (or root-if-gated) |
| 7. Response printed back to you | With personality defaults |
| 8. `Ctrl+C` → checkpoint saved | Resume with `gdr --resume` |

---

## If you want to change any of this

| Setting | Where |
|--------|-------|
| Tone / name / style | `DEFAULT_PROFILE` in `agent.py` |
| Model | `MODEL = "sarvam-105b"` in `agent.py` |
| API keys | `export SARVAM_API_KEY="..."`, etc. |
| Sudo commands | `export GDR_SUDO_ALLOWLIST="..."` |
| Allow root? | `export GDR_I_UNDERSTAND_ROOT_RISK=1` |
| Allow power? | `export GDR_ALLOW_POWER=1` |

Want me to show you your currently configured values (which env vars are set), or change any of the defaults?

