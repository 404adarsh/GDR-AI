"""Tests for Digital Activity Timeline & Native OS Lifecycle Tracking.
Verifies differentiation of OS boot vs service restart, natural language timeline queries,
heartbeat tracking, and inferred shutdown detection.
"""

from datetime import datetime, date
import json
from pathlib import Path
import tempfile
import time
import pytest

from gdr.system.timeline import ActivityTimelineTracker, get_native_os_boot_time


@pytest.fixture
def temp_timeline_tracker():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_timeline.db"
        tracker = ActivityTimelineTracker(db_path=db_path, device_id="test_node_01")
        yield tracker, db_path


def test_boot_vs_service_restart_distinction(temp_timeline_tracker):
    """Verify that restarting the companion service does NOT increment OS boot count."""
    tracker1, db_path = temp_timeline_tracker
    stats1 = tracker1.get_daily_stats()
    assert stats1["boot_count"] == 1

    events1 = [e["event_type"] for e in tracker1.get_events()]
    assert "os_boot" in events1
    assert "service_start" in events1

    # Simulate Aarushi service or application restarting without machine rebooting
    tracker2 = ActivityTimelineTracker(db_path=db_path, device_id="test_node_01")
    stats2 = tracker2.get_daily_stats()
    assert stats2["boot_count"] == 1  # Boot count MUST remain 1!

    events2 = [e["event_type"] for e in tracker2.get_events()]
    assert "service_restart" in events2


def test_natural_language_timeline_queries(temp_timeline_tracker):
    """Verify natural query answering for startup time, uptime, and shutdowns."""
    tracker, _ = temp_timeline_tracker

    # 1. PC Boot query
    ans_boot = tracker.answer_activity_query("When did I turn on my PC today?")
    assert "turned on your PC today at" in ans_boot or "was booted at" in ans_boot

    # 2. PC Uptime query
    ans_uptime = tracker.answer_activity_query("How long has my PC been running?")
    assert "running for approximately" in ans_uptime

    # 3. Boot count query
    ans_count = tracker.answer_activity_query("How many times did I start my computer today?")
    assert "1 time" in ans_count

    # 4. Shutdown query when still running
    ans_shutdown = tracker.answer_activity_query("When did I shut down my computer?")
    assert "No computer shutdown has been recorded" in ans_shutdown


def test_activity_heartbeat_and_work_sessions(temp_timeline_tracker):
    """Verify heartbeat and coding session tracking accumulate active time and projects."""
    tracker, _ = temp_timeline_tracker

    tracker.record_user_activity("coding_session", project="GDR-Agent")
    tracker.heartbeat(active=True, project="GDR-Agent")

    stats = tracker.get_daily_stats()
    assert stats["total_active_seconds"] >= 60.0
    assert "GDR-Agent" in stats["projects"]

    timeline_lines = tracker.format_readable_timeline()
    assert any("Coding session active" in line for line in timeline_lines)


def test_inferred_shutdown_after_unexpected_termination():
    """Verify that if an earlier session had no clean shutdown, an inferred shutdown is logged on next boot."""
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_timeline.db"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
        CREATE TABLE boot_sessions (
            boot_session_id TEXT PRIMARY KEY,
            os_boot_time REAL NOT NULL,
            device_id TEXT NOT NULL,
            first_detected REAL NOT NULL,
            last_heartbeat REAL,
            clean_shutdown INTEGER DEFAULT 0
        );
        """)
        conn.execute("""
        CREATE TABLE timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boot_session_id TEXT NOT NULL,
            service_session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            iso_time TEXT NOT NULL,
            date_str TEXT NOT NULL,
            reliability TEXT DEFAULT 'measured',
            details_json TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE daily_summaries (
            date_str TEXT PRIMARY KEY,
            boot_count INTEGER DEFAULT 0,
            total_active_seconds REAL DEFAULT 0.0,
            total_idle_seconds REAL DEFAULT 0.0,
            service_uptime_seconds REAL DEFAULT 0.0,
            ide_active_seconds REAL DEFAULT 0.0,
            breaks_taken INTEGER DEFAULT 0,
            projects_json TEXT,
            summary_text TEXT,
            updated_at TEXT
        );
        """)
        # Pre-populate DB with an unclosed previous session from today
        now = time.time()
        today_str = date.today().isoformat()
        conn.execute(
            "INSERT INTO boot_sessions VALUES ('boot_prev_dead_session', ?, 'test_node_01', ?, ?, 0)",
            (now - 7200, now - 7200, now - 3600)
        )
        conn.commit()
        conn.close()

        # Start tracker: this will detect the dead session and record an inferred shutdown
        tracker = ActivityTimelineTracker(db_path=db_path, device_id="test_node_01")
        events = tracker.get_events(today_str)
        shutdown_events = [e for e in events if e["event_type"] == "os_shutdown"]
        assert len(shutdown_events) >= 1
        assert shutdown_events[0]["reliability"] == "inferred"

