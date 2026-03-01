"""Handler for log messages.

This module handles all processing and display of log messages and error messages in Sparv.

The `SparvLogHandler` class is responsible for setting up the logging configuration and contains most of the code for
handling log messages. It also provides a progress bar and additional features for enhanced logging capabilities. The
logging in this module uses a logger named "sparv_logging".

# Message Origins

Log messages in Sparv originate from two main sources:

1. Sparv modules. These modules log messages using a logger ("sparv") acquired from the `get_logger()` function. Sparv
   modules run in separate processes, and their logger communicates with the main thread's log handler over a TCP
   socket. The messages are then handled by the main thread's "sparv_logging" logger. This includes log messages from
   parts of the Sparv core imported by the modules.

2. Snakemake. Log messages from Snakemake are handled by a custom logging plugin which simply forwards these log records
   to the Sparv log handler's `snakemake_log_handler()` method, which processes the messages and updates the progress.

## Exceptions and Error Handling

The Sparv core (outside of the API functions used by the modules) generally does not use log messages, but instead
raises `SparvErrorMessage` exceptions. These exceptions are caught in the `__main__` module and passed to the
`handle_exception()` method of the `SparvLogHandler` instance. They are there turned into error messages and printed.

Any exceptions (including `SparvErrorMessage`) raised in Sparv modules are first caught by `run_snake.py` and converted
to error log messages. The execution of the module process is then interrupted, which leads to Snakemake throwing a
WorkflowError exception. This is caught by the `__main__` module and forwarded to the `handle_exception()` which
ignores the error message (as the error has already been logged).
"""

from __future__ import annotations

import datetime
import logging
import logging.handlers
import pickle
import re
import socketserver
import struct
import threading
import time
import traceback
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path
from typing import Any

import snakemake
from pythonjsonlogger import jsonlogger
from rich import box, progress
from rich.control import Control, ControlType
from rich.logging import RichHandler
from rich.table import Table
from rich.text import Text
from rich.traceback import Traceback
from snakemake.common import NOTHING_TO_BE_DONE_MSG
from snakemake.exceptions import MissingInputException, WorkflowError
from snakemake.logging import get_event_level, logger_manager
from snakemake_interface_logger_plugins.common import LogEvent

from sparv.core import io
from sparv.core.console import console
from sparv.core.logger import CurrentProgress, SparvLogger, ensure_logger_class
from sparv.core.misc import SparvErrorMessage
from sparv.core.paths import paths

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s - %(name)s (%(process)d) - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"

ensure_logger_class()

# Messages from the Sparv core
messages = {
    "missing_configs": defaultdict(set),
    "missing_binaries": defaultdict(set),
    "missing_classes": defaultdict(set),
}

missing_annotations_msg = (
    "There can be many reasons for this. Please make sure that there are no problems with the "
    "corpus configuration file, like misspelled annotation names (including unintentional "
    "whitespace characters) or references to non-existent or implicit source annotations."
)


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Handler for streaming logging requests.

    This handler receives logging records from a TCP socket and logs them using the Sparv logger.
    """

    def handle(self) -> None:
        """Handle multiple requests - each expected to be a 4-byte length followed by the LogRecord in pickle format."""
        data_length_bytes = 4
        while True:
            chunk = self.connection.recv(data_length_bytes)
            if len(chunk) < data_length_bytes:
                break
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk += self.connection.recv(slen - len(chunk))
            obj = pickle.loads(chunk)
            record = logging.makeLogRecord(obj)
            self.handle_log_record(record)

    @staticmethod
    def handle_log_record(record: logging.LogRecord) -> None:
        """Handle log record."""
        sparv_logger = logging.getLogger("sparv_logging")
        sparv_logger.handle(record)


class LogLevelCounterHandler(logging.Handler):
    """Handler that counts the number of log messages per log level."""

    def __init__(self, count_dict: dict[str, int], *args: Any, **kwargs: Any) -> None:
        """Initialize handler.

        Args:
            count_dict: Dictionary to store the count of log messages per log level.
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.levelcount = count_dict

    def emit(self, record: logging.LogRecord) -> None:
        """Increment level counter for each log message."""
        if record.levelno < SparvLogger.FINAL:
            self.levelcount[record.levelname] += 1


class FileHandlerWithDirCreation(logging.FileHandler):
    """FileHandler which creates necessary directories when the first log message is handled."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record and create necessary directories if needed."""
        if self.stream is None:
            Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
        super().emit(record)


