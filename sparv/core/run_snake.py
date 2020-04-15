"""This script is used by Snakemake to run Sparv modules."""

import importlib
import logging

from sparv.core import paths, log
from sparv.core.registry import annotators

# The snakemake variable is provided by Snakemake. The below is just to get fewer errors in editor.
try:
    snakemake
except:
    snakemake = None

# Import module
modules_path = ".".join(("sparv", paths.modules_dir))
module_name = snakemake.params.module_name
module = importlib.import_module(".".join((modules_path, module_name)))

# Get function name and parameters
f_name = snakemake.params.f_name
parameters = snakemake.params.parameters

log.setup_logging(verbose=snakemake.params.log)
logger = logging.getLogger("sparv")
logger.info("RUN: %s(%s)", f_name, ", ".join("%s=%s" % (i[0], repr(i[1])) for i in list(parameters.items())))

# Execute function
annotators[module_name][f_name][0](**parameters)
