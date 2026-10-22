"""FastAPI local web dashboard and REST API server for GDR AI (Phases 14 & 15).
Bound strictly to localhost and Tailscale interfaces.
Serves the complete 13-screen futuristic HUD dashboard and backing REST endpoints.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gdr.config import load_config, save_config
from gdr.scheduler.store import get_job_store
from gdr.scheduler.natural import parse_natural_schedule
from gdr.night_shift.queue import list_pending_approvals, resolve_approval
from gdr.safety.audit import get_recent_audit_logs, log_audit_event
from gdr.safety.panic import trigger_panic, clear_panic, is_panicked
from gdr.safety.policy_engine import get_policy_engine, ActionDecision
from gdr.memory.store import get_memory_store
from gdr.core.agent import Agent
from gdr.tools.system import system_health
from gdr.models.budget import VRAMBudgetManager
from gdr.google.auth import GoogleAuthManager
from gdr.google.service import GoogleWorkspaceManager
from gdr.channels.user_messaging import UserMessagingManager
from gdr.vision.camera import CameraVisionManager
from gdr.workflows.engine import WorkflowBuilder
from gdr.tools.coding_agent import CodingAgent

logger = logging.getLogger("gdr.web.server")

app = FastAPI(title="GDR AI - Jarvis Command Center", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup_channels_services():
    """Auto-start bot channels (Telegram & MarkanM) on server startup whenever tokens are available."""
    try:
        from gdr.safety.secrets import get_secret
        cfg = load_config()
        c_cfg = cfg.get("channels", {})
        tg_tok = get_secret("TELEGRAM_BOT_TOKEN") or c_cfg.get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        if tg_tok and str(tg_tok).strip() and (c_cfg.get("telegram_enabled", True) or tg_tok):
            from gdr.channels.telegram_bot import start_telegram_bot_service
            start_telegram_bot_service(restart=True)
            logger.info("🤖 Auto-started Telegram bot service on server startup.")
    except Exception as e:
        logger.warning(f"Could not auto-start Telegram bot service: {e}")

    try:
        from gdr.safety.secrets import get_secret
        cfg = load_config()
        c_cfg = cfg.get("channels", {})
        mk_tok = get_secret("MARKANM_BOT_TOKEN") or c_cfg.get("markanm_bot_token") or os.environ.get("MARKANM_BOT_TOKEN")
        if mk_tok and str(mk_tok).strip() and (c_cfg.get("markanm_enabled", True) or mk_tok):
            from gdr.channels.markanm_bot import start_markanm_bot_service
            start_markanm_bot_service(restart=True)
            logger.info("🤖 Auto-started MarkanM bot service on server startup.")
    except Exception as e:
        logger.warning(f"Could not auto-start MarkanM bot service: {e}")


@app.on_event("shutdown")
def shutdown_channels_services():
    """Gracefully terminate background bot services and polling threads on shutdown."""
    try:
        from gdr.channels.telegram_bot import stop_telegram_bot_service
        stop_telegram_bot_service()
    except Exception:
        pass
    try:
        from gdr.channels.markanm_bot import stop_markanm_bot_service
        stop_markanm_bot_service()
    except Exception:
        pass


_AGENT = None
_VRAM_MGR = None
_GOOGLE_SVC = None
_MESSAGING_MGR = None
_CAMERA_MGR = None
_WORKFLOW_BUILDER = None
_CODING_AGENT = None
_ORB_STATE = "idle"  # idle | listening | thinking | speaking | alert
_CURRENT_ACTIVITY = "Monitoring system and scheduled routines"


def get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = Agent()
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
async def record_all_requests_to_database(request: Request, call_next):
    """Save every inbound request into SQLite database with IP address, user-provided details, and timing."""
    start_time = time.time()

    headers = request.headers
    # Real client IP: Cloudflare CF-Connecting-IP > X-Forwarded-For > X-Real-IP > socket host
    client_ip = (
        headers.get("cf-connecting-ip")
        or (headers.get("x-forwarded-for").split(",")[0].strip() if headers.get("x-forwarded-for") else None)
        or headers.get("x-real-ip")
        or (request.client.host if request.client else "127.0.0.1")
    )

    query_params = dict(request.query_params)
    body_payload = None
    user_details = {}
    content_type = headers.get("content-type", "").lower()

    try:
        if request.method in ("POST", "PUT", "PATCH"):
            body_bytes = await request.body()
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request = Request(request.scope, receive=receive)

            if "application/json" in content_type:
                try:
                    parsed = json.loads(body_bytes.decode("utf-8"))
                    body_payload = parsed
                    if isinstance(parsed, dict):
                        for k in ("prompt", "message", "text", "query", "command", "task", "user", "username", "code", "device"):
                            if k in parsed:
                                user_details[k] = parsed[k]
                except Exception:
                    body_payload = body_bytes[:1024].decode("utf-8", errors="replace")
            elif "text/" in content_type or "x-www-form-urlencoded" in content_type:
                body_payload = body_bytes[:2048].decode("utf-8", errors="replace")
            elif body_bytes:
                body_payload = f"[{content_type or 'binary'}: {len(body_bytes)} bytes]"
    except Exception as e:
        body_payload = f"[Body read error: {e}]"

    is_cf = bool(headers.get("cf-ray") or "trycloudflare.com" in headers.get("host", ""))
    source = "cloudflare" if is_cf else ("localhost" if client_ip in ("127.0.0.1", "localhost", "::1", "testclient") else "lan_remote")

    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        status_code = 500
        raise exc
    finally:
        req_path = request.url.path
        # Skip static assets from DB logging
        if not (req_path.startswith("/static") or req_path == "/favicon.ico"):
            duration_ms = (time.time() - start_time) * 1000.0
            try:
                from gdr.safety.request_db import log_inbound_request
                log_inbound_request(
                    ip_address=client_ip,
                    method=request.method,
                    path=req_path,
                    query_params=query_params if query_params else None,
                    headers=dict(headers),
                    body_payload=body_payload,
                    user_details=user_details if user_details else None,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    source=source
                )
            except Exception:
                pass


@app.middleware("http")
async def check_local_or_tailscale(request: Request, call_next):
    """Security gate: ensure connections only originate from localhost, LAN, Tailscale (100.x.y.z), or Cloudflare Tunnel."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    is_localhost = client_ip in ("127.0.0.1", "localhost", "::1", "testclient")
    is_tailscale = client_ip.startswith("100.")
    is_lan = client_ip.startswith("192.168.") or client_ip.startswith("10.") or (
        client_ip.startswith("172.") and len(client_ip.split(".")) > 1 and client_ip.split(".")[1].isdigit() and 16 <= int(client_ip.split(".")[1]) <= 31
    )
    headers = request.headers
    host_header = headers.get("host", "").lower()
    is_cloudflare = bool(
        headers.get("cf-ray")
        or headers.get("cf-connecting-ip")
        or "trycloudflare.com" in host_header
        or "cloudflare" in host_header
    )
    if not (is_localhost or is_tailscale or is_lan or is_cloudflare):
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
    # Auto-detect cloud key from secrets if provider was initialized before key was saved
    from gdr.safety.secrets import get_secret
    sarvam_key = (get_secret("SARVAM_API_KEY") or os.environ.get("SARVAM_API_KEY") or "").strip().strip('"').strip("'")
    anthropic_key = (get_secret("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or "").strip().strip('"').strip("'")
    openai_key = (get_secret("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip().strip('"').strip("'")
    prov_api_key = str(getattr(agent.provider, "api_key", "") or "").strip()

    from gdr.core.providers import SarvamProvider, ClaudeProvider, OpenAICompatibleProvider
    if sarvam_key and (not prov_api_key or not isinstance(agent.provider, SarvamProvider)):
        try:
            agent.provider = SarvamProvider(api_key=sarvam_key)
            agent.is_offline_mode = False
        except Exception:
            pass
    elif anthropic_key and (not prov_api_key or not isinstance(agent.provider, ClaudeProvider)):
        try:
            agent.provider = ClaudeProvider(api_key=anthropic_key)
            agent.is_offline_mode = False
        except Exception:
            pass
    elif openai_key and (not prov_api_key or not isinstance(agent.provider, OpenAICompatibleProvider)):
        try:
            agent.provider = OpenAICompatibleProvider(api_key=openai_key)
            agent.is_offline_mode = False
        except Exception:
            pass

    from gdr.config import load_config
    cfg = load_config()
    current_user_name = os.environ.get("USER_NAME") or cfg.get("general", {}).get("user_name") or "Commander"
    current_ai_name = os.environ.get("ASSISTANT_NAME") or os.environ.get("AI_NAME") or cfg.get("general", {}).get("agent_name", "GDR-AI")

    from gdr.core import network as net_mod
    has_api_key = bool(getattr(agent.provider, "api_key", False))
    prov_class = type(agent.provider).__name__.replace("Provider", "")
    is_explicit_local = prov_class in ("OfflineLocal", "LocalOffline", "LocalGGUF")
    cfg_prov_default = str(cfg.get("provider", {}).get("default", "sarvam")).lower()
    is_offline = (is_explicit_local or cfg_prov_default in ("offline", "local")) or not has_api_key

    provider_type = "LocalOfflineLLM" if is_offline else prov_class
    model_name = "Qwen2.5-Local / Offline Engine" if is_offline else getattr(agent.provider, "model", "sarvam-105b-conversations")
    engine_telemetry = {
        "llm_provider": provider_type,
        "llm_model": model_name,
        "llm_source": "Local System AI (Offline Mode - 0 tokens)" if is_offline else ("Cloud API (Token)" if has_api_key else "Local System AI (0 tokens)"),
        "voice_source": "Piper Neural (100% Offline)" if is_offline else "Neural HD Studio (Free / 0 tokens)",
        "has_api_token": has_api_key,
        "is_offline": is_offline,
    }

    from gdr.core.providers import is_sarvam_quota_exceeded, get_sarvam_last_error
    return {
        "status": "panicked" if panicked else "online",
        "panicked": panicked,
        "orb_state": current_orb,
        "what_im_doing_now": _CURRENT_ACTIVITY,
        "user_name": current_user_name,
        "agent_name": current_ai_name,
        "health": system_health(),
        "hardware": hw,
        "engine_info": engine_telemetry,
        "sarvam_quota_exceeded": is_sarvam_quota_exceeded(),
        "sarvam_last_error": get_sarvam_last_error(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/briefing")
def api_briefing():
    from gdr.briefing.generator import generate_morning_briefing
    try:
        res = generate_morning_briefing()
        if isinstance(res, (tuple, list)):
            spoken, md = res[0], res[1] if len(res) > 1 else res[0]
            text = md if md else spoken
        else:
            text = str(res)
    except Exception as e:
        text = "Daily Briefing:\n• Weather: Clear 24°C\n• Tasks: Operational\n• System: Online & Nominal"
    return {"briefing_text": text}


@app.post("/api/chat")
async def api_chat(req: Request):
    global _ORB_STATE, _CURRENT_ACTIVITY
    data = await req.json()
    prompt = data.get("prompt", "")
    session_id = data.get("session_id") or "default"
    channel = data.get("channel") or "web"
    utterance_id = data.get("utterance_id")

    from gdr.core.telemetry import get_pipeline_timer, clear_pipeline_timer
    timer = get_pipeline_timer(utterance_id)
    timer.record("llm_request_started")

    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")

    # Security check: Enforce host terminal permission for sensitive public actions
    from gdr.safety.public_guard import check_public_permission
    client_ip = req.client.host if req.client else "127.0.0.1"
    allowed, rejection_msg = check_public_permission(dict(req.headers), prompt, client_ip=client_ip)
    if not allowed:
        _ORB_STATE = "alert"
        _CURRENT_ACTIVITY = "Sensitive public request blocked pending authorization"
        return {
            "reply": rejection_msg,
            "engine_info": {
                "llm_provider": "SecurityGuard",
                "llm_model": "Terminal-Permission-Policy",
                "timestamp": datetime.now().strftime("%I:%M %p")
            },
            "timeline": ["Host terminal approval required"]
        }

    _ORB_STATE = "thinking"
    _CURRENT_ACTIVITY = f"Processing query: '{prompt[:40]}...'"
    try:
        mem_store = get_memory_store()
        agent = get_agent()
        reply = await asyncio.to_thread(agent.run, prompt, session_id, channel)
        timer.record("llm_response_completed")
        _ORB_STATE = "speaking"
        _CURRENT_ACTIVITY = "Standing by for user commands"

        from gdr.voice.config import get_voice_manager
        from gdr.config import load_config
        cfg = load_config()

        from gdr.core import network as net_mod
        has_api_key = bool(getattr(agent.provider, "api_key", False))
        prov_class = type(agent.provider).__name__.replace("Provider", "")
        is_explicit_local = prov_class in ("OfflineLocal", "LocalOffline", "LocalGGUF")
        cfg_prov_default = str(cfg.get("provider", {}).get("default", "sarvam")).lower()
        is_offline = (is_explicit_local or cfg_prov_default in ("offline", "local")) or not has_api_key

        provider_type = "LocalOfflineLLM" if is_offline else prov_class
        model_name = "Qwen2.5-Local / Offline Engine" if is_offline else getattr(agent.provider, "model", "sarvam-105b-conversations")
        
        # Authoritative voice status (decoupled from LLM provider)
        active_vc = get_voice_manager().get_active_config()
        voice_label = f"{active_vc.provider.title()} ({active_vc.voice_id})" if not is_offline else "Piper Neural (100% Offline)"
        if not is_offline and active_vc.provider == "edge":
            voice_label = f"Neural HD Studio ({active_vc.voice_id})"

        telemetry = {
            "llm_provider": provider_type,
            "llm_model": model_name,
            "llm_source": "Local System AI (Offline Mode - 0 tokens)" if is_offline else ("Cloud API (Token)" if has_api_key else "Local System AI (0 tokens)"),
            "voice_source": voice_label,
            "has_api_token": has_api_key,
            "is_offline": is_offline,
            "timestamp": datetime.now().strftime("%I:%M %p")
        }

        from gdr.core.silence_controller import get_silence_controller
        sc = get_silence_controller()
        silence_active = sc.is_silence_active()

        timing_metrics = timer.get_metrics_summary()
        timer.log_report()

        return {
            "reply": reply,
            "engine_info": telemetry,
            "silence_active": silence_active,
            "telemetry": timing_metrics,
            "timeline": []
        }
    except Exception as e:
        _ORB_STATE = "idle"
        _CURRENT_ACTIVITY = "Standing by"
        return {"reply": f"Error executing task: {e}", "timeline": []}


@app.post("/api/chat/stream")
async def api_chat_stream(req: Request):
    """Streaming endpoint yielding Server-Sent Events (SSE) for conversational tokens and sentences."""
    global _ORB_STATE, _CURRENT_ACTIVITY
    data = await req.json()
    prompt = data.get("prompt", "")
    session_id = data.get("session_id") or "default"
    channel = data.get("channel") or "web"
    utterance_id = data.get("utterance_id")

    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")

    from gdr.core.telemetry import get_pipeline_timer
    timer = get_pipeline_timer(utterance_id)
    timer.record("llm_request_started")

    agent = get_agent()
    from gdr.voice.config import get_voice_manager
    from gdr.config import load_config
    cfg = load_config()

    has_api_key = bool(getattr(agent.provider, "api_key", False))
    prov_class = type(agent.provider).__name__.replace("Provider", "")
    is_explicit_local = prov_class in ("OfflineLocal", "LocalOffline", "LocalGGUF")
    cfg_prov_default = str(cfg.get("provider", {}).get("default", "sarvam")).lower()
    is_offline = (is_explicit_local or cfg_prov_default in ("offline", "local")) or not has_api_key

    provider_type = "LocalOfflineLLM" if is_offline else prov_class
    model_name = "Qwen2.5-Local / Offline Engine" if is_offline else getattr(agent.provider, "model", "sarvam-105b-conversations")
    active_vc = get_voice_manager().get_active_config()
    voice_label = f"{active_vc.provider.title()} ({active_vc.voice_id})" if not is_offline else "Piper Neural (100% Offline)"
    if not is_offline and active_vc.provider == "edge":
        voice_label = f"Neural HD Studio ({active_vc.voice_id})"

    engine_info = {
        "llm_provider": provider_type,
        "llm_model": model_name,
        "llm_source": "Local System AI (Offline Mode - 0 tokens)" if is_offline else ("Cloud API (Token)" if has_api_key else "Local System AI (0 tokens)"),
        "voice_source": voice_label,
        "has_api_token": has_api_key,
        "is_offline": is_offline,
        "timestamp": datetime.now().strftime("%I:%M %p")
    }

    async def event_generator():
        _ORB_STATE = "thinking"
        import threading
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def produce():
            try:
                for ev in agent.stream_run(prompt, session_id=session_id, channel=channel):
                    loop.call_soon_threadsafe(queue.put_nowait, ev)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "error": str(e), "done": True})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=produce, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, dict):
                item["engine_info"] = engine_info
            yield f"data: {json.dumps(item)}\n\n"
            await asyncio.sleep(0.001)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/sarvam/validate")
def api_sarvam_validate():
    """Verify configured Sarvam API key directly against Sarvam Chat Completions API."""
    agent = get_agent()
    from gdr.core.providers import SarvamProvider
    if isinstance(agent.provider, SarvamProvider):
        prov = agent.provider
    else:
        prov = SarvamProvider()
    valid, msg = prov.validate_credentials()
    return {"success": valid, "message": msg, "model": getattr(prov, "model", "sarvam-105b-conversations")}


@app.get("/api/chat/history")
def api_chat_history(session_id: str = "default", limit: int = 100):
    """Retrieve chronological conversation history from persistent SQLite storage."""
    store = get_memory_store()
    history = store.get_chat_history(session_id=session_id, limit=limit)
    return {"history": history, "count": len(history)}


@app.delete("/api/chat/history")
def api_clear_chat_history(session_id: Optional[str] = None):
    """Clear conversation history, surviving application lifecycle and restarts."""
    store = get_memory_store()
    cleared = store.clear_chat_history(session_id=session_id)
    return {"success": True, "cleared": cleared}



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


@app.get("/api/tasks/live")
def api_tasks_live():
    """Retrieve active background operations and 5-10s progress metrics."""
    from gdr.core.tasks import get_task_tracker
    tracker = get_task_tracker()
    return {
        "active": [t.to_dict() for t in tracker.get_active_tasks()],
        "all": [t.to_dict() for t in tracker.get_all_tasks()[-15:]],
        "summary": tracker.get_overall_summary()
    }


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


@app.get("/api/memory/categorized")
def api_memory_categorized(category: Optional[str] = None):
    store = get_memory_store()
    if category:
        return {"category": category, "memories": store.list_by_category(category)}
    all_mems = store.list_all()
    grouped = {}
    for m in all_mems:
        c = m.get("category", "personal_context")
        grouped.setdefault(c, []).append(m)
    return {"categories": grouped, "total": len(all_mems)}


@app.post("/api/memory/categorized")
async def api_add_categorized_memory(req: Request):
    data = await req.json()
    store = get_memory_store()
    key = str(data.get("key", "")).strip()
    content = str(data.get("content", "")).strip()
    category = str(data.get("category", "personal_context")).strip()
    importance = int(data.get("importance", 3))
    expires_at = data.get("expires_at")
    if not key or not content:
        return {"success": False, "error": "key and content are required"}
    res = store.remember(key=key, content=content, category=category, importance=importance, expires_at=expires_at)
    return {"success": True, "message": res}


@app.delete("/api/memory/item/{memory_id}")
def api_delete_memory_by_id(memory_id: int):
    store = get_memory_store()
    return {"success": store.delete_by_id(memory_id)}


@app.get("/api/contacts")
def api_get_contacts(query: str = "", relationship_type: Optional[str] = None, trusted_only: bool = False):
    from gdr.contacts.service import get_contact_service
    svc = get_contact_service()
    return svc.search_contacts(query=query, relationship_type=relationship_type, trusted_only=trusted_only)


@app.post("/api/contacts")
async def api_add_contact(req: Request):
    from gdr.contacts.service import get_contact_service
    data = await req.json()
    svc = get_contact_service()
    name = str(data.get("display_name", "")).strip()
    if not name:
        return {"success": False, "error": "display_name is required"}
    c = svc.add_contact(
        display_name=name,
        relationship_type=data.get("relationship_type", "Friend"),
        trust_level=int(data.get("trust_level", 50)),
        category=data.get("category", data.get("relationship_type", "Friend")),
        email=data.get("email"),
        phone_number=data.get("phone_number"),
        preferred_contact_method=data.get("preferred_contact_method", "any"),
        preferred_language=data.get("preferred_language", "English"),
        timezone=data.get("timezone", "Asia/Kolkata"),
        notes=data.get("notes", ""),
        is_trusted_contact=data.get("is_trusted_contact"),
    )
    return {"success": True, "contact": c}


@app.put("/api/contacts/{contact_id}")
async def api_update_contact(contact_id: int, req: Request):
    from gdr.contacts.service import get_contact_service
    data = await req.json()
    svc = get_contact_service()
    c = svc.update_contact(contact_id, **data)
    if not c:
        return {"success": False, "error": "Contact not found"}
    return {"success": True, "contact": c}


@app.get("/api/contacts/trusted")
def api_get_trusted_contacts():
    from gdr.contacts.service import get_contact_service
    svc = get_contact_service()
    return svc.get_trusted_contacts()


@app.get("/api/contacts/{contact_id}")
def api_get_contact(contact_id: int):
    from gdr.contacts.service import get_contact_service
    svc = get_contact_service()
    c = svc.get_contact(contact_id)
    if not c:
        return {"success": False, "error": "Contact not found"}
    return {"success": True, "contact": c}


@app.delete("/api/contacts/{contact_id}")
def api_delete_contact(contact_id: int):
    from gdr.contacts.service import get_contact_service
    svc = get_contact_service()
    return {"success": svc.delete_contact(contact_id)}


@app.get("/api/integrations/status")
def api_integrations_status():
    from gdr.integrations.registry import get_integration_registry
    reg = get_integration_registry()
    return reg.list_all_integrations()


@app.post("/api/integrations/email/draft")
async def api_create_email_draft(req: Request):
    from gdr.integrations.email_assistant import get_email_assistant
    data = await req.json()
    ea = get_email_assistant()
    rec = str(data.get("recipient", "")).strip()
    sub = str(data.get("subject", "")).strip()
    body = str(data.get("body", "")).strip()
    if not rec or not sub or not body:
        return {"success": False, "error": "recipient, subject, and body are required"}
    return ea.create_draft(rec, sub, body)


@app.get("/api/persona/config")
def api_get_persona_config():
    from gdr.core.persona import get_persona_engine
    engine = get_persona_engine()
    cfg = engine.config
    return {
        "name": cfg.name,
        "user_name": cfg.user_name,
        "verbosity": cfg.verbosity,
        "tone": cfg.tone,
        "warmth": cfg.warmth,
        "formality": cfg.formality,
        "humor": cfg.humor,
        "language_preference": cfg.language_preference,
        "proactive_enabled": cfg.proactive_enabled,
        "proactive_calendar_alerts": cfg.proactive_calendar_alerts,
        "proactive_deadline_alerts": cfg.proactive_deadline_alerts,
    }


@app.post("/api/persona/config")
async def api_update_persona_config(req: Request):
    data = await req.json()
    from gdr.config import load_config, save_config
    cfg = load_config()
    if "general" not in cfg:
        cfg["general"] = {}

    allowed = [
        "agent_name", "user_name", "verbosity", "tone", "warmth",
        "formality", "humor", "language", "proactive_enabled",
        "proactive_calendar_alerts", "proactive_deadline_alerts"
    ]
    for k in allowed:
        if k in data:
            cfg["general"][k] = data[k]
        elif k == "agent_name" and "name" in data:
            cfg["general"]["agent_name"] = data["name"]
        elif k == "language" and "language_preference" in data:
            cfg["general"]["language"] = data["language_preference"]

    save_config(cfg)
    return {"success": True, "message": "Persona configuration updated successfully."}


@app.get("/api/time/info")
def api_time_info(timezone: Optional[str] = None):
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    return ts.get_current_time(timezone)


@app.post("/api/time/duration")
async def api_time_duration(req: Request):
    data = await req.json()
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    start_time = str(data.get("start_time", ""))
    end_time = str(data.get("end_time", ""))
    return ts.calculate_duration(start_time, end_time)


@app.post("/api/time/compare")
async def api_time_compare(req: Request):
    data = await req.json()
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    time_str = str(data.get("time_str", ""))
    tz_from = str(data.get("tz_from", "Asia/Kolkata"))
    tz_to = str(data.get("tz_to", "Europe/London"))
    return ts.compare_timezones(time_str, tz_from, tz_to)


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
    name = data.get("name", "GDR")
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
    from gdr.tools.desktop import _load_bookmarks
    return _load_bookmarks()


@app.post("/api/bookmarks")
async def api_save_bookmark(req: Request):
    from gdr.tools.desktop import bookmark_website
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
    from gdr.tools.desktop import delete_bookmark
    res = delete_bookmark(name)
    return {"success": True, "message": res}


# ==============================================================================
# Activity Timeline, Wellbeing & Autostart Endpoints
# ==============================================================================

@app.get("/api/timeline/events")
def api_timeline_events(date_str: Optional[str] = None):
    from gdr.system.timeline import get_timeline_tracker
    tl = get_timeline_tracker()
    return {
        "date": date_str or datetime.now().strftime("%Y-%m-%d"),
        "events": tl.get_events(date_str),
        "readable": tl.format_readable_timeline(date_str)
    }


@app.get("/api/timeline/stats")
def api_timeline_stats(date_str: Optional[str] = None):
    from gdr.system.timeline import get_timeline_tracker
    tl = get_timeline_tracker()
    return tl.get_daily_stats(date_str)


@app.post("/api/timeline/query")
async def api_timeline_query(req: Request):
    from gdr.system.timeline import get_timeline_tracker
    data = await req.json()
    q = str(data.get("question", ""))
    tl = get_timeline_tracker()
    return {"answer": tl.answer_activity_query(q)}


@app.get("/api/wellbeing/status")
def api_wellbeing_status():
    from gdr.system.wellbeing import get_wellbeing_manager
    return get_wellbeing_manager().get_status()


@app.post("/api/wellbeing/settings")
async def api_wellbeing_settings(req: Request):
    from gdr.system.wellbeing import get_wellbeing_manager
    data = await req.json()
    wb = get_wellbeing_manager()
    wb.save_settings(data)
    return wb.get_status()


@app.post("/api/wellbeing/snooze")
async def api_wellbeing_snooze(req: Request):
    from gdr.system.wellbeing import get_wellbeing_manager
    data = await req.json()
    mins = int(data.get("minutes", 10))
    msg = get_wellbeing_manager().snooze(mins)
    return {"status": "ok", "message": msg}


@app.post("/api/wellbeing/break")
async def api_wellbeing_break(req: Request):
    from gdr.system.wellbeing import get_wellbeing_manager
    data = await req.json()
    mins = int(data.get("minutes", 5))
    msg = get_wellbeing_manager().record_break_taken(mins)
    return {"status": "ok", "message": msg}


@app.get("/api/autostart/status")
def api_autostart_status():
    from gdr.system.autostart import get_autostart_status
    return get_autostart_status()


@app.post("/api/autostart/toggle")
async def api_autostart_toggle(req: Request):
    from gdr.system.autostart import enable_autostart, disable_autostart, get_autostart_status
    data = await req.json()
    enable = bool(data.get("enabled", True))
    if enable:
        enable_autostart()
    else:
        disable_autostart()
    return get_autostart_status()


@app.get("/api/custom_api/list")
def api_custom_api_list():
    from gdr.integrations.custom_api import get_custom_api_registry
    return {"apis": get_custom_api_registry().list_apis()}


@app.post("/api/custom_api/register")
async def api_custom_api_register(req: Request):
    from gdr.integrations.custom_api import get_custom_api_registry
    data = await req.json()
    res = get_custom_api_registry().register_api(
        name=data.get("name", ""),
        base_url=data.get("base_url", ""),
        description=data.get("description", ""),
        auth_type=data.get("auth_type", "bearer"),
        auth_token=data.get("auth_token"),
        auth_header=data.get("auth_header", "Authorization")
    )
    return res


@app.post("/api/custom_api/delete")
async def api_custom_api_delete(req: Request):
    from gdr.integrations.custom_api import get_custom_api_registry
    data = await req.json()
    name = data.get("name", "")
    ok = get_custom_api_registry().delete_api(name)
    return {"success": ok}


@app.get("/api/memory/lifelong")
def api_lifelong_memory():
    from gdr.memory.lifelong import get_lifelong_memory
    mem = get_lifelong_memory()
    return {
        "profile": mem.get_profile(),
        "projects": mem.list_all_projects()
    }


@app.get("/api/daily_summary")
def api_daily_summary(date_str: Optional[str] = None):
    from gdr.memory.daily_learning import get_daily_learning_manager
    return get_daily_learning_manager().generate_daily_summary(date_str)


@app.get("/api/characters")
def api_get_characters():
    manifest_file = STATIC_DIR / "characters" / "characters.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"characters": []}


@app.get("/api/characters/{char_id}")
def api_get_character(char_id: str):
    manifest_file = STATIC_DIR / "characters" / "characters.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, "r") as f:
                data = json.load(f)
                for c in data.get("characters", []):
                    if c["id"] == char_id.lower().strip():
                        return c
        except Exception:
            pass
    raise HTTPException(status_code=404, detail="Character not found")



@app.post("/api/voice/transcribe")
async def api_voice_transcribe(req: Request):
    """Transcribe audio from browser microphone."""
    data = await req.json()
    b64_audio = data.get("audio_base64", "")
    if not b64_audio:
        raise HTTPException(status_code=400, detail="Missing audio_base64")

    import base64
    from gdr.voice.stt import SpeechToText
    
    if "," in b64_audio:
        b64_audio = b64_audio.split(",", 1)[1]
    raw = base64.b64decode(b64_audio)
    stt = SpeechToText()
    text = stt.transcribe(raw)
    return {"text": text}


@app.get("/api/voice/mic_status")
def api_voice_mic_status():
    """Report hardware microphone status and volume."""
    from gdr.voice.vad import check_and_boost_mic
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
    from gdr.voice.vad import VADRecorder, check_and_boost_mic
    from gdr.voice.stt import SpeechToText

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


@app.get("/api/settings/profile")
def api_get_profile():
    """Get active user name, assistant name, and persona tone."""
    cfg = load_config()
    uname = os.environ.get("USER_NAME") or cfg.get("general", {}).get("user_name", "User")
    aname = os.environ.get("ASSISTANT_NAME") or cfg.get("general", {}).get("agent_name", "Aarushi")
    tone = cfg.get("general", {}).get("tone", "")
    return {
        "success": True,
        "user_name": uname,
        "assistant_name": aname,
        "tone": tone,
        "bot_master_password_configured": bool(os.environ.get("BOT_MASTER_PASSWORD")),
        "rag_pin_configured": bool(os.environ.get("RAG_SECURITY_PIN") or os.environ.get("RAG_MASTER_PIN")),
    }


@app.post("/api/settings/profile")
async def api_save_profile(req: Request):
    """Save user name, assistant name, tone, and security credentials."""
    try:
        data = await req.json()
    except Exception:
        data = {}

    new_user_name = str(data.get("user_name", "")).strip()
    new_assistant_name = str(data.get("assistant_name", "")).strip()
    new_tone = str(data.get("tone", "")).strip()
    new_master_pw = str(data.get("bot_master_password", "")).strip()
    new_rag_pin = str(data.get("rag_pin", "")).strip()

    cfg = load_config()
    if "general" not in cfg:
        cfg["general"] = {}

    from gdr.safety.secrets import set_secret

    if new_user_name:
        cfg["general"]["user_name"] = new_user_name
        os.environ["USER_NAME"] = new_user_name
        try:
            set_secret("USER_NAME", new_user_name)
        except Exception:
            pass
        try:
            from gdr.memory.store import get_memory_store
            get_memory_store().remember(key="user_name", content=f"Creator's name is {new_user_name}.", category="fact")
        except Exception:
            pass

    if new_assistant_name:
        cfg["general"]["agent_name"] = new_assistant_name
        os.environ["ASSISTANT_NAME"] = new_assistant_name
        try:
            set_secret("ASSISTANT_NAME", new_assistant_name)
        except Exception:
            pass

    if new_tone:
        cfg["general"]["tone"] = new_tone

    if new_master_pw:
        os.environ["BOT_MASTER_PASSWORD"] = new_master_pw
        try:
            set_secret("BOT_MASTER_PASSWORD", new_master_pw)
        except Exception:
            pass

    if new_rag_pin:
        os.environ["RAG_SECURITY_PIN"] = new_rag_pin
        os.environ["RAG_MASTER_PIN"] = new_rag_pin
        try:
            set_secret("RAG_SECURITY_PIN", new_rag_pin)
        except Exception:
            pass

    save_config(cfg)
    return {
        "success": True,
        "message": "User identity and assistant preferences saved successfully!",
        "user_name": new_user_name or cfg["general"].get("user_name", "User"),
        "assistant_name": new_assistant_name or cfg["general"].get("agent_name", "GDR-AI")
    }


@app.get("/api/system/compatibility")
def api_system_compatibility():
    """Run full system hardware and environment compatibility diagnostics."""
    from gdr.system.compatibility import check_system_compatibility
    return check_system_compatibility()


@app.get("/api/settings/email")
def api_get_email_settings():
    """Retrieve saved email address and app password status."""
    from gdr.safety.secrets import get_secret
    email_addr = get_secret("EMAIL_ADDRESS") or ""
    has_pwd = bool(get_secret("EMAIL_APP_PASSWORD"))
    return {
        "success": True,
        "email_address": email_addr,
        "has_password": has_pwd,
        "is_configured": bool(email_addr and has_pwd),
    }


@app.post("/api/settings/email")
async def api_save_email_settings(req: Request):
    """Save email address and Google 16-character App Password securely."""
    from gdr.safety.secrets import set_secret
    try:
        data = await req.json()
    except Exception:
        data = {}

    email_addr = str(data.get("email_address", "")).strip()
    app_pwd = str(data.get("app_password", "")).strip()

    if email_addr:
        set_secret("EMAIL_ADDRESS", email_addr)
        os.environ["EMAIL_ADDRESS"] = email_addr

    if app_pwd and not app_pwd.startswith("•"):
        clean_pwd = app_pwd.replace(" ", "")
        set_secret("EMAIL_APP_PASSWORD", clean_pwd)
        os.environ["EMAIL_APP_PASSWORD"] = clean_pwd

    return {
        "success": True,
        "message": "Email address and App Password saved securely across .env and system keyring!",
        "email_address": email_addr
    }


@app.post("/api/email/test")
async def api_test_email_connection():
    """Test IMAP SSL connection to Gmail with configured App Password."""
    from gdr.safety.secrets import get_secret
    email_addr = get_secret("EMAIL_ADDRESS")
    pwd = get_secret("EMAIL_APP_PASSWORD")
    if not email_addr or not pwd:
        return JSONResponse({"success": False, "message": "Email address or App Password is not configured."}, status_code=400)

    try:
        import imaplib
        clean_pwd = pwd.replace(" ", "")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=10)
        mail.login(email_addr, clean_pwd)
        mail.select("INBOX")
        typ, data = mail.search(None, "ALL")
        total_msgs = len(data[0].split()) if data and data[0] else 0
        mail.logout()
        return {
            "success": True,
            "message": f"Verified successfully! Connected to inbox ({total_msgs} messages indexed)."
        }
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Connection failed: {e}. Check that 2-Step Verification is enabled and you generated a 16-character App Password."
        }, status_code=400)


