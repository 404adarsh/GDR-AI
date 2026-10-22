"""Browser automation agent for blockbrain AI.
Fixes Playwright sync API cross-thread issues by using a dedicated worker thread with message queues.
Supports persistent user profiles, CDP connection to existing Chrome, tab awareness, and safe form filling.
"""

from pathlib import Path
import json
import os
import queue
import threading
import time
from typing import Dict, Any, Optional, List

from blockbrain.tools.registry import tool
from blockbrain.safety.untrusted import wrap_untrusted_content

BROWSER_DATA_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "browser_profile"
FORM_PROFILE_FILE = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "form_profile.json"


class BrowserWorker(threading.Thread):
    """Dedicated background thread managing Playwright to guarantee thread-affinity."""
    def __init__(self):
        super().__init__(name="blockbrain-Browser-Worker", daemon=True)
        self.req_queue = queue.Queue()
        self.resp_queue = queue.Queue()
        self.running = True
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.start()

    def run(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            self.playwright = p
            while self.running:
                try:
                    action, args = self.req_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                try:
                    handler = getattr(self, f"_handle_{action}", None)
                    if handler:
                        res = handler(**args)
                    else:
                        res = f"Error: Unknown browser action '{action}'"
                    self.resp_queue.put({"success": True, "result": res})
                except Exception as e:
                    self.resp_queue.put({"success": False, "error": str(e)})

    def execute(self, action: str, **kwargs) -> Any:
        self.req_queue.put((action, kwargs))
        res = self.resp_queue.get(timeout=60)
        if not res.get("success"):
            return f"Browser error: {res.get('error')}"
        return res.get("result")

    def _ensure_browser(self):
        if self.context is None:
            # First check if real Chrome is open with remote debugging on port 9222
            try:
                self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9222")
                self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
                self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
                return
            except Exception:
                pass

            # Otherwise launch persistent browser context
            BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_DATA_DIR),
                headless=True,
                viewport={"width": 1280, "height": 800}
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def _handle_open(self, url: str) -> str:
        self._ensure_browser()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
        title = self.page.title()
        return f"Navigated to '{url}' (Title: {title})"

    def _handle_get_content(self, max_chars: int = 5000) -> str:
        self._ensure_browser()
        text = self.page.inner_text("body")[:max_chars]
        title = self.page.title()
        url = self.page.url
        raw = f"URL: {url}\nTitle: {title}\n\nContent:\n{text}"
        return wrap_untrusted_content(f"web page ({url})", raw)

    def _handle_click(self, selector: str) -> str:
        self._ensure_browser()
        self.page.click(selector, timeout=10000)
        return f"Clicked element '{selector}'."

    def _handle_fill(self, selector: str, value: str) -> str:
        self._ensure_browser()
        self.page.fill(selector, value, timeout=10000)
        return f"Filled '{selector}' with value."

    def _handle_list_tabs(self) -> str:
        self._ensure_browser()
        tabs = []
        for idx, p in enumerate(self.context.pages):
            is_active = " [Active]" if p == self.page else ""
            tabs.append(f"Tab {idx}: {p.title()} ({p.url}){is_active}")
        return "\n".join(tabs) if tabs else "No open tabs."

    def _handle_screenshot(self, output_path: str = "/tmp/browser_page.png") -> str:
        self._ensure_browser()
        self.page.screenshot(path=output_path)
        return f"Saved screenshot to {output_path}."


_WORKER: Optional[BrowserWorker] = None


def get_worker() -> BrowserWorker:
    global _WORKER
    if _WORKER is None:
        _WORKER = BrowserWorker()
    return _WORKER


@tool(name="browser_open", description="Open URL in browser.", category="browser", tier="AUTO")
def browser_open(url: str) -> str:
    return get_worker().execute("open", url=url)


@tool(name="browser_get_content", description="Extract visible text from current browser page.", category="browser", tier="AUTO")
def browser_get_content(max_chars: int = 5000) -> str:
    return get_worker().execute("get_content", max_chars=max_chars)


@tool(name="browser_click", description="Click an element on page matching CSS selector or text.", category="browser", tier="AUTO")
def browser_click(selector: str) -> str:
    return get_worker().execute("click", selector=selector)


@tool(name="browser_fill", description="Fill a text input field on the current page.", category="browser", tier="AUTO")
def browser_fill(selector: str, value: str) -> str:
    return get_worker().execute("fill", selector=selector, value=value)


@tool(name="browser_list_tabs", description="List all open browser tabs and URLs.", category="browser", tier="AUTO")
def browser_list_tabs() -> str:
    return get_worker().execute("list_tabs")


@tool(name="browser_screenshot", description="Capture a screenshot of current web page.", category="browser", tier="AUTO")
def browser_screenshot(output_path: str = "/tmp/browser_page.png") -> str:
    return get_worker().execute("screenshot", output_path=output_path)


@tool(name="browser_submit_form", description="Submit a web form. Requires APPROVAL.", category="browser", tier="APPROVAL", requires_approval=True)
def browser_submit_form(submit_selector: str) -> str:
    """Submit a form on the active page after confirmation."""
    return get_worker().execute("click", selector=submit_selector)

