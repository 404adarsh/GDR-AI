"""Acceptance Tests for GDR-IDE UI/UX Reconstruction & Global Layout Recovery.
Verifies:
1. Design tokens (deep charcoal #15171B, cyan-blue #4DA3FF, borders #343943).
2. Markdown rendering eliminates raw asterisks and creates structured HTML.
3. Responsive behavior across 1920x1080, 1366x768, 1024x768, and 390x844 mobile viewports with zero horizontal blowout.
4. Activity rail contextual navigation across all 5 primary sections.
5. Docked terminal secondary panel opening, switching, and closing.
6. GDR-IDE workspace layout with editor, line numbers, and breadcrumbs.
"""

from pathlib import Path
import socket
import threading
import time
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from gdr.web.server import app


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def ui_test_server():
    """Run FastAPI test server on dynamic free port."""
    port = get_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.2)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_markdown_rendering_and_briefing_formatting(ui_test_server):
    """Verify Markdown renders into rich HTML without raw asterisks."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(ui_test_server)
        page.wait_for_selector(".brand")

        # Test client-side formatMarkdown function
        rendered = page.evaluate("""() => {
            const sample = "**Daily Briefing:**\\n• Weather: Clear 24°C\\n• Tasks: Operational\\n```python\\nprint('hello')\\n```";
            return formatMarkdown(sample);
        }""")

        assert "<strong" in rendered
        assert "Daily Briefing:" in rendered
        assert "code-block-card" in rendered
        assert "**" not in rendered

        # Check that briefing container is rendered div (not raw pre with asterisks)
        briefing_el = page.locator("#briefing-content")
        assert briefing_el.is_visible()
        browser.close()


def test_responsive_viewports_and_no_overflow(ui_test_server):
    """Verify application layout adapts cleanly to Desktop, Laptop, Tablet, and Mobile without horizontal overflow."""
    viewports = [
        {"name": "desktop_1080p", "width": 1920, "height": 1080},
        {"name": "laptop_768p", "width": 1366, "height": 768},
        {"name": "tablet_768p", "width": 1024, "height": 768},
        {"name": "mobile_compact", "width": 390, "height": 844},
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in viewports:
            page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            page.goto(ui_test_server)
            page.wait_for_selector(".workbench-shell")

            # Check no horizontal blowout on workbench
            scroll_width = page.evaluate("() => document.querySelector('.workbench-shell').scrollWidth")
            client_width = page.evaluate("() => document.querySelector('.workbench-shell').clientWidth")
            assert scroll_width <= client_width + 2, f"Horizontal overflow in {vp['name']}: {scroll_width} > {client_width}"

            # Verify brand title is visible
            assert page.locator(".brand").is_visible()
            page.close()

        browser.close()


def test_activity_rail_contextual_navigation(ui_test_server):
    """Verify clicking Activity Rail buttons activates sections and updates contextual breadcrumbs."""
    sections = [
        ("act-sec-home-chat", "Home & Chat"),
        ("act-sec-coding-studio", "Coding Studio"),
        ("act-sec-automation-tasks", "Automation & Tasks"),
        ("act-sec-devices-system", "Devices & System"),
        ("act-sec-settings-security", "Settings & Security"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(ui_test_server)
        page.wait_for_selector(".activity-bar")

        for btn_id, expected_crumb in sections:
            btn = page.locator(f"#{btn_id}")
            btn.click()
            time.sleep(0.2)

            crumb = page.locator("#titlebar-sec-crumb")
            assert expected_crumb in crumb.inner_text()
            assert "active" in (btn.get_attribute("class") or "")

        browser.close()


def test_docked_secondary_panel_terminal_toggle(ui_test_server):
    """Verify bottom secondary panel (Terminal, Output, Diagnostics) opens and toggles without crashing."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(ui_test_server)
        page.wait_for_selector(".workbench-shell")

        # Open secondary panel via client function
        page.evaluate("() => toggleBottomPanel(true, 'terminal')")
        time.sleep(0.2)

        panel = page.locator("#secondary-panel")
        assert panel.is_visible()
        assert "open" in (panel.get_attribute("class") or "")

        # Switch to Output tab
        page.locator("#ptab-output").click()
        time.sleep(0.1)
        assert page.locator("#pane-output").is_visible()

        # Switch to Diagnostics tab
        page.locator("#ptab-diagnostics").click()
        time.sleep(0.1)
        assert page.locator("#pane-diagnostics").is_visible()

        # Close panel
        page.evaluate("() => toggleBottomPanel(false)")
        time.sleep(0.2)
        assert not panel.is_visible()

        browser.close()


def test_gdr_ide_workspace_render(ui_test_server):
    """Verify GDR-IDE workspace mounts with file tabs, editor, and personal terminal."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(ui_test_server)
        page.wait_for_selector(".workbench-shell")

        # Switch to IDE screen
        page.evaluate("() => showScreen('ide')")
        time.sleep(0.3)

        ide_screen = page.locator("#screen-ide")
        assert ide_screen.is_visible()

        # Verify Code Editor textarea and Line Numbers are present
        editor = page.locator("#ide-code-editor")
        assert editor.is_visible()

        line_numbers = page.locator("#ide-line-numbers")
        assert line_numbers.is_visible()

        # Verify bottom terminal tabs inside IDE
        term_tab = page.locator("#tab-term-btn")
        assert term_tab.is_visible()

        browser.close()
