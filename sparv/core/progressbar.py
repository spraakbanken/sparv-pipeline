"""Handler for Snakemake log messages."""
import sys
from pathlib import Path

from alive_progress import alive_bar
from snakemake import logger


class ProgressLogger:
    """Class providing a log handler for Snakemake"""

    icon = "\U0001f426"

    def __init__(self):
        self.bar_mgr = None
        self.exit = lambda *x: None
        self.bar = None
        self.stopped = True
        self.last_percentage = 0

    def setup_bar(self, total: int):
        """Initialize the progress bar."""
        print()
        self.bar_mgr = (alive_bar(total, enrich_print=False, title=ProgressLogger.icon, length=30))
        self.exit = type(self.bar_mgr).__exit__
        self.bar = type(self.bar_mgr).__enter__(self.bar_mgr)
        self.stopped = False

    def log_handler(self, msg):
        """Log handler for Snakemake displaying a progress bar."""

        level = msg["level"]

        if level == "run_info":
            if self.bar is None:
                # Get number of jobs
                jobs: str = msg["msg"].split("\t")[-1]
                if jobs.isdigit():
                    self.setup_bar(int(jobs))

        elif level == "progress":
            # Set up progress bar if needed
            if self.bar is None:
                self.setup_bar(msg["total"])

            # Advance progress
            self.bar()

            # Print regular updates if output is not a terminal (i.e. doesn't support the progress bar)
            if not sys.stdout.isatty():
                percentage = (100 * msg["done"]) // msg["total"]
                if percentage > self.last_percentage:
                    self.last_percentage = percentage
                    print(f"Progress: {percentage}%")

            if msg["done"] == msg["total"]:
                self.stop()

        elif level == "job_info":
            if msg["msg"] and self.bar is not None:
                # Only update status message, don't advance progress
                self.bar(text=ProgressLogger.icon + "  " + msg["msg"], incr=0)

        elif level == "info":
            if msg["msg"] == "Nothing to be done.":
                print(msg["msg"])

        # Defer to Snakemake's default log handler for some types of messages
        elif level in ("warning", "error", "job_error"):
            logger.text_handler(msg)

    def stop(self):
        """Stop the progress bar."""
        if not self.stopped:
            self.exit(self.bar_mgr, None, None, None)
            self.stopped = True

            # Remove Snakemake log file if empty (which it will be unless errors occurred)
            log_file = Path(logger.get_logfile())
            if log_file.is_file() and log_file.stat().st_size == 0:
                log_file.unlink()

            print()


def minimal_log_handler(msg):
    """Minimal log handler for Snakemake, forwarding important messages to the default
    handler while silencing the rest."""

    # Defer to Snakemake's default log handler for some types of messages
    if msg["level"] in ("warning", "error", "job_error"):
        logger.text_handler(msg)
