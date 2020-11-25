"""Script used by Snakemake to run Sparv modules."""

import importlib.util
import logging
import sys

from pkg_resources import iter_entry_points

from sparv.core import log_handler, paths
from sparv.core import registry
from sparv.util import SparvErrorMessage

custom_name = "custom"
plugin_name = "plugin"

# The snakemake variable is provided automatically by Snakemake; the below is just to please the IDE
try:
    snakemake
except NameError:
    from snakemake.script import Snakemake
    snakemake: Snakemake


def exit_with_error_message(message, logger_name):
    """Log error message and exit with non-zero status."""
    error_logger = logging.getLogger(logger_name)
    error_logger.error(message)
    sys.exit(123)


class StreamToLogger:
    """File-like stream object that redirects writes to a logger instance."""

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        self.logger.log(self.log_level, buf.rstrip())


# Import module
modules_path = ".".join(("sparv", paths.modules_dir))
module_name = snakemake.params.module_name
# Import custom module
if module_name.startswith(custom_name):
    name = module_name[len(custom_name) + 1:]
    module_path = paths.corpus_dir.resolve() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
else:
    try:
        # Try to import standard Sparv module
        module = importlib.import_module(".".join((modules_path, module_name)))
    except ModuleNotFoundError:
        # Try to find plugin module
        entry_points = dict((e.name, e) for e in iter_entry_points(f"sparv.{plugin_name}"))
        entry_point = entry_points.get(module_name)
        if entry_point:
            entry_point.load()
        else:
            exit_with_error_message(
                f"Couldn't load plugin '{module_name}'. Please make sure it was installed correctly.", "sparv")


# Get function name and parameters
f_name = snakemake.params.f_name
parameters = snakemake.params.parameters

log_handler.setup_logging(snakemake.config["log_server"],
                          log_level=snakemake.config["log_level"],
                          log_file_level=snakemake.config["log_file_level"])
logger = logging.getLogger("sparv")
logger.info("RUN: %s:%s(%s)", module_name, f_name, ", ".join("%s=%s" % (i[0], repr(i[1])) for i in
                                                             list(parameters.items())))

# Redirect any prints to logging module
old_stdout = sys.stdout
old_stderr = sys.stderr
module_logger = logging.getLogger("sparv.modules." + module_name)
sys.stdout = StreamToLogger(module_logger)
sys.stderr = StreamToLogger(module_logger, logging.WARNING)

# Execute function
try:
    registry.modules[module_name].functions[f_name]["function"](**parameters)
    if snakemake.params.export_dirs:
        logger.export_dirs(snakemake.params.export_dirs)
except SparvErrorMessage as e:
    # Any exception raised here would be printed directly to the terminal, due to how Snakemake runs the script.
    # Instead we log the error message and exit with a non-zero status to signal to Snakemake that
    # something went wrong.
    exit_with_error_message(e.message, "sparv.modules." + module_name)
finally:
    # Restore printing to stdout and stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr
