"""Dynamic skill and plugin loader for blockbrain AI.
Scans ~/.blockbrain/skills/ for custom Python tools and provides Model Context Protocol (MCP) client support.
"""

import importlib.util
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from blockbrain.tools.registry import tool, _TOOL_REGISTRY

SKILLS_DIR = Path(os.environ.get("blockbrain_SKILLS_DIR", Path.home() / ".blockbrain" / "skills"))


def load_user_skills() -> List[str]:
    """Scan ~/.blockbrain/skills/ and import any Python tool files."""
    loaded = []
    if not SKILLS_DIR.exists():
        try:
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            return loaded

    for py_file in SKILLS_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        module_name = f"blockbrain_custom_skill_{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(py_file))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                loaded.append(py_file.name)
        except Exception as e:
            print(f"⚠️ Failed to load skill {py_file.name}: {e}")

    return loaded


@tool(name="list_skills", description="List custom skills and plugins loaded from ~/.blockbrain/skills.", category="skills", tier="AUTO")
def list_skills() -> str:
    loaded = load_user_skills()
    if not loaded:
        return f"No custom skills found in {SKILLS_DIR}. Drop any .py file decorated with @tool there to extend blockbrain AI."
    return f"Loaded custom skills:\n" + "\n".join(f"• {s}" for s in loaded)

