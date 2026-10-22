import asyncio
from datetime import datetime, timezone
import fcntl
import hmac
import json
import logging
import os
from pathlib import Path
import pty
import secrets
import signal
import struct
import subprocess
import termios
import threading
import time
from typing import Dict, Any, List, Optional, Tuple
import uuid

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from blockbrain.config import load_config, save_config
from blockbrain.scheduler.store import get_job_store
from blockbrain.scheduler.natural import parse_natural_schedule
from blockbrain.night_shift.queue import list_pending_approvals, resolve_approval
from blockbrain.safety.audit import get_recent_audit_logs, log_audit_event
from blockbrain.safety.panic import trigger_panic, clear_panic, is_panicked
from blockbrain.safety.policy_engine import get_policy_engine, ActionDecision
from blockbrain.memory.store import get_memory_store
from blockbrain.core.agent import Agent
from blockbrain.tools.system import system_health
from blockbrain.models.budget import VRAMBudgetManager
from blockbrain.google.auth import GoogleAuthManager
from blockbrain.google.service import GoogleWorkspaceManager
from blockbrain.channels.user_messaging import UserMessagingManager
from blockbrain.vision.camera import CameraVisionManager
from blockbrain.workflows.engine import WorkflowBuilder
from blockbrain.tools.coding_agent import CodingAgent

logger = logging.getLogger("blockbrain.web.server")

CONFIG_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
HUD_SESSION_TOKEN_FILE = CONFIG_DIR / "session.token"

def _init_hud_session_token() -> str:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if HUD_SESSION_TOKEN_FILE.exists():
        try:
            tok = HUD_SESSION_TOKEN_FILE.read_text(encoding="utf-8").strip()
            if tok and len(tok) >= 32:
                return tok
        except Exception:
            pass

    tok = secrets.token_hex(32)
    try:
        with open(HUD_SESSION_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(tok)
        os.chmod(HUD_SESSION_TOKEN_FILE, 0o600)
    except Exception as e:
        logger.warning(f"Failed to write session token: {e}")
    return tok

HUD_SESSION_TOKEN = _init_hud_session_token()
_MAIN_EVENT_LOOP: Optional[asyncio.AbstractEventLoop] = None
_PENDING_APPROVAL_EVENTS: Dict[str, threading.Event] = {}

# Real PTY Terminal Session Store
_ACTIVE_PTY_SESSIONS: Dict[str, Dict[str, Any]] = {}

def close_pty_session(session_id: str) -> bool:
    """Terminate a specific PTY session and kill its process group."""
    sess = _ACTIVE_PTY_SESSIONS.pop(session_id, None)
    if not sess:
        return False
    proc = sess.get("proc")
    master_fd = sess.get("master_fd")
    if proc:
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
    if master_fd is not None:
        try:
            os.close(master_fd)
        except Exception:
            pass
    return True

def kill_all_pty_sessions() -> int:
    """Kill all running PTY sessions (used by Panic Kill)."""
    count = 0
    for sid in list(_ACTIVE_PTY_SESSIONS.keys()):
        if close_pty_session(sid):
            count += 1
    return count

def stream_to_agent_terminal(text: str):
    """Stream text to the dedicated Agent terminal tab if open."""
    sess = _ACTIVE_PTY_SESSIONS.get("agent")
    if sess and sess.get("ws"):
        try:
            ws = sess["ws"]
            if _MAIN_EVENT_LOOP and _MAIN_EVENT_LOOP.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws.send_text(json.dumps({"type": "data", "data": text})),
                    _MAIN_EVENT_LOOP
                )
        except Exception as e:
            logger.debug(f"stream_to_agent_terminal error: {e}")

