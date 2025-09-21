#!/usr/bin/env python
import os
import sys
import signal
import time

from .scheduler import Scheduler
from .checkers import PingChecker, HttpChecker, HttpsChecker
from .checkers import SpeedtestChecker, IPerfChecker, IPerf3Checker

def main() -> int:
    """Application entry point"""
    scheduler = Scheduler()

    # Add checkers with optional initial delay
    scheduler.add_checker(PingChecker(), initial_delay=2)
    scheduler.add_checker(HttpChecker(), initial_delay=5)
    scheduler.add_checker(HttpsChecker(), initial_delay=5)
    scheduler.add_checker(SpeedtestChecker(), initial_delay=10)
    scheduler.add_checker(IPerfChecker(), initial_delay=10)
    scheduler.add_checker(IPerf3Checker(), initial_delay=10)

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        print("Starting monitoring scheduler...")
        scheduler.start()

        # Keep main thread alive
        while scheduler.is_running:
            time.sleep(1)

    except Exception as e:
        print(f"Fatal error: {e}")
        scheduler.stop()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