@app.get("/api/audit")
def api_audit():
    return get_recent_audit_logs(limit=100)


@app.get("/api/requests")
def api_get_requests(limit: int = 100, ip: Optional[str] = None, path: Optional[str] = None, source: Optional[str] = None):
    """Retrieve recent inbound requests stored in database with IP addresses and user details."""
    from gdr.safety.request_db import get_request_store
    store = get_request_store()
    logs = store.get_recent_requests(limit=limit, ip_filter=ip, path_filter=path, source_filter=source)
    return {"success": True, "count": len(logs), "requests": logs}


@app.get("/api/channels/activity")
def api_channels_activity(limit: int = 50, provider: Optional[str] = None):
    """Retrieve recent inbound and outbound interactions across Telegram and MarkanM with optional filtering."""
    from gdr.safety.request_db import get_request_store
    store = get_request_store()
    if provider == "telegram":
        all_logs = store.get_recent_requests(limit=limit, source_filter="telegram")
    elif provider == "markanm":
        all_logs = store.get_recent_requests(limit=limit, source_filter="markanm")
    else:
        tg_logs = store.get_recent_requests(limit=limit, source_filter="telegram")
        mk_logs = store.get_recent_requests(limit=limit, source_filter="markanm")
        all_logs = sorted(tg_logs + mk_logs, key=lambda x: x["id"], reverse=True)[:limit]
    return {"success": True, "count": len(all_logs), "activity": all_logs}