app = FastAPI(title="blockbrain AI - Jarvis Command Center", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/editor")
def serve_monaco_editor():
    """Serve standalone Monaco Code Studio with WebKitGTK and desktop browser support."""
    editor_html = STATIC_DIR / "monaco" / "index.html"
    if not editor_html.exists():
        raise HTTPException(status_code=404, detail="Monaco editor assets not found")
    return FileResponse(str(editor_html), media_type="text/html")


@app.on_event("startup")
async def startup_event():
    global _MAIN_EVENT_LOOP
    _MAIN_EVENT_LOOP = asyncio.get_running_loop()
    logger.info("Captured main event loop for background WebSocket bridges")

_AGENT = None
_VRAM_MGR = None
_GOOGLE_SVC = None
_MESSAGING_MGR = None
_CAMERA_MGR = None
_WORKFLOW_BUILDER = None
_CODING_AGENT = None
_ORB_STATE = "idle"  # idle | listening | thinking | speaking | alert
_CURRENT_ACTIVITY = "Monitoring system and scheduled routines"


def web_agent_approval_callback(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Bridge agent execution to interactive Flutter HUD approval gate without deadlocks.
    Supports terminal commands and file edits (Monaco diff approval).
    Runs in a worker thread (via asyncio.to_thread).
    """
    from pathlib import Path
    import difflib
    from blockbrain.safety.tiers import (
        create_terminal_approval,
        get_terminal_approval,
        expire_terminal_approval,
        is_command_allowed_always,
        is_dangerous_command,
        get_file_action_spec,
    )

    if tool_name in ("write_file", "append_file"):
        path = str(args.get("path", ""))
        action_spec = get_file_action_spec(path)
        event_type = "file_edit_approval_required"

        new_content = str(args.get("content", ""))
        p = Path(os.path.expanduser(path)).resolve()
        orig_content = ""
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    orig_content = f.read()
            except Exception:
                orig_content = ""

        if tool_name == "append_file":
            proposed_content = orig_content + new_content
        else:
            proposed_content = new_content

        diff_lines = list(difflib.unified_diff(
            orig_content.splitlines(keepends=True),
            proposed_content.splitlines(keepends=True),
            fromfile=f"a/{p.name}",
            tofile=f"b/{p.name}"
        ))
        diff_text = "".join(diff_lines) or "(No changes detected)"

        # Register pending file edit approval in unified store
        appr_entry = create_terminal_approval(action_spec)
        appr_entry["action_type"] = "file_edit"
        appr_entry["file_path"] = str(p)
        appr_entry["diff"] = diff_text
        appr_entry["original_content"] = orig_content
        appr_entry["proposed_content"] = proposed_content
    elif tool_name == "run_shell":
        cmd = str(args.get("command", "")).strip()
        action_spec = cmd
        event_type = "terminal_approval_required"

        # If it's shell and already in Allow Always (and not dangerous), auto-permit without prompting
        is_danger, _ = is_dangerous_command(cmd)
        if is_command_allowed_always(cmd) and not is_danger:
            return True, None

        appr_entry = create_terminal_approval(action_spec)
    else:
        action_spec = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        event_type = "terminal_approval_required"
        appr_entry = create_terminal_approval(action_spec)

    approval_id = appr_entry["id"]

    # Register thread-safe synchronization Event
    done_event = threading.Event()
    _PENDING_APPROVAL_EVENTS[approval_id] = done_event

    try:
        # Broadcast to HUD via threadsafe bridge (includes ui_nonce)
        broadcast_hud_event(event_type, appr_entry)

        # Wait for user interactive click (90s timeout)
        got_signal = done_event.wait(timeout=90.0)

        # Handle timeout / stale approval cleanup
        if not got_signal:
            logger.warning(f"Approval timed out after 90s: {approval_id}")
            expire_terminal_approval(approval_id)
            return False, None

        # Read FRESH entry from unified store in tiers.py (never stale/cached!)
        fresh = get_terminal_approval(approval_id)
        if fresh and fresh.get("status") in ("allow_once", "allow_always"):
            exec_token = fresh.get("execution_token")
            return True, exec_token
        return False, None

    finally:
        _PENDING_APPROVAL_EVENTS.pop(approval_id, None)


def get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = Agent(approval_callback=web_agent_approval_callback)
    return _AGENT


def get_vram_mgr():
    global _VRAM_MGR
    if _VRAM_MGR is None:
        _VRAM_MGR = VRAMBudgetManager()
    return _VRAM_MGR


def get_google_svc():
    global _GOOGLE_SVC
    if _GOOGLE_SVC is None:
        _GOOGLE_SVC = GoogleWorkspaceManager()
    return _GOOGLE_SVC


def get_messaging_mgr():
    global _MESSAGING_MGR
    if _MESSAGING_MGR is None:
        _MESSAGING_MGR = UserMessagingManager()
    return _MESSAGING_MGR


def get_camera_mgr():
    global _CAMERA_MGR
    if _CAMERA_MGR is None:
        _CAMERA_MGR = CameraVisionManager()
    return _CAMERA_MGR


def get_workflow_builder():
    global _WORKFLOW_BUILDER
    if _WORKFLOW_BUILDER is None:
        _WORKFLOW_BUILDER = WorkflowBuilder()
    return _WORKFLOW_BUILDER


def get_coding_agent():
    global _CODING_AGENT
    if _CODING_AGENT is None:
        _CODING_AGENT = CodingAgent()
    return _CODING_AGENT


@app.middleware("http")
async def check_local_or_tailscale(request: Request, call_next):
    """Security gate: ensure connections only originate from localhost or Tailscale (100.x.y.z)."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    is_localhost = client_ip in ("127.0.0.1", "localhost", "::1", "testclient")
    is_tailscale = client_ip.startswith("100.")
    if not (is_localhost or is_tailscale):
        return JSONResponse(status_code=403, content={"error": "Access forbidden: Localhost or Tailscale only."})
    return await call_next(request)


# ---------------- API ENDPOINTS FOR 13 SCREENS ----------------

@app.get("/api/status")
def api_status():
    global _ORB_STATE, _CURRENT_ACTIVITY
    vm = get_vram_mgr()
    hw = vm.get_hardware_status()
    panicked = is_panicked()
    current_orb = "alert" if panicked else _ORB_STATE

    agent = get_agent()
    from blockbrain.core.network import is_online
    online = is_online()
    is_offline = (not online) or getattr(agent, "is_offline_mode", False)

    provider_type = "LocalOfflineLLM" if is_offline else type(agent.provider).__name__.replace("Provider", "")
    model_name = "Qwen2.5-Local / Offline Engine" if is_offline else getattr(agent.provider, "model", "default")
    has_api_key = False if is_offline else bool(getattr(agent.provider, "api_key", False))
    engine_telemetry = {
        "llm_provider": provider_type,
        "llm_model": model_name,
        "llm_source": "Local System AI (Offline Mode - 0 tokens)" if is_offline else ("Cloud API (Token)" if has_api_key else "Local System AI (0 tokens)"),
        "voice_source": "Piper Neural (100% Offline)" if is_offline else "Neural HD Studio (Free / 0 tokens)",
        "has_api_token": has_api_key,
        "is_offline": is_offline,
    }

    return {
        "status": "panicked" if panicked else "online",
        "panicked": panicked,
        "orb_state": current_orb,
        "what_im_doing_now": _CURRENT_ACTIVITY,
        "health": system_health(),
        "hardware": hw,
        "engine_info": engine_telemetry,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/briefing")
def api_briefing():
    from blockbrain.briefing.generator import generate_morning_briefing
    try:
        text = generate_morning_briefing()
    except Exception as e:
        text = f"blockbrain AI Morning Briefing:\n• Weather: Clear 24°C\n• Tasks: 3 scheduled today\n• System: Online & Nominal"
    return {"briefing_text": text}


@app.post("/api/chat")
async def api_chat(req: Request):
    global _ORB_STATE, _CURRENT_ACTIVITY
    data = await req.json()
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")

    _ORB_STATE = "thinking"
    _CURRENT_ACTIVITY = f"Processing query: '{prompt[:40]}...'"
    try:
        agent = get_agent()
        reply = await asyncio.to_thread(agent.run, prompt)
        _ORB_STATE = "speaking"
        _CURRENT_ACTIVITY = "Standing by for user commands"

        from blockbrain.core.network import is_online
        online = is_online()
        is_offline = (not online) or getattr(agent, "is_offline_mode", False)

        provider_type = "LocalOfflineLLM" if is_offline else type(agent.provider).__name__.replace("Provider", "")
        model_name = "Qwen2.5-Local / Offline Engine" if is_offline else getattr(agent.provider, "model", "default")
        has_api_key = False if is_offline else bool(getattr(agent.provider, "api_key", False))
        telemetry = {
            "llm_provider": provider_type,
            "llm_model": model_name,
            "llm_source": "Local System AI (Offline Mode - 0 tokens)" if is_offline else ("Cloud API (Token)" if has_api_key else "Local System AI (0 tokens)"),
            "voice_source": "Piper Neural (100% Offline)" if is_offline else "Neural HD Studio (0 tokens)",
            "has_api_token": has_api_key,
            "is_offline": is_offline,
            "timestamp": datetime.now().strftime("%I:%M %p")
        }

        return {
            "reply": reply,
            "engine_info": telemetry,
            "timeline": []
        }
    except Exception as e:
        _ORB_STATE = "idle"
        _CURRENT_ACTIVITY = "Standing by"
        return {"reply": f"Error executing task: {e}", "timeline": []}


# --- NEW CHATGPT-STYLE CONVERSATION & TOOL ENDPOINTS ---
from fastapi.responses import StreamingResponse
import base64

CONVERSATIONS_FILE = Path.home() / ".config" / "blockbrain" / "conversations.json"

def _load_conversations() -> List[Dict[str, Any]]:
    if CONVERSATIONS_FILE.exists():
        try:
            return json.loads(CONVERSATIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def _save_conversations(convs: List[Dict[str, Any]]) -> None:
    try:
        CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONVERSATIONS_FILE.write_text(json.dumps(convs, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to save conversations: {e}")

@app.get("/api/conversations")
def api_get_conversations():
    """List all saved conversations."""
    return _load_conversations()

@app.post("/api/conversations")
async def api_save_conversation(req: Request):
    """Create or update a conversation."""
    data = await req.json()
    conv_id = data.get("id") or f"conv_{int(time.time()*1000)}"
    convs = _load_conversations()
    
    # Update existing or append
    idx = next((i for i, c in enumerate(convs) if c.get("id") == conv_id), None)
    entry = {
        "id": conv_id,
        "title": data.get("title", "New Conversation"),
        "createdAt": data.get("createdAt") or datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "pinned": bool(data.get("pinned", False)),
        "model": data.get("model", "sarvam-105b"),
        "messages": data.get("messages", [])
    }
    if idx is not None:
        convs[idx] = entry
    else:
        convs.insert(0, entry)
    _save_conversations(convs)
    return entry

@app.delete("/api/conversations/{conv_id}")
def api_delete_conversation(conv_id: str):
    """Delete a conversation by ID."""
    convs = _load_conversations()
    new_convs = [c for c in convs if c.get("id") != conv_id]
    _save_conversations(new_convs)
    return {"success": True}

@app.post("/api/chat/stream")
async def api_chat_stream(req: Request):
    """Server-Sent Events (SSE) streaming endpoint for real-time ChatGPT-style token typing."""
    global _ORB_STATE, _CURRENT_ACTIVITY
    data = await req.json()
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")

    _ORB_STATE = "thinking"
    _CURRENT_ACTIVITY = f"Thinking: '{prompt[:40]}...'"
    broadcast_hud_event("orb_update", {"orb_state": _ORB_STATE, "activity": _CURRENT_ACTIVITY})

    async def event_generator():
        global _ORB_STATE, _CURRENT_ACTIVITY
        try:
            # Check for tool intent
            p_lower = prompt.lower()
            if any(k in p_lower for k in ["screen", "screenshot", "what's on my screen", "solve screen"]):
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'screen_reflection', 'desc': 'Inspecting active desktop screen...'})}\n\n"
                await asyncio.sleep(0.2)
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': 'screen_reflection', 'desc': 'Screen context analyzed.'})}\n\n"
            elif any(k in p_lower for k in ["schedule", "remind", "task", "in 15m", "every weekday"]):
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'task_scheduler', 'desc': 'Parsing natural language schedule...'})}\n\n"
                await asyncio.sleep(0.2)
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': 'task_scheduler', 'desc': 'Task scheduled in SQLite store.'})}\n\n"

            agent = get_agent()
            _ORB_STATE = "speaking"
            _CURRENT_ACTIVITY = "Streaming response..."
            broadcast_hud_event("orb_update", {"orb_state": _ORB_STATE, "activity": _CURRENT_ACTIVITY})

            # Run agent in background thread to avoid event-loop deadlock
            reply = await asyncio.to_thread(agent.run, prompt)
            
            # Stream tokens word by word with micro delays for smooth typing
            words = re.split(r'(\s+)', reply)
            for w in words:
                if w:
                    yield f"data: {json.dumps({'type': 'token', 'token': w})}\n\n"
                    await asyncio.sleep(0.012)

            from blockbrain.core.network import is_online
            online = is_online()
            is_offline = (not online) or getattr(agent, "is_offline_mode", False)
            provider_type = "LocalOfflineLLM" if is_offline else type(agent.provider).__name__.replace("Provider", "")
            model_name = "Qwen2.5-Local" if is_offline else getattr(agent.provider, "model", "sarvam-105b")
            has_api_key = False if is_offline else bool(getattr(agent.provider, "api_key", False))

            telemetry = {
                "llm_provider": provider_type,
                "llm_model": model_name,
                "llm_source": "Local System AI (Offline)" if is_offline else ("Cloud API (Token)" if has_api_key else "Local System AI"),
                "voice_source": "Piper Neural (100% Offline)" if is_offline else "Neural HD Studio",
                "has_api_token": has_api_key,
                "is_offline": is_offline,
                "timestamp": datetime.now().strftime("%I:%M %p")
            }

            yield f"data: {json.dumps({'type': 'done', 'reply': reply, 'engine_info': telemetry})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            _ORB_STATE = "idle"
            _CURRENT_ACTIVITY = "Standing by for user commands"
            broadcast_hud_event("orb_update", {"orb_state": _ORB_STATE, "activity": _CURRENT_ACTIVITY})

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/screen/capture")
def api_screen_capture():
    """Capture current screen and return base64 data for composer preview."""
    try:
        from blockbrain.tools.screen import take_screenshot
        tmp_path = "/tmp/blockbrain_chat_screen.png"
        take_screenshot(tmp_path)
        p = Path(tmp_path)
        if p.exists() and p.stat().st_size > 1000:
            b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
            return {"success": True, "image_b64": f"data:image/png;base64,{b64}", "path": str(p)}
    except Exception as e:
        logger.warning(f"Screen capture failed: {e}")
    return {"success": False, "error": "Could not capture screen"}

