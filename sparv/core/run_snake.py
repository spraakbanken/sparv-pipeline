"""This script is used by Snakemake to run Sparv modules."""

import importlib
import logging
import os
import sys

from pkg_resources import iter_entry_points

from sparv.core import log, paths
from sparv.core.registry import annotators
from sparv.util import SparvErrorMessage

custom_name = "custom"
plugin_name = "plugin"

# The snakemake variable is provided by Snakemake. The below is just to get fewer errors in editor.
try:
    snakemake
except NameError:
    snakemake = None


def exit_with_error_message(error, snakemake_pid, pid, module_name, function_name):
    """Save error message to temporary file (to be read by log handler) and exit with non-zero status."""
    log_file = paths.log_dir / "{}.{}.error.{}.{}.log".format(snakemake_pid, pid or 0, module_name, function_name)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(str(error))
    sys.exit(123)


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
            e = f"Couldn't load plugin '{module_name}'. Please make sure it was installed correctly."
            exit_with_error_message(e, snakemake.params.pid, os.getpid(), "sparv", "run")


# Get function name and parameters
f_name = snakemake.params.f_name
parameters = snakemake.params.parameters

log.setup_logging(log_level=snakemake.params.log)
logger = logging.getLogger("sparv")
logger.info("RUN: %s:%s(%s)", module_name, f_name, ", ".join("%s=%s" % (i[0], repr(i[1])) for i in
                                                             list(parameters.items())))

# Execute function
try:
    annotators[module_name][f_name]["function"](**parameters)
except SparvErrorMessage as e:
    # Any exception raised here would be printed directly to the terminal, due to how Snakemake runs the script.
    # Instead we save the error message to a file and exit with a non-zero status to signal to Snakemake that
    # something went wrong. The log handler will take care of printing the error message to the user.
    exit_with_error_message(e.message, snakemake.params.pid, os.getpid(), module_name, f_name)