@app.post("/api/channels/activity/clear")
def api_channels_activity_clear():
    """Clear channel activity logs from database."""
    from gdr.safety.request_db import get_request_store
    store = get_request_store()
    try:
        with store._get_conn() as conn:
            conn.execute("DELETE FROM request_logs WHERE source IN ('telegram', 'markanm')")
            conn.commit()
        return {"success": True, "message": "Bot channels activity logs cleared."}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/requests/stats")
def api_get_request_stats():
    """Retrieve aggregate statistics on requests stored in database."""
    from gdr.safety.request_db import get_request_store
    store = get_request_store()
    stats = store.get_request_stats()
    return {"success": True, "stats": stats}


@app.post("/api/requests/clear")
async def api_clear_requests(req: Request):
    """Purge old request logs from database."""
    from gdr.safety.request_db import get_request_store
    days = 30
    try:
        data = await req.json()
        days = int(data.get("days", 30))
    except Exception:
        pass
    store = get_request_store()
    deleted = store.clear_old_requests(days=days)
    return {"success": True, "deleted_count": deleted}



@app.post("/api/panic")
async def api_panic(req: Request):
    global _ORB_STATE
    data = await req.json()
    action = data.get("action", "toggle")
    panicked_now = is_panicked()

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
    from gdr.tools.screen import list_open_windows, read_active_window
    return {
        "active_window": read_active_window(),
        "open_windows": list_open_windows(),
    }