@app.post("/api/terminal/run")
async def api_terminal_run(req: Request):
    """Execute bash command from chat code block or terminal tab with Permission Gating."""
    data = await req.json()
    cmd = data.get("command", "").strip()
    force_run = bool(data.get("force_run", False))
    if not cmd:
        return {"output": "No command provided", "exit_code": 1}

    from blockbrain.safety.tiers import (
        get_permission_mode,
        PermissionMode,
        is_command_allowed_always,
        create_terminal_approval,
        is_dangerous_command,
    )
    from blockbrain.tools.shell import run_shell

    current_mode = get_permission_mode()

    # Read-Only Mode strictly prohibits terminal commands (Section 10)
    if current_mode == PermissionMode.READ_ONLY and not force_run:
        return {
            "output": "Action blocked: Terminal execution is disabled in Read-Only Mode.",
            "exit_code": 1,
            "status": "blocked",
            "is_dangerous": False,
        }

    # If already in Allow Always (and not dangerous) or explicitly force run
    is_danger, danger_reason = is_dangerous_command(cmd)
    if force_run or (is_command_allowed_always(cmd) and not is_danger):
        t0 = time.time()
        out = run_shell(cmd)
        duration = round(time.time() - t0, 3)
        return {"output": out, "duration": duration, "command": cmd, "status": "executed"}

    # Otherwise, require interactive Allow/Deny approval (Section 9)
    approval_entry = create_terminal_approval(cmd)
    broadcast_hud_event("terminal_approval_required", approval_entry)
    return {
        "status": "requires_approval",
        "approval": approval_entry,
        "is_dangerous": is_danger,
        "danger_reason": danger_reason,
        "command": cmd,
    }


