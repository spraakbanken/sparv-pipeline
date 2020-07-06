"""This script is used by Snakemake to run Sparv modules."""

import importlib
import logging
import os

from pkg_resources import iter_entry_points

from sparv.core import log, log_handler, paths
from sparv.core.registry import annotators
from sparv.util import SparvErrorMessage

custom_name = "custom"
plugin_name = "plugin"

# The snakemake variable is provided by Snakemake. The below is just to get fewer errors in editor.
try:
    snakemake
except NameError:
    snakemake = None

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
            log_handler.exit_with_message(e, snakemake.params.pid, os.getpid(), "sparv", "run")


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
    log_handler.exit_with_message(e, snakemake.params.pid, os.getpid(), module_name, f_name)
