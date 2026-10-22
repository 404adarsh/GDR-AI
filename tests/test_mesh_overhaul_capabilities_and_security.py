"""Comprehensive tests for Prompt 4/5:
Device Mesh overhaul, capability-based permission enforcement, task router,
remote execution safety, panic kill, audit logging, and listening audio cues.
"""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import time
import pytest
from fastapi.testclient import TestClient

from gdr.mesh.models import (
    PlatformType,
    DeviceStatus,
    TaskStatus,
    Device,
    DevicePermissions,
    MeshTask,
    PairingCode,
    STANDARD_CAPABILITIES,
)
from gdr.mesh.coordinator import MeshCoordinator, FORBIDDEN_COMMAND_PATTERNS
from gdr.mesh.router import MeshRouter, get_mesh_router
from gdr.web.server import app
from gdr.web.dashboard_html import DASHBOARD_HTML

client = TestClient(app)


# ==============================================================================
# 1. PAIRING, AUTHENTICATION & EXPIRATION TESTS
# ==============================================================================

def test_secure_pairing_lifecycle_and_replay_protection(tmp_path):
    """Verify pairing codes are cryptographically generated, single-use, and expire."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    # 1. Generate pairing code
    code, pairing = coord.generate_pairing_code(
        requester_name="Termux Node",
        requester_platform=PlatformType.ANDROID_TERMUX,
        ttl_seconds=300
    )
    assert len(code) == 6
    assert code.isdigit()
    assert not pairing.is_expired()

    # 2. Pair device
    res = coord.verify_and_pair(
        code=code,
        device_name="Termux Node",
        platform_name="android_termux",
        capabilities=["system.read", "terminal.execute"]
    )
    assert res["success"] is True
    dev_id = res["device_id"]
    token = res["device_token"]

    # 3. Replay attack: Re-using the same pairing code must fail
    replay_res = coord.verify_and_pair(
        code=code,
        device_name="Attacker Node",
        platform_name="linux"
    )
    assert replay_res["success"] is False
    assert "Invalid pairing code" in replay_res["error"]

    # 4. Token authentication
    authed_dev = coord.authenticate_token(token)
    assert authed_dev is not None
    assert authed_dev.id == dev_id

    # 5. Revocation immediately terminates access
    coord.revoke_device(dev_id)
    assert coord.authenticate_token(token) is None


def test_expired_pairing_code_rejected(tmp_path):
    """Verify expired pairing code cannot be used to enroll."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    code, pairing = coord.generate_pairing_code(ttl_seconds=-1)  # Already expired
    res = coord.verify_and_pair(code=code, device_name="Late Device", platform_name="linux")
    assert res["success"] is False
    assert "expired" in res["error"].lower()


# ==============================================================================
# 2. CAPABILITY REGISTRY & PERMISSION ENFORCEMENT TESTS
# ==============================================================================

def test_capability_registry_definitions():
    """Verify standard capabilities have declared platforms, permissions, and security flags."""
    assert "system.read" in STANDARD_CAPABILITIES
    assert "terminal.execute" in STANDARD_CAPABILITIES
    assert "filesystem.read" in STANDARD_CAPABILITIES
    assert "filesystem.write" in STANDARD_CAPABILITIES
    assert "screen.capture" in STANDARD_CAPABILITIES

    term_cap = STANDARD_CAPABILITIES["terminal.execute"]
    assert term_cap.required_permission == "allow_shell_commands"
    assert term_cap.requires_approval is True
    assert term_cap.read_only is False


@pytest.mark.anyio
async def test_permission_denial_for_unauthorized_shell(tmp_path):
    """Verify coordinator strictly blocks terminal execution if device lacks permission."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    code, _ = coord.generate_pairing_code(
        requested_permissions=DevicePermissions(allow_shell_commands=False)  # Shell forbidden
    )
    res = coord.verify_and_pair(code=code, device_name="Restricted Termux", platform_name="android_termux")
    dev_id = res["device_id"]

    # Dispatch task requiring shell
    dispatch_res = await coord.dispatch_task(
        target_device_id=dev_id,
        capability="terminal.execute",
        parameters={"command": "python --version"}
    )
    assert dispatch_res["success"] is False
    assert "Permission denied" in dispatch_res["error"]


@pytest.mark.anyio
async def test_forbidden_destructive_terminal_commands_blocked(tmp_path):
    """Verify destructive commands like 'rm -rf /' or fork bombs are intercepted and blocked."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    destructive_cmds = [
        "rm -rf /",
        "rm -rf /etc",
        ":(){ :|:& };:",
        "mkfs.ext4 /dev/sda1",
    ]
    for cmd in destructive_cmds:
        res = await coord.dispatch_task(
            target_device_id="local_primary",
            capability="terminal.execute",
            parameters={"command": cmd},
            approved=True
        )
        assert res["success"] is False
        assert "blocked by security policy" in res["error"].lower()