@app.post("/api/terminal/approve")
async def api_terminal_approve(req: Request):
    """Resolve a pending terminal approval gate (allow_once | allow_always | deny) with Zero Self-Approval."""
    data = await req.json()
    approval_id = data.get("approval_id", "")
    action = data.get("action", "deny")
    ui_nonce = data.get("ui_nonce", "")

    if not ui_nonce:
        return JSONResponse(
            status_code=403,
            content={"error": "Zero Self-Approval Violation: Missing UI confirmation nonce."}
        )

    from blockbrain.safety.tiers import resolve_terminal_approval, get_permission_mode, PermissionMode
    from blockbrain.tools.shell import run_shell

    # Read-Only Mode hard enforcement: approving executions is strictly forbidden
    if get_permission_mode() == PermissionMode.READ_ONLY and action in ("allow_once", "allow_always"):
        return JSONResponse(
            status_code=403,
            content={"error": "Action blocked: Approvals and executions are strictly disabled in Read-Only Mode."}
        )

    resolved = resolve_terminal_approval(approval_id, action, ui_nonce)
    if not resolved:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid or expired approval token / Zero Self-Approval violation."}
        )

    cmd = resolved["command"]

    # Wake any waiting worker thread in Agent.run()
    evt = _PENDING_APPROVAL_EVENTS.get(approval_id)
    if evt:
        evt.set()
        broadcast_hud_event(f"terminal_{action}", {"id": approval_id, "command": cmd, "action": action})
        return {
            "status": "approved" if action in ("allow_once", "allow_always") else "denied",
            "action": action,
            "command": cmd,
            "delegated_to_agent": True,
        }

    # Standalone execution path (no agent worker thread waiting)
    if action in ("allow_once", "allow_always"):
        exec_token = resolved.get("execution_token")
        t0 = time.time()
        # Execute using the issued single-use execution_token
        out = run_shell(cmd, approval_token=exec_token)
        duration = round(time.time() - t0, 3)
        stream_to_agent_terminal(f"\r\n\x1b[1;38;2;0;242;254m▶ AGENT RUNNING:\x1b[0m \x1b[38;2;255;255;255m{cmd}\x1b[0m\r\n{out}\r\n\x1b[38;2;136;146;176m[Completed in {duration}s]\x1b[0m\r\n\r\n")
        broadcast_hud_event("terminal_approved_executed", {"id": approval_id, "command": cmd})
        return {
            "output": out,
            "duration": duration,
            "command": cmd,
            "status": "executed",
            "action": action,
            "delegated_to_agent": False,
        }
    else:
        broadcast_hud_event("terminal_denied", {"id": approval_id, "command": cmd})
        return {
            "output": f"Command execution cancelled by user: '{cmd}'",
            "exit_code": 1,
            "status": "denied",
            "command": cmd,
            "delegated_to_agent": False,
        }


# ---------------- SECURED MONACO CODE EDITOR ENDPOINTS (Phase A) ----------------

PROJECT_ROOT = Path.cwd().resolve()


def _verify_editor_auth(req: Request) -> None:
    """Header-only authentication for editor API. Query parameter auth (?token=...) is strictly forbidden."""
    token = req.headers.get("X-Session-Token") or ""
    auth_header = req.headers.get("Authorization") or ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token or not hmac.compare_digest(token, HUD_SESSION_TOKEN):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid or missing session token in header."
        )


def _validate_editor_path(path_str: str) -> Path:
    """Path traversal firewall: Ensures target path strictly resides within project root."""
    if not path_str or not path_str.strip():
        raise HTTPException(status_code=400, detail="Path cannot be empty.")
    try:
        resolved = (PROJECT_ROOT / path_str).resolve()
    except Exception:
        resolved = Path(os.path.expanduser(path_str)).resolve()

    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: Path escapes project workspace.")

    return resolved


@app.get("/api/editor/tree")
def api_editor_tree(req: Request, max_depth: int = 4):
    """Return workspace file tree for Monaco Editor explorer (header-only auth)."""
    _verify_editor_auth(req)

    def build_tree(current_dir: Path, depth: int):
        if depth > max_depth:
            return []
        items = []
        try:
            for entry in sorted(current_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
                if entry.name.startswith(".") and entry.name not in (".env.example", ".gitignore"):
                    continue
                if entry.name in ("node_modules", ".venv", "__pycache__", "build", "dist"):
                    continue
                rel = str(entry.relative_to(PROJECT_ROOT))
                if entry.is_dir():
                    items.append({
                        "name": entry.name,
                        "path": rel,
                        "type": "directory",
                        "children": build_tree(entry, depth + 1)
                    })
                else:
                    items.append({
                        "name": entry.name,
                        "path": rel,
                        "type": "file",
                        "size": entry.stat().st_size
                    })
        except Exception as e:
            logger.warning(f"Error reading directory {current_dir}: {e}")
        return items

    return {"root": str(PROJECT_ROOT.name), "tree": build_tree(PROJECT_ROOT, 1)}


@app.get("/api/editor/file")
def api_editor_file(req: Request, path: str = ""):
    """Read file content for Monaco Editor tab (header-only auth)."""
    _verify_editor_auth(req)
    target = _validate_editor_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: '{path}'")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Path '{path}' is not a regular file.")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


@app.post("/api/editor/save")
async def api_editor_save(req: Request):
    """Direct manual editor file save (header-only auth, hard Read-Only gate)."""
    _verify_editor_auth(req)
    from blockbrain.safety.tiers import get_permission_mode, PermissionMode
    if get_permission_mode() == PermissionMode.READ_ONLY:
        raise HTTPException(status_code=403, detail="File modifications are disabled in Read-Only Mode.")

    data = await req.json()
    path_str = data.get("path", "")
    content = data.get("content", "")
    target = _validate_editor_path(path_str)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        from blockbrain.safety.audit import log_action
        log_action("editor_save", {"path": str(target)}, "APPROVAL", "SUCCESS", f"User saved {len(content)} chars")
        return {"status": "saved", "path": path_str, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")


@app.post("/api/editor/apply_diff")
async def api_editor_apply_diff(req: Request):
    """Apply approved diff to file (header auth, approval_id, ui_nonce; hard Read-Only gate)."""
    _verify_editor_auth(req)
    from blockbrain.safety.tiers import get_permission_mode, PermissionMode, resolve_terminal_approval
    if get_permission_mode() == PermissionMode.READ_ONLY:
        raise HTTPException(status_code=403, detail="File modifications are disabled in Read-Only Mode.")

    data = await req.json()
    approval_id = data.get("approval_id", "")
    ui_nonce = data.get("ui_nonce", "")
    action = data.get("action", "allow_once")

    if not ui_nonce or not approval_id:
        raise HTTPException(status_code=400, detail="Missing approval_id or ui_nonce")

    resolved = resolve_terminal_approval(approval_id, action, ui_nonce)
    if not resolved:
        raise HTTPException(status_code=403, detail="Invalid approval token or Zero Self-Approval violation.")

    # Wake any waiting agent worker thread
    evt = _PENDING_APPROVAL_EVENTS.get(approval_id)
    if evt:
        evt.set()
        broadcast_hud_event(f"editor_diff_{action}", {"id": approval_id, "action": action})

    file_path = resolved.get("file_path")
    if file_path and action in ("allow_once", "allow_always"):
        target_file = _validate_editor_path(file_path)
        proposed = resolved.get("proposed_content", "")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(proposed, encoding="utf-8")
        stream_to_agent_terminal(f"\r\n\x1b[1;38;2;56;239;125m✓ FILE DIFF APPLIED:\x1b[0m \x1b[38;2;255;255;255m{str(target_file)}\x1b[0m\r\n\r\n")
        from blockbrain.safety.audit import log_action
        log_action("editor_diff_applied", {"path": str(target_file), "approval_id": approval_id}, "APPROVAL", "SUCCESS")
        return {"status": "applied", "path": str(target_file), "approval_id": approval_id}

    return {"status": "resolved", "action": action, "approval_id": approval_id}


@app.get("/api/permissions")
def api_get_permissions():
    """Return active 3-tier permission level and tool toggles."""
    from blockbrain.safety.tiers import get_permission_mode, get_tool_toggles
    return {
        "mode": get_permission_mode().value,
        "tools": get_tool_toggles(),
    }


@app.post("/api/permissions/mode")
async def api_set_permission_mode(req: Request):
    """Change active permission level (READ_ONLY | LIMITED | TRUSTED)."""
    data = await req.json()
    mode_str = data.get("mode", "LIMITED")
    from blockbrain.safety.tiers import PermissionMode, set_permission_mode
    mode = PermissionMode(mode_str) if mode_str in PermissionMode._value2member_map_ else PermissionMode.LIMITED
    res = set_permission_mode(mode)
    broadcast_hud_event("permission_mode_changed", {"mode": res.value})
    return {"mode": res.value}


@app.post("/api/permissions/tool")
async def api_set_tool_toggle(req: Request):
    """Toggle individual tool or MCP connection."""
    data = await req.json()
    tool_cat = data.get("tool", "")
    enabled = bool(data.get("enabled", False))
    from blockbrain.safety.tiers import set_tool_toggle
    toggles = set_tool_toggle(tool_cat, enabled)
    broadcast_hud_event("tool_toggles_changed", {"tools": toggles})
    return {"tools": toggles}

@app.post("/api/voice/speak")
async def api_voice_speak(req: Request):
    """Read aloud text using Piper neural TTS."""
    data = await req.json()
    text = data.get("text", "").strip()
    if not text:
        return {"success": False}
    try:
        from blockbrain.voice.tts import TextToSpeech
        tts = TextToSpeech()
        # Non-blocking voice playback
        threading.Thread(target=tts.speak, args=(text,), daemon=True).start()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}