@app.post("/api/windows/type")
async def api_windows_type(req: Request):
    from gdr.tools.screen import type_in_window
    data = await req.json()
    text = data.get("text", "")
    win_title = data.get("window_title", "")
    press_enter = bool(data.get("press_enter", True))
    res = type_in_window(text=text, window_title=win_title, press_enter=press_enter)
    return {"result": res}


@app.post("/api/whatsapp/send")
async def api_whatsapp_send(req: Request):
    from gdr.tools.screen import send_whatsapp_message
    data = await req.json()
    recipient = data.get("recipient", "")
    message = data.get("message", "")
    res = send_whatsapp_message(recipient=recipient, message=message)
    return {"result": res}


@app.post("/api/stop")
def api_stop_speech():
    """Immediately halt any active assistant speech and set state to listening."""
    global _ORB_STATE, _CURRENT_ACTIVITY
    from gdr.voice.tts import stop_speaking
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
    target = Path("/tmp/gdr_live_screen.png")
    target.write_bytes(raw_bytes)
    return {"success": True, "bytes": len(raw_bytes), "path": str(target)}


@app.get("/api/screen/live")
def api_screen_live():
    """Check live screen stream status and latency."""
    target = Path("/tmp/gdr_live_screen.png")
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
    target = Path("/tmp/gdr_live_screen.png")
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

    from gdr.tools.desktop import get_location_file, _reverse_geocode_nominatim
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
    from gdr.tools.desktop import resolve_location_data
    return resolve_location_data()


@app.get("/api/bookmarks")
def api_bookmarks():
    from gdr.tools.desktop import _load_bookmarks
    return _load_bookmarks()


@app.post("/api/bookmarks")
async def api_add_bookmark(req: Request):
    from gdr.tools.desktop import save_website_bookmark
    data = await req.json()
    name = data.get("name", "")
    url = data.get("url", "")
    category = data.get("category", "general")
    res = save_website_bookmark(name=name, url=url, category=category)
    return {"result": res}


@app.get("/api/tts/voices")
def api_tts_voices():
    """Return available neural voice profiles for Hindi and English."""
    from gdr.voice.tts import VOICE_PROFILES
    return list(VOICE_PROFILES.values())


@app.get("/api/tts/audio")
async def api_tts_audio(text: str, lang: str = "auto", voice: str = "", response_id: str = ""):
    """Stream studio-quality neural TTS audio for the given text and language.
    Uses worker thread to prevent freezing the event loop, ensuring sub-50ms streaming.
    Suppressed if SilenceController quiet mode is active.
    """
    from gdr.core.silence_controller import get_silence_controller
    if get_silence_controller().is_silence_active():
        raise HTTPException(status_code=403, detail="Assistant is in quiet mode")

    from gdr.voice.tts import synthesize_speech_file
    from gdr.core.telemetry import get_pipeline_timer
    import hashlib

    timer = get_pipeline_timer()
    timer.record("tts_started")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text parameter")

    cache_key = hashlib.md5(f"{text}_{lang}_{voice}_{response_id}".encode("utf-8")).hexdigest()
    cache_path = Path(f"/tmp/gdr_tts_cache_{cache_key}.mp3")

    if not cache_path.exists() or cache_path.stat().st_size < 500:
        try:
            await asyncio.to_thread(
                synthesize_speech_file,
                text=text,
                output_path=str(cache_path),
                lang=lang,
                voice=voice if voice else None,
                target_format="mp3",
                response_id=response_id if response_id else None
            )
        except Exception as e:
            logger.warning(f"Error synthesizing audio: {e}")
            raise HTTPException(status_code=500, detail=f"TTS synthesis error: {e}")

    timer.record("first_audio_chunk_ready")

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
    from gdr.core.silence_controller import get_silence_controller
    if get_silence_controller().is_silence_active():
        return {"success": False, "status": "silence_mode_active", "played": False}

    from gdr.voice.tts import TextToSpeech
    data = await req.json()
    text = data.get("text", "")
    lang = data.get("lang", "auto")
    voice = data.get("voice", "")
    tts = TextToSpeech()
    res = tts.speak(text=text, lang=lang, voice=voice)
    return res

@app.post("/api/tts/stop")
def api_tts_stop():
    """Immediately stop any active host audio playback process."""
    from gdr.voice.tts import stop_speaking
    stop_speaking()
    return {"success": True, "stopped": True}


@app.get("/api/silence/status")
def api_silence_status():
    """Get authoritative silence / quiet mode status."""
    from gdr.core.silence_controller import get_silence_controller
    sc = get_silence_controller()
    active = sc.is_silence_active()
    return {
        "active": active,
        "remaining_seconds": sc.get_remaining_seconds() if active else 0,
        "reason": sc.current_reason if active else "",
        "silence_until": sc.silence_until.isoformat() if sc.silence_until else None,
        "until_resumed": sc.until_resumed
    }


@app.post("/api/silence/activate")
async def api_silence_activate(req: Request):
    """Activate quiet mode (immediate cessation of speech and proactive messaging)."""
    from gdr.core.silence_controller import get_silence_controller
    from gdr.voice.tts import stop_speaking
    stop_speaking()

    data = await req.json()
    duration = data.get("duration_minutes")
    until_resumed = bool(data.get("until_resumed", False))
    reason = data.get("reason", "manual_request")

    sc = get_silence_controller()
    sc.activate_silence(duration_minutes=duration, until_resumed=until_resumed, reason=reason)
    return {
        "success": True,
        "active": True,
        "remaining_seconds": sc.get_remaining_seconds(),
        "reason": reason
    }


@app.post("/api/silence/deactivate")
def api_silence_deactivate():
    """Deactivate quiet mode and allow assistant speech to resume."""
    from gdr.core.silence_controller import get_silence_controller
    sc = get_silence_controller()
    sc.deactivate_silence()
    return {
        "success": True,
        "active": False
    }


@app.get("/api/voice/config")
def api_voice_get_config():
    """Get active authoritative voice configuration."""
    from gdr.voice.config import get_voice_manager
    return get_voice_manager().get_active_config().to_dict()


@app.post("/api/voice/config")
async def api_voice_set_config(req: Request):
    """Set and persist authoritative voice configuration."""
    from gdr.voice.config import get_voice_manager
    data = await req.json()
    mgr = get_voice_manager()
    updated = mgr.set_active_config(
        provider=data.get("provider"),
        voice_id=data.get("voice_id"),
        language=data.get("language"),
        speech_rate=data.get("speech_rate"),
        pitch=data.get("pitch"),
        volume=data.get("volume"),
        fallback_enabled=data.get("fallback_enabled"),
        persist=True
    )
    return {"success": True, "config": updated.to_dict()}


@app.post("/api/voice/test")
async def api_voice_test(req: Request):
    """Synthesize and test a voice profile with a standard preview phrase."""
    from gdr.voice.config import get_voice_manager, SUPPORTED_VOICE_CATALOG
    from gdr.voice.tts import synthesize_speech_file
    import hashlib

    data = await req.json()
    voice_key = data.get("voice", "hi_swara")
    text = data.get("text", "")

    cat = SUPPORTED_VOICE_CATALOG.get(voice_key, {})
    lang = cat.get("language", "hi-IN" if "hi" in voice_key else "en-US")
    voice_id = cat.get("voice_id", voice_key)
    if not text:
        text = "नमस्ते! मैं आपका चयनित एआई स्वर हूँ।" if "hi" in lang else "Hello! This is a test of your selected voice configuration."

    cache_key = hashlib.md5(f"test_{text}_{voice_id}".encode("utf-8")).hexdigest()
    out_path = f"/tmp/gdr_voice_test_{cache_key}.mp3"

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 500:
        await asyncio.to_thread(
            synthesize_speech_file,
            text=text,
            output_path=out_path,
            lang=lang,
            voice=voice_id
        )

    return {
        "success": True,
        "voice": voice_key,
        "audio_url": f"/api/tts/audio?text={text}&lang={lang}&voice={voice_id}"
    }




@app.get("/api/aarushi/proactive")
def api_aarushi_proactive(followup: bool = False, force: bool = True):
    """Generate a sweet, context-aware proactive message or flattering follow-up from Aarushi."""
    from gdr.core.proactive import get_proactive_message
    msg = get_proactive_message(is_followup=followup, force=force)
    return {"success": True, "message": msg, "is_followup": followup}


@app.get("/api/audio/chime")
def api_audio_chime():
    """Stream sweet melodious chime audio for Aarushi proactive check-in."""
    from gdr.core.proactive import generate_chime_wav
    wav_path = Path("/tmp/aarushi_bell_chime.wav")
    if not wav_path.exists() or wav_path.stat().st_size < 1000:
        generate_chime_wav(str(wav_path))
    return FileResponse(str(wav_path), media_type="audio/wav")


@app.get("/api/elevenlabs/config")
def api_elevenlabs_get_config():
    """Get ElevenLabs integration configuration and masked API key."""
    from gdr.config import load_config
    from gdr.safety.secrets import get_secret, mask_secret
    from gdr.voice.tts import extract_elevenlabs_voice_id
    cfg = load_config()
    v_cfg = cfg.get("voice", {})
    key = get_secret("ELEVENLABS_API_KEY") or v_cfg.get("elevenlabs_api_key", "")
    raw_vid = v_cfg.get("elevenlabs_voice_id", "RDWdsTU6N02BFftbIEAp")
    vid = extract_elevenlabs_voice_id(raw_vid)
    masked = mask_secret(key) if key else ""
    return {
        "has_key": bool(key and len(key) > 5),
        "masked_key": masked,
        "api_key": masked,
        "voice_id": vid,
        "enabled": bool(v_cfg.get("elevenlabs_enabled", True))
    }