class InternalFilter(logging.Filter):
    """Filter out internal log messages."""

    @staticmethod
    def filter(record: logging.LogRecord) -> bool:
        """Filter out internal records.

        Args:
            record: Log record.

        Returns:
            True if record is not internal, False otherwise.
        """
        return record.levelno < SparvLogger.INTERNAL


class ProgressInternalFilter(logging.Filter):
    """Filter out progress and internal log messages."""

    @staticmethod
    def filter(record: logging.LogRecord) -> bool:
        """Filter out progress and internal records.

        Args:
            record: Log record.

        Returns:
            True if record is not progress or internal, False otherwise.
        """
        return record.levelno < SparvLogger.PROGRESS


class InternalLogHandler(logging.Handler):
    """Handler for internal log messages.

    Used to update the progress bar and collect export directories.
    """

    def __init__(self, export_dirs_list: set, progress_: progress.Progress, jobs: OrderedDict, job_ids: dict) -> None:
        """Initialize handler.

        Args:
            export_dirs_list: Set to be updated with export directories.
            progress_: Progress bar object.
            jobs: Dictionary of jobs.
            job_ids: Translation from (Sparv task name, source file) to Snakemake job ID.
        """
        self.export_dirs_list = export_dirs_list
        self.progress: progress.Progress = progress_
        self.jobs = jobs
        self.job_ids = job_ids
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        """Handle log record."""
        if record.msg == "export_dirs":
            self.export_dirs_list.update(record.export_dirs)
        elif record.msg == "progress":
            job_id = self.job_ids.get((record.job, record.file or ""))
            if job_id is not None:
                try:
                    if not self.jobs[job_id]["task"]:
                        self.jobs[job_id]["task"] = self.progress.add_task(
                            "",
                            start=bool(record.total),
                            completed=record.progress or record.advance or 0,
                            total=record.total or 100.0,
                        )
                    else:
                        if record.total:
                            self.progress.start_task(self.jobs[job_id]["task"])
                            self.progress.update(self.jobs[job_id]["task"], total=record.total)
                        if record.progress:
                            self.progress.update(self.jobs[job_id]["task"], completed=record.progress)
                        elif record.advance or not record.total:
                            self.progress.advance(self.jobs[job_id]["task"], advance=record.advance or 1)
                except KeyError:
                    pass


class ModifiedRichHandler(RichHandler):
    """RichHandler modified to print names instead of paths."""

    def emit(self, record: logging.LogRecord) -> None:
        """Replace path with name and call parent method."""
        record.pathname = record.name if record.name != "sparv_logging" else ""
        record.lineno = 0
        super().emit(record)


class ProgressWithTable(progress.Progress):
    """Progress bar with additional table."""

    def __init__(self, all_tasks: dict, current_tasks: OrderedDict, max_len: int, *args: Any, **kwargs: Any) -> None:
        """Initialize progress bar with table.

        Args:
            all_tasks: Dictionary of all tasks.
            current_tasks: Currently running tasks.
            max_len: Maximum length of task names.
            args: Additional arguments.
            kwargs: Additional keyword arguments.
        """
        self.all_tasks = all_tasks
        self.current_tasks = current_tasks
        self.task_max_len = max_len
        super().__init__(*args, **kwargs)

    def get_renderables(self) -> Iterable[progress.RenderableType]:
        """Get a number of renderables for the progress display.

        Yields:
            Renderables for the progress display.
        """
        # Progress bar
        yield self.make_tasks_table(self.tasks[:1])

        # Task table
        if self.all_tasks:
            rows = []
            elapsed_max_len = 7
            bar_col = progress.BarColumn(bar_width=20)
            for task in list(self.current_tasks.values()):  # Make a copy to avoid mutations while iterating
                elapsed = str(timedelta(seconds=round(time.time() - task["starttime"])))
                elapsed_max_len = max(len(elapsed), elapsed_max_len)
                try:
                    rows.append(
                        (
                            task["name"],
                            f"[dim]{task['file']}[/dim]",
                            bar_col(self._tasks[task["task"]]) if task["task"] else "",
                            elapsed,
                        )
                    )
                except KeyError:  # May happen if self._tasks has changed
                    pass

            table = Table(show_header=False, box=box.SIMPLE, expand=True)
            table.add_column("Task", no_wrap=True, min_width=self.task_max_len + 2, ratio=1)
            table.add_column("File", no_wrap=True)
            table.add_column("Bar", width=10)
            table.add_column(
                "Elapsed", no_wrap=True, width=elapsed_max_len, justify="right", style="progress.remaining"
            )
            table.add_row("[b]Task[/]", "[b]File[/]", "", "[default b]Elapsed[/]")
            for row in rows:
                table.add_row(*row)
            yield table