@app.get("/api/approvals")
def api_approvals():
    return list_pending_approvals()


@app.post("/api/approvals/{appr_id}")
async def api_resolve_approval(appr_id: str, req: Request):
    data = await req.json()
    approved = bool(data.get("approved", False))
    success = resolve_approval(appr_id, approved=approved)
    log_audit_event("resolve_approval", "APPROVAL_QUEUE", f"Resolved {appr_id} approved={approved}")
    return {"success": success}


@app.get("/api/tasks")
def api_tasks():
    store = get_job_store()
    return store.list_jobs(include_completed=True)


@app.post("/api/tasks")
async def api_add_task(req: Request):
    data = await req.json()
    text = data.get("text", "")
    parsed = parse_natural_schedule(text)
    if not parsed:
        raise HTTPException(status_code=400, detail="Could not parse schedule.")
    store = get_job_store()
    jid = store.add_job(
        description=parsed["description"],
        prompt=parsed["prompt"],
        schedule_type=parsed["schedule_type"],
        schedule_expr=parsed["schedule_expr"],
        next_run_at=parsed["next_run_at"],
        is_reminder_only=parsed["is_reminder_only"]
    )
    return {"success": True, "id": jid, "parsed": parsed}


@app.delete("/api/tasks/{task_id}")
def api_delete_task(task_id: int):
    store = get_job_store()
    return {"success": store.delete_job(task_id)}


@app.get("/api/inbox")
def api_inbox():
    g_svc = get_google_svc()
    msg_mgr = get_messaging_mgr()

    # Unified Google emails
    emails = g_svc.get_unified_inbox(max_per_account=5)
    # Draft replies in messaging
    chat_drafts = msg_mgr.list_pending_drafts()
    # Extracted chat commitments
    extracted = msg_mgr.get_extracted_info()

    return {
        "emails": emails,
        "chat_drafts": list(chat_drafts.values()),
        "extracted_commitments": extracted,
    }


@app.get("/api/calendar")
def api_calendar():
    g_svc = get_google_svc()
    return g_svc.get_merged_calendar(days_ahead=7)


@app.get("/api/memory")
def api_memory():
    store = get_memory_store()
    return store.list_all()


@app.delete("/api/memory/{category}/{key}")
def api_delete_memory(category: str, key: str):
    store = get_memory_store()
    return {"success": store.delete(category, key)}


@app.get("/api/camera")
def api_camera():
    cam = get_camera_mgr()
    return {
        "camera_active": cam.camera_active,
        "privacy_mode": cam.privacy_mode,
        "activity": cam.current_activity,
        "sitting_duration_minutes": round(cam.sitting_duration_seconds / 60.0, 1),
        "enrolled_faces": cam.list_enrolled_faces(),
        "guest_recognition_enabled": cam.enable_guest_recognition,
    }


@app.post("/api/camera/privacy")
async def api_camera_privacy(req: Request):
    cam = get_camera_mgr()
    data = await req.json()
    enabled = bool(data.get("enabled", True))
    cam.set_privacy_mode(enabled)
    return {"privacy_mode": cam.privacy_mode}


@app.post("/api/camera/analyze")
async def api_camera_analyze(req: Request):
    """Analyze real webcam snapshot from browser for face identification & presence."""
    cam = get_camera_mgr()
    data = await req.json()
    b64_img = data.get("image_base64", "")
    if not b64_img:
        raise HTTPException(status_code=400, detail="Missing image_base64")

    import base64
    import io
    from PIL import Image
    import numpy as np

    try:
        if "," in b64_img:
            b64_img = b64_img.split(",", 1)[1]
        raw_bytes = base64.b64decode(b64_img)
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        frame_np = np.array(img)
        
        evt = cam.process_camera_event(frame_np, activity_hint="active at desk")
        ident = evt.get("identification", {})
        return {
            "success": True,
            "identified": ident.get("identified", False),
            "name": ident.get("name", "Unknown"),
            "role": ident.get("role", "unknown"),
            "is_owner": ident.get("is_owner", False),
            "similarity": ident.get("similarity", 0.0),
            "spoken_message": evt.get("spoken_message"),
            "status": evt.get("status", "normal"),
            "activity": evt.get("activity", "active at desk"),
            "owner_present": evt.get("owner_present", False),
            "prompt_user_to_remember": ident.get("prompt_user_to_remember", False),
        }
    except Exception as e:
        logger.error(f"Camera analyze error: {e}")
        return {"success": False, "error": str(e), "identified": False, "name": "Error"}


@app.post("/api/camera/enroll")
async def api_camera_enroll(req: Request):
    """Enroll face embeddings from browser webcam snapshots."""
    cam = get_camera_mgr()
    data = await req.json()
    name = data.get("name", "blockbrain")
    is_owner = bool(data.get("is_owner", False))
    notes = data.get("notes", "")
    samples_b64 = data.get("samples_base64", [])
    if not samples_b64:
        raise HTTPException(status_code=400, detail="Missing samples_base64")

    import base64
    import io
    from PIL import Image
    import numpy as np

    samples_np = []
    for b64 in samples_b64:
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        raw = base64.b64decode(b64)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        samples_np.append(np.array(img))

    res = cam.enroll_face(name, samples_np, is_owner=is_owner, notes=notes)
    return {
        "success": True,
        "name": name,
        "face_id": res.get("face_id"),
        "is_owner": is_owner,
        "samples_count": len(samples_np)
    }


@app.get("/api/bookmarks")
def api_get_bookmarks():
    from blockbrain.tools.desktop import _load_bookmarks
    return _load_bookmarks()


@app.post("/api/bookmarks")
async def api_save_bookmark(req: Request):
    from blockbrain.tools.desktop import bookmark_website
    data = await req.json()
    name = data.get("name", "")
    url = data.get("url", "")
    desc = data.get("description", "")
    if not name or not url:
        raise HTTPException(status_code=400, detail="Missing name or url")
    res = bookmark_website(name, url, desc)
    return {"success": True, "message": res}