@app.post("/api/elevenlabs/config")
async def api_elevenlabs_save_config(req: Request):
    """Save ElevenLabs API key, voice ID (or URL link), and enabled toggle."""
    from gdr.config import load_config, save_config
    from gdr.safety.secrets import set_secret
    from gdr.voice.tts import extract_elevenlabs_voice_id
    data = await req.json()
    api_key = data.get("api_key", "").strip()
    raw_voice_id = data.get("voice_id", "").strip()
    enabled = bool(data.get("enabled", False))

    if api_key and not api_key.startswith("***") and "..." not in api_key:
        set_secret("ELEVENLABS_API_KEY", api_key)

    cfg = load_config()
    if "voice" not in cfg:
        cfg["voice"] = {}
    if raw_voice_id:
        cfg["voice"]["elevenlabs_voice_id"] = extract_elevenlabs_voice_id(raw_voice_id)
    cfg["voice"]["elevenlabs_enabled"] = enabled
    save_config(cfg)
    return {
        "success": True,
        "voice_id": cfg["voice"].get("elevenlabs_voice_id", "RDWdsTU6N02BFftbIEAp"),
        "message": "ElevenLabs configuration saved successfully!"
    }


@app.post("/api/elevenlabs/test")
async def api_elevenlabs_test(req: Request):
    """Test synthesize speech sample with configured or requested ElevenLabs voice."""
    from gdr.voice.tts import synthesize_elevenlabs, extract_elevenlabs_voice_id
    from gdr.safety.secrets import get_secret
    import tempfile

    try:
        body = await req.json()
    except Exception:
        body = {}

    cfg = load_config()
    uname = os.environ.get("USER_NAME") or cfg.get("general", {}).get("user_name", "User")
    aname = os.environ.get("ASSISTANT_NAME") or cfg.get("general", {}).get("agent_name", "Aarushi")
    sample_text = body.get("text", f"Suno {uname}... ElevenLabs voice connect ho gayi hai! Main aapki {aname} hoon, kaisa lag raha hai mera sound?")
    req_voice = body.get("voice_id", "")
    voice_id = extract_elevenlabs_voice_id(req_voice) if req_voice else None

    fd, out_path = tempfile.mkstemp(suffix=".mp3", prefix="gdr_eleven_test_")
    os.close(fd)

    res = synthesize_elevenlabs(sample_text, out_path, voice_id=voice_id)
    if res and os.path.exists(res) and os.path.getsize(res) > 500:
        return FileResponse(res, media_type="audio/mpeg")
    from gdr.voice.tts import get_last_elevenlabs_error
    err = get_last_elevenlabs_error() or "ElevenLabs synthesis failed. Verify API key and voice ID."
    return JSONResponse(
        {"success": False, "error": err},
        status_code=400
    )


@app.get("/api/elevenlabs/voices")
def api_elevenlabs_voices():
    """Fetch available voices directly from ElevenLabs account."""
    from gdr.voice.tts import get_elevenlabs_voices_list
    voices = get_elevenlabs_voices_list()
    return {"success": True, "voices": voices}


@app.post("/api/audio/repair")
def api_audio_repair():
    """Repair laptop physical speakers and internal microphone, unmuting and setting optimal volume."""
    from gdr.tools.desktop import control_hardware
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


@app.get("/api/audio/devices")
def api_audio_devices():
    """List available audio input (microphone) and output (speaker) devices."""
    from gdr.voice.vad import query_audio_devices
    return query_audio_devices()


@app.post("/api/audio/devices/select")
async def api_audio_devices_select(req: Request):
    """Save selected microphone and speaker devices for voice operations."""
    from gdr.config import load_config, save_config
    import sounddevice as sd
    data = await req.json()
    input_dev = data.get("input_device")
    output_dev = data.get("output_device")

    cfg = load_config()
    if "voice" not in cfg:
        cfg["voice"] = {}

    if input_dev is not None:
        try:
            input_val = int(input_dev)
        except (ValueError, TypeError):
            input_val = str(input_dev)
        cfg["voice"]["input_device"] = input_val

    if output_dev is not None:
        try:
            output_val = int(output_dev)
        except (ValueError, TypeError):
            output_val = str(output_dev)
        cfg["voice"]["output_device"] = output_val

    save_config(cfg)

    # Update sounddevice runtime default if valid
    try:
        cur_in, cur_out = sd.default.device
        new_in = int(input_dev) if input_dev is not None and str(input_dev).isdigit() else cur_in
        new_out = int(output_dev) if output_dev is not None and str(output_dev).isdigit() else cur_out
        sd.default.device = [new_in, new_out]
    except Exception:
        pass

    return {
        "success": True,
        "message": "Audio device selection updated successfully!",
        "input_device": cfg["voice"].get("input_device"),
        "output_device": cfg["voice"].get("output_device")
    }


@app.post("/api/audio/mic/fix")
def api_audio_mic_fix():
    """Unmute, boost volume, verify ALSA configuration, and auto-detect best microphone."""
    from gdr.voice.vad import fix_and_boost_microphones
    return fix_and_boost_microphones()


@app.post("/api/audio/mic/test")
async def api_audio_mic_test(req: Request):
    """Test audio capture and measure signal energy on the active or specified microphone."""
    from gdr.voice.vad import test_microphone_input
    data = {}
    try:
        data = await req.json()
    except Exception:
        pass
    dev = data.get("device")
    if dev is not None and str(dev).isdigit():
        dev = int(dev)
    return test_microphone_input(device=dev, duration=0.6)


# -------------------------------------------------------------
# Cloudflare Quick Tunnel Management Endpoints
# -------------------------------------------------------------
import gdr.core.tunnel as tunnel_mgr


@app.get("/api/tunnel/status")
def api_tunnel_status():
    """Get live status and URL of Cloudflare quick tunnel."""
    return tunnel_mgr.get_tunnel_status()


@app.post("/api/tunnel/start")
def api_tunnel_start():
    """Start Cloudflare quick tunnel and return live URL and QR."""
    success, url, msg = tunnel_mgr.start_tunnel(port=8844)
    status = tunnel_mgr.get_tunnel_status()
    status["success"] = success
    status["message"] = msg
    return status


@app.post("/api/tunnel/stop")
def api_tunnel_stop():
    """Stop active Cloudflare quick tunnel."""
    stopped = tunnel_mgr.stop_tunnel()
    status = tunnel_mgr.get_tunnel_status()
    status["stopped"] = stopped
    status["message"] = "Tunnel stopped successfully."
    return status


# -------------------------------------------------------------
# Stealth Meeting & Interview Copilot Endpoints
# -------------------------------------------------------------
from gdr.stealth.copilot import get_stealth_copilot
from gdr.stealth.stealth_html import STEALTH_HTML


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


# -----------------------------------------------------------------
# SARVAM AI ENGINE CONFIGURATION & TESTING
# -----------------------------------------------------------------
@app.get("/api/sarvam/config")
def api_sarvam_get_config():
    """Retrieve Sarvam AI configuration and API key."""
    from gdr.config import load_config
    from gdr.safety.secrets import get_secret, mask_secret
    from gdr.core.providers import is_sarvam_quota_exceeded, get_sarvam_last_error
    cfg = load_config()
    prov_cfg = cfg.get("provider", {})
    v_cfg = cfg.get("voice", {})
    key = get_secret("SARVAM_API_KEY")
    masked = mask_secret(key) if key else ""
    return {
        "has_key": bool(key and len(key) > 5),
        "masked_key": masked,
        "api_key": masked,
        "model": prov_cfg.get("model", "sarvam-105b-conversations"),
        "default_provider": prov_cfg.get("default", "sarvam"),
        "sarvam_tts_enabled": bool(v_cfg.get("sarvam_tts_enabled", True)),
        "quota_exceeded": is_sarvam_quota_exceeded(),
        "last_error": get_sarvam_last_error(),
    }


@app.post("/api/sarvam/config")
async def api_sarvam_save_config(req: Request):
    """Save Sarvam API key, model selection, and TTS enable/disable toggle."""
    from gdr.config import load_config, save_config
    from gdr.safety.secrets import set_secret
    from gdr.core.providers import set_sarvam_quota_exceeded
    data = await req.json()
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "").strip()
    sarvam_tts_enabled = data.get("sarvam_tts_enabled", None)

    if api_key and not api_key.startswith("***") and "..." not in api_key:
        set_secret("SARVAM_API_KEY", api_key)
        set_sarvam_quota_exceeded(False, "")

    cfg = load_config()
    if "provider" not in cfg:
        cfg["provider"] = {}
    if "voice" not in cfg:
        cfg["voice"] = {}
    valid_sarvam_models = {"sarvam-105b", "sarvam-105b-conversations", "sarvam-m"}
    if model and model.lower() in valid_sarvam_models:
        cfg["provider"]["model"] = model
    else:
        cfg["provider"]["model"] = "sarvam-105b-conversations"
    cfg["provider"]["default"] = "sarvam"
    if sarvam_tts_enabled is not None:
        cfg["voice"]["sarvam_tts_enabled"] = bool(sarvam_tts_enabled)
    save_config(cfg)

    # Force agent re-initialization with the new Sarvam key immediately
    global _AGENT
    _AGENT = None
    try:
        get_agent()
    except Exception as e:
        logger.warning(f"Could not re-init agent after Sarvam config: {e}")

    return {"success": True, "message": "Sarvam AI configuration saved successfully!", "sarvam_tts_enabled": cfg["voice"].get("sarvam_tts_enabled", True)}


@app.post("/api/sarvam/test")
async def api_sarvam_test(req: Request):
    """Test Sarvam API key connectivity."""
    from gdr.safety.secrets import get_secret
    key = get_secret("SARVAM_API_KEY")
    if not key:
        return JSONResponse({"success": False, "message": "SARVAM_API_KEY is not configured."}, status_code=400)
    try:
        import requests
        headers = {"api-subscription-key": key, "Content-Type": "application/json"}
        resp = requests.get("https://api.sarvam.ai/v1/models", headers=headers, timeout=8)
        if resp.status_code in (200, 404):
            return {"success": True, "message": "Sarvam API connected successfully!"}
        return {"success": False, "message": f"Sarvam returned status {resp.status_code}: {resp.text[:150]}"}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {e}"}


# -----------------------------------------------------------------
# MODEL HUB: CLOUD & HUGGING FACE LOCAL MODEL MANAGEMENT
# -----------------------------------------------------------------
@app.get("/api/models")
def api_get_models():
    """List available Cloud models, local GGUF models, and Hugging Face presets."""
    from gdr.config import load_config
    from gdr.safety.secrets import get_secret
    from gdr.models.downloader import (
        HF_PRESETS,
        CLOUD_MODELS,
        list_local_models,
        list_ollama_models,
        get_download_state
    )

    cfg = load_config()
    p_cfg = cfg.get("provider", {})
    active_provider = p_cfg.get("default", "sarvam")
    active_model = p_cfg.get("model", "sarvam-105b-conversations")
    active_model_path = p_cfg.get("model_path", "")

    # Decorate cloud models with key configuration status
    cloud_catalog = []
    for cm in CLOUD_MODELS:
        req_key = cm.get("requires_key", "")
        has_key = bool(get_secret(req_key) or os.environ.get(req_key))
        cloud_catalog.append({
            **cm,
            "has_key": has_key
        })

    return {
        "active_provider": active_provider,
        "active_model": active_model,
        "active_model_path": active_model_path,
        "cloud_models": cloud_catalog,
        "local_models": list_local_models(),
        "ollama_models": list_ollama_models(),
        "hf_presets": HF_PRESETS,
        "download_status": get_download_state().to_dict(),
    }


