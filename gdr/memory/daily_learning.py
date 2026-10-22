"""Daily Learning & Personalized Session Summaries for Aarushi AI.
Generates comprehensive end-of-day recaps and provides morning recall of previous day's work,
completed items, unfinished tasks, and project continuity without fabricating details.
"""

from datetime import datetime, date, timedelta
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from gdr.memory.store import get_memory_store
from gdr.system.timeline import get_timeline_tracker
from gdr.system.wellbeing import get_wellbeing_manager
from gdr.tools.registry import tool

logger = logging.getLogger("gdr.memory.daily_learning")


class DailyLearningManager:
    """Consolidates daily work sessions, unfinished tasks, and morning recall."""

    def __init__(self):
        self.store = get_memory_store()
        self.timeline = get_timeline_tracker()
        self.wellbeing = get_wellbeing_manager()

    def record_completed_task(self, task_name: str, project: Optional[str] = None):
        """Record a completed task for today."""
        today = date.today().isoformat()
        key = f"task_done_{today}_{task_name.lower().replace(' ', '_')[:30]}"
        content = json.dumps({
            "task": task_name,
            "project": project or "General",
            "date": today,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
        self.store.remember(key, content, category="episodic_memory", importance=4)

    def record_unfinished_task(self, task_name: str, project: Optional[str] = None, next_step: Optional[str] = None):
        """Record an unfinished task or blocker to resume later."""
        today = date.today().isoformat()
        clean_name = task_name.lower().replace(" ", "_")[:30]
        key = f"task_pending_{clean_name}"
        content = json.dumps({
            "task": task_name,
            "project": project or "General",
            "next_step": next_step or "",
            "date_recorded": today,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        })
        self.store.remember(key, content, category="project_memory", importance=4)

    def generate_daily_summary(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate day's timeline, completed features, unfinished tasks, and wellbeing."""
        dt_str = target_date or date.today().isoformat()
        stats = self.timeline.get_daily_stats(dt_str)
        events = self.timeline.get_events(dt_str)

        # Retrieve completed tasks for target date
        all_episodic = self.store.list_by_category("episodic_memory")
        completed = []
        for it in all_episodic:
            if dt_str in it.get("key", ""):
                try:
                    data = json.loads(it["content"])
                    if data.get("status") == "completed":
                        completed.append(data.get("task"))
                except Exception:
                    pass

        # Retrieve pending tasks
        all_proj = self.store.list_by_category("project_memory")
        pending = []
        for it in all_proj:
            if "task_pending_" in it.get("key", ""):
                try:
                    data = json.loads(it["content"])
                    if data.get("status") == "pending":
                        pending.append(data.get("task"))
                except Exception:
                    pass

        active_sec = stats.get("total_active_seconds", 0.0)
        active_hours = round(active_sec / 3600, 1)

        summary_text = (
            f"Daily Summary for {dt_str}:\n"
            f"• Active Work Time: ~{active_hours} hours\n"
            f"• Machine Starts: {stats.get('boot_count', 1)}\n"
            f"• Breaks Taken: {stats.get('breaks_taken', 0)}\n"
            f"• Projects: {', '.join(stats.get('projects', [])) or 'General'}\n"
            f"• Completed: {', '.join(completed) if completed else 'None recorded'}\n"
            f"• Unfinished Tasks: {', '.join(pending) if pending else 'None'}"
        )

        return {
            "date": dt_str,
            "active_hours": active_hours,
            "boot_count": stats.get("boot_count", 1),
            "breaks_taken": stats.get("breaks_taken", 0),
            "projects": stats.get("projects", []),
            "completed_tasks": completed,
            "pending_tasks": pending,
            "summary_text": summary_text
        }

    def get_morning_recall(self) -> str:
        """Provide morning greeting summarizing yesterday's work and offering to resume pending tasks."""
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        summary = self.generate_daily_summary(yesterday_str)

        projects = summary.get("projects", [])
        completed = summary.get("completed_tasks", [])
        pending = summary.get("pending_tasks", [])

        proj_desc = f" on {', '.join(projects)}" if projects else ""

        lines = [f"Good morning! Yesterday, you worked{proj_desc}."]
        if completed:
            lines.append(f"You completed: {', '.join(completed[:3])}.")

        if pending:
            task_str = pending[0]
            lines.append(f"You have an unfinished task: '{task_str}'. Would you like to continue from where you left off?")
        else:
            lines.append("You're all caught up on planned tasks. What would you like to build today?")

        return " ".join(lines)


_GLOBAL_DAILY_LEARNING: Optional[DailyLearningManager] = None


def get_daily_learning_manager() -> DailyLearningManager:
    global _GLOBAL_DAILY_LEARNING
    if _GLOBAL_DAILY_LEARNING is None:
        _GLOBAL_DAILY_LEARNING = DailyLearningManager()
    return _GLOBAL_DAILY_LEARNING


# ==============================================================================
# LLM Accessible Tools
# ==============================================================================

@tool(name="record_task_completed", category="memory", tier="AUTO")
def record_task_completed_tool(task_name: str, project: Optional[str] = None) -> str:
    """Record that a task or feature has been completed in the day's session."""
    dl = get_daily_learning_manager()
    dl.record_completed_task(task_name, project)
    return f"Recorded completed task: '{task_name}'."


@tool(name="record_unfinished_task", category="memory", tier="AUTO")
def record_unfinished_task_tool(task_name: str, project: Optional[str] = None, next_step: Optional[str] = None) -> str:
    """Record an unfinished task or blocker to be resumed in future sessions."""
    dl = get_daily_learning_manager()
    dl.record_unfinished_task(task_name, project, next_step)
    return f"Recorded unfinished task: '{task_name}' (will recall at next startup)."


@tool(name="get_daily_summary_report", category="memory", tier="AUTO")
def get_daily_summary_report_tool(target_date: Optional[str] = None) -> str:
    """Get the full daily summary report including active work time, projects, completed, and pending tasks."""
    dl = get_daily_learning_manager()
    data = dl.generate_daily_summary(target_date)
    return data["summary_text"]

