"""Summarizes and exports annotation version information."""


from datetime import datetime

import yaml

from sparv import __version__ as sparv_version
from sparv.api import Export, exporter, get_logger

logger = get_logger(__name__)


@exporter("YAML file containing annotation version info")
def yaml_export(out: Export = Export("version_info/info_[metadata.id].yaml")):
    """Create YAML file containing annotation version information."""
    info_dict = {
        "Sparv version": sparv_version,
        "Annotation date": datetime.today().strftime("%Y-%m-%d")
    }

    # Write YAML file
    logger.info("Exported: %s", out)
    content = yaml.dump(info_dict, allow_unicode=True, indent=4, sort_keys=False, default_flow_style=False)
    with open(out, "w", encoding="utf-8") as o:
        o.writelines(content)
