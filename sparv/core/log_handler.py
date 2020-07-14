"""Handler for Snakemake log messages."""
import os
import re
import sys
import time
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from alive_progress import alive_bar
from snakemake import logger

from sparv.core import paths
from sparv.util.misc import SparvErrorMessage


class LogHandler:
    """Class providing a log handler for Snakemake."""

    icon = "\U0001f426"

    def __init__(self, progressbar=False, summary=False):
        """Initialize log handler.

        Args:
            progressbar: Set to True to enable progress bar. Disabled by default.
            summary: Set to True to write a final summary (elapsed time). Disabled by default.
        """
        self.use_progressbar = progressbar
        self.show_summary = summary
        self.finished = False
        self.messages = defaultdict(list)
        self.missing_configs = None
        self.missing_configs_re = None
        self.missing_configs_annotators = defaultdict(list)
        self.handled_missing_configs = set()
        self.start_time = time.time()

        # Progress bar related variables
        self.bar_mgr = None
        self.exit = lambda *x: None
        self.bar = None
        self.last_percentage = 0

    def setup_bar(self, total: int):
        """Initialize the progress bar."""
        print()
        self.bar_mgr = (alive_bar(total, enrich_print=False, title=LogHandler.icon, length=30))
        self.exit = type(self.bar_mgr).__exit__
        self.bar = type(self.bar_mgr).__enter__(self.bar_mgr)

    def log_handler(self, msg):
        """Log handler for Snakemake displaying a progress bar."""
        def read_log_files(log_type: str):
            """Find log files tied to this process and return log messages."""
            messages = []
            for log_file in paths.log_dir.glob("{}.*.{}.*".format(os.getpid(), log_type)):
                log_info = re.match(r"\d+\.\d+\." + log_type + r"\.([^.]+)\.([^.]+)", log_file.stem)
                assert log_info, "Could not parse log file name: {}".format(log_file)
                messages.append((*log_info.groups(), log_file.read_text()))
                log_file.unlink()
            return messages

        level = msg["level"]

        if level == "run_info" and self.use_progressbar:
            if self.bar is None:
                # Get number of jobs
                jobs: str = msg["msg"].split("\t")[-1]
                if jobs.isdigit():
                    self.setup_bar(int(jobs))

        elif level == "progress":
            if self.use_progressbar:
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

        elif level == "job_info" and self.use_progressbar:
            if msg["msg"] and self.bar is not None:
                if msg["msg"].startswith("EXIT_MESSAGE: "):
                    self.messages["final"].append(msg["msg"][14:])
                else:
                    # Only update status message, don't advance progress
                    self.bar.text(msg["msg"])

        elif level == "info":
            if msg["msg"] == "Nothing to be done.":
                logger.text_handler(msg)

        elif level == "error":
            handled = False

            # SparvErrorMessage exception from pipeline core
            if "SparvErrorMessage" in msg["msg"]:
                # Parse error message
                message = re.search(
                    r"{}([^\n]*)\n([^\n]*)\n(.*?){}".format(SparvErrorMessage.start_marker,
                                                            SparvErrorMessage.end_marker),
                    msg["msg"])
                if message:
                    self.messages["error"].append(message.groups())
                    handled = True

            # Exit status 123 means a SparvErrorMessage exception saved to file
            elif "exit status 123" in msg["msg"] or ("SystemExit" in msg["msg"] and "123" in msg["msg"]):
                self.messages["error"].extend(read_log_files("error"))
                handled = True

            # Errors due to missing config variables
            elif "MissingInputException" in msg["msg"] or "MissingOutputException" in msg["msg"]:
                config_variable = self.missing_configs_re.search(msg["msg"])
                if config_variable:
                    handled = True
                    annotator = self.missing_configs[config_variable.group(1)]
                    if annotator not in self.handled_missing_configs:
                        self.handled_missing_configs.add(annotator)
                        for message in self.missing_configs_annotators[annotator]:
                            self.messages["error"].append((*annotator, message))

            # Unhandled errors
            if not handled:
                self.messages["real_error"].append(msg)

        elif level in ("warning", "job_error"):
            # Save other errors and warnings for later
            self.messages["real_error"].append(msg)

        elif level == "dag_debug" and "job" in msg:
            # If a module can't be used due to missing config variables, a log is created. Read those log files and
            # save to a dictionary.
            if self.missing_configs is None:
                self.missing_configs = {}
                for log in read_log_files("missing_config"):
                    annotator = tuple(log[0:2])
                    for line in log[2].splitlines()[1:]:
                        self.missing_configs[line.lstrip("- ")] = annotator
                    self.missing_configs_annotators[annotator].append(log[2])

            self.missing_configs_re = re.compile(r"\[({})\]".format("|".join(self.missing_configs.keys())))

            # Check the rules used by the current operation, and see if any is unusable
            if msg["status"] == "selected":
                job_name = tuple(str(msg["job"]).split("::"))
                if job_name in self.missing_configs_annotators and job_name not in self.handled_missing_configs:
                    self.handled_missing_configs.add(job_name)
                    for error_message in self.missing_configs_annotators[job_name]:
                        self.messages["error"].append(*job_name, error_message)

    def stop(self):
        """Stop the progress bar and output any error messages."""
        # Make sure this is only run once
        if not self.finished:
            # Stop progress bar
            if self.bar is not None:
                self.exit(self.bar_mgr, None, None, None)

            self.finished = True

            # Remove Snakemake log file if empty (which it will be unless errors occurred)
            snakemake_log_file = logger.get_logfile()
            if snakemake_log_file is not None:
                log_file = Path(snakemake_log_file)
                if log_file.is_file() and log_file.stat().st_size == 0:
                    log_file.unlink()

            print()

            # Print user-friendly error messages
            if self.messages["error"]:
                logger.logger.error("Job execution failed with the following message{}:".format(
                    "s" if len(self.messages) > 1 else ""))
                for message in self.messages["error"]:
                    module_name, f_name, msg = message
                    logger.logger.error("\n[{}:{}]\n{}".format(module_name, f_name, msg))
            # Defer to Snakemake's default log handler for other errors
            elif self.messages["real_error"]:
                for error in self.messages["real_error"]:
                    logger.text_handler(error)
            elif self.messages["final"]:
                for message in self.messages["final"]:
                    logger.logger.info(message)

            if self.show_summary:
                if self.messages:
                    print()
                elapsed = round(time.time() - self.start_time)
                logger.logger.info("Time elapsed: {}".format(timedelta(seconds=elapsed)))