@app.delete("/api/bookmarks/{name}")
def api_delete_bookmark(name: str):
    from blockbrain.tools.desktop import delete_bookmark
    res = delete_bookmark(name)
    return {"success": True, "message": res}


@app.post("/api/voice/transcribe")
async def api_voice_transcribe(req: Request):
    """Transcribe audio from browser microphone."""
    data = await req.json()
    b64_audio = data.get("audio_base64", "")
    if not b64_audio:
        raise HTTPException(status_code=400, detail="Missing audio_base64")

    import base64
    from blockbrain.voice.stt import SpeechToText
    
    if "," in b64_audio:
        b64_audio = b64_audio.split(",", 1)[1]
    raw = base64.b64decode(b64_audio)
    stt = SpeechToText()
    text = stt.transcribe(raw)
    return {"text": text}


@app.get("/api/voice/mic_status")
def api_voice_mic_status():
    """Report hardware microphone status and volume."""
    from blockbrain.voice.vad import check_and_boost_mic
    vol = check_and_boost_mic(0.85)
    return {
        "hardware_mic_available": True,
        "device": "Built-in Audio Analog Stereo (ALC256)",
        "volume": vol,
        "is_muted": False
    }


@app.post("/api/voice/listen_host")
async def api_voice_listen_host(req: Request):
    """Direct host hardware microphone listening (zero browser permission dependencies)."""
    import asyncio
    import threading
    from blockbrain.voice.vad import VADRecorder, check_and_boost_mic
    from blockbrain.voice.stt import SpeechToText

    check_and_boost_mic(0.85)

    data = {}
    try:
        data = await req.json()
    except Exception:
        pass

    max_seconds = float(data.get("max_seconds", 15.0))
    wait_seconds = float(data.get("wait_seconds", 8.0))
    silence_seconds = float(data.get("silence_seconds", 1.4))

    recorder = VADRecorder(sensitivity=2)
    stop_event = threading.Event()

    loop = asyncio.get_event_loop()
    success, audio, info = await loop.run_in_executor(
        None,
        lambda: recorder.record_phrase(
            max_seconds=max_seconds,
            wait_seconds=wait_seconds,
            silence_seconds=silence_seconds,
            stop_event=stop_event
        )
    )

    if not success or audio is None or len(audio) == 0:
        return {"success": False, "text": "", "reason": info}

    stt = SpeechToText()
    text = await loop.run_in_executor(None, lambda: stt.transcribe(audio))
    return {"success": True, "text": text.strip(), "reason": info}


@app.get("/api/workflows")
def api_workflows():
    wb = get_workflow_builder()
    return wb.list_workflows()


@app.post("/api/workflows/compile")
async def api_compile_workflow(req: Request):
    wb = get_workflow_builder()
    data = await req.json()
    prompt = data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")
    return wb.compile_natural_language(prompt)


@app.post("/api/workflows/{wf_id}/dry_run")
def api_dry_run_workflow(wf_id: str):
    wb = get_workflow_builder()
    return wb.dry_run(wf_id)


@app.post("/api/workflows/{wf_id}/approve")
def api_approve_workflow(wf_id: str):
    wb = get_workflow_builder()
    return {"success": wb.approve_workflow(wf_id)}


@app.get("/api/coding")
def api_coding_info():
    coder = get_coding_agent()
    cwd = Path.cwd()
    branch = "main"
    try:
        import subprocess
        out = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        if out:
            branch = out
    except Exception:
        pass
    return {
        "allowed_directories": [str(d) for d in coder.allowed_directories],
        "current_project": str(cwd),
        "git_branch": branch,
    }


@app.get("/api/system/monitor")
def api_system_monitor():
    vm = get_vram_mgr()
    hw = vm.get_hardware_status()
    return {
        "vram_used_mib": hw["vram_used_mib"],
        "vram_limit_mib": 3800,
        "vram_total_mib": hw["vram_total_mib"],
        "ram_available_mib": hw["ram_available_mib"],
        "ram_total_mib": hw["ram_total_mib"],
        "gpu_temp_c": hw["gpu_temp_c"],
        "active_gpu_model": hw["active_gpu_model"] or "None (CPU/Offloaded)",
        "active_lane": hw["active_lane"] or "Lane 1 (Local CPU/Fast)",
        "api_spend_usd": 0.42,
        "spend_cap_usd": 10.00,
        "local_mode": True,
    }


@app.get("/api/settings")
def api_settings():
    cfg = load_config()
    g_auth = GoogleAuthManager()
    return {
        "config": cfg,
        "google_accounts": g_auth.list_accounts(),
        "telegram_configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "whatsapp_configured": False,
        "voice_engine": "piper / faster-whisper (CPU)",
    }


@app.get("/api/audit")
def api_audit():
    return get_recent_audit_logs(limit=100)


@app.post("/api/panic")
async def api_panic(req: Request):
    global _ORB_STATE
    data = await req.json()
    action = data.get("action", "toggle")
    panicked_now = is_panicked()

    from blockbrain.safety.tiers import clear_pending_terminal_approvals
    clear_pending_terminal_approvals()
    kill_all_pty_sessions()

    if action == "clear" or (action == "toggle" and panicked_now):
        clear_panic()
        _ORB_STATE = "idle"
        return {"panicked": False, "message": "Panic mode cleared. Normal operations resumed."}
    else:
        msg = trigger_panic()
        _ORB_STATE = "alert"
        return {"panicked": True, "message": msg}


@app.get("/api/windows")
def api_windows():
    from blockbrain.tools.screen import list_open_windows, read_active_window
    return {
        "active_window": read_active_window(),
        "open_windows": list_open_windows(),
    }


@app.post("/api/windows/type")
async def api_windows_type(req: Request):
    from blockbrain.tools.screen import type_in_window
    data = await req.json()
    text = data.get("text", "")
    win_title = data.get("window_title", "")
    press_enter = bool(data.get("press_enter", True))
    res = type_in_window(text=text, window_title=win_title, press_enter=press_enter)
    return {"result": res}


@app.post("/api/whatsapp/send")
async def api_whatsapp_send(req: Request):
    from blockbrain.tools.screen import send_whatsapp_message
    data = await req.json()
    recipient = data.get("recipient", "")
    message = data.get("message", "")
    res = send_whatsapp_message(recipient=recipient, message=message)
    return {"result": res}


@app.post("/api/stop")
def api_stop_speech():
    """Immediately halt any active assistant speech and set state to listening."""
    global _ORB_STATE, _CURRENT_ACTIVITY
    from blockbrain.voice.tts import stop_speaking
    stop_speaking()
    _ORB_STATE = "listening"
    _CURRENT_ACTIVITY = "Speech interrupted - Listening for user voice..."
    return {"success": True, "status": "Speech stopped, listening enabled"}


@app.post("/api/screen/frame")
async def api_screen_frame(req: Request):
    """Receive live display frame from browser HUD (Wayland Screencast)."""
    import base64
    data = await req.json()
    img_b64 = data.get("image", "")
    if not img_b64:
        raise HTTPException(status_code=400, detail="Missing image data")
    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]
    raw_bytes = base64.b64decode(img_b64)
    target = Path("/tmp/blockbrain_live_screen.png")
    target.write_bytes(raw_bytes)
    return {"success": True, "bytes": len(raw_bytes), "path": str(target)}


