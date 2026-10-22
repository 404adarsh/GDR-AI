"""Scheduler execution engine for GDR AI.
Polls SQLite job store, dispatches reminders, executes scheduled agent routines, and handles recurrence.
"""

from datetime import datetime
import threading
import time
from typing import Optional
from croniter import croniter

from gdr.scheduler.store import get_job_store, JobStore
from gdr.voice.tts import TextToSpeech
from gdr.channels.push import send_push
from gdr.safety.panic import is_panicked


class SchedulerEngine:
    def __init__(self, store: Optional[JobStore] = None):
        self.store = store or get_job_store()
        self.running = False
        self.tts = TextToSpeech()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, name="GDR-Scheduler-Engine", daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self):
        while self.running:
            if is_panicked():
                time.sleep(2.0)
                continue

            try:
                due_jobs = self.store.get_due_jobs()
                for job in due_jobs:
                    self._execute_job(job)
            except Exception as e:
                print(f"⚠️ Scheduler loop error: {e}")

            time.sleep(2.0)

    def _execute_job(self, job: dict):
        job_id = job["id"]
        desc = job["description"]
        prompt = job["prompt"]
        is_reminder = bool(job["is_reminder_only"])
        sched_type = job["schedule_type"]
        sched_expr = job["schedule_expr"]

        print(f"\n⏰ [JOB TRIGGERED] ID: {job_id} | {desc}")
        self.store.update_job_status(job_id, "running")

        # 1. Delivery
        if is_reminder:
            # Deliver spoken reminder + push notification
            send_push(f"Reminder: {desc}", prompt, priority="high")
            try:
                self.tts.speak(f"Reminder: {prompt}")
            except Exception:
                pass
        else:
            # Execute agent task in background
            try:
                from gdr.core.agent import Agent
                agent = Agent()
                output = agent.run(prompt)
                send_push(f"Completed: {desc}", output[:300])
            except Exception as e:
                send_push(f"Task Failed: {desc}", str(e), priority="high")

        # 2. Rescheduling for recurring cron
        if sched_type == "cron":
            now = datetime.now()
            itr = croniter(sched_expr, now)
            next_run = itr.get_next(datetime)
            self.store.update_job_status(job_id, "pending", next_run_at=next_run)
            print(f"🔄 Recurring job {job_id} rescheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.store.update_job_status(job_id, "completed")

