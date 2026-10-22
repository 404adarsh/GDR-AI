"""Background Task Manager & Real-Time Progress Tracker for GDR AI.

Enables simultaneous task execution (downloads, builds, scans, shell routines)
while keeping the conversational agent responsive across all interfaces.
Provides live progress notifications every 5 to 10 seconds detailing:
- What has been completed so far ("how much it did")
- What remains ("how much it left")
- Time elapsed & estimated remaining time (ETA)
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable
import uuid

logger = logging.getLogger("gdr.core.tasks")


@dataclass
class TaskProgress:
    task_id: str
    name: str
    description: str
    status: str = "running"  # "running", "completed", "failed", "paused"
    total_steps: int = 100
    completed_steps: int = 0
    started_at: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    status_message: str = "In progress..."
    result: Optional[str] = None
    error: Optional[str] = None

    @property
    def percentage(self) -> int:
        if self.total_steps <= 0:
            return 0
        return min(100, max(0, int((self.completed_steps / self.total_steps) * 100)))

    @property
    def elapsed_seconds(self) -> int:
        return int(time.time() - self.started_at)

    @property
    def estimated_remaining_seconds(self) -> int:
        pct = self.percentage
        if pct <= 0:
            return 30
        elapsed = self.elapsed_seconds
        total_estimated = elapsed / (pct / 100.0)
        return max(0, int(total_estimated - elapsed))

    def format_progress_report(self) -> str:
        """Generate a natural progress statement describing completion and remainder."""
        pct = self.percentage
        elapsed = self.elapsed_seconds
        remaining = self.estimated_remaining_seconds

        did = f"{pct}% completed ({self.completed_steps}/{self.total_steps} steps, {elapsed}s elapsed)"
        left = f"~{remaining}s remaining" if remaining > 0 else "finishing up"
        msg = f" • [{self.status_message}]" if self.status_message else ""
        return f"⚡ Task '{self.name}': {did}. {left}{msg}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "percentage": self.percentage,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "elapsed_seconds": self.elapsed_seconds,
            "remaining_seconds": self.estimated_remaining_seconds,
            "status_message": self.status_message,
            "started_at": datetime.fromtimestamp(self.started_at).strftime("%I:%M:%S %p"),
            "report": self.format_progress_report()
        }


class TaskProgressTracker:
    """Singleton tracker for simultaneous background operations with periodic notifications."""

    _instance: Optional["TaskProgressTracker"] = None

    def __new__(cls) -> "TaskProgressTracker":
        if cls._instance is None:
            cls._instance = super(TaskProgressTracker, cls).__new__(cls)
            cls._instance._tasks: Dict[str, TaskProgress] = {}
            cls._instance._lock = threading.Lock()
            cls._instance._listeners: List[Callable[[str], None]] = []
            cls._instance._start_progress_notifier()
        return cls._instance

    def _start_progress_notifier(self):
        """Background daemon thread reporting active tasks every 5-8 seconds."""
        def _loop():
            while True:
                time.sleep(6.0)
                try:
                    active = self.get_active_tasks()
                    if active:
                        for task in active:
                            report = task.format_progress_report()
                            # Record to timeline and notify listeners
                            try:
                                from gdr.system.timeline import get_os_timeline
                                get_os_timeline().record_event("TASK_PROGRESS", report)
                            except Exception:
                                pass
                            for listener in list(self._listeners):
                                try:
                                    listener(report)
                                except Exception:
                                    pass
                except Exception as e:
                    logger.debug(f"Progress notifier notice: {e}")

        t = threading.Thread(target=_loop, daemon=True, name="TaskProgressNotifierThread")
        t.start()

    def add_progress_listener(self, callback: Callable[[str], None]):
        """Subscribe to 5-10 second progress notifications."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def register_task(
        self,
        name: str,
        description: str = "",
        total_steps: int = 100,
        task_id: Optional[str] = None
    ) -> TaskProgress:
        """Register a new long-running task."""
        t_id = task_id or f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        task = TaskProgress(
            task_id=t_id,
            name=name,
            description=description or name,
            total_steps=max(1, total_steps)
        )
        with self._lock:
            self._tasks[t_id] = task
        logger.info(f"Registered background task #{t_id}: {name}")
        return task

    def update_progress(
        self,
        task_id: str,
        completed_steps: int,
        status_message: str = ""
    ):
        """Update ongoing progress for a task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == "running":
                task.completed_steps = min(task.total_steps, max(0, completed_steps))
                task.last_update = time.time()
                if status_message:
                    task.status_message = status_message

    def complete_task(self, task_id: str, result_message: str = "Completed successfully"):
        """Mark task as successfully completed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "completed"
                task.completed_steps = task.total_steps
                task.result = result_message
                task.status_message = result_message
                task.last_update = time.time()
        try:
            from gdr.system.timeline import get_os_timeline
            get_os_timeline().record_event("TASK_COMPLETED", f"Completed: {task.name if task else task_id}")
        except Exception:
            pass

    def fail_task(self, task_id: str, error_message: str = "Task failed"):
        """Mark task as failed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = "failed"
                task.error = error_message
                task.status_message = f"Failed: {error_message}"
                task.last_update = time.time()

    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_active_tasks(self) -> List[TaskProgress]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == "running"]

    def get_all_tasks(self) -> List[TaskProgress]:
        with self._lock:
            return list(self._tasks.values())

    def get_overall_summary(self) -> str:
        """Provide a consolidated natural language summary of all active tasks."""
        active = self.get_active_tasks()
        if not active:
            return "No active background tasks running right now. All nominal."
        lines = [t.format_progress_report() for t in active]
        return "\n".join(lines)


def get_task_tracker() -> TaskProgressTracker:
    return TaskProgressTracker()


def run_simultaneous_task(
    name: str,
    worker_fn: Callable[[Callable[[int, str], None]], Any],
    description: str = "",
    total_steps: int = 100
) -> str:
    """Execute a complex long-running job in background thread with live 5-10s tracking.

    Returns immediately with task_id so conversational agent can continue talking simultaneously!
    """
    tracker = get_task_tracker()
    task = tracker.register_task(name=name, description=description, total_steps=total_steps)

    def _bg_runner():
        def _update(step: int, msg: str = ""):
            tracker.update_progress(task.task_id, completed_steps=step, status_message=msg)

        try:
            result = worker_fn(_update)
            tracker.complete_task(task.task_id, result_message=str(result or "Completed"))
        except Exception as e:
            tracker.fail_task(task.task_id, error_message=str(e))

    t = threading.Thread(target=_bg_runner, daemon=True, name=f"TaskWorker-{task.task_id}")
    t.start()

    return task.task_id