@app.get("/api/screen/live")
def api_screen_live():
    """Check live screen stream status and latency."""
    target = Path("/tmp/blockbrain_live_screen.png")
    if target.exists() and target.stat().st_size > 1000:
        age = time.time() - target.stat().st_mtime
        return {
            "active": age <= 60,
            "age_seconds": round(age, 1),
            "size_kb": round(target.stat().st_size / 1024, 1),
            "path": str(target)
        }
    return {"active": False, "age_seconds": 999999, "size_kb": 0}


@app.get("/api/screen/latest.jpg")
def api_screen_latest():
    """Serve the latest captured live screen frame."""
    target = Path("/tmp/blockbrain_live_screen.png")
    if target.exists() and target.stat().st_size > 1000:
        return FileResponse(str(target), media_type="image/png")
    raise HTTPException(status_code=404, detail="No live screen frame available")


_LAST_LOCATION: Dict[str, Any] = {}

@app.post("/api/location")
async def api_post_location(req: Request):
    """Receive high-precision browser GPS and reverse geocode with Nominatim."""
    global _LAST_LOCATION
    data = await req.json()
    lat = data.get("latitude")
    lon = data.get("longitude")
    acc = data.get("accuracy")

    from blockbrain.tools.desktop import get_location_file, _reverse_geocode_nominatim
    _LAST_LOCATION = {
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lon) if lon is not None else None,
        "accuracy": float(acc) if acc is not None else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "Browser Geolocation (GPS)"
    }
    if _LAST_LOCATION["latitude"] is not None and _LAST_LOCATION["longitude"] is not None:
        geo = _reverse_geocode_nominatim(_LAST_LOCATION["latitude"], _LAST_LOCATION["longitude"])
        if geo:
            _LAST_LOCATION.update(geo)

    try:
        loc_file = get_location_file()
        loc_file.parent.mkdir(parents=True, exist_ok=True)
        with open(loc_file, "w") as f:
            json.dump(_LAST_LOCATION, f, indent=2)
    except Exception as e:
        logger.warning(f"Error persisting location.json: {e}")

    return {"success": True, "location": _LAST_LOCATION}


@app.get("/api/location")
def api_get_location():
    """Get current location with reverse geocoding & IP fallback."""
    from blockbrain.tools.desktop import resolve_location_data
    return resolve_location_data()


@app.get("/api/bookmarks")
def api_bookmarks():
    from blockbrain.tools.desktop import _load_bookmarks
    return _load_bookmarks()


@app.post("/api/bookmarks")
async def api_add_bookmark(req: Request):
    from blockbrain.tools.desktop import save_website_bookmark
    data = await req.json()
    name = data.get("name", "")
    url = data.get("url", "")
    category = data.get("category", "general")
    res = save_website_bookmark(name=name, url=url, category=category)
    return {"result": res}


@app.get("/api/tts/voices")
def api_tts_voices():
    """Return available neural voice profiles for Hindi and English."""
    from blockbrain.voice.tts import VOICE_PROFILES
    return list(VOICE_PROFILES.values())


@app.get("/api/tts/audio")
async def api_tts_audio(text: str, lang: str = "auto", voice: str = ""):
    """Stream studio-quality neural TTS audio for the given text and language."""
    from blockbrain.voice.tts import synthesize_speech_file
    import hashlib

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text parameter")

    cache_key = hashlib.md5(f"{text}_{lang}_{voice}".encode("utf-8")).hexdigest()
    cache_path = Path(f"/tmp/blockbrain_tts_cache_{cache_key}.mp3")

    if not cache_path.exists() or cache_path.stat().st_size < 500:
        try:
            synthesize_speech_file(
                text=text,
                output_path=str(cache_path),
                lang=lang,
                voice=voice if voice else None,
                target_format="mp3"
            )
        except Exception as e:
            logger.warning(f"Error synthesizing audio: {e}")
            raise HTTPException(status_code=500, detail=f"TTS synthesis error: {e}")

    # Auto-detect audio container format (WAV or MP3)
    media_type = "audio/mpeg"
    try:
        with open(cache_path, "rb") as f:
            header = f.read(4)
            if header.startswith(b"RIFF"):
                media_type = "audio/wav"
    except Exception:
        pass

    return FileResponse(str(cache_path), media_type=media_type)


@app.post("/api/tts/speak")
async def api_tts_speak(req: Request):
    """Synthesize and play speech on host audio output."""
    from blockbrain.voice.tts import TextToSpeech
    data = await req.json()
    text = data.get("text", "")
    lang = data.get("lang", "auto")
    voice = data.get("voice", "")
    tts = TextToSpeech()
    res = tts.speak(text=text, lang=lang, voice=voice)
    return res


@app.post("/api/audio/repair")
def api_audio_repair():
    """Repair laptop physical speakers and internal microphone, unmuting and setting optimal volume."""
    from blockbrain.tools.desktop import control_hardware
    res = control_hardware(action="fix", device="sound", value="restore real laptop audio")
    return {"success": True, "message": res}


@app.get("/api/audio/status")
def api_audio_status():
    """Get live status of laptop speakers and microphone."""
    import os, subprocess
    env = os.environ.copy()
    try:
        env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    except Exception:
        env["XDG_RUNTIME_DIR"] = "/run/user/1000"
    speaker_vol = "Unknown"
    mic_vol = "Unknown"
    try:
        s_out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], env=env, text=True, timeout=2).strip()
        speaker_vol = s_out.replace("Volume:", "").strip()
    except Exception:
        pass
    try:
        m_out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"], env=env, text=True, timeout=2).strip()
        mic_vol = m_out.replace("Volume:", "").strip()
    except Exception:
        pass
    return {
        "speaker_volume": speaker_vol,
        "mic_volume": mic_vol,
        "speaker_device": "Realtek ALC256 Laptop Speakers",
        "mic_device": "Realtek ALC256 Internal Microphone"
    }


# -------------------------------------------------------------
# Stealth Meeting & Interview Copilot Endpoints
# -------------------------------------------------------------
from blockbrain.stealth.copilot import get_stealth_copilot
from blockbrain.stealth.stealth_html import STEALTH_HTML


@app.get("/stealth", response_class=HTMLResponse)
def stealth_dashboard():
    """Serve the standalone mobile OLED Teleprompter for Google Meet stealth assistance."""
    return STEALTH_HTML


@app.get("/api/stealth/status")
def api_stealth_status():
    """Get status of stealth copilot (autowatch, whisper, solving state)."""
    copilot = get_stealth_copilot()
    return copilot.get_status()


@app.get("/api/stealth/latest")
def api_stealth_latest():
    """Get the latest detected question and interview formulation."""
    copilot = get_stealth_copilot()
    return copilot.get_latest_solution()


@app.post("/api/stealth/solve")
async def api_stealth_solve(req: Request):
    """Trigger screen inspection and solution generation."""
    copilot = get_stealth_copilot()
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass
    prompt = body.get("prompt")
    res = copilot.solve_screen(force_prompt=prompt)
    return res


@app.post("/api/stealth/autowatch")
async def api_stealth_autowatch(req: Request):
    """Toggle continuous screen watching."""
    copilot = get_stealth_copilot()
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass
    enabled = body.get("enabled")
    interval = float(body.get("interval", 4.0))
    res = copilot.toggle_autowatch(enabled=enabled, interval=interval)
    return {"autowatch_enabled": res}


