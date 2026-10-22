"""blockbrain Always-On Background Daemon (`blockbraind`).
Manages the persistent scheduler, task queues, and channel listeners.
Designed to run as a systemd --user service.
"""

import signal
import sys
import time

from blockbrain.scheduler.engine import SchedulerEngine
from blockbrain.safety.panic import trigger_panic, clear_panic


def main():
    print("🚀 blockbrain AI Daemon (blockbraind) starting...")
    engine = SchedulerEngine()

    def handle_shutdown(signum, frame):
        print("\n🛑 Shutting down blockbraind daemon gracefully...")
        engine.stop()
        sys.exit(0)

    def handle_panic(signum, frame):
        print("\n🚨 Panic signal received by blockbraind.")
        trigger_panic()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGUSR1, handle_panic)

    engine.start()
    print("✅ blockbraind daemon active and monitoring scheduled routines.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        handle_shutdown(None, None)


if __name__ == "__main__":
    main()