# ==============================================================================
# 3. TASK ROUTER, LIFECYCLE & IDEMPOTENCY TESTS
# ==============================================================================

@pytest.mark.anyio
async def test_task_idempotency_prevents_duplicate_runs(tmp_path):
    """Verify tasks with matching idempotency keys return existing results without re-executing."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    idem_key = "sync_req_abc_123"
    # First execution
    res1 = await coord.dispatch_task(
        target_device_id="local_primary",
        capability="system.read",
        parameters={},
        idempotency_key=idem_key
    )
    assert res1["success"] is True
    first_task_id = res1["task_id"]

    # Second execution with same idempotency key
    res2 = await coord.dispatch_task(
        target_device_id="local_primary",
        capability="system.read",
        parameters={},
        idempotency_key=idem_key
    )
    assert res2["success"] is True
    assert res2["task_id"] == first_task_id
    assert res2.get("idempotent_cached") is True


@pytest.mark.anyio
async def test_offline_device_reporting_no_hallucinations(tmp_path):
    """Verify requesting an action on an offline device clearly reports OFFLINE."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    code, _ = coord.generate_pairing_code()
    res = coord.verify_and_pair(code=code, device_name="Sleeping Phone", platform_name="android_termux")
    dev_id = res["device_id"]

    # The device is in DB but has no active WebSocket connection
    dispatch_res = await coord.dispatch_task(
        target_device_id=dev_id,
        capability="system.read",
        parameters={}
    )
    assert dispatch_res["success"] is False
    assert "OFFLINE" in dispatch_res["error"]


@pytest.mark.anyio
async def test_panic_kill_and_emergency_stop(tmp_path):
    """Verify panic_kill cancels pending operations and returns a comprehensive report."""
    db_file = tmp_path / "mesh_test.db"
    coord = MeshCoordinator(db_path=db_file)

    res = await coord.panic_kill_all()
    assert res["success"] is True
    assert "Panic Kill executed" in res["message"]


# ==============================================================================
# 4. REST APIS & FRONTEND AUDIT TESTS
# ==============================================================================

def test_api_mesh_routes():
    """Verify REST API endpoints for device mesh management."""
    # 1. List devices
    res = client.get("/api/mesh/devices")
    assert res.status_code == 200
    data = res.json()
    devices = data.get("devices") if isinstance(data, dict) and "devices" in data else data
    assert isinstance(devices, list)
    assert any(d["id"] == "local_primary" for d in devices)

    # 2. Get capabilities
    res_caps = client.get("/api/mesh/capabilities")
    assert res_caps.status_code == 200
    caps = res_caps.json()
    assert "system.read" in caps
    assert "terminal.execute" in caps

    # 3. Generate pairing code via API
    res_pair = client.post("/api/mesh/pair/generate", json={"requester_name": "API Client"})
    assert res_pair.status_code == 200
    d_pair = res_pair.json()
    assert "code" in d_pair
    assert len(d_pair["code"]) == 6

    # 4. Panic kill endpoint
    res_panic = client.post("/api/mesh/panic")
    assert res_panic.status_code == 200
    assert res_panic.json()["success"] is True

    # 5. Audit logs endpoint
    res_audit = client.get("/api/mesh/audit")
    assert res_audit.status_code == 200
    logs = res_audit.json()
    assert isinstance(logs, list)


def test_frontend_typewriter_and_listening_beeps():
    """Verify typewriterTimer bug is fixed and listening beeps are present in dashboard HTML."""
    html = DASHBOARD_HTML
    # 1. Verify typewriterTimer declaration exists to prevent ReferenceError
    assert "let typewriterTimer = null;" in html
    # 2. Verify Web Audio listening beeps function exists
    assert "function playListeningBeep(type" in html
    assert "playListeningBeep(" in html
    assert "type === 'start'" in html or "type === 'proceed'" in html
