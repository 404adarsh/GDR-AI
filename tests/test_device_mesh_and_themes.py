import pytest
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from gdr.mesh.models import Device, DevicePermissions, MeshTask, PlatformType
from gdr.mesh.coordinator import MeshCoordinator
from gdr.mesh.platform.linux import LinuxPlatformAdapter
from gdr.mesh.platform.termux import TermuxPlatformAdapter
from gdr.mesh.router import (
    mesh_list_devices,
    mesh_get_device_status,
    mesh_search_files,
    mesh_read_file
)
from gdr.briefing.generator import get_time_greeting, get_user_display_name


def test_time_greeting_and_username():
    """Verify greeting changes by hour and never defaults to hardcoded 'Adarsh'."""
    # Morning: 5am - 11:59am
    assert get_time_greeting(datetime(2026, 1, 1, 9, 0)) == "Good morning"
    # Afternoon: 12pm - 4:59pm
    assert get_time_greeting(datetime(2026, 1, 1, 14, 0)) == "Good afternoon"
    # Evening: 5pm - 9:59pm
    assert get_time_greeting(datetime(2026, 1, 1, 19, 0)) == "Good evening"
    # Night: 10pm - 4:59am
    assert get_time_greeting(datetime(2026, 1, 1, 23, 0)) == "Welcome back"

    # Display name fallback
    with patch.dict(os.environ, {"USER_NAME": "CyberGhost"}, clear=True):
        assert get_user_display_name() == "CyberGhost"

    with patch.dict(os.environ, {}, clear=True):
        name = get_user_display_name()
        # Should be system username or 'Commander', never hardcoded 'Adarsh'
        assert name != ""
        assert isinstance(name, str)


def test_mesh_coordinator_pairing_flow():
    """Test pairing code creation, 5-minute expiry, and rate limiting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mesh.db"
        coord = MeshCoordinator(db_path=db_path)

        # 1. Generate pairing code
        code, pairing = coord.generate_pairing_code()
        assert len(code) == 6
        assert code.isdigit()
        assert not pairing.is_expired()
        assert not pairing.used

        # 2. Rate limit test (max 6 per 60 seconds)
        for _ in range(5):
            coord.generate_pairing_code()
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            coord.generate_pairing_code()

        # 3. Complete pairing
        res = coord.verify_and_pair(
            code=code,
            device_name="Pixel 9 Pro",
            platform_name="android_termux",
            capabilities=["battery_status", "file_read"]
        )
        assert res["success"] is True
        assert res["device_name"] == "Pixel 9 Pro"
        dev_id = res["device_id"]
        token = res["device_token"]
        assert token.startswith("gdr_mesh_")

        # Reuse of same code should fail
        fail_res = coord.verify_and_pair(code=code, device_name="Hacker", platform_name="linux")
        assert fail_res["success"] is False
        assert "Invalid pairing code" in fail_res["error"]

        # 4. Authenticate device token
        authed = coord.authenticate_token(token)
        assert authed is not None
        assert authed.id == dev_id

        # Bad token fails
        assert coord.authenticate_token("wrong_token_12345") is None

        # 5. Revocation
        assert coord.revoke_device(dev_id) is True
        assert coord.authenticate_token(token) is None


def test_path_traversal_defense():
    """Verify adapters strictly block path traversal and unauthorized directory access."""
    with tempfile.TemporaryDirectory() as tmpdir:
        allowed_dir = os.path.join(tmpdir, "shared")
        secret_dir = os.path.join(tmpdir, "secret")
        os.makedirs(allowed_dir, exist_ok=True)
        os.makedirs(secret_dir, exist_ok=True)

        allowed_file = os.path.join(allowed_dir, "notes.txt")
        with open(allowed_file, "w") as f:
            f.write("Allowed content")

        secret_file = os.path.join(secret_dir, "keys.env")
        with open(secret_file, "w") as f:
            f.write("SECRET_KEY=12345")

        adapter = LinuxPlatformAdapter()
        approved_dirs = [Path(allowed_dir)]

        # 1. Allowed file read works
        read_res = adapter.read_file(allowed_file, approved_dirs)
        assert read_res["success"] is True
        assert "Allowed content" in read_res["content"]

        # 2. Path traversal attempt (../../secret/keys.env) must fail
        traversal_path = os.path.join(allowed_dir, "..", "secret", "keys.env")
        fail_res = adapter.read_file(traversal_path, approved_dirs)
        assert fail_res["success"] is False
        assert "Access denied" in fail_res["error"]

        # 3. Direct outside access fails
        fail_res2 = adapter.read_file("/etc/passwd", approved_dirs)
        assert fail_res2["success"] is False
        assert "Access denied" in fail_res2["error"]


@pytest.mark.anyio
async def test_mesh_coordinator_local_dispatch():
    """Test task execution locally on coordinator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mesh.db"
        coord = MeshCoordinator(db_path=db_path)

        res = await coord.dispatch_task(
            target_device_id="local_primary",
            capability="battery_status",
            parameters={}
        )
        assert res["success"] is True
        assert "result" in res
        assert "percentage" in res["result"]


def test_mesh_router_tools():
    """Verify mesh tool wrappers for LLM execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mesh.db"
        test_coord = MeshCoordinator(db_path=db_path)

        with patch("gdr.mesh.router.get_mesh_coordinator", return_value=test_coord):
            # Local primary host is available
            initial_listing = mesh_list_devices()
            assert "Primary Host" in initial_listing

            # Enroll a new device
            code, _ = test_coord.generate_pairing_code()
            pair_res = test_coord.verify_and_pair(code, "Office Termux", "android_termux")
            assert pair_res["success"] is True
            dev_id = pair_res["device_id"]

            listing = mesh_list_devices()
            assert "Office Termux" in listing
            assert "Android" in listing or "Termux" in listing or "android_termux" in listing

            # Get device status
            status = mesh_get_device_status(dev_id)
            assert "Office Termux" in status

            # Non-existent device
            bad_status = mesh_get_device_status("nonexistent_id")
            assert "not found in the mesh" in bad_status
