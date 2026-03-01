"""Summarizes and exports annotation version information."""

import importlib.metadata
from datetime import datetime
from pathlib import Path

import yaml

# from sparv import __version__ as sparv_version
from sparv.api import Export, exporter, get_logger

logger = get_logger(__name__)

sparv_version = importlib.metadata.version("sparv")


@exporter("YAML file containing annotation version info")
def yaml_export(out: Export = Export("version_info/info_[metadata.id].yaml")) -> None:
    """Create YAML file containing annotation version information.

    Args:
        out: The output file path.
    """
    info_dict = {
        "Sparv version": sparv_version,
        "Annotation date": datetime.today().strftime("%Y-%m-%d"),
    }

    # Write YAML file
    content = yaml.dump(info_dict, allow_unicode=True, indent=4, sort_keys=False, default_flow_style=False)
    with Path(out).open("w", encoding="utf-8") as o:
        o.writelines(content)
    logger.info("Exported: %s", out)