class SparvLogHandler:
    """Main log handler for Sparv."""

    icon = "\U0001f426"

    def __init__(
        self,
        progressbar: bool = True,
        log_level: str | None = None,
        log_file_level: str | None = None,
        simple: bool = False,
        stats: bool = False,
        pass_through: bool = False,
        dry_run: bool = False,
        keep_going: bool = False,
        json: bool = False,
        root_dir: str | None = None,
    ) -> None:
        """Initialize log handler.

        Args:
            progressbar: Set to False to disable progress bar. Enabled by default.
            log_level: Log level for logging to stdout.
            log_file_level: Log level for logging to file.
            simple: Set to True to show less info about currently running jobs.
            stats: Set to True to show stats after completion.
            pass_through: Let Snakemake's log messages pass through uninterrupted.
            dry_run: Set to True to print summary about jobs.
            keep_going: Set to True if the keepgoing flag is enabled for Snakemake.
            json: Set to True to enable JSON output.
            root_dir: Root directory for the corpus (if set using `--dir`).
        """
        self.use_progressbar = progressbar and console.is_terminal
        self.simple = simple or not console.is_terminal
        self.pass_through = pass_through
        self.dry_run = dry_run
        self.keep_going = keep_going
        self.json = json
        self.log_level = log_level
        self.log_file_level = log_file_level
        self.log_filename = None
        self.log_levelcount = defaultdict(int)
        self.root_dir = root_dir
        self.finished = False
        self.handled_error = False  # Set to True if an error has been handled, i.e. not unexpected errors
        self.messages = {
            "error": [],
            "unhandled_error": [],
        }
        self.missing_configs_re = None
        self.missing_binaries_re = None
        self.missing_classes_re = None
        self.export_dirs = set()
        self.start_time = time.time()
        self.jobs = {}
        self.jobs_max_len = 0
        self.stats = stats
        self.stats_data = defaultdict(float)
        self.logger = None
        self.terminated = False
        self.reasons = ""

        # Progress bar related variables
        self.progress: progress.Progress | None = None
        self.bar: progress.TaskID | None = None
        self.bar_started: bool = False
        self.last_percentage = 0
        self.current_jobs = OrderedDict()
        self.job_ids = {}  # Translation from (Sparv task name, source file) to numerical Snakemake job ID

        # Create a simple TCP socket-based logging receiver
        tcpserver = socketserver.ThreadingTCPServer(("localhost", 0), RequestHandlerClass=LogRecordStreamHandler)
        self.log_server = tcpserver.server_address

        # Start a thread with the server
        server_thread = threading.Thread(target=tcpserver.serve_forever)
        server_thread.daemon = True  # Exit the server thread when the main thread terminates
        server_thread.start()

        if self.use_progressbar:
            self.setup_bar()
        else:
            # When using progress bar, we must hold off on setting up logging until after the bar is initialized
            self.setup_loggers()

    def setup_loggers(self) -> None:
        """Set up log handlers for logging to stdout and log file."""
        if not self.log_level or not self.log_file_level:
            return

        self.logger = logging.getLogger("sparv_logging")
        internal_filter = InternalFilter()
        progress_internal_filter = ProgressInternalFilter()

        # Set logger to the lowest selected log level, but not higher than warning (we still want to count warnings)
        self.logger.setLevel(
            min(
                logging.WARNING, getattr(logging, self.log_level.upper()), getattr(logging, self.log_file_level.upper())
            )
        )

        # stdout logger
        if self.json:
            stream_handler = logging.StreamHandler()
        else:
            stream_handler = ModifiedRichHandler(enable_link_path=False, rich_tracebacks=True, console=console)

        stream_handler.setLevel(self.log_level.upper())
        stream_handler.addFilter(internal_filter)
        stream_handler.addFilter(lambda record: not getattr(record, "to_file", False))

        if self.json:
            stream_formatter = json_formatter = jsonlogger.JsonFormatter(
                LOG_FORMAT_DEBUG, rename_fields={"asctime": "time", "levelname": "level"}
            )
        else:
            stream_formatter = logging.Formatter(
                "%(message)s" if stream_handler.level > logging.DEBUG else "(%(process)d) - %(message)s",
                datefmt=TIME_FORMAT,
            )

        stream_handler.setFormatter(stream_formatter)
        self.logger.addHandler(stream_handler)

        # File logger
        self.log_filename = f"{datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S.%f')}.log"
        file_handler = FileHandlerWithDirCreation(
            Path(self.root_dir or Path().cwd()) / paths.log_dir / self.log_filename,
            mode="w",
            encoding="UTF-8",
            delay=True,
        )
        file_handler.setLevel(self.log_file_level.upper())
        file_handler.addFilter(progress_internal_filter)
        file_handler.addFilter(lambda record: not getattr(record, "to_stdout", False))

        if self.json:
            file_formatter = json_formatter
        else:
            file_formatter = logging.Formatter(LOG_FORMAT if file_handler.level > logging.DEBUG else LOG_FORMAT_DEBUG)

        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Level counter
        levelcount_handler = LogLevelCounterHandler(self.log_levelcount)
        levelcount_handler.setLevel(logging.WARNING)
        self.logger.addHandler(levelcount_handler)

        # Internal log handler
        internal_handler = InternalLogHandler(self.export_dirs, self.progress, self.current_jobs, self.job_ids)
        internal_handler.setLevel(SparvLogger.INTERNAL)
        self.logger.addHandler(internal_handler)

    def setup_bar(self) -> None:
        """Initialize the progress bar but don't start it yet."""
        console.print()
        progress_layout = [
            progress.SpinnerColumn("dots2"),
            progress.BarColumn(bar_width=40 if self.simple else None),
            progress.TextColumn("[progress.description]{task.description}"),
            progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            progress.TextColumn("[progress.remaining]{task.completed} of {task.total} tasks"),
            progress.TextColumn("{task.fields[text]}"),
        ]
        if self.simple:
            self.progress = progress.Progress(*progress_layout, console=console)
        else:
            self.progress = ProgressWithTable(
                self.jobs, self.current_jobs, self.jobs_max_len, *progress_layout, console=console
            )
        self.progress.start()
        self.bar = self.progress.add_task(self.icon, start=False, total=0, text="[dim]Preparing...[/dim]")

        # Logging needs to be set up after the bar, to make use of its print hook
        self.setup_loggers()

    def start_bar(self, total: int) -> None:
        """Start progress bar.

        Args:
            total: Total number of tasks.
        """
        self.progress.update(self.bar, total=total)
        self.progress.start_task(self.bar)
        self.bar_started = True

    def info(self, msg: str) -> None:
        """Print info message.

        Args:
            msg: Message to print.
        """
        if self.json:
            self.logger.log(SparvLogger.FINAL, msg)
        else:
            console.print(Text(msg, style="green"))

    def warning(self, msg: str) -> None:
        """Print warning message.

        Args:
            msg: Message to print.
        """
        if self.json:
            self.logger.log(SparvLogger.FINAL, msg)
        else:
            console.print(Text(msg, style="yellow"))

    def error(self, msg: str) -> None:
        """Print error message.

        Args:
            msg: Message to print.
        """
        if self.json:
            self.logger.log(SparvLogger.FINAL, msg)
        else:
            console.print(Text(msg, style="red"))

    def missing_config_message(self, source: str) -> None:
        """Create error message when config variables are missing."""
        variables = messages["missing_configs"][source]
        message = "The following config variable{} need{} to be set:\n • {}".format(
            *("s", "") if len(variables) > 1 else ("", "s"), "\n • ".join(variables)
        )
        self.messages["error"].append((source, message))

    def missing_binary_message(self, source: str) -> None:
        """Create error message when binaries are missing."""
        binaries = messages["missing_binaries"][source]
        message = "The following executable{} {} needed but could not be found:\n • {}".format(
            *("s", "are") if len(binaries) > 1 else ("", "is"), "\n • ".join(binaries)
        )
        self.messages["error"].append((source, message))

    def missing_class_message(self, source: str, classes: list[str] | None = None) -> None:
        """Create error message when class variables are missing."""
        variables = messages["missing_classes"][source] or classes
        message = "The following class{} need{} to be set:\n • {}".format(
            *("es", "") if len(variables) > 1 else ("", "s"), "\n • ".join(variables)
        )

        if "text" in variables:
            message += (
                "\n\nNote: The 'text' class can also be set using the configuration variable "
                "'import.text_annotation', but only if it refers to an annotation from the "
                "source files."
            )

        self.messages["error"].append((source, message))

    def missing_annotations_or_files(self, source: str, files: str) -> None:
        """Create error message when annotations or other files are missing."""
        errmsg = []
        missing_annotations = []
        missing_other = []
        for f in map(Path, files.splitlines()):
            if paths.work_dir in f.parents:
                # If the missing file is within the Sparv workdir, it is probably an annotation
                f_rel = f.relative_to(paths.work_dir)
                *_, annotation, attr = f_rel.parts
                if attr == io.SPAN_ANNOTATION:
                    missing_annotations.append((annotation,))
                else:
                    missing_annotations.append((annotation, attr))
            else:
                missing_other.append(str(f))
        if missing_annotations:
            errmsg = [
                "The following input annotation{} {} missing:\n • {}\n".format(
                    "s" if len(missing_annotations) > 1 else "",
                    "are" if len(missing_annotations) > 1 else "is",
                    "\n • ".join(
                        ":".join(ann) if len(ann) == 2 else ann[0]  # noqa: PLR2004
                        for ann in missing_annotations
                    ),
                )
            ]
        if missing_other:
            if errmsg:
                errmsg.append("\n")
            errmsg.append(
                "The following input file{} {} missing:\n • {}\n".format(
                    "s" if len(missing_other) > 1 else "",
                    "are" if len(missing_other) > 1 else "is",
                    "\n • ".join(missing_other),
                )
            )
        if errmsg:
            errmsg.append("\n" + missing_annotations_msg)
        self.messages["error"].append((source, "".join(errmsg)))

    def handle_exception(self, exception: Exception) -> None:
        """Handle exceptions from the Sparv core.

        Any exception raised in the Sparv core (i.e. not in a Sparv module) will be caught in the __main__ module and
        passed to this method. Exceptions raised in Sparv modules are caught earlier in the pipeline (in a separate
        process) and logged, but also lead to a WorkflowError exception being raised in Snakemake, which is then caught
        and ignored here.

        Args:
            exception: The exception to handle.
        """
        if isinstance(exception, SparvErrorMessage):
            # SparvErrorMessage exception from pipeline core
            # Parse and extract the error message
            message = re.search(
                rf"{SparvErrorMessage.start_marker}([^\n]*)\n([^\n]*)\n(.*?){SparvErrorMessage.end_marker}",
                str(exception),
                flags=re.DOTALL,
            )
            if message:
                module, function, error_message = message.groups()
                error_source = f"{module}:{function}" if module and function else None
                self.messages["error"].append((error_source, error_message))
                self.handled_error = True
        elif isinstance(exception, MissingInputException):
            # Errors due to missing config variables or binaries leading to missing input files
            msg_contents = re.search(r" for rule (\S+):\n.*affected files:\n(.+)", str(exception), flags=re.DOTALL)
            rule_name, filelist = msg_contents.groups()
            filelist = "\n".join(f.strip() for f in filelist.splitlines())
            rule_name = rule_name.replace("::", ":")
            if self.missing_configs_re.search(filelist):
                self.missing_config_message(rule_name)
            elif self.missing_binaries_re.search(filelist):
                self.missing_binary_message(rule_name)
            elif self.missing_classes_re.search(filelist):
                self.missing_class_message(rule_name, self.missing_classes_re.findall(filelist))
            else:
                self.missing_annotations_or_files(rule_name, filelist)
            self.handled_error = True
        elif (
            isinstance(exception, WorkflowError) and str(exception) == "At least one job did not complete successfully."
        ):
            # This is the generic Snakemake error message when a running workflow fails. We should already have handled
            # and printed the error in run_snake.py, so we silently ignore it here.
            pass
        else:
            # Any other exception from the Sparv core
            self.messages["unhandled_error"].append((f"{type(exception).__name__}: {exception}", exception))

    def snakemake_log_handler(self, record: logging.LogRecord) -> None:
        """Handle log records from Snakemake's own logging system.

        Args:
            record: Log record to handle.
        """
        snake_level, record_level = get_event_level(record)

        if snake_level == LogEvent.RUN_INFO:  # Log message with a list of jobs to do and total job count
            # Parse list of planned jobs and total job count
            lines = record.msg.splitlines()[3:]
            total_jobs = lines[-1].split()[1]
            for j in lines[:-1]:
                job, count = j.split()
                if ":" in job and "::" not in job:
                    job += "*"  # Differentiate entrypoints from actual rules in the list
                self.jobs[job.replace("::", ":")] = int(count)
            self.jobs_max_len = max(map(len, self.jobs))

            # Get number of jobs and start progress bar
            if self.use_progressbar and not self.bar_started and total_jobs.isdigit():
                self.start_bar(int(total_jobs))

        elif snake_level == LogEvent.PROGRESS:  # Progress update for the main progress
            if self.use_progressbar:
                # Advance progress
                self.progress.advance(self.bar)

            # Print regular progress updates if output is not a terminal (i.e. doesn't support the progress bar) or
            # output format is JSON
            elif self.logger and (self.json or not console.is_terminal):
                percentage = (100 * record.done) // record.total
                if percentage > self.last_percentage:
                    self.last_percentage = percentage
                    self.logger.log(SparvLogger.PROGRESS, f"{percentage}%")  # noqa: G004

            if record.done == record.total:
                self.stop()

        elif snake_level == LogEvent.JOB_INFO and self.use_progressbar:  # Info about a job starting
            if record.msg and self.bar is not None:
                # Update progress status message
                self.progress.update(self.bar, text=record.rule_msg if self.simple else "")

                if not self.simple:
                    file = record.wildcards.get("file", "")
                    if file.startswith(str(paths.work_dir)):
                        file = file[len(str(paths.work_dir)) + 1 :]

                    self.current_jobs[record.jobid] = {
                        "task": None,
                        "name": record.rule_msg,
                        "starttime": time.time(),
                        "file": file,
                    }
                    self.job_ids[record.rule_msg, file] = record.jobid

        elif (
            (snake_level == LogEvent.JOB_FINISHED or (snake_level == LogEvent.JOB_ERROR and self.keep_going))
            and self.use_progressbar
            and (
                (hasattr(record, "job_id") and record.job_id in self.current_jobs)
                or (hasattr(record, "jobid") and record.jobid in self.current_jobs)
            )
        ):  # Job finished, alternatively job error but keep_going is enabled
            # JOB_FINISHED uses job_id while JOB_ERROR uses jobid
            job_id = record.job_id if hasattr(record, "job_id") else record.jobid
            this_job = self.current_jobs[job_id]
            if self.stats:
                self.stats_data[this_job["name"]] += time.time() - this_job["starttime"]
            if this_job["task"]:  # Job has a progress bar
                self.progress.remove_task(this_job["task"])
            self.job_ids.pop((this_job["name"], this_job["file"]), None)
            self.current_jobs.pop(job_id, None)
            if snake_level == LogEvent.JOB_ERROR and record.msg:
                self.messages["unhandled_error"].append((record.getMessage(), None))

        elif snake_level is None and record_level == "INFO":  # Info messages
            if self.pass_through:
                self.info(record.msg)
            elif NOTHING_TO_BE_DONE_MSG in record.msg:
                self.info("Nothing to be done.")
            elif record.msg.startswith("Will exit after finishing currently running jobs") and not self.terminated:
                self.logger.log(logging.INFO, "Will exit after finishing currently running jobs")
                self.terminated = True
            if self.dry_run and "Reasons:" in record.msg:
                # Save reasons for tasks being scheduled
                self.reasons = record.msg.split("\n", 2)[2]

        elif snake_level == LogEvent.ERROR or record_level == "ERROR":  # Error messages
            if self.pass_through:
                self.messages["unhandled_error"].append((record.getMessage(), None))
                return
            handled = False

            if "exit status 123" in record.msg:
                # Exit status 123 means a Sparv module caused an exception, either a SparvErrorMessage exception, or
                # an unexpected exception. Either way, the error message has already been logged, so it doesn't need to
                # be printed again.
                self.handled_error = True

            # Missing output files
            elif "MissingOutputException" in record.message:
                msg_contents = re.search(r"Missing files after .*?:\n(.+)", record.message, flags=re.DOTALL)
                missing_files = "\n • ".join(
                    line.split(" (missing locally", 1)[0] for line in msg_contents[1].strip().splitlines()
                )
                message = (
                    "The following output files were expected but are missing:\n"
                    f" • {missing_files}\n\n{missing_annotations_msg}"
                )
                self.messages["error"].append((None, message))
                handled = True
            elif "Exiting because a job execution failed." in record.message:
                pass
            elif "run_snake.py' returned non-zero exit status 1." in record.message:
                # This happens when run_snake.py crashes unexpectedly, i.e. not due to an exception in a Sparv module.
                # The error message should already have been printed, either to stderr or to the log, depending on
                # whether it happened before redirecting stderr to the log.
                handled = True
            elif "Error: Directory cannot be locked." in record.message:
                message = (
                    "Directory cannot be locked. If you are sure that no other Sparv instance is currently "
                    "using this directory, run 'sparv run --unlock' to remove the lock."
                )
                self.messages["error"].append((None, message))
                handled = True
            elif "died with <Signals." in record.message:
                # The run_snake.py subprocess was killed
                signal_match = re.search(r"died with <Signals.([A-Z]+)", record.message)
                self.messages["error"].append(
                    (
                        None,
                        f"A Sparv subprocess was unexpectedly killed due to receiving a {signal_match[1]} signal.",
                    )
                )
                self.handled_error = True

            # Unhandled errors
            if not handled:
                self.messages["unhandled_error"].append((record.getMessage(), None))
            else:
                self.handled_error = True

        elif (snake_level == LogEvent.JOB_ERROR and not self.keep_going) or record_level == "WARNING":
            # Save other errors and warnings for later
            if record.message:
                self.messages["unhandled_error"].append((record.getMessage(), None))

        elif snake_level == LogEvent.WORKFLOW_STARTED:
            # Create regular expressions for searching for missing config variables or binaries
            all_configs = {v for varlist in messages["missing_configs"].values() for v in varlist}
            self.missing_configs_re = re.compile(r"\[({})]".format("|".join(all_configs)))

            all_binaries = {b for binlist in messages["missing_binaries"].values() for b in binlist}
            self.missing_binaries_re = re.compile(r"^({})$".format("|".join(all_binaries)), flags=re.MULTILINE)

            all_classes = {v for varlist in messages["missing_classes"].values() for v in varlist}
            self.missing_classes_re = re.compile(r"<({})>".format("|".join(all_classes)))

    def stop(self) -> None:
        """Stop the progress bar and output any messages."""
        # Make sure this is only run once
        if self.finished:
            return

        # Stop progress bar
        if self.bar is not None:
            if self.bar_started:
                # Add message about elapsed time
                elapsed = round(time.time() - self.start_time)
                self.progress.update(self.bar, text=f"Total time: {timedelta(seconds=elapsed)}")
            else:
                # Hide bar if it was never started
                self.progress.update(self.bar, visible=False)

            # Stop bar
            self.progress.stop()
            if not self.simple and self.bar_started:
                # Clear table header from screen
                console.control(
                    Control(
                        ControlType.CARRIAGE_RETURN, *((ControlType.CURSOR_UP, 1), (ControlType.ERASE_IN_LINE, 2)) * 2
                    )
                )

        self.finished = True

        # Execution failed but we handled the error
        if self.handled_error:
            # Print any collected core error messages
            if self.messages["error"]:
                errmsg = [f"Sparv exited with the following error message{'s' if len(self.messages) > 1 else ''}:"]
                for message in self.messages["error"]:
                    error_source, msg = message
                    error_source = f"[{error_source}]\n" if error_source else ""
                    errmsg.append(f"\n{error_source}{msg}")
                self.error("\n".join(errmsg))
            elif self.log_filename:
                # Errors from modules have already been logged to both stdout and the log file
                self.error(
                    f"Job execution failed. See log messages above or {paths.log_dir / self.log_filename} for details."
                )
            else:
                # Errors from modules have already been logged to stdout
                self.error("Job execution failed. See log messages above for details.")
        # Unhandled errors
        elif self.messages["unhandled_error"]:
            # If debug log level is set, print full error message with traceback, otherwise just a summary.
            # The log file always contains the full error message.
            for error_message, exception in self.messages["unhandled_error"]:
                errmsg = ["An unexpected error occurred."]
                if self.log_level and logging._nameToLevel[self.log_level.upper()] > logging.DEBUG:
                    errmsg[0] += (
                        f" For more details, please check '{paths.log_dir / self.log_filename}', or rerun Sparv "
                        "with the '--log debug' argument.\n"
                    )
                    if error_message:
                        errmsg.append(error_message)
                    self.error("\n".join(errmsg))
                elif exception:
                    self.error("\n".join(errmsg))
                    console.print(
                        Traceback.from_exception(
                            type(exception), exception, exception.__traceback__, suppress=[snakemake]
                        )
                    )
                else:
                    errmsg.append("")
                    errmsg.append(error_message or "An unknown error occurred.")
                    self.error("\n".join(errmsg))

                # Always log full error message to file, no matter the log level
                if exception:
                    # Get traceback from the exception
                    full_message = "".join(
                        traceback.format_exception(type(exception), exception, exception.__traceback__)
                    )
                else:
                    full_message = error_message
                self.logger.error(full_message or "An unknown error occurred.", extra={"to_file": True})
        else:
            spacer = ""
            if self.export_dirs:
                spacer = "\n"
                self.info(
                    "The exported files can be found in the following location{}:\n • {}".format(
                        "s" if len(self.export_dirs) > 1 else "", "\n • ".join(sorted(self.export_dirs))
                    )
                )

            if self.stats_data:
                spacer = ""
                table = Table(show_header=False, box=box.SIMPLE)
                table.add_column("Task", no_wrap=True, min_width=self.jobs_max_len + 2, ratio=1)
                table.add_column("Time taken", no_wrap=True, justify="right", style="progress.remaining")
                table.add_column("Percentage", no_wrap=True, justify="right")
                table.add_row("[b]Task[/]", "[default b]Time taken[/]", "[b]Percentage[/b]")
                total_time = sum(self.stats_data.values())
                for task, elapsed in sorted(self.stats_data.items(), key=lambda x: -x[1]):
                    table.add_row(task, str(timedelta(seconds=round(elapsed))), f"{100 * elapsed / total_time:.1f}%")
                console.print(table)

            if self.log_levelcount:
                # Errors or warnings were logged but execution finished anyway. Notify user of potential problems.
                problems = []
                if self.log_levelcount["ERROR"]:
                    problems.append(
                        f"{self.log_levelcount['ERROR']} error{'s' if self.log_levelcount['ERROR'] > 1 else ''}"
                    )
                if self.log_levelcount["WARNING"]:
                    problems.append(
                        f"{self.log_levelcount['WARNING']} warning{'s' if self.log_levelcount['WARNING'] > 1 else ''}"
                    )
                self.warning(
                    f"{spacer}Job execution finished but {' and '.join(problems)} occurred. See log messages "
                    f"above or {paths.log_dir / self.log_filename} for details."
                )
            elif self.dry_run:
                console.print("The following tasks were scheduled but not run:")
                table = Table(show_header=False, box=box.SIMPLE)
                table.add_column(justify="right")
                table.add_column()
                for job in self.jobs:
                    table.add_row(str(self.jobs[job]), job)
                table.add_row()
                table.add_row(str(sum(self.jobs.values())), "Total number of tasks")
                console.print(table)
                if self.reasons:
                    console.print("Reasons:\n")
                    console.print(self.reasons)

            if self.terminated:
                self.info(f"{spacer}Sparv was stopped by a TERM signal")

    @staticmethod
    def cleanup() -> None:
        """Remove Snakemake log files."""
        snakemake_log_files = logger_manager.get_logfile()
        for snakemake_log_file in snakemake_log_files:
            log_file = Path(snakemake_log_file)
            if log_file.is_file():
                try:
                    log_file.unlink()
                except PermissionError:
                    pass


def setup_logging(
    log_server: tuple[str | bytes | bytearray, int],
    log_level: str = "warning",
    log_file_level: str = "warning",
    file: str | None = None,
    job: str | None = None,
) -> None:
    """Set up logging with socket handler.

    This is used to send log messages from child processes (e.g. Sparv modules) to the main process over a socket.

    Args:
        log_server: Tuple with host and port for logging server.
        log_level: Log level for logging to stdout.
        log_file_level: Log level for logging to file.
        file: Source file name for current job.
        job: Current task name.
    """
    # Set logger to use the lowest selected log level, but never higher than warning (we still want to count warnings)
    log_level = min(logging.WARNING, getattr(logging, log_level.upper()), getattr(logging, log_file_level.upper()))
    socket_logger = logging.getLogger("sparv")
    socket_logger.propagate = False  # Prevent propagation to root logger
    socket_logger.setLevel(log_level)
    socket_handler = logging.handlers.SocketHandler(*log_server)
    socket_logger.addHandler(socket_handler)
    CurrentProgress.current_file = file
    CurrentProgress.current_job = job