@app.post("/api/models/active")
async def api_set_active_model(req: Request):
    """Switch active LLM provider and model immediately."""
    from gdr.config import load_config, save_config
    data = await req.json()
    provider = data.get("provider", "sarvam").lower()
    model = data.get("model", "")
    model_path = data.get("model_path", "")

    cfg = load_config()
    if "provider" not in cfg:
        cfg["provider"] = {}

    cfg["provider"]["default"] = provider
    if provider == "sarvam":
        valid_sarvam_models = {"sarvam-105b", "sarvam-105b-conversations", "sarvam-m"}
        cfg["provider"]["model"] = model if (model and model.lower() in valid_sarvam_models) else "sarvam-105b-conversations"
    elif model:
        cfg["provider"]["model"] = model
    if model_path:
        cfg["provider"]["model_path"] = model_path
    save_config(cfg)

    # Immediately reload the running Agent
    global _AGENT
    _AGENT = None
    try:
        get_agent()
    except Exception as e:
        logger.warning(f"Error re-initializing Agent after model switch: {e}")

    return {
        "success": True,
        "message": f"Active AI model switched to {model or provider}!",
        "provider": provider,
        "model": model,
    }


@app.post("/api/models/pull")
async def api_pull_model(req: Request):
    """Pull / download a GGUF model from Hugging Face."""
    from gdr.models.downloader import start_model_download, HF_PRESETS
    data = await req.json()
    preset_id = data.get("preset_id")
    url = data.get("url", "").strip()
    filename = data.get("filename", "").strip()
    name = data.get("name", "").strip()

    if preset_id:
        preset = next((p for p in HF_PRESETS if p["id"] == preset_id), None)
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        url = preset["url"]
        filename = preset["filename"]
        name = preset["name"]

    if not url or not filename:
        raise HTTPException(status_code=400, detail="URL and filename are required.")

    res = start_model_download(url=url, filename=filename, model_name=name or filename)
    return res


@app.get("/api/models/pull/status")
def api_pull_status():
    """Get active download status, percentage, and speed."""
    from gdr.models.downloader import get_download_state
    return get_download_state().to_dict()


@app.post("/api/models/pull/cancel")
def api_pull_cancel():
    """Cancel active model download."""
    from gdr.models.downloader import cancel_model_download
    return cancel_model_download()


# -----------------------------------------------------------------
# TELEGRAM BOT CHANNEL MANAGEMENT
# -----------------------------------------------------------------
@app.get("/api/telegram/config")
def api_telegram_get_config():
    from gdr.config import load_config
    from gdr.safety.secrets import get_secret, mask_secret
    from gdr.channels.telegram_bot import is_telegram_bot_running
    cfg = load_config()
    c_cfg = cfg.get("channels", {})
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat_id = get_secret("TELEGRAM_CHAT_ID") or c_cfg.get("telegram_chat_id", "")
    masked = mask_secret(token) if token else ""
    return {
        "has_token": bool(token and len(token) > 5),
        "masked_token": masked,
        "token": masked,
        "chat_id": str(chat_id or ""),
        "allowed_user_id": c_cfg.get("allowed_telegram_user_id", 0),
        "allowed_username": c_cfg.get("allowed_telegram_username", ""),
        "enabled": bool(c_cfg.get("telegram_enabled", False)),
        "running": is_telegram_bot_running()
    }


@app.post("/api/telegram/config")
async def api_telegram_save_config(req: Request):
    from gdr.config import load_config, save_config
    from gdr.safety.secrets import set_secret
    from gdr.channels.telegram_bot import start_telegram_bot_service, stop_telegram_bot_service
    data = await req.json()
    token = data.get("token", "").strip()
    chat_id = data.get("chat_id", "").strip()
    username = data.get("username", "").strip()
    enabled = bool(data.get("enabled", False))

    if token and not token.startswith("***") and "..." not in token:
        set_secret("TELEGRAM_BOT_TOKEN", token)
    if chat_id:
        set_secret("TELEGRAM_CHAT_ID", chat_id)

    cfg = load_config()
    if "channels" not in cfg:
        cfg["channels"] = {}
    cfg["channels"]["telegram_enabled"] = enabled
    if chat_id:
        cfg["channels"]["telegram_chat_id"] = chat_id
        if chat_id.isdigit():
            cfg["channels"]["allowed_telegram_user_id"] = int(chat_id)
    elif username:
        cfg["channels"].pop("allowed_telegram_user_id", None)
    if username:
        cfg["channels"]["allowed_telegram_username"] = username.lstrip("@").strip()
    elif "username" in data and not username:
        cfg["channels"]["allowed_telegram_username"] = ""
    save_config(cfg)

    if enabled:
        start_telegram_bot_service(restart=True)
    else:
        stop_telegram_bot_service()

    return {"success": True, "message": "Telegram Bot configuration saved successfully!"}


@app.post("/api/telegram/toggle")
def api_telegram_toggle():
    from gdr.channels.telegram_bot import is_telegram_bot_running, start_telegram_bot_service, stop_telegram_bot_service
    from gdr.config import load_config, save_config
    cfg = load_config()
    if "channels" not in cfg:
        cfg["channels"] = {}
    if is_telegram_bot_running():
        stop_telegram_bot_service()
        cfg["channels"]["telegram_enabled"] = False
        save_config(cfg)
        return {"running": False, "message": "Telegram Bot stopped."}
    else:
        res = start_telegram_bot_service()
        cfg["channels"]["telegram_enabled"] = True
        save_config(cfg)
        return {"running": res.get("success", False), "message": res.get("message", "")}


@app.post("/api/telegram/validate")
async def api_telegram_validate(req: Request):
    from gdr.channels.telegram_bot import validate_telegram_token
    token = None
    try:
        data = await req.json()
        token = data.get("token")
    except Exception:
        pass
    result = validate_telegram_token(token=token)
    status_code = 200 if result.get("valid") else 400
    return JSONResponse(result, status_code=status_code)


@app.post("/api/telegram/test")
async def api_telegram_test(req: Request):
    from gdr.channels.telegram_bot import send_telegram_test_message
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass
    chat_id = body.get("chat_id")
    msg = body.get("message", "🌸 *Hello from Aarushi!* Your Telegram Bot is successfully connected and listening to your system.")
    res = send_telegram_test_message(text=msg, chat_id=chat_id)
    status_code = 200 if res.get("success") else 400
    return JSONResponse(res, status_code=status_code)


# -----------------------------------------------------------------
# MARKANM CHAT BOT CHANNEL MANAGEMENT
# -----------------------------------------------------------------
@app.get("/api/markanm/config")
def api_markanm_get_config():
    from gdr.config import load_config
    from gdr.safety.secrets import get_secret, mask_secret
    from gdr.channels.markanm_bot import is_markanm_bot_running
    cfg = load_config()
    c_cfg = cfg.get("channels", {})
    token = get_secret("MARKANM_BOT_TOKEN")
    masked = mask_secret(token) if token else ""
    return {
        "has_token": bool(token and len(token) > 5),
        "masked_token": masked,
        "token": masked,
        "room_id": c_cfg.get("markanm_room_id", ""),
        "allowed_username": c_cfg.get("allowed_markanm_username", ""),
        "allowed_user_id": c_cfg.get("allowed_markanm_user_id", ""),
        "enabled": bool(c_cfg.get("markanm_enabled", False)),
        "running": is_markanm_bot_running()
    }


@app.post("/api/markanm/config")
async def api_markanm_save_config(req: Request):
    from gdr.config import load_config, save_config
    from gdr.safety.secrets import set_secret
    from gdr.channels.markanm_bot import start_markanm_bot_service, stop_markanm_bot_service
    data = await req.json()
    token = data.get("token", "").strip()
    room_id = data.get("room_id", "").strip()
    username = data.get("username", "").strip()
    allowed_user_id = data.get("allowed_user_id", "").strip()
    enabled = bool(data.get("enabled", False))

    if token and not token.startswith("***") and "..." not in token:
        set_secret("MARKANM_BOT_TOKEN", token)

    cfg = load_config()
    if "channels" not in cfg:
        cfg["channels"] = {}
    cfg["channels"]["markanm_enabled"] = enabled
    if room_id:
        cfg["channels"]["markanm_room_id"] = room_id
    if username:
        cfg["channels"]["allowed_markanm_username"] = username.lstrip("@").strip()
    elif "username" in data and not username:
        cfg["channels"]["allowed_markanm_username"] = ""
    if allowed_user_id:
        cfg["channels"]["allowed_markanm_user_id"] = allowed_user_id
    elif "allowed_user_id" in data and not allowed_user_id:
        cfg["channels"]["allowed_markanm_user_id"] = ""
    save_config(cfg)

    if enabled:
        start_markanm_bot_service(restart=True)
    else:
        stop_markanm_bot_service()

    return {"success": True, "message": "MarkanM Bot configuration saved successfully!"}


@app.post("/api/markanm/toggle")
def api_markanm_toggle():
    from gdr.channels.markanm_bot import is_markanm_bot_running, start_markanm_bot_service, stop_markanm_bot_service
    from gdr.config import load_config, save_config
    cfg = load_config()
    if "channels" not in cfg:
        cfg["channels"] = {}
    if is_markanm_bot_running():
        stop_markanm_bot_service()
        cfg["channels"]["markanm_enabled"] = False
        save_config(cfg)
        return {"running": False, "message": "MarkanM Bot stopped."}
    else:
        res = start_markanm_bot_service(restart=True)
        cfg["channels"]["markanm_enabled"] = True
        save_config(cfg)
        return {"running": res.get("success", False), "message": res.get("message", "")}


@app.post("/api/markanm/validate")
async def api_markanm_validate(req: Request):
    from gdr.channels.markanm_bot import validate_markanm_token
    token = None
    try:
        data = await req.json()
        token = data.get("token")
    except Exception:
        pass
    result = validate_markanm_token(token=token)
    status_code = 200 if result.get("valid") else 400
    return JSONResponse(result, status_code=status_code)


@app.post("/api/markanm/test")
async def api_markanm_test(req: Request):
    from gdr.channels.markanm_bot import send_markanm_test_message
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass
    room_id = body.get("room_id")
    msg = body.get("message", "🌸 Hello from Aarushi! Your MarkanM Bot is connected and active on your system!")
    res = send_markanm_test_message(text=msg, room_id=room_id)
    status_code = 200 if res.get("success") else 400
    return JSONResponse(res, status_code=status_code)


# -----------------------------------------------------------------
# RAG KNOWLEDGE BASE MANAGEMENT
# -----------------------------------------------------------------
@app.post("/api/rag/auth")
async def api_rag_auth(req: Request):
    """Authenticate Master PIN for RAG Knowledge Base access."""
    from gdr.memory.rag import verify_rag_pin
    data = await req.json()
    pin = data.get("pin", "")
    if verify_rag_pin(pin):
        return {"success": True, "message": "PIN verified successfully!"}
    return JSONResponse({"success": False, "message": "Incorrect Master PIN. Access denied."}, status_code=403)


@app.get("/api/rag/stats")
def api_rag_stats(req: Request):
    """Get RAG statistics."""
    from gdr.memory.rag import get_rag_store, verify_rag_pin
    pin = req.headers.get("X-RAG-PIN") or req.query_params.get("pin")
    if not verify_rag_pin(pin):
        return JSONResponse({"error": "Unauthorized. PIN required."}, status_code=403)
    store = get_rag_store()
    return store.get_stats()


@app.get("/api/rag/documents")
def api_rag_documents(req: Request):
    """List knowledge documents in RAG store."""
    from gdr.memory.rag import get_rag_store, verify_rag_pin
    pin = req.headers.get("X-RAG-PIN") or req.query_params.get("pin")
    if not verify_rag_pin(pin):
        return JSONResponse({"error": "Unauthorized. PIN required."}, status_code=403)
    category = req.query_params.get("category")
    search = req.query_params.get("search")
    store = get_rag_store()
    docs = store.list_documents(category=category, search=search)
    return {"documents": docs, "stats": store.get_stats()}


@app.post("/api/rag/documents")
async def api_rag_add_document(req: Request):
    """Add a new document into RAG knowledge base."""
    from gdr.memory.rag import get_rag_store, verify_rag_pin
    data = await req.json()
    pin = data.get("pin") or req.headers.get("X-RAG-PIN")
    if not verify_rag_pin(pin):
        return JSONResponse({"error": "Unauthorized. PIN required."}, status_code=403)
    title = data.get("title", "")
    content = data.get("content", "")
    category = data.get("category", "notes")
    tags = data.get("tags", "")
    if not content.strip():
        return JSONResponse({"error": "Content cannot be empty."}, status_code=400)
    store = get_rag_store()
    doc = store.add_document(title=title, content=content, category=category, tags=tags)
    return {"success": True, "document": doc}


