"""Tests for Autostart Installation & Background Companion Service.
Verifies cross-platform autostart configuration, PID-lock enforcement,
and single-instance daemon lifecycle.
"""

from pathlib import Path
import tempfile
import time
import pytest

from gdr.system.autostart import LinuxAutostart, DarwinAutostart, WindowsAutostart, get_autostart_status
from gdr.system.companion_service import CompanionService


def test_linux_autostart_lifecycle():
    """Verify Linux XDG desktop autostart entry creation and cleanup."""
    with tempfile.TemporaryDirectory() as td:
        xdg_dir = Path(td) / "autostart"
        service_dir = Path(td) / "systemd" / "user"

        orig_xdg = LinuxAutostart._xdg_dir
        orig_desktop = LinuxAutostart._desktop_file
        orig_sysd = LinuxAutostart._systemd_dir
        orig_svc = LinuxAutostart._service_file

        try:
            LinuxAutostart.XDG_DIR = xdg_dir
            LinuxAutostart.DESKTOP_FILE = xdg_dir / "gdr-aarushi.desktop"
            LinuxAutostart.SYSTEMD_DIR = service_dir
            LinuxAutostart.SERVICE_FILE = service_dir / "gdr-aarushi.service"

            # 1. Enable autostart
            assert LinuxAutostart.enable() is True
            assert LinuxAutostart.DESKTOP_FILE.exists()
            content = LinuxAutostart.DESKTOP_FILE.read_text()
            assert "Aarushi AI Companion" in content
            assert "--background" in content

            # 2. Check status
            st = LinuxAutostart.get_status()
            assert st["installed"] is True
            assert st["mechanism"] == "xdg_desktop"

            # 3. Disable autostart
            assert LinuxAutostart.disable() is True
            assert not LinuxAutostart.DESKTOP_FILE.exists()
        finally:
            LinuxAutostart.XDG_DIR = orig_xdg
            LinuxAutostart.DESKTOP_FILE = orig_desktop
            LinuxAutostart.SYSTEMD_DIR = orig_sysd
            LinuxAutostart.SERVICE_FILE = orig_svc


def test_darwin_autostart_lifecycle():
    """Verify macOS LaunchAgent plist creation and removal."""
    with tempfile.TemporaryDirectory() as td:
        agents_dir = Path(td) / "LaunchAgents"

        orig_dir = DarwinAutostart.AGENTS_DIR
        orig_plist = DarwinAutostart.PLIST_FILE

        try:
            DarwinAutostart.AGENTS_DIR = agents_dir
            DarwinAutostart.PLIST_FILE = agents_dir / "com.gdr.aarushi.plist"

            assert DarwinAutostart.enable() is True
            assert DarwinAutostart.PLIST_FILE.exists()
            plist_text = DarwinAutostart.PLIST_FILE.read_text()
            assert "com.gdr.aarushi" in plist_text
            assert "RunAtLoad" in plist_text

            st = DarwinAutostart.get_status()
            assert st["installed"] is True

            assert DarwinAutostart.disable() is True
            assert not DarwinAutostart.PLIST_FILE.exists()
        finally:
            DarwinAutostart.AGENTS_DIR = orig_dir
            DarwinAutostart.PLIST_FILE = orig_plist


def test_windows_autostart_lifecycle():
    """Verify Windows startup folder batch file creation and removal."""
    with tempfile.TemporaryDirectory() as td:
        startup_dir = Path(td) / "Startup"

        orig_func = WindowsAutostart._get_startup_folder
        WindowsAutostart._get_startup_folder = classmethod(lambda cls: startup_dir)

        try:
            assert WindowsAutostart.enable() is True
            bat_file = startup_dir / "GDR-Aarushi.bat"
            assert bat_file.exists()
            content = bat_file.read_text()
            assert "Aarushi" in content

            assert WindowsAutostart.disable() is True
            assert not bat_file.exists()
        finally:
            WindowsAutostart._get_startup_folder = orig_func


def test_companion_service_pid_lock():
    """Verify single-instance PID locking in companion service."""
    with tempfile.TemporaryDirectory() as td:
        cfg_dir = Path(td)
        svc = CompanionService(config_dir=cfg_dir)

        # Initially not running
        st1 = svc.get_status()
        assert st1["running"] is False

        # Simulate PID file creation with active process
        import os
        pid_file = cfg_dir / "companion.pid"
        pid_file.write_text(str(os.getpid()))

        st2 = svc.get_status()
        assert st2["running"] is True
        assert st2["pid"] == os.getpid()

        # Starting when already running must fail
        assert svc.start() is False

