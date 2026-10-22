"""Night Shift task execution runner.
Executes background tasks overnight with automatic redirection of APPROVAL actions to the morning queue.
"""

from datetime import datetime
from typing import Dict, Any, List

from gdr.night_shift.queue import NightShiftStore, queue_for_approval
from gdr.core.agent import Agent
from gdr.channels.push import send_push


def _night_shift_approval_callback(tool_name: str, args: Dict[str, Any]) -> bool:
    """Overnight, GDR must never execute sensitive tools autonomously.
    Queues them in the approval queue and returns False to the tool runner.
    """
    appr_id = queue_for_approval(tool_name, args, reason="Queued overnight by Night Shift")
    print(f"🌙 [NIGHT SHIFT] Action '{tool_name}' intercepted and queued for morning approval (#{appr_id}).")
    return False


def run_night_shift() -> str:
    """Execute all pending night shift tasks."""
    store = NightShiftStore()
    tasks = [t for t in store.list_tasks() if t.get("status") == "pending"]

    if not tasks:
        return "No pending night shift tasks found."

    print(f"\n🌙 Running Night Shift: {len(tasks)} tasks queued...")
    results = []

    for task in tasks:
        task_id = task["id"]
        goal = task["goal"]
        print(f"\n👉 Executing Night Task #{task_id}: '{goal}'...")
        store.update_task(task_id, "running")

        agent = Agent(approval_callback=_night_shift_approval_callback)
        prompt = (
            f"You are running in overnight NIGHT SHIFT mode.\n"
            f"Goal: {goal}\n"
            f"Important: Do NOT attempt to ask the user interactive questions. "
            f"Prepare full drafts, research, analysis, or local file changes. "
            f"Any sending/deleting action will be intercepted and queued for morning approval."
        )

        try:
            report = agent.run(prompt, is_night_shift=True)
            store.update_task(task_id, "completed", report=report)
            results.append(f"• Task #{task_id} ({goal}): Completed.\n  Summary: {report[:200]}...")
        except Exception as e:
            store.update_task(task_id, "failed", report=f"Error: {e}")
            results.append(f"• Task #{task_id} ({goal}): Failed ({e}).")

    summary = "\n".join(results)
    send_push("🌙 Night Shift Complete", f"Completed {len(tasks)} overnight tasks.\n\n{summary[:250]}...")
    return summary