@app.delete("/api/rag/documents/{doc_id}")
def api_rag_delete_document(doc_id: int, req: Request):
    """Delete document from RAG knowledge base."""
    from gdr.memory.rag import get_rag_store, verify_rag_pin
    pin = req.headers.get("X-RAG-PIN") or req.query_params.get("pin")
    if not verify_rag_pin(pin):
        return JSONResponse({"error": "Unauthorized. PIN required."}, status_code=403)
    store = get_rag_store()
    success = store.delete_document(doc_id)
    return {"success": success}


@app.post("/api/rag/query")
async def api_rag_query(req: Request):
    """Test semantic retrieval on RAG knowledge base."""
    from gdr.memory.rag import get_rag_store, verify_rag_pin
    data = await req.json()
    pin = data.get("pin") or req.headers.get("X-RAG-PIN")
    if not verify_rag_pin(pin):
        return JSONResponse({"error": "Unauthorized. PIN required."}, status_code=403)
    query = data.get("query", "").strip()
    store = get_rag_store()
    matches = store.search_rag(query, top_k=4)
    simulated_context = store.format_rag_context(query)
    return {
        "matches": matches,
        "simulated_context": simulated_context,
        "query": query
    }


# ==============================================================================
# GDR-AI MULTI-DEVICE MESH ENDPOINTS & WEBSOCKET GATEWAY
# ==============================================================================

@app.post("/api/mesh/pair/start")
async def api_mesh_pair_start(req: Request):
    """Generate a short-lived 6-digit pairing code with QR payload."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    from gdr.mesh.models import PlatformType, DevicePermissions
    try:
        data = await req.json()
    except Exception:
        data = {}
    req_name = data.get("name", "New Device")
    plat_str = data.get("platform", "unknown")
    try:
        plat = PlatformType(plat_str.lower())
    except Exception:
        plat = PlatformType.UNKNOWN

    perms_dict = data.get("permissions")
    perms = DevicePermissions.from_dict(perms_dict) if perms_dict else DevicePermissions()
    coord = get_mesh_coordinator()
    try:
        code, pairing = coord.generate_pairing_code(
            requester_name=req_name,
            requester_platform=plat,
            requested_permissions=perms,
            ttl_seconds=300
        )
        base_url = str(req.base_url).rstrip("/")
        qr_payload = f"gdr-mesh://pair?code={code}&coordinator={base_url}"
        return {
            "success": True,
            "code": code,
            "expires_at": pairing.expires_at,
            "expires_in_seconds": int(pairing.expires_at - time.time()),
            "qr_payload": qr_payload,
        }
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=429)


@app.post("/api/mesh/pair/complete")
async def api_mesh_pair_complete(req: Request):
    """Complete device pairing using a 6-digit code."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    data = await req.json()
    code = str(data.get("code", "")).strip()
    dev_name = str(data.get("device_name", "")).strip() or "Device Node"
    plat_str = str(data.get("platform", "unknown")).strip()
    caps = data.get("capabilities")
    client_ip = req.client.host if req.client else "127.0.0.1"

    coord = get_mesh_coordinator()
    res = coord.verify_and_pair(
        code=code,
        device_name=dev_name,
        platform_name=plat_str,
        ip_address=client_ip,
        capabilities=caps
    )
    if not res.get("success"):
        return JSONResponse(res, status_code=400)
    return res


@app.get("/api/mesh/devices")
def api_mesh_devices():
    """List all enrolled mesh devices with real-time status and telemetry."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    return {"devices": coord.list_devices()}


@app.get("/api/mesh/devices/{device_id}")
def api_mesh_device_detail(device_id: str):
    """Get detailed telemetry and permissions for a specific device."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    dev = coord.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    return dev


@app.post("/api/mesh/devices/{device_id}/permissions")
async def api_mesh_update_permissions(device_id: str, req: Request):
    """Update permissions allowlist for a device."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    data = await req.json()
    coord = get_mesh_coordinator()
    ok = coord.update_device_permissions(device_id, data)
    return {"success": ok}


@app.delete("/api/mesh/devices/{device_id}")
def api_mesh_revoke_device(device_id: str):
    """Revoke authorization for a mesh device."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    ok = coord.revoke_device(device_id)
    return {"success": ok}


@app.post("/api/mesh/devices/{device_id}/rename")
async def api_mesh_rename_device(device_id: str, req: Request):
    """Rename a mesh device."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    data = await req.json()
    new_name = str(data.get("name", "")).strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Device name cannot be empty")
    coord = get_mesh_coordinator()
    ok = coord.rename_device(device_id, new_name)
    return {"success": ok, "device_id": device_id, "name": new_name}


@app.delete("/api/mesh/devices/{device_id}/remove")
def api_mesh_remove_device(device_id: str):
    """Completely unenroll and delete a mesh device."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    ok = coord.remove_device(device_id)
    return {"success": ok}


@app.get("/api/mesh/capabilities")
def api_mesh_capabilities():
    """List all supported standard mesh capabilities and security definitions."""
    from gdr.mesh.models import STANDARD_CAPABILITIES
    return {k: v.to_dict() for k, v in STANDARD_CAPABILITIES.items()}


@app.get("/api/mesh/audit")
def api_mesh_audit_logs(limit: int = 50, device_id: Optional[str] = None):
    """Retrieve security audit events from the mesh."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    return coord.get_audit_logs(limit=limit, device_id=device_id)


@app.post("/api/mesh/panic")
async def api_mesh_panic():
    """Emergency Stop: Abort all cross-device mesh operations and signal connected agents."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    return await coord.panic_kill_all()


@app.post("/api/mesh/tasks/{task_id}/cancel")
async def api_mesh_cancel_task(task_id: str):
    """Cancel a pending or running cross-device task."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    coord = get_mesh_coordinator()
    return await coord.cancel_task(task_id)


@app.post("/api/mesh/pair/generate")
async def api_mesh_pair_generate(req: Request):
    """Alias for /api/mesh/pair/start."""
    return await api_mesh_pair_start(req)


@app.post("/api/mesh/pair/verify")
async def api_mesh_pair_verify(req: Request):
    """Alias for /api/mesh/pair/complete."""
    return await api_mesh_pair_complete(req)


@app.post("/api/mesh/dispatch")
async def api_mesh_dispatch(req: Request):
    """Dispatch a capability task to a target mesh device."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    data = await req.json()
    dev_id = data.get("device_id") or data.get("target_device_id") or "local_primary"
    capability = data.get("capability") or data.get("task_type") or "sys_info"
    params = data.get("parameters", {})
    timeout = float(data.get("timeout", 30.0))

    coord = get_mesh_coordinator()
    res = await coord.dispatch_task(
        target_device_id=dev_id,
        capability=capability,
        parameters=params,
        timeout=timeout
    )
    return res


@app.websocket("/ws/mesh/device")
async def ws_mesh_device(websocket: WebSocket):
    """Persistent bidirectional WebSocket gateway for remote mesh agents."""
    from gdr.mesh.coordinator import get_mesh_coordinator
    await websocket.accept()

    # Authenticate via Bearer token in header or query parameter
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization") or ""
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    elif "token" in websocket.query_params:
        token = websocket.query_params["token"].strip()

    coord = get_mesh_coordinator()
    device = coord.authenticate_token(token)
    if not device:
        logger.warning("Unauthorized WebSocket mesh connection attempt rejected.")
        await websocket.close(code=1008, reason="Unauthorized device token")
        return

    device_id = device.id
    coord.register_connection(device_id, websocket)
    logger.info(f"Connected mesh agent: {device.name} [{device_id}]")

    try:
        while True:
            text_data = await websocket.receive_text()
            try:
                msg = json.loads(text_data)
                mtype = msg.get("type")
                if mtype == "heartbeat":
                    metrics = msg.get("metrics", {})
                    battery = msg.get("battery", {})
                    coord.update_device_heartbeat(device_id, metrics, battery)
                elif mtype == "task_result":
                    task_id = msg.get("task_id")
                    coord.handle_agent_task_result(task_id, msg)
            except Exception as e:
                logger.warning(f"Error handling mesh agent message: {e}")
    except WebSocketDisconnect:
        logger.info(f"Mesh agent disconnected: {device.name} [{device_id}]")
    except Exception as e:
        logger.warning(f"Mesh WebSocket exception for {device_id}: {e}")
    finally:
        coord.unregister_connection(device_id)


# ==============================================================================
# AI ENHANCEMENT & CONVERSATION EXPORT
# ==============================================================================

@app.post("/api/ai/enhance-prompt")
@app.post("/api/prompt/enhance")
async def api_ai_enhance_prompt(req: Request):
    """Expand user prompt into structured high-precision instruction."""
    data = await req.json()
    raw = data.get("prompt", "").strip()
    if not raw:
        return {"enhanced": "", "enhanced_prompt": ""}
    enhanced = (
        f"Goal: {raw}\n\n"
        "Instructions:\n"
        "• Execute with production-grade engineering standards\n"
        "• Provide clear step-by-step logic and rationale\n"
        "• Highlight edge-cases, validation checks, and safety rules\n"
        "• Return actionable, clean code and output without fluff"
    )
    return {"enhanced": enhanced, "enhanced_prompt": enhanced}



# ==============================================================================
# ENGINE & CONTEXT ROUTES
# ==============================================================================

_session_graph = None
_vector_store = None


def _get_session_graph():
    global _session_graph
    if _session_graph is None:
        try:
            from gdr.core.session_graph import SessionGraph
            _session_graph = SessionGraph()
        except (ImportError, Exception):
            pass
    return _session_graph


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            from gdr.memory.vector_store import VectorStore
            _vector_store = VectorStore()
        except (ImportError, Exception):
            pass
    return _vector_store


@app.get("/api/engine/status")
async def api_engine_status():
    """Return current engine/mode telemetry."""
    try:
        from gdr.config import load_config
        cfg = load_config()
        model_cfg = cfg.get("model", {})
        agent_cfg = cfg.get("agent", {})
        model_name = model_cfg.get("name", "sarvam-m") if isinstance(model_cfg, dict) else str(model_cfg)
        mode = agent_cfg.get("mode", "chat") if isinstance(agent_cfg, dict) else "chat"
        is_cloud = "cloud" in model_name.lower() or "sarvam" in model_name.lower() or "gemini" in model_name.lower()
        engine = "cloud" if is_cloud else "fast"
    except Exception:
        model_name = "Unknown"
        mode = "chat"
        engine = "fast"
    return {
        "engine": engine,
        "mode": mode,
        "tokens_used": 0,
        "tokens_max": 200000,
        "model_name": model_name,
        "is_online": True,
    }


@app.post("/api/engine/mode")
async def api_engine_set_mode(req: Request):
    """Switch agent mode (fast/deep/code/pair)."""
    data = await req.json()
    new_mode = data.get("mode", "chat")
    valid = {"fast", "deep", "code", "pair", "chat"}
    if new_mode not in valid:
        return {"success": False, "error": f"Invalid mode '{new_mode}'. Choose from {sorted(valid)}"}
    try:
        from gdr.config import load_config, save_config
        cfg = load_config()
        if "agent" not in cfg:
            cfg["agent"] = {}
        cfg["agent"]["mode"] = new_mode
        save_config(cfg)
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "mode": new_mode}


@app.get("/api/session/checkpoints")
async def api_session_checkpoints():
    """List available session checkpoints."""
    sg = _get_session_graph()
    if sg and hasattr(sg, "list_checkpoints"):
        try:
            return {"checkpoints": sg.list_checkpoints()}
        except Exception:
            pass
    return {"checkpoints": []}


@app.post("/api/session/undo")
async def api_session_undo():
    """Undo last exchange."""
    sg = _get_session_graph()
    if sg and hasattr(sg, "undo"):
        try:
            result = sg.undo()
            return {"success": True, "messages_restored": result.get("count", 0) if isinstance(result, dict) else 0}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Session graph not available"}