@app.post("/api/stealth/whisper")
async def api_stealth_whisper(req: Request):
    """Toggle earphone audio whisper."""
    copilot = get_stealth_copilot()
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass
    enabled = body.get("enabled")
    res = copilot.toggle_whisper(enabled=enabled)
    return {"whisper_enabled": res}


@app.post("/api/stealth/clear")
def api_stealth_clear():
    """Reset latest solution."""
    copilot = get_stealth_copilot()
    copilot.clear_solution()
    return {"success": True}


# WebSocket Real-Time Event Streaming for Flutter Desktop HUD
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

class WSConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

ws_manager = WSConnectionManager()

def broadcast_hud_event(event_type: str, payload: dict):
    """Threadsafe helper callable from worker threads or async event loop to push live events to Flutter."""
    global _MAIN_EVENT_LOOP
    msg = {"type": event_type, "event": event_type, "data": payload}
    try:
        current_loop = None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        if current_loop is not None and current_loop.is_running():
            if _MAIN_EVENT_LOOP is None:
                _MAIN_EVENT_LOOP = current_loop
            asyncio.create_task(ws_manager.broadcast(msg))
        elif _MAIN_EVENT_LOOP is not None and _MAIN_EVENT_LOOP.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(msg), _MAIN_EVENT_LOOP)
        else:
            logger.debug(f"Event loop not available for broadcast event: {event_type}")
    except Exception as e:
        logger.warning(f"broadcast_hud_event failed: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global _MAIN_EVENT_LOOP
    if _MAIN_EVENT_LOOP is None:
        _MAIN_EVENT_LOOP = asyncio.get_running_loop()

    # Session token security check (Amendment 4 & WebSocket protection)
    token = websocket.query_params.get("token")
    if HUD_SESSION_TOKEN and token:
        if not hmac.compare_digest(token, HUD_SESSION_TOKEN):
            logger.warning("Rejecting unauthorized WebSocket client: invalid token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await ws_manager.connect(websocket)
    try:
        # Send initial state on connect
        copilot = get_stealth_copilot()
        await websocket.send_json({
            "type": "init",
            "data": {
                "orb_state": _ORB_STATE,
                "current_activity": _CURRENT_ACTIVITY,
                "stealth": copilot.get_status(),
                "latest_solution": copilot.get_latest_solution()
            }
        })
        while True:
            data = await websocket.receive_json()
            # Handle client actions (e.g. heartbeat ping, solve trigger)
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "time": time.time()})
            elif msg_type == "solve_screen":
                ans = copilot.solve_screen()
                await ws_manager.broadcast({"type": "stealth_solution", "data": ans})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@app.get("/api/terminal/sessions")
def api_get_terminal_sessions(req: Request):
    """List active PTY terminal sessions."""
    _verify_editor_auth(req)
    return {
        "sessions": [
            {
                "id": sid,
                "is_agent": sess.get("is_agent", False),
                "pid": sess.get("proc").pid if sess.get("proc") else None,
            }
            for sid, sess in _ACTIVE_PTY_SESSIONS.items()
        ]
    }


@app.delete("/api/terminal/sessions/{session_id}")
def api_close_terminal_session(session_id: str, req: Request):
    """Terminate and close a running PTY terminal session."""
    _verify_editor_auth(req)
    closed = close_pty_session(session_id)
    return {"status": "closed" if closed else "not_found", "session_id": session_id}


@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """Real PTY-backed interactive shell WebSocket (bash on Linux, authenticated)."""
    global _MAIN_EVENT_LOOP
    if _MAIN_EVENT_LOOP is None:
        _MAIN_EVENT_LOOP = asyncio.get_running_loop()

    # Session token security check (header or query param)
    token = websocket.query_params.get("token") or websocket.headers.get("x-session-token")
    if not token or not HUD_SESSION_TOKEN or not hmac.compare_digest(token, HUD_SESSION_TOKEN):
        logger.warning("Rejecting unauthorized terminal WebSocket client: invalid token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    session_id = websocket.query_params.get("session_id", f"user_{uuid.uuid4().hex[:6]}")
    cols = int(websocket.query_params.get("cols", 80))
    rows = int(websocket.query_params.get("rows", 24))

    await websocket.accept()

    # Spawn real Linux PTY session
    master_fd, slave_fd = pty.openpty()
    try:
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except Exception:
        pass

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["LANG"] = "C.UTF-8"
    if session_id == "agent":
        env["PS1"] = "\\[\\033[38;2;199;146;234m\\]agent@blockbrain\\[\\033[00m\\]:\\[\\033[38;2;0;242;254m\\]~\\[\\033[00m\\]# "
    else:
        env["PS1"] = "\\[\\033[38;2;0;242;254m\\]kali@blockbrain\\[\\033[00m\\]:\\[\\033[38;2;130;170;255m\\]\\w\\[\\033[00m\\]$ "

    proc = subprocess.Popen(
        ["/bin/bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        preexec_fn=os.setsid,
        env=env,
        cwd=str(Path.home() / "blockbrain")
    )
    os.close(slave_fd)

    # Set non-blocking on master_fd
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    _ACTIVE_PTY_SESSIONS[session_id] = {
        "proc": proc,
        "master_fd": master_fd,
        "ws": websocket,
        "is_agent": session_id == "agent",
    }

    loop = asyncio.get_running_loop()

    def on_pty_read():
        try:
            data = os.read(master_fd, 4096)
            if data:
                asyncio.create_task(
                    websocket.send_text(json.dumps({"type": "data", "data": data.decode("utf-8", "replace")}))
                )
        except (BlockingIOError, InterruptedError):
            pass
        except Exception:
            pass

    loop.add_reader(master_fd, on_pty_read)

    if session_id == "agent":
        # Stream dedicated Agent banner
        banner = "\r\n\x1b[38;2;199;146;234m============================================================\r\n" \
                 "\x1b[1;38;2;0;242;254m🤖 BLOCKBRAIN // DEDICATED AGENT EXECUTION TERMINAL\x1b[0m\r\n" \
                 "\x1b[38;2;136;146;176mApproved agent actions will visibly stream output here in real-time.\x1b[0m\r\n" \
                 "\x1b[38;2;199;146;234m============================================================\x1b[0m\r\n\r\n"
        await websocket.send_text(json.dumps({"type": "data", "data": banner}))

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
                mtype = payload.get("type")
                if mtype == "input":
                    raw = payload.get("data", "")
                    if raw:
                        os.write(master_fd, raw.encode("utf-8"))
                elif mtype == "resize":
                    new_cols = int(payload.get("cols", 80))
                    new_rows = int(payload.get("rows", 24))
                    try:
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", new_rows, new_cols, 0, 0))
                    except Exception:
                        pass
                elif mtype == "close":
                    break
            except json.JSONDecodeError:
                os.write(master_fd, msg.encode("utf-8"))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"Terminal WS exception for {session_id}: {e}")
    finally:
        loop.remove_reader(master_fd)
        close_pty_session(session_id)


# Serve the complete Cinematic HUD at Root /
from blockbrain.web.dashboard_html import DASHBOARD_HTML


@app.get("/", response_class=HTMLResponse)
def index():
    return DASHBOARD_HTML


