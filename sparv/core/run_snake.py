"""This script is used by Snakemake to run Sparv modules."""

import importlib
import logging
import os

from sparv.core import paths, log, log_handler
from sparv.core.registry import annotators
from sparv.util import SparvErrorMessage

custom_name = "custom"

# The snakemake variable is provided by Snakemake. The below is just to get fewer errors in editor.
try:
    snakemake
except NameError:
    snakemake = None

# Import module
modules_path = ".".join(("sparv", paths.modules_dir))
module_name = snakemake.params.module_name
if module_name.startswith(custom_name):
    name = module_name[len(custom_name) + 1:]
    module_path = paths.corpus_dir.resolve() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
else:
    module = importlib.import_module(".".join((modules_path, module_name)))

# Get function name and parameters
f_name = snakemake.params.f_name
parameters = snakemake.params.parameters

log.setup_logging(verbose=snakemake.params.log)
logger = logging.getLogger("sparv")
logger.info("RUN: %s:%s(%s)", module_name, f_name, ", ".join("%s=%s" % (i[0], repr(i[1])) for i in
                                                             list(parameters.items())))

# Execute function
try:
    annotators[module_name][f_name]["function"](**parameters)
except SparvErrorMessage as e:
    log_handler.exit_with_message(e, snakemake.params.pid, os.getpid(), module_name, f_name)
