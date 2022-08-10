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
from collections import defaultdict, OrderedDict
from datetime import timedelta
from pathlib import Path
from typing import Optional

import rich.box as box
import rich.progress as progress
from rich.control import Control, ControlType
from rich.logging import RichHandler
from rich.table import Table
from rich.text import Text
from snakemake import logger

from sparv.core import io, paths
from sparv.core.console import console
from sparv.core.misc import SparvErrorMessage

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s - %(name)s (%(process)d) - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"

# Variables set by setup_logging()
current_file = None
current_job = None

# Add internal logging level used for non-logging-related communication from child processes to log handler
INTERNAL = 100
logging.addLevelName(INTERNAL, "INTERNAL")


def _log_progress(self, progress=None, advance=None, total=None):
    """Log progress of task."""
    if self.isEnabledFor(INTERNAL):
        self._log(INTERNAL, "progress", (), extra={"progress": progress, "advance": advance, "total": total,
                                                   "job": current_job, "file": current_file})


# Add progress function to logger
logging.progress = _log_progress
logging.Logger.progress = _log_progress

# Add logging level used for progress output (must be lower than INTERNAL)
PROGRESS = 90
logging.addLevelName(PROGRESS, "PROGRESS")


def _export_dirs(self, dirs):
    """Send list of export dirs to log handler."""
    if self.isEnabledFor(INTERNAL):
        self._log(INTERNAL, "export_dirs", (), extra={"export_dirs": dirs})


# Add log function to logger
logging.export_dirs = _export_dirs
logging.Logger.export_dirs = _export_dirs

# Messages from the Sparv core
messages = {
    "missing_configs": defaultdict(set),
    "missing_binaries": defaultdict(set),
    "missing_classes": defaultdict(set)
}

missing_annotations_msg = "There can be many reasons for this. Please make sure that there are no problems with the " \
                          "corpus configuration file, like misspelled annotation names (including unintentional " \
                          "whitespace characters) or references to non-existent or implicit source annotations."


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
        if record.levelno < PROGRESS:
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


class ProgressInternalFilter(logging.Filter):
    """Filter out progress and internal log messages."""

    def filter(self, record):
        """Filter out progress and internal records."""
        return record.levelno < PROGRESS


class InternalLogHandler(logging.Handler):
    """Handler for internal log messages."""

    def __init__(self, export_dirs_list, progress_, jobs, job_ids):
        self.export_dirs_list = export_dirs_list
        self.progress: progress.Progress = progress_
        self.jobs = jobs
        self.job_ids = job_ids
        super().__init__()

    def emit(self, record):
        """Handle log record."""
        if record.msg == "export_dirs":
            self.export_dirs_list.update(record.export_dirs)
        elif record.msg == "progress":
            job_id = self.job_ids.get((record.job, record.file))
            if job_id is not None:
                if not self.jobs[job_id]["task"]:
                    self.jobs[job_id]["task"] = self.progress.add_task(
                        "",
                        start=bool(record.total),
                        completed=record.progress or record.advance or 0,
                        total=record.total or 100.0
                    )
                else:
                    try:
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
        record.pathname = record.name if not record.name == "sparv_logging" else ""
        record.lineno = 0
        super().emit(record)


class ProgressWithTable(progress.Progress):
    """Progress bar with additional table."""

    def __init__(self, all_tasks, current_tasks, max_len, *args, **kwargs):
        self.all_tasks = all_tasks
        self.current_tasks = current_tasks
        self.task_max_len = max_len
        super().__init__(*args, **kwargs)

    def get_renderables(self):
        """Get a number of renderables for the progress display."""
        # Progress bar
        yield self.make_tasks_table(self.tasks[0:1])

        # Task table
        if self.all_tasks:
            rows = []
            elapsed_max_len = 7
            bar_col = progress.BarColumn(bar_width=20)
            for task in list(self.current_tasks.values()):  # Make a copy to avoid mutations while iterating
                elapsed = str(timedelta(seconds=round(time.time() - task["starttime"])))
                if len(elapsed) > elapsed_max_len:
                    elapsed_max_len = len(elapsed)
                rows.append((
                    task["name"],
                    f"[dim]{task['file']}[/dim]",
                    bar_col(self._tasks[task["task"]]) if task["task"] else "",
                    elapsed
                ))

            table = Table(show_header=False, box=box.SIMPLE, expand=True)
            table.add_column("Task", no_wrap=True, min_width=self.task_max_len + 2, ratio=1)
            table.add_column("File", no_wrap=True)
            table.add_column("Bar", width=10)
            table.add_column("Elapsed", no_wrap=True, width=elapsed_max_len, justify="right",
                             style="progress.remaining")
            table.add_row("[b]Task[/]", "[b]File[/]", "", "[default b]Elapsed[/]")
            for row in rows:
                table.add_row(*row)
            yield table


