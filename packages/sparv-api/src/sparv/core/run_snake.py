"""Script used by Snakemake to run Sparv modules."""

import importlib.util
import logging
import sys
import traceback
from importlib.metadata import entry_points

from sparv.core import io, log_handler, registry
from sparv.core.misc import SparvErrorMessage
from sparv.core.paths import paths

custom_name = "custom"
plugin_name = "plugin"

# The snakemake variable is provided automatically by Snakemake; the below is just to please linters
snakemake = snakemake  # noqa


def exit_with_error_message(message: str, logger_name: str) -> None:
    """Log an error message and exit with a non-zero status."""
    error_logger = logging.getLogger(logger_name)
    if snakemake.params.source_file:
        message += f"\n\n(file: {snakemake.params.source_file})"
    error_logger.error(message)
    sys.exit(123)


class StreamToLogger:
    """File-like stream object that redirects writes to a logger instance."""

    def __init__(self, logger: logging.Logger, log_level: int = logging.INFO) -> None:
        """Initialize the file-like stream object with a logger and a log level.

        Args:
            logger: Logger instance.
            log_level: Log level.
        """
        self.logger = logger
        self.log_level = log_level

    def write(self, buf: str) -> None:
        """Write to the logger.

        Args:
            buf: String to write.
        """
        self.logger.log(self.log_level, buf.rstrip())

    @staticmethod
    def isatty() -> bool:
        """Return False to indicate that this is not a terminal.

        Returns:
            Always returns False.
        """
        return False

    @staticmethod
    def flush() -> None:
        """Do nothing; needed for compatibility with sys.stdout."""


# Set compression
if snakemake.params.compression:
    io.compression = snakemake.params.compression

# Import module
modules_path = f"sparv.{paths.modules_dir}"
module_name = snakemake.params.module_name

use_preloader = snakemake.params.use_preloader
preloader_busy = False

if use_preloader:
    from sparv.core import preload

    sock = None
    try:
        if snakemake.params.force_preloader:
            sock = preload.connect_to_socket(snakemake.params.socket)
        else:
            # Try to connect to the preloader and fall back to running without it if it's unavailable
            sock = preload.connect_to_socket(snakemake.params.socket, timeout=True)
            sock.settimeout(0.5)
            # Ping preloader to verify that it's free
            preload.send_data(sock, preload.PING)
            response = preload.receive_data(sock)  # Timeouts if busy
            sock.settimeout(None)
    except (TimeoutError, BlockingIOError):
        use_preloader = False
        preloader_busy = True
        if sock is not None:
            sock.close()

if not use_preloader:
    # Import custom module
    if module_name.startswith(custom_name):
        name = module_name[len(custom_name) + 1 :]
        module_path = paths.corpus_dir.resolve() / f"{name}.py"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        try:
            # Try to import standard Sparv module
            module = importlib.import_module(f"{modules_path}.{module_name}")
        except ModuleNotFoundError:
            # Try to find plugin module
            entry_points = {e.name: e for e in entry_points(group=f"sparv.{plugin_name}")}
            if entry_point := entry_points.get(module_name):
                module = entry_point.load()
            else:
                exit_with_error_message(
                    f"Couldn't load plugin '{module_name}'. Please make sure it was installed correctly.", "sparv"
                )
    registry.add_module_to_registry(module, module_name, skip_language_check=True)

# Get function name and parameters
f_name = snakemake.params.f_name
parameters = snakemake.params.parameters

log_handler.setup_logging(
    snakemake.config["log_server"],
    log_level=snakemake.config["log_level"],
    log_file_level=snakemake.config["log_file_level"],
    file=snakemake.params.source_file,
    job=f"{module_name}:{f_name}",
)
logger = logging.getLogger("sparv")
logger.info("RUN: %s:%s(%s)", module_name, f_name, ", ".join(f"{i[0]}={i[1]!r}" for i in list(parameters.items())))

# Redirect any prints to logging module
old_stdout = sys.stdout
old_stderr = sys.stderr
module_logger = logging.getLogger(f"sparv.modules.{module_name}")
sys.stdout = StreamToLogger(module_logger)
sys.stderr = StreamToLogger(module_logger, logging.WARNING)

if not use_preloader:
    if preloader_busy:
        logger.info("Preloader is busy; executing without preloader.")
    # Execute function
    try:
        registry.modules[module_name].functions[f_name]["function"](**parameters)
        if snakemake.params.export_dirs:
            logger.export_dirs(snakemake.params.export_dirs)
    except KeyboardInterrupt:
        exit_with_error_message("Execution was terminated by an interrupt signal", f"sparv.modules.{module_name}")
    except SparvErrorMessage as e:
        # Any exception raised here would be printed directly to the terminal, due to how Snakemake runs the script.
        # Instead, we log the error message and exit with a non-zero status to signal to Snakemake that
        # something went wrong.
        exit_with_error_message(e.message, f"sparv.modules.{module_name}")
    except Exception as e:
        current_file = f" for the file {snakemake.params.source_file!r}" if snakemake.params.source_file else ""
        errmsg = f"An error occurred while executing {module_name}:{f_name}{current_file}:\n\n"
        errmsg_stdout = errmsg + f"  {type(e).__name__}: {e}"
        if logger.level > logging.DEBUG:
            errmsg_stdout += (
                f"\n\nFor more details, please check the log file in the '{paths.log_dir}' directory, or rerun Sparv "
                "with the '--log debug' argument."
            )
        logger.error(errmsg_stdout, extra={"to_stdout": True})
        logger.debug(traceback.format_exc(), extra={"to_stdout": True})
        logger.exception(errmsg, extra={"to_file": True})
        sys.exit(123)
    finally:
        # Restore printing to stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
else:
    try:
        preload.send_data(sock, (f"{module_name}:{f_name}", parameters, snakemake.config, snakemake.params.source_file))
        response = preload.receive_data(sock)
        if isinstance(response, SparvErrorMessage):
            exit_with_error_message(response.message, f"sparv.modules.{module_name}")
        elif isinstance(response, BaseException):
            exit_with_error_message(str(response), f"sparv.modules.{module_name}")
        elif response is not True:
            exit_with_error_message(
                "An error occurred while using the Sparv preloader.", f"sparv.modules.{module_name}"
            )
    finally:
        sock.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
