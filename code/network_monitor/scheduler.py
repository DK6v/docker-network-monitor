import datetime
import time
import threading
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from .checkers import BaseChecker

@dataclass
class ScheduledTask:
    """Data class for scheduled task"""
    checker: BaseChecker
    next_time: datetime.datetime
    interval: int = 0
    enabled: bool = True

class Scheduler:
    """Main scheduler class for managing monitoring tasks"""

    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.is_running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event: threading.Event = threading.Event()

    def add_checker(self, checker: BaseChecker, initial_delay: int = 0) -> None:
        """
        Add a checker to the scheduler

        Args:
            checker: Checker instance to add
            initial_delay: Initial delay in seconds before first run
        """
        if checker.enabled():
            next_time = datetime.datetime.now() + datetime.timedelta(seconds=initial_delay)
            task = ScheduledTask(checker=checker, next_time=next_time)
            self.tasks.append(task)
            print(f"Added checker: {checker.__class__.__name__}, first run at: {next_time}")
        else:
            print(f"Checker disabled: {checker.__class__.__name__}")

    def remove_checker(self, checker_class_name: str) -> bool:
        """
        Remove a checker by class name

        Args:
            checker_class_name: Name of the checker class to remove

        Returns:
            bool: True if removed, False if not found
        """
        for task in self.tasks:
            if task.checker.__class__.__name__ == checker_class_name:
                self.tasks.remove(task)
                print(f"Removed checker: {checker_class_name}")
                return True
        return False

    def start(self) -> None:
        """Start the scheduler in a background thread"""
        if not self.tasks:
            raise ValueError("No checkers added to scheduler")

        if self.is_running:
            print("Scheduler is already running")
            return

        self.is_running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler"""
        if not self.is_running:
            return

        self.is_running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5.0)
        print("Scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop running in background thread"""
        while self.is_running and not self.stop_event.is_set():
            try:
                self._run_pending_tasks()
                self._sleep_until_next_task()
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                time.sleep(1)  # Prevent tight error loop

    def _run_pending_tasks(self) -> None:
        """Execute all tasks that are due to run"""
        current_time = datetime.datetime.now()

        for task in self.tasks:
            if task.enabled and task.next_time <= current_time:
                try:
                    print(f"Running checker: {task.checker.__class__.__name__}")
                    interval = task.checker.check()
                    task.interval = interval
                    task.next_time = current_time + datetime.timedelta(seconds=interval)
                    print(f"Next run for {task.checker.__class__.__name__} at: {task.next_time}")
                except Exception as e:
                    print(f"Error running checker {task.checker.__class__.__name__}: {e}")
                    # Retry after short delay on error
                    task.next_time = current_time + datetime.timedelta(seconds=30)

    def _sleep_until_next_task(self) -> None:
        """Calculate and sleep until next task execution"""
        if not self.tasks:
            time.sleep(1)
            return

        current_time = datetime.datetime.now()
        next_time = min(task.next_time for task in self.tasks if task.enabled)

        if next_time > current_time:
            sleep_time = (next_time - current_time).total_seconds()
            # Sleep in small intervals to allow for quick shutdown
            max_sleep = min(sleep_time, 1.0)  # Sleep max 1 second at a time
            self.stop_event.wait(timeout=max_sleep)

    def get_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            'running': self.is_running,
            'task_count': len(self.tasks),
            'next_run': min(task.next_time for task in self.tasks) if self.tasks else None,
            'tasks': [
                {
                    'checker': task.checker.__class__.__name__,
                    'enabled': task.enabled,
                    'interval': task.interval,
                    'next_run': task.next_time
                }
                for task in self.tasks
            ]
        }

    def enable_checker(self, checker_class_name: str) -> bool:
        """Enable a specific checker"""
        for task in self.tasks:
            if task.checker.__class__.__name__ == checker_class_name:
                task.enabled = True
                return True
        return False

    def disable_checker(self, checker_class_name: str) -> bool:
        """Disable a specific checker"""
        for task in self.tasks:
            if task.checker.__class__.__name__ == checker_class_name:
                task.enabled = False
                return True
        return False
