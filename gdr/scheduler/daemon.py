"""GDR Always-On Background Daemon (`gdrd`).
Manages the persistent scheduler, task queues, and channel listeners.
Designed to run as a systemd --user service.
"""

import signal
import sys
import time

from gdr.scheduler.engine import SchedulerEngine
from gdr.safety.panic import trigger_panic, clear_panic


def main():
    print("🚀 GDR AI Daemon (gdrd) starting...")
    engine = SchedulerEngine()

    def handle_shutdown(signum, frame):
        print("\n🛑 Shutting down gdrd daemon gracefully...")
        engine.stop()
        sys.exit(0)

    def handle_panic(signum, frame):
        print("\n🚨 Panic signal received by gdrd.")
        trigger_panic()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, handle_panic)

    engine.start()
    print("✅ gdrd daemon active and monitoring scheduled routines.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        handle_shutdown(None, None)


if __name__ == "__main__":
    main()