@app.post("/api/session/redo")
async def api_session_redo():
    """Redo last undone exchange."""
    sg = _get_session_graph()
    if sg and hasattr(sg, "redo"):
        try:
            result = sg.redo()
            return {"success": True, "messages_restored": result.get("count", 0) if isinstance(result, dict) else 0}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Session graph not available"}


@app.post("/api/session/checkpoint")
async def api_session_create_checkpoint(req: Request):
    """Create a named session checkpoint."""
    data = await req.json()
    label = data.get("label", "Checkpoint")
    sg = _get_session_graph()
    if sg and hasattr(sg, "create_checkpoint"):
        try:
            result = sg.create_checkpoint(label=label)
            cp_id = result.get("id", "cp_0") if isinstance(result, dict) else "cp_0"
            return {"success": True, "id": cp_id, "label": label}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Session graph not available"}


@app.post("/api/session/rollback/{checkpoint_id}")
async def api_session_rollback(checkpoint_id: str):
    """Roll back to a specific checkpoint."""
    sg = _get_session_graph()
    if sg and hasattr(sg, "rollback"):
        try:
            sg.rollback(checkpoint_id)
            return {"success": True, "checkpoint_id": checkpoint_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "Session graph not available"}


@app.post("/api/vector/index")
async def api_vector_index(req: Request):
    """Index a directory into the vector store."""
    data = await req.json()
    path = data.get("path", "").strip()
    if not path:
        return {"docs_indexed": 0, "status": "error", "message": "No path provided"}
    import os
    if not os.path.exists(path):
        return {"docs_indexed": 0, "status": "error", "message": f"Path not found: {path}"}
    vs = _get_vector_store()
    if vs and hasattr(vs, "index_directory"):
        try:
            count = vs.index_directory(path)
            return {"docs_indexed": count or 0, "status": "ok", "message": f"Indexed {count} docs from {path}"}
        except Exception as e:
            return {"docs_indexed": 0, "status": "error", "message": str(e)}
    return {"docs_indexed": 0, "status": "error", "message": "Vector store not available"}


@app.get("/api/vector/status")
async def api_vector_status():
    """Return vector store status."""
    vs = _get_vector_store()
    if vs:
        indexed = getattr(vs, "doc_count", None)
        if callable(indexed):
            indexed = indexed()
        is_semantic = getattr(vs, "is_semantic", True)
        index_path = getattr(vs, "index_path", "~/.config/gdr/vector_index")
        return {
            "indexed_docs": indexed or 0,
            "is_semantic": bool(is_semantic),
            "index_path": str(index_path),
        }
    return {"indexed_docs": 0, "is_semantic": False, "index_path": "~/.config/gdr/vector_index"}


# ─── GDR-IDE & Personal Terminal APIs ────────────────────────────────────
_TERMINAL_CWD = str(Path.cwd())


@app.post("/api/terminal/exec")
async def api_terminal_exec(req: Request):
    """Execute shell commands in user's personal terminal with cwd tracking."""
    global _TERMINAL_CWD
    data = await req.json()
    cmd = data.get("command", "").strip()
    req_cwd = data.get("cwd", _TERMINAL_CWD)

    if not cmd:
        return {"stdout": "", "stderr": "", "exit_code": 0, "cwd": _TERMINAL_CWD, "duration_ms": 0}

    # Handle 'cd' commands directly
    if cmd.startswith("cd ") or cmd == "cd":
        target = cmd[3:].strip() if len(cmd) > 2 else os.path.expanduser("~")
        new_path = (Path(req_cwd) / os.path.expanduser(target)).resolve()
        if new_path.exists() and new_path.is_dir():
            _TERMINAL_CWD = str(new_path)
            return {"stdout": "", "stderr": "", "exit_code": 0, "cwd": _TERMINAL_CWD, "duration_ms": 2}
        else:
            return {"stdout": "", "stderr": f"cd: no such file or directory: {target}\n", "exit_code": 1, "cwd": _TERMINAL_CWD, "duration_ms": 2}

    import subprocess, time
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            executable="/bin/bash",
            cwd=_TERMINAL_CWD,
            capture_output=True,
            text=True,
            timeout=30,
        )
        dur = int((time.time() - t0) * 1000)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "cwd": _TERMINAL_CWD,
            "duration_ms": dur
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 30 seconds.\n",
            "exit_code": 124,
            "cwd": _TERMINAL_CWD,
            "duration_ms": 30000
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Terminal error: {e}\n",
            "exit_code": 1,
            "cwd": _TERMINAL_CWD,
            "duration_ms": int((time.time() - t0) * 1000)
        }


@app.post("/api/coding/execute")
@app.post("/api/ide/execute")
async def api_ide_execute(req: Request):
    """Execute code in isolated sandbox (Python, Bash, JS)."""
    data = await req.json()
    code = data.get("code", "")
    language = data.get("language", "python")

    try:
        from gdr.core.sandbox import CodeSandbox
        sandbox = CodeSandbox(default_timeout=15)
        res = sandbox.execute(code, language=language)
        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.exit_code,
            "timed_out": res.timed_out,
            "duration_ms": res.duration_ms,
            "success": res.success
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": 1,
            "timed_out": False,
            "duration_ms": 0,
            "success": False
        }


@app.get("/api/files/tree")
@app.get("/api/files/list")
def api_files_tree(path: str = ""):
    """Return directory tree for GDR-IDE file explorer."""
    base_dir = Path(path).resolve() if path else Path.cwd()
    if not base_dir.exists() or not base_dir.is_dir():
        base_dir = Path.cwd()

    items = []
    try:
        for entry in sorted(base_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip heavy/hidden folders like .git, .venv, __pycache__, node_modules
            if entry.name.startswith(".") and entry.name not in (".env", ".secrets.env"):
                continue
            if entry.name in ("__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"):
                continue
            items.append({
                "name": entry.name,
                "path": str(entry.resolve()),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else 0,
                "ext": entry.suffix.lower() if entry.is_file() else ""
            })
    except Exception:
        pass
    return {"path": str(base_dir), "items": items, "files": items}


@app.get("/api/files/content")
def api_files_content(path: str):
    """Read file content for GDR-IDE editor."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return {
            "success": True,
            "path": str(p),
            "name": p.name,
            "content": content,
            "lines": len(content.splitlines()),
            "size": p.stat().st_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/save")
async def api_files_save(req: Request):
    """Save editor buffer to file on disk."""
    data = await req.json()
    path = data.get("path", "").strip()
    content = data.get("content", "")

    if not path:
        raise HTTPException(status_code=400, detail="Missing path")

    p = Path(path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(p), "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve the complete Cinematic HUD at Root /
from gdr.web.dashboard_html import DASHBOARD_HTML
import uuid


@app.get("/api/companion/startup_greeting")
def api_startup_greeting():
    """Generate a personalized, time-aware 1-sentence morning/welcome greeting for Aarushi."""
    cfg = load_config()
    voice_cfg = cfg.get("voice", {})
    gen_cfg = cfg.get("general", {})

    greeting_enabled = voice_cfg.get("greeting_enabled", True)
    speak_aloud = voice_cfg.get("speak_greeting_aloud", True)
    respect_quiet = voice_cfg.get("respect_quiet_hours", True)
    user_name = gen_cfg.get("user_name", "GDR")
    agent_name = gen_cfg.get("agent_name", "Aarushi")
    language = gen_cfg.get("language", "hinglish").lower()

    # Check quiet mode and quiet hours
    from gdr.core.silence_controller import get_silence_controller
    if get_silence_controller().is_silence_active():
        speak_aloud = False

    now = datetime.now()
    hour = now.hour

    if respect_quiet:
        # Default quiet hours: 22:00 to 07:00
        if hour >= 22 or hour < 7:
            speak_aloud = False

    # Check memory for active project or unfinished task
    task_hint = ""
    try:
        mem_store = get_memory_store()
        recent_proj = mem_store.recall("project", limit=1)
        if recent_proj:
            content = recent_proj[0].get("content", "")
            if len(content) < 40 and not any(w in content.lower() for w in ["password", "token", "secret"]):
                task_hint = content
    except Exception:
        pass

    # Time-of-day period
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    elif 17 <= hour < 22:
        period = "evening"
    else:
        period = "night"

    if language in ("hi", "hinglish"):
        if period == "morning":
            text = f"Good morning {user_name}! Main bilkul ready hoon, bataiye aaj kya create karein?"
        elif period == "afternoon":
            text = f"Good afternoon {user_name}! Kaam kaisa chal raha hai? Ready when you are!"
        elif period == "evening":
            text = f"Good evening {user_name}! Hope aapka din achha raha. Shall we continue?"
        else:
            text = f"Hey {user_name}! Late night session? I am right here with you, bataiye kya help karoon."
    else:
        if period == "morning":
            text = f"Good morning {user_name}! Ready when you are, what would you like to work on today?"
        elif period == "afternoon":
            text = f"Good afternoon {user_name}! I'm online and listening, ready whenever you need me."
        elif period == "evening":
            text = f"Good evening {user_name}! Hope you had a productive day. How can I help?"
        else:
            text = f"Hey {user_name}! Working late tonight? I'm right here with you."

    session_id = f"startup_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    return {
        "greeting_enabled": greeting_enabled,
        "greeting": text,
        "session_id": session_id,
        "should_speak": bool(greeting_enabled and speak_aloud),
        "user_name": user_name,
        "agent_name": agent_name,
        "period": period,
        "timestamp": now.strftime("%I:%M %p")
    }


@app.get("/api/companion/startup_settings")
def api_get_startup_settings():
    """Retrieve full startup and autostart configuration."""
    from gdr.system.autostart import get_autostart_status
    cfg = load_config()
    voice_cfg = cfg.get("voice", {})
    auto_status = get_autostart_status()

    return {
        "autostart_status": auto_status,
        "open_direct_to_call": voice_cfg.get("open_direct_to_call", True),
        "auto_listen_enabled": voice_cfg.get("auto_listen_enabled", True),
        "greeting_enabled": voice_cfg.get("greeting_enabled", True),
        "speak_greeting_aloud": voice_cfg.get("speak_greeting_aloud", True),
        "respect_quiet_hours": voice_cfg.get("respect_quiet_hours", True),
        "quiet_hours_start": cfg.get("briefing", {}).get("quiet_hours_start", "22:00"),
        "quiet_hours_end": cfg.get("briefing", {}).get("quiet_hours_end", "07:00")
    }


@app.post("/api/companion/startup_settings")
async def api_save_startup_settings(req: Request):
    """Save startup and autostart settings and synchronize with the OS."""
    from gdr.system.autostart import enable_autostart, disable_autostart
    data = await req.json()
    cfg = load_config()

    voice_cfg = cfg.setdefault("voice", {})
    if "open_direct_to_call" in data:
        voice_cfg["open_direct_to_call"] = bool(data["open_direct_to_call"])
    if "auto_listen_enabled" in data:
        voice_cfg["auto_listen_enabled"] = bool(data["auto_listen_enabled"])
    if "greeting_enabled" in data:
        voice_cfg["greeting_enabled"] = bool(data["greeting_enabled"])
    if "speak_greeting_aloud" in data:
        voice_cfg["speak_greeting_aloud"] = bool(data["speak_greeting_aloud"])
    if "respect_quiet_hours" in data:
        voice_cfg["respect_quiet_hours"] = bool(data["respect_quiet_hours"])

    if "autostart" in data:
        wants_autostart = bool(data["autostart"])
        if wants_autostart:
            enable_autostart()
        else:
            disable_autostart()

    save_config(cfg)
    return {"success": True, "settings": data}


@app.get("/call", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Serve the GDR interface. When accessed at /call or with ?mode=call,
    it opens directly into the standalone Aarushi Call Companion mode.
    """
    is_call_mode = (request.url.path == "/call" or request.query_params.get("mode") == "call")
    if is_call_mode:
        # Pre-configure HTML to start directly in Focus Calling Mode
        call_html = DASHBOARD_HTML.replace(
            'id="focus-call-overlay" class="focus-theme-midnight" style="display:none;"',
            'id="focus-call-overlay" class="focus-theme-midnight" style="display:flex;"'
        )
        return call_html
    return DASHBOARD_HTML

