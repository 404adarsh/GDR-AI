"""Lifelong Personal Memory Engine for Aarushi AI.
Maintains persistent personal profile, structured project memory, episodic memories,
and procedural instructions across sessions, reboots, and updates.
Prevents credential leakage, handles deduplication and contradiction resolution.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from gdr.memory.store import (
    MemoryStore,
    get_memory_store,
    normalize_category,
    contains_sensitive_credentials,
)
from gdr.tools.registry import tool

logger = logging.getLogger("gdr.memory.lifelong")


class LifelongMemoryEngine:
    """High-level lifelong memory manager for Aarushi."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or get_memory_store()

    # 1. Personal Profile
    def set_profile_fact(self, key: str, value: str, source: str = "user_confirmed") -> str:
        """Set a persistent personal profile fact (name, style, preferences, goals)."""
        return self.store.save_personal_profile(key, value, source_type=source)

    def get_profile(self) -> Dict[str, Any]:
        """Get user profile attributes."""
        return self.store.get_personal_profile()

    # 2. Project Memory
    def update_project(
        self,
        project_name: str,
        purpose: str = "",
        tech_stack: str = "",
        state: str = "",
        completed_features: Optional[List[str]] = None,
        bugs: Optional[List[str]] = None,
        decisions: Optional[List[str]] = None,
        blockers: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        project_path: Optional[str] = None,
    ) -> str:
        """Store or update verified project memory."""
        return self.store.save_project_context(
            project_name=project_name,
            purpose=purpose,
            tech_stack=tech_stack,
            state=state,
            completed_features=completed_features,
            bugs=bugs,
            decisions=decisions,
            blockers=blockers,
            next_steps=next_steps,
            project_path=project_path,
        )

    def get_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored project memory."""
        return self.store.get_project_context(project_name)

    def list_all_projects(self) -> List[Dict[str, Any]]:
        """List all tracked projects."""
        return self.store.list_projects()

    # 3. Procedural Memory
    def save_workflow(
        self,
        workflow_name: str,
        steps: List[str],
        commands: Optional[List[str]] = None,
        context: str = "",
    ) -> str:
        """Store verified procedures and workflows."""
        return self.store.save_procedure(workflow_name, steps, commands, context)

    def get_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve verified procedure steps and commands."""
        return self.store.get_procedure(workflow_name)

    # 4. Episodic Memory
    def record_episode(
        self,
        title: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        importance: int = 3,
    ) -> str:
        """Record a meaningful event or discussion from a session."""
        key = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title.lower().replace(' ', '_')}"
        payload = {
            "title": title,
            "summary": summary,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }
        return self.store.remember(
            key=key,
            content=json.dumps(payload),
            category="episodic_memory",
            importance=importance,
            source_type="observed_event",
        )

    # 5. Search, Contradiction & Export
    def search(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search memories across all categories with relevance scoring."""
        return self.store.recall(query=query, limit=limit, category=category)

    def update_contradiction(self, key: str, new_content: str, reason: str = "User correction") -> str:
        """Update a contradictory fact and preserve data integrity."""
        return self.store.resolve_contradiction(key, new_content, reason=reason)

    def export_data(self, format_type: str = "json") -> str:
        """Export all stored lifelong memories."""
        return self.store.export_memories(export_format=format_type)


_GLOBAL_LIFELONG_ENGINE: Optional[LifelongMemoryEngine] = None


def get_lifelong_memory() -> LifelongMemoryEngine:
    global _GLOBAL_LIFELONG_ENGINE
    if _GLOBAL_LIFELONG_ENGINE is None:
        _GLOBAL_LIFELONG_ENGINE = LifelongMemoryEngine()
    return _GLOBAL_LIFELONG_ENGINE


# ==============================================================================
# LLM Accessible Tools
# ==============================================================================

@tool(name="save_project_memory", category="memory", tier="AUTO")
def save_project_memory_tool(
    project_name: str,
    state: str,
    purpose: str = "",
    tech_stack: str = "",
    next_steps: Optional[List[str]] = None,
    blockers: Optional[List[str]] = None,
) -> str:
    """Save or update structured context for a project (state, purpose, blockers, next steps)."""
    engine = get_lifelong_memory()
    return engine.update_project(
        project_name=project_name,
        purpose=purpose,
        tech_stack=tech_stack,
        state=state,
        next_steps=next_steps,
        blockers=blockers,
    )


@tool(name="get_project_memory", category="memory", tier="AUTO")
def get_project_memory_tool(project_name: str) -> str:
    """Retrieve verified memory and recent state for a project."""
    engine = get_lifelong_memory()
    data = engine.get_project(project_name)
    if not data:
        return f"No recorded memory found for project '{project_name}'."
    return json.dumps(data, indent=2)


@tool(name="save_procedural_workflow", category="memory", tier="AUTO")
def save_procedural_workflow_tool(
    workflow_name: str,
    steps: List[str],
    commands: Optional[List[str]] = None,
) -> str:
    """Save verified recurring workflow instructions or developer procedures."""
    engine = get_lifelong_memory()
    return engine.save_workflow(workflow_name=workflow_name, steps=steps, commands=commands)


@tool(name="get_procedural_workflow", category="memory", tier="AUTO")
def get_procedural_workflow_tool(workflow_name: str) -> str:
    """Retrieve verified recurring instructions or commands for a workflow."""
    engine = get_lifelong_memory()
    data = engine.get_workflow(workflow_name)
    if not data:
        return f"No procedural workflow found for '{workflow_name}'."
    return json.dumps(data, indent=2)

