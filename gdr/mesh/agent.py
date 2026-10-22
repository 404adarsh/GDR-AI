"""GDR-AI Mesh Client Agent.
Runs on enrolled devices (Android Termux, Linux, Windows, macOS), maintains
an authenticated connection to the coordinator, and executes authorized tasks
with safety checks and panic-kill responsiveness.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
from typing import Dict, Any, Optional

from gdr.mesh.platform.base import BasePlatformAdapter, get_platform_adapter

logger = logging.getLogger("gdr.mesh.agent")

FORBIDDEN_COMMAND_PATTERNS = [
    r"\brm\s+-(?:[a-zA-Z]*r[a-zA-Z]*f|[a-zA-Z]*f[a-zA-Z]*r)\s+/(?:$|\s|etc|var|usr|bin|boot|dev|sys|proc)",
    r"\bmkfs\b",
    r":\(\)\s*\{",
    r"\bdd\s+if=/dev/zero\s+of=/dev/sd",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bchown\s+-R\s+.*\s+/",
    r">\s*/dev/sd[a-z]",
]

MAX_OUTPUT_CHARS = 50_000


class MeshAgent:
    """Agent running on a client device in the mesh."""

    def __init__(
        self,
        coordinator_url: str,
        device_token: str,
        device_id: Optional[str] = None,
        adapter: Optional[BasePlatformAdapter] = None
    ):
        self.coordinator_url = coordinator_url.rstrip("/")
        if self.coordinator_url.startswith("https://"):
            self.ws_url = "wss://" + self.coordinator_url[8:] + "/ws/mesh/device"
        elif self.coordinator_url.startswith("http://"):
            self.ws_url = "ws://" + self.coordinator_url[7:] + "/ws/mesh/device"
        else:
            self.ws_url = f"ws://{self.coordinator_url}/ws/mesh/device"

        self.device_token = device_token
        self.device_id = device_id
        self.adapter = adapter or get_platform_adapter()
        self._running = False
        self._ws = None
        self._active_task: Optional[asyncio.Task] = None

    async def run(self):
        """Main agent loop: connect, send telemetry, listen for tasks, auto-reconnect."""
        try:
            import websockets
        except ImportError:
            logger.error("Websockets library required for MeshAgent. Install with 'pip install websockets'.")
            return

        self._running = True
        backoff = 2.0

        while self._running:
            try:
                headers = {"Authorization": f"Bearer {self.device_token}"}
                logger.info(f"Connecting to Mesh Coordinator at {self.ws_url}...")
                async with websockets.connect(self.ws_url, extra_headers=headers) as ws:
                    self._ws = ws
                    backoff = 2.0
                    logger.info("✅ Connected to GDR-AI Device Mesh coordinator!")

                    heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
                    try:
                        async for message in ws:
                            await self._handle_message(ws, message)
                    finally:
                        heartbeat_task.cancel()
            except Exception as e:
                if not self._running:
                    break
                logger.warning(f"Connection lost to Mesh Coordinator: {e}. Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

    async def _heartbeat_loop(self, ws):
        """Send system metrics and battery heartbeat every 25 seconds."""
        while self._running:
            try:
                metrics = self.adapter.get_system_info()
                battery = self.adapter.get_battery_status()
                payload = {
                    "type": "heartbeat",
                    "metrics": metrics,
                    "battery": battery,
                    "timestamp": time.time(),
                }
                await ws.send(json.dumps(payload))
            except Exception as e:
                logger.debug(f"Heartbeat send failed: {e}")
                break
            await asyncio.sleep(25.0)

    async def _handle_message(self, ws, message_text: str):
        """Process incoming task requests, cancellations, and panic kill signals."""
        try:
            data = json.loads(message_text)
        except Exception:
            return

        msg_type = data.get("type")

        if msg_type == "panic_kill":
            logger.warning("🚨 PANIC KILL received from coordinator: aborting active task.")
            if self._active_task and not self._active_task.done():
                self._active_task.cancel()
            return

        if msg_type == "task_cancel":
            logger.info(f"Task cancel requested for {data.get('task_id')}")
            if self._active_task and not self._active_task.done():
                self._active_task.cancel()
            return

        if msg_type == "task_request":
            task_id = data.get("task_id")
            capability = data.get("capability")
            params = data.get("parameters", {})

            # Launch task
            self._active_task = asyncio.create_task(self.execute_task(capability, params))
            try:
                res = await self._active_task
            except asyncio.CancelledError:
                res = {"success": False, "error": "Task cancelled by emergency stop."}

            response_payload = {
                "type": "task_result",
                "task_id": task_id,
                "success": res.get("success", False),
                "result": res.get("result"),
                "error": res.get("error"),
            }
            try:
                await ws.send(json.dumps(response_payload))
            except Exception as e:
                logger.warning(f"Failed to return task result: {e}")
            finally:
                self._active_task = None

    async def execute_task(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a local task based on capability."""
        approved_dirs = self.adapter.resolve_approved_directories(
            params.get("allowed_directories", ["~/Downloads", "~/Documents", "~/storage/shared/Documents"])
        )

        try:
            if capability in ("sys_info", "system_info", "system.read"):
                return {"success": True, "result": self.adapter.get_system_info()}

            elif capability in ("battery_status", "battery"):
                return {"success": True, "result": self.adapter.get_battery_status()}

            elif capability in ("file_search", "search_files", "filesystem.read"):
                q = params.get("query", "")
                results = self.adapter.search_files(q, approved_dirs)
                return {"success": True, "result": results}

            elif capability in ("file_read", "read_file"):
                p = params.get("path", "")
                return self.adapter.read_file(p, approved_dirs)

            elif capability in ("diagnostic_check", "diagnostic"):
                cmd = params.get("command", "uptime")
                return self.adapter.execute_diagnostic(cmd)

            elif capability in ("terminal.execute", "terminal", "shell"):
                cmd = params.get("command", "").strip()
                if not cmd:
                    return {"success": False, "error": "No command provided."}

                for pat in FORBIDDEN_COMMAND_PATTERNS:
                    if re.search(pat, cmd, re.IGNORECASE):
                        return {"success": False, "error": "Command blocked by security policy."}

                timeout = params.get("timeout", 20)
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                    out_text = (stdout.decode(errors="replace") or stderr.decode(errors="replace"))[:MAX_OUTPUT_CHARS]
                    return {
                        "success": proc.returncode == 0,
                        "result": out_text,
                        "error": stderr.decode(errors="replace") if proc.returncode != 0 else None,
                        "returncode": proc.returncode,
                    }
                except asyncio.TimeoutError:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    return {"success": False, "error": f"Execution timed out after {timeout} seconds."}

            elif capability in ("notifications.send", "notification"):
                title = params.get("title", "GDR-AI")
                msg = params.get("message", "")
                # Try Termux notification first
                if shutil.which("termux-notification"):
                    subprocess.run(["termux-notification", "--title", title, "--content", msg], check=False)
                    return {"success": True, "result": f"Termux notification posted: '{title}'"}
                elif shutil.which("notify-send"):
                    subprocess.run(["notify-send", title, msg], check=False)
                    return {"success": True, "result": f"Desktop notification posted: '{title}'"}
                return {"success": True, "result": f"Notification logged: '{title}: {msg}'"}

            elif capability in ("process.inspect", "processes"):
                res = self.adapter.execute_diagnostic("ps aux")
                return res

            else:
                return {"success": False, "error": f"Unknown capability '{capability}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self):
        self._running = False
        if self._ws:
            try:
                asyncio.create_task(self._ws.close())
            except Exception:
                pass