class LogHandler:
    """Class providing a log handler for Snakemake."""

    icon = "\U0001f426"

    def __init__(self, progressbar=True, log_level=None, log_file_level=None, simple=False, stats=False,
                 pass_through=False, dry_run=False):
        """Initialize log handler.

        Args:
            progressbar: Set to False to disable progress bar. Enabled by default.
            log_level: Log level for logging to stdout.
            log_file_level: Log level for logging to file.
            simple: Set to True to show less info about currently running jobs.
            stats: Set to True to show stats after completion.
            pass_through: Let Snakemake's log messages pass through uninterrupted.
            dry_run: Set to True to print summary about jobs.
        """
        self.use_progressbar = progressbar and console.is_terminal
        self.simple = simple or not console.is_terminal
        self.pass_through = pass_through
        self.dry_run = dry_run
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
        self.jobs_max_len = 0
        self.stats = stats
        self.stats_data = defaultdict(float)
        self.logger = None

        # Progress bar related variables
        self.progress: Optional[progress.Progress] = None
        self.bar: Optional[progress.TaskID] = None
        self.bar_started: bool = False
        self.last_percentage = 0
        self.current_jobs = OrderedDict()
        self.job_ids = {}  # Translation from (Sparv task name, source file) to Snakemake job ID

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

    def setup_loggers(self):
        """Set up log handlers for logging to stdout and log file."""
        if not self.log_level or not self.log_file_level:
            return

        self.logger = logging.getLogger("sparv_logging")
        internal_filter = InternalFilter()
        progress_internal_filter = ProgressInternalFilter()

        # stdout logger
        stream_handler = ModifiedRichHandler(enable_link_path=False, rich_tracebacks=True, console=console)
        stream_handler.setLevel(self.log_level.upper())
        stream_handler.addFilter(internal_filter)
        log_format = "%(message)s" if stream_handler.level > logging.DEBUG else "(%(process)d) - %(message)s"
        stream_handler.setFormatter(logging.Formatter(log_format, datefmt=TIME_FORMAT))
        self.logger.addHandler(stream_handler)

        # File logger
        self.log_filename = "{}.log".format(datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S.%f"))
        file_handler = FileHandlerWithDirCreation(os.path.join(paths.log_dir, self.log_filename), mode="w",
                                                  encoding="UTF-8", delay=True)
        file_handler.setLevel(self.log_file_level.upper())
        file_handler.addFilter(progress_internal_filter)
        log_format = LOG_FORMAT if file_handler.level > logging.DEBUG else LOG_FORMAT_DEBUG
        file_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(file_handler)

        # Level counter
        levelcount_handler = LogLevelCounterHandler(self.log_levelcount)
        levelcount_handler.setLevel(logging.WARNING)
        self.logger.addHandler(levelcount_handler)

        # Internal log handler
        internal_handler = InternalLogHandler(self.export_dirs, self.progress, self.current_jobs, self.job_ids)
        internal_handler.setLevel(INTERNAL)
        self.logger.addHandler(internal_handler)

    def setup_bar(self):
        """Initialize the progress bar but don't start it yet."""
        print()
        progress_layout = [
            progress.SpinnerColumn("dots2"),
            progress.BarColumn(bar_width=None if not self.simple else 40),
            progress.TextColumn("[progress.description]{task.description}"),
            progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            progress.TextColumn("[progress.remaining]{task.completed} of {task.total} tasks"),
            progress.TextColumn("{task.fields[text]}")
        ]
        if self.simple:
            self.progress = progress.Progress(*progress_layout, console=console)
        else:
            self.progress = ProgressWithTable(self.jobs, self.current_jobs, self.jobs_max_len,
                                              *progress_layout, console=console)
        self.progress.start()
        self.bar = self.progress.add_task(self.icon, start=False, total=0, text="[dim]Preparing...[/dim]")

        # Logging needs to be set up after the bar, to make use if its print hook
        self.setup_loggers()

    def start_bar(self, total: int):
        """Start progress bar."""
        self.progress.update(self.bar, total=total)
        self.progress.start_task(self.bar)
        self.bar_started = True

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
                            "'import.text_annotation', but only if it refers to an annotation from the " \
                            "source files."

            self.messages["error"].append((source, _message))

        def missing_annotations_or_files(source, files):
            """Create error message when annotations or other files are missing."""
            errmsg = []
            missing_annotations = []
            missing_other = []
            for f in files.splitlines():
                f = Path(f)
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
                    "The following input annotation{} {} missing:\n"
                    " • {}\n".format(
                        "s" if len(missing_annotations) > 1 else "",
                        "are" if len(missing_annotations) > 1 else "is",
                        "\n • ".join(":".join(ann) if len(ann) == 2 else ann[0] for ann in missing_annotations)
                    )
                ]
            if missing_other:
                if errmsg:
                    errmsg.append("\n")
                errmsg.append(
                    "The following input file{} {} missing:\n"
                    " • {}\n".format(
                        "s" if len(missing_other) > 1 else "",
                        "are" if len(missing_other) > 1 else "is",
                        "\n • ".join(missing_other)
                    )
                )
            if errmsg:
                errmsg.append("\n" + missing_annotations_msg)
            self.messages["error"].append((source, "".join(errmsg)))

        level = msg["level"]

        if level == "run_info":
            # Parse list of jobs do to and total job count
            lines = msg["msg"].splitlines()[2:]
            total_jobs = lines[-1].strip()
            for j in lines[:-1]:
                _, count, job = j.split("\t")
                self.jobs[job.replace("::", ":")] = int(count)

            self.jobs_max_len = max(map(len, self.jobs))

            if self.use_progressbar and not self.bar_started:
                # Get number of jobs and start progress bar
                if total_jobs.isdigit():
                    self.start_bar(int(total_jobs))

        elif level == "progress":
            if self.use_progressbar:
                # Advance progress
                self.progress.advance(self.bar)

            # Print regular updates if output is not a terminal (i.e. doesn't support the progress bar)
            elif self.logger and not console.is_terminal:
                percentage = (100 * msg["done"]) // msg["total"]
                if percentage > self.last_percentage:
                    self.last_percentage = percentage
                    self.logger.log(PROGRESS, f"{percentage}%")

            if msg["done"] == msg["total"]:
                self.stop()

        elif level == "job_info" and self.use_progressbar:
            if msg["msg"] and self.bar is not None:
                # Update progress status message
                self.progress.update(self.bar, text=msg["msg"] if self.simple else "")

                if not self.simple:
                    file = msg["wildcards"].get("file", "")
                    if file.startswith(str(paths.work_dir)):
                        file = file[len(str(paths.work_dir)) + 1:]

                    self.current_jobs[msg["jobid"]] = {
                        "task": None,
                        "name": msg["msg"],
                        "starttime": time.time(),
                        "file": file
                    }

                    self.job_ids[(msg["msg"], file)] = msg["jobid"]

        elif level == "job_finished" and self.use_progressbar and msg["jobid"] in self.current_jobs:
            this_job = self.current_jobs[msg["jobid"]]
            if self.stats:
                self.stats_data[this_job["name"]] += time.time() - this_job["starttime"]
            if this_job["task"]:
                self.progress.remove_task(this_job["task"])
            self.job_ids.pop((this_job["name"], this_job["file"]), None)
            self.current_jobs.pop(msg["jobid"], None)

        elif level == "info":
            if self.pass_through or msg["msg"] == "Nothing to be done.":
                self.info(msg["msg"])

        elif level == "error":
            if self.pass_through:
                self.messages["unhandled_error"].append(msg)
                return
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
            elif "MissingInputException" in msg["msg"]:
                msg_contents = re.search(r" for rule (\S+):\n(.+)", msg["msg"])
                rule_name, filelist = msg_contents.groups()
                rule_name = rule_name.replace("::", ":")
                if self.missing_configs_re.search(filelist):
                    missing_config_message(rule_name)
                elif self.missing_binaries_re.search(filelist):
                    missing_binary_message(rule_name)
                elif self.missing_classes_re.search(filelist):
                    missing_class_message(rule_name, self.missing_classes_re.findall(filelist))
                else:
                    missing_annotations_or_files(rule_name, filelist)
                handled = True

            # Missing output files
            elif "MissingOutputException" in msg["msg"]:
                msg_contents = re.search(r"Missing files after .*?:\n(.+)\nThis might be due to", msg["msg"],
                                         flags=re.DOTALL)
                missing_files = "\n • ".join(msg_contents.group(1).strip().splitlines())
                message = f"The following output files were expected but are missing:\n" \
                          f" • {missing_files}\n" + missing_annotations_msg
                self.messages["error"].append((None, message))
                handled = True
            elif "Exiting because a job execution failed." in msg["msg"]:
                pass
            elif "run_snake.py\' returned non-zero exit status 1." in msg["msg"]:
                handled = True
            elif "Error: Directory cannot be locked." in msg["msg"]:
                message = "Directory cannot be locked. Please make sure that no other Sparv instance is currently " \
                          "processing this corpus. If you are sure that no other Sparv instance is using this " \
                          "directory, run 'sparv run --unlock' to remove the lock."
                self.messages["error"].append((None, message))
                handled = True
            elif "IncompleteFilesException:" in msg["msg"]:
                msg_contents = re.search(r"Incomplete files:\n(.+)", msg["msg"], flags=re.DOTALL)
                incomplete_files = "\n • ".join(msg_contents.group(1).strip().splitlines())
                message = "The files below seem to be incomplete. If you are sure that certain files are not " \
                          "incomplete, mark them as complete with 'sparv run --mark-complete <filenames>'.\n" \
                          "To re-generate the files instead, rerun your command with the --rerun-incomplete flag.\n" \
                          "Incomplete files:\n" \
                          f" • {incomplete_files}"
                self.messages["error"].append((None, message))
                handled = True

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
        """Stop the progress bar and output any messages."""
        # Make sure this is only run once
        if not self.finished:
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
                    console.control(Control(
                        ControlType.CARRIAGE_RETURN,
                        *((ControlType.CURSOR_UP, 1), (ControlType.ERASE_IN_LINE, 2)) * 2
                    ))

            self.finished = True

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
                    if self.log_filename:
                        self.error(
                            "Job execution failed. See log messages above or {} for details.".format(
                                os.path.join(paths.log_dir, self.log_filename)))
                    else:
                        self.error("Job execution failed. See log messages above for details.")
            # Unhandled errors
            elif self.messages["unhandled_error"]:
                for error in self.messages["unhandled_error"]:
                    errmsg = ["An unexpected error occurred."]
                    if self.log_level and logging._nameToLevel[self.log_level.upper()] > logging.DEBUG:
                        errmsg[0] += " To display further details about this error, rerun Sparv with the " \
                                     "'--log debug' argument.\n"
                        if "msg" in error:
                            error_lines = error["msg"].splitlines()
                            if " in line " in error_lines[0]:
                                errmsg.append(error_lines[0].split(" in line ")[0] + ":")
                                for line in error_lines[1:]:
                                    if line.startswith("  File "):
                                        break
                                    errmsg.append(line)
                    else:
                        errmsg.append("")
                        errmsg.append(error.get("msg", "An unknown error occurred."))
                    self.error("\n".join(errmsg))
            else:
                spacer = ""
                if self.export_dirs:
                    spacer = "\n"
                    self.info("The exported files can be found in the following location{}:\n • {}".format(
                        "s" if len(self.export_dirs) > 1 else "", "\n • ".join(sorted(self.export_dirs))))

                if self.stats_data:
                    spacer = ""
                    table = Table(show_header=False, box=box.SIMPLE)
                    table.add_column("Task", no_wrap=True, min_width=self.jobs_max_len + 2, ratio=1)
                    table.add_column("Time taken", no_wrap=True, width=10, justify="right", style="progress.remaining")
                    table.add_column("Percentage", no_wrap=True, justify="right")
                    table.add_row("[b]Task[/]", "[default b]Time taken[/]", "[b]Percentage[/b]")
                    total_time = sum(self.stats_data.values())
                    for task, elapsed in sorted(self.stats_data.items(), key=lambda x: -x[1]):
                        table.add_row(task, str(timedelta(seconds=round(elapsed))),
                                      "{:.1f}%".format(100 * elapsed / total_time))
                    console.print(table)

                if self.log_levelcount:
                    # Errors or warnings were logged but execution finished anyway. Notify user of potential problems.
                    problems = []
                    if self.log_levelcount["ERROR"]:
                        problems.append("{} error{}".format(self.log_levelcount["ERROR"],
                                                            "s" if self.log_levelcount["ERROR"] > 1 else ""))
                    if self.log_levelcount["WARNING"]:
                        problems.append("{} warning{}".format(self.log_levelcount["WARNING"],
                                                              "s" if self.log_levelcount["WARNING"] > 1 else ""))
                    self.warning(
                        "{}Job execution finished but {} occurred. See log messages above or {} for details.".format(
                            spacer, " and ".join(problems), os.path.join(paths.log_dir, self.log_filename)))
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


def setup_logging(log_server, log_level: str = "warning", log_file_level: str = "warning", file=None, job=None):
    """Set up logging with socket handler."""
    # Use the lowest log level, but never higher than warning
    log_level = min(logging.WARNING, getattr(logging, log_level.upper()), getattr(logging, log_file_level.upper()))
    socket_logger = logging.getLogger("sparv")
    socket_logger.setLevel(log_level)
    socket_handler = logging.handlers.SocketHandler(*log_server)
    socket_logger.addHandler(socket_handler)
    global current_file, current_job
    current_file = file
    current_job = job
