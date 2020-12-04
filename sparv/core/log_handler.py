"""Handler for log messages, both from the logging library and from Snakemake."""
import datetime
import logging
import logging.handlers
import os
import pickle
import re
import socketserver
import struct
import threading
import time
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Optional

import rich.progress as progress
from rich.logging import RichHandler
from rich.text import Text
from snakemake import logger

from sparv.core import paths
from sparv.core.console import console
from sparv.util.misc import SparvErrorMessage

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s - %(name)s (%(process)d) - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"

# Add internal logging level used for non-logging-related communication from child processes to log handler
INTERNAL = 100
logging.addLevelName(INTERNAL, "INTERNAL")


def export_dirs(self, dirs):
    """Send list of export dirs to log handler."""
    if self.isEnabledFor(INTERNAL):
        self._log(INTERNAL, "export_dirs", (), extra={"export_dirs": dirs})


# Add log function to logger
logging.export_dirs = export_dirs
logging.Logger.export_dirs = export_dirs

# Messages from the Sparv core
messages = {
    "missing_configs": defaultdict(set),
    "missing_binaries": defaultdict(set),
    "missing_classes": defaultdict(set)
}


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Handler for streaming logging requests."""

    def handle(self):
        """Handle multiple requests - each expected to be a 4-byte length followed by the LogRecord in pickle format."""
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = pickle.loads(chunk)
            record = logging.makeLogRecord(obj)
            self.handle_log_record(record)

    @staticmethod
    def handle_log_record(record):
        """Handle log record."""
        sparv_logger = logging.getLogger("sparv_logging")
        sparv_logger.handle(record)


class LogLevelCounterHandler(logging.Handler):
    """Handler that counts the number of log messages per log level."""

    def __init__(self, count_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.levelcount = count_dict

    def emit(self, record):
        """Increment level counter for each log message."""
        if record.levelno != INTERNAL:
            self.levelcount[record.levelname] += 1


class FileHandlerWithDirCreation(logging.FileHandler):
    """FileHandler which creates necessary directories when the first log message is handled."""

    def emit(self, record):
        """Emit a record and create necessary directories if needed."""
        if self.stream is None:
            os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
        super().emit(record)


class InternalFilter(logging.Filter):
    """Filter out internal log messages."""

    def filter(self, record):
        """Filter out internal records."""
        return record.levelno < INTERNAL


class InternalLogHandler(logging.Handler):
    """Handler for internal log messages."""

    def __init__(self, export_dirs_list):
        self.export_dirs_list = export_dirs_list
        super().__init__()

    def emit(self, record):
        """Handle log record."""
        if record.msg == "export_dirs":
            self.export_dirs_list.update(record.export_dirs)


class ModifiedRichHandler(RichHandler):
    """RichHandler modified to print names instead of paths."""

    def emit(self, record: logging.LogRecord) -> None:
        """Replace path with name and call parent method."""
        record.pathname = record.name
        record.lineno = 0
        super().emit(record)


class LogHandler:
    """Class providing a log handler for Snakemake."""

    icon = "\U0001f426"

    def __init__(self, progressbar=True, summary=False, log_level=None, log_file_level=None):
        """Initialize log handler.

        Args:
            progressbar: Set to False to disable progress bar. Enabled by default.
            summary: Set to True to write a final summary (elapsed time). Disabled by default.
            log_level: Log level for logging to stdout.
            log_file_level: Log level for logging to file.
        """
        self.use_progressbar = progressbar
        self.show_summary = summary
        self.log_level = log_level
        self.log_file_level = log_file_level
        self.log_filename = None
        self.log_levelcount = defaultdict(int)
        self.finished = False
        self.handled_error = False
        self.messages = defaultdict(list)
        self.missing_configs_re = None
        self.missing_binaries_re = None
        self.missing_classes_re = None
        self.export_dirs = set()
        self.start_time = time.time()
        self.jobs = {}

        # Progress bar related variables
        self.progress_mgr = None
        self.exit = lambda *x: None
        self.progress: Optional[progress.Progress] = None
        self.bar: Optional[progress.TaskID] = None
        self.last_percentage = 0

        # Create a simple TCP socket-based logging receiver
        tcpserver = socketserver.ThreadingTCPServer(("localhost", 0), RequestHandlerClass=LogRecordStreamHandler)
        self.log_server = tcpserver.server_address

        # Start a thread with the server
        server_thread = threading.Thread(target=tcpserver.serve_forever)
        server_thread.daemon = True  # Exit the server thread when the main thread terminates
        server_thread.start()

        if not self.use_progressbar:  # When using progress bar, we must wait until after the bar is initialized.
            self.setup_loggers()

    def setup_loggers(self):
        """Set up log handlers for logging to stdout and log file."""
        if not self.log_level or not self.log_file_level:
            return

        sparv_logger = logging.getLogger("sparv_logging")
        internal_filter = InternalFilter()

        # stdout logger
        stream_handler = ModifiedRichHandler(enable_link_path=False, console=console)
        stream_handler.setLevel(self.log_level.upper())
        stream_handler.addFilter(internal_filter)
        log_format = "%(message)s" if stream_handler.level > logging.DEBUG else "(%(process)d) - %(message)s"
        stream_handler.setFormatter(logging.Formatter(log_format, datefmt=TIME_FORMAT))
        sparv_logger.addHandler(stream_handler)

        # File logger
        self.log_filename = "{}.log".format(datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S.%f"))
        file_handler = FileHandlerWithDirCreation(os.path.join(paths.log_dir, self.log_filename), mode="w",
                                                  encoding="UTF-8", delay=True)
        file_handler.setLevel(self.log_file_level.upper())
        file_handler.addFilter(internal_filter)
        log_format = LOG_FORMAT if file_handler.level > logging.DEBUG else LOG_FORMAT_DEBUG
        file_handler.setFormatter(logging.Formatter(log_format))
        sparv_logger.addHandler(file_handler)

        # Level counter
        levelcount_handler = LogLevelCounterHandler(self.log_levelcount)
        levelcount_handler.setLevel(logging.WARNING)
        sparv_logger.addHandler(levelcount_handler)

        # Internal log handler
        internal_handler = InternalLogHandler(self.export_dirs)
        internal_handler.setLevel(INTERNAL)
        sparv_logger.addHandler(internal_handler)

    def setup_bar(self, total: int):
        """Initialize the progress bar."""
        print()
        self.progress_mgr = progress.Progress(
            progress.TextColumn("[progress.description]{task.description}"),
            progress.BarColumn(),
            progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            progress.TimeRemainingColumn(),
            progress.TextColumn("{task.fields[text]}"),
            console=console
        )
        self.exit = type(self.progress_mgr).__exit__
        self.progress = type(self.progress_mgr).__enter__(self.progress_mgr)
        self.bar = self.progress.add_task(self.icon, total=total, text="")

        # Logging needs to be set up after the bar, to make use if its print hook
        self.setup_loggers()

    @staticmethod
    def info(msg):
        """Print info message."""
        console.print(Text(msg, style="green"))

    @staticmethod
    def warning(msg):
        """Print warning message."""
        console.print(Text(msg, style="yellow"))

    @staticmethod
    def error(msg):
        """Print error message."""
        console.print(Text(msg, style="red"))

    def log_handler(self, msg):
        """Log handler for Snakemake displaying a progress bar."""
        def missing_config_message(source):
            """Create error message when config variables are missing."""
            _variables = messages["missing_configs"][source]
            _message = "The following config variable{} need{} to be set:\n • {}".format(
                *("s", "") if len(_variables) > 1 else ("", "s"),
                "\n • ".join(_variables))
            self.messages["error"].append((source, _message))

        def missing_binary_message(source):
            """Create error message when binaries are missing."""
            _binaries = messages["missing_binaries"][source]
            _message = "The following executable{} {} needed but could not be found:\n • {}".format(
                *("s", "are") if len(_binaries) > 1 else ("", "is"),
                "\n • ".join(_binaries))
            self.messages["error"].append((source, _message))

        def missing_class_message(source, classes=None):
            """Create error message when class variables are missing."""
            _variables = messages["missing_classes"][source]
            if not _variables:
                _variables = classes
            _message = "The following class{} need{} to be set:\n • {}".format(
                *("es", "") if len(_variables) > 1 else ("", "s"),
                "\n • ".join(_variables))

            if "text" in _variables:
                _message += "\n\nNote: The 'text' class can also be set using the configuration variable " \
                            "'import.document_annotation', but only if it refers to an annotation from the " \
                            "source files."

            self.messages["error"].append((source, _message))

        level = msg["level"]

        if level == "run_info" and self.use_progressbar:
            # Parse list of jobs do to and total job count
            lines = msg["msg"].splitlines()[2:]
            total_jobs = lines[-1].strip()
            self.jobs = {}
            for j in lines[:-1]:
                _, count, job = j.split("\t")
                self.jobs[job.replace("::", ":")] = int(count)

            if self.bar is None:
                # Get number of jobs
                if total_jobs.isdigit():
                    self.setup_bar(int(total_jobs))

        elif level == "progress":
            if self.use_progressbar:
                # Set up progress bar if needed
                if self.bar is None:
                    self.setup_bar(msg["total"])

                # Advance progress
                self.progress.advance(self.bar)

                # Print regular updates if output is not a terminal (i.e. doesn't support the progress bar)
                if not console.is_terminal:
                    percentage = (100 * msg["done"]) // msg["total"]
                    if percentage > self.last_percentage:
                        self.last_percentage = percentage
                        print(f"Progress: {percentage}%")

            if msg["done"] == msg["total"]:
                self.stop()

        elif level == "job_info" and self.use_progressbar:
            if msg["msg"] and self.bar is not None:
                # Update progress status message
                self.progress.update(self.bar, text=msg["msg"])

        elif level == "info":
            if msg["msg"] == "Nothing to be done.":
                self.info(msg["msg"])

        elif level == "error":
            handled = False

            # SparvErrorMessage exception from pipeline core
            if "SparvErrorMessage" in msg["msg"]:
                # Parse error message
                message = re.search(
                    r"{}([^\n]*)\n([^\n]*)\n(.*?){}".format(SparvErrorMessage.start_marker,
                                                            SparvErrorMessage.end_marker),
                    msg["msg"], flags=re.DOTALL)
                if message:
                    module, function, error_message = message.groups()
                    error_source = ":".join((module, function)) if module and function else None
                    self.messages["error"].append((error_source, error_message))
                    handled = True

            # Exit status 123 means a Sparv module raised a SparvErrorMessage exception
            # The error message has already been logged so doesn't need to be printed again
            elif "exit status 123" in msg["msg"] or ("SystemExit" in msg["msg"] and "123" in msg["msg"]):
                handled = True

            # Errors due to missing config variables or binaries leading to missing input files
            elif "MissingInputException" in msg["msg"] or "MissingOutputException" in msg["msg"]:
                msg_contents = re.search(r" for rule (\S+):\n(.+)", msg["msg"])
                rule_name, filelist = msg_contents.groups()
                rule_name = rule_name.replace("::", ":")
                if self.missing_configs_re.search(filelist):
                    handled = True
                    missing_config_message(rule_name)
                elif self.missing_binaries_re.search(filelist):
                    handled = True
                    missing_binary_message(rule_name)
                elif self.missing_classes_re.search(filelist):
                    handled = True
                    missing_class_message(rule_name, self.missing_classes_re.findall(filelist))

            # Unhandled errors
            if not handled:
                self.messages["unhandled_error"].append(msg)
            else:
                self.handled_error = True

        elif level in ("warning", "job_error"):
            # Save other errors and warnings for later
            self.messages["unhandled_error"].append(msg)

        elif level == "dag_debug" and "job" in msg:
            # Create regular expressions for searching for missing config variables or binaries
            if self.missing_configs_re is None:
                all_configs = set([v for varlist in messages["missing_configs"].values() for v in varlist])
                self.missing_configs_re = re.compile(r"\[({})]".format("|".join(all_configs)))

            if self.missing_binaries_re is None:
                all_binaries = set([b for binlist in messages["missing_binaries"].values() for b in binlist])
                self.missing_binaries_re = re.compile(r"^({})$".format("|".join(all_binaries)), flags=re.MULTILINE)

            if self.missing_classes_re is None:
                all_classes = set([v for varlist in messages["missing_classes"].values() for v in varlist])
                self.missing_classes_re = re.compile(r"<({})>".format("|".join(all_classes)))

            # Check the rules selected for the current operation, and see if any is unusable due to missing configs
            if msg["status"] == "selected":
                job_name = str(msg["job"]).replace("::", ":")
                if job_name in messages["missing_configs"]:
                    missing_config_message(job_name)
                    self.handled_error = True
                    # We need to stop Snakemake by raising an exception, and BrokenPipeError is the only exception
                    # not leading to a full traceback being printed (due to Snakemake's handling of exceptions)
                    raise BrokenPipeError()

    def stop(self):
        """Stop the progress bar and output any error messages."""
        # Make sure this is only run once
        if not self.finished:
            # Stop progress bar
            if self.bar is not None:
                # Add message about elapsed time
                elapsed = round(time.time() - self.start_time)
                self.progress.update(self.bar, text=f"Total time: {timedelta(seconds=elapsed)}")

                # Stop bar
                self.exit(self.progress_mgr, None, None, None)

            self.finished = True
            print()

            # Execution failed but we handled the error
            if self.handled_error:
                # Print any collected core error messages
                if self.messages["error"]:
                    self.error("Sparv exited with the following error message{}:".format(
                        "s" if len(self.messages) > 1 else ""))
                    for message in self.messages["error"]:
                        error_source, msg = message
                        error_source = f"[{error_source}]\n" if error_source else ""
                        self.error(f"\n{error_source}{msg}")
                else:
                    # Errors from modules have already been logged, so notify user
                    self.error(
                        "Job execution failed. See log messages above or {} for details.".format(
                            os.path.join(paths.log_dir, self.log_filename)))
            # Defer to Snakemake's default log handler for unhandled errors
            elif self.messages["unhandled_error"]:
                for error in self.messages["unhandled_error"]:
                    logger.text_handler(error)
            elif self.export_dirs:
                self.info("The exported files can be found in the following location{}:\n • {}".format(
                    "s" if len(self.export_dirs) > 1 else "", "\n • ".join(sorted(self.export_dirs))))
            elif self.log_levelcount:
                # Errors or warnings were logged but execution finished anyway. Notify user of potential problems.
                problems = []
                if self.log_levelcount["ERROR"]:
                    problems.append("{} error{}".format(self.log_levelcount["ERROR"],
                                                        "s" if self.log_levelcount["ERROR"] > 1 else ""))
                if self.log_levelcount["WARNING"]:
                    problems.append("{} warning{}".format(self.log_levelcount["WARNING"],
                                                          "s" if self.log_levelcount["WARNING"] > 1 else ""))
                self.warning(
                    "Job execution finished but {} occured. See log messages above or {} for details.".format(
                        " and ".join(problems), os.path.join(paths.log_dir, self.log_filename)))

            if self.show_summary:
                if self.messages:
                    print()
                elapsed = round(time.time() - self.start_time)
                self.info("Time elapsed: {}".format(timedelta(seconds=elapsed)))

    @staticmethod
    def cleanup():
        """Remove Snakemake log files."""
        snakemake_log_file = logger.get_logfile()
        if snakemake_log_file is not None:
            log_file = Path(snakemake_log_file)
            if log_file.is_file():
                try:
                    log_file.unlink()
                except PermissionError:
                    pass


def setup_logging(log_server, log_level: Optional[str] = "warning", log_file_level: Optional[str] = "warning"):
    """Set up logging with socket handler."""
    # Use the lowest log level, but never higher than warning
    log_level = min(logging.WARNING, getattr(logging, log_level.upper()), getattr(logging, log_file_level.upper()))
    socket_logger = logging.getLogger("sparv")
    socket_logger.setLevel(log_level)
    socket_handler = logging.handlers.SocketHandler(*log_server)
    socket_logger.addHandler(socket_handler)
