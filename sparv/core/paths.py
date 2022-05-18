"""Paths used by Sparv."""
import os
from pathlib import Path
from typing import Union, Optional

import appdirs
import yaml


def read_sparv_config():
    """Get Sparv data path from config file."""
    data = {}
    if sparv_config_file.is_file():
        try:
            with open(sparv_config_file, encoding="utf-8") as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
        except:
            data = {}
    return data


def get_data_path(subpath: Union[str, Path] = "") -> Optional[Path]:
    """Get location of directory containing Sparv models, binaries and other files."""
    global data_dir

    if not data_dir:
        # Environment variable overrides config
        data_dir_str = os.environ.get(data_dir_env) or read_sparv_config().get("sparv_data")
        if data_dir_str:
            data_dir = Path(data_dir_str).expanduser()

    if subpath and data_dir:
        return data_dir / subpath
    elif subpath:
        return Path(subpath)
    else:
        return data_dir


# Path to the 'sparv' package
sparv_path = Path(__file__).parent.parent

# Config file containing path to Sparv data dir
sparv_config_file = Path(appdirs.user_config_dir("sparv"), "config.yaml")

# Package-internal paths
modules_dir = "modules"
core_modules_dir = "core_modules"

# Sparv data path (to be read from config)
data_dir = None
# Environment variable to override data path from config
data_dir_env = "SPARV_DATADIR"

# Data resource paths (below data_dir)
config_dir = get_data_path("config")
default_config_file = get_data_path(config_dir / "config_default.yaml")
presets_dir = get_data_path(config_dir / "presets")
models_dir = get_data_path("models")
bin_dir = get_data_path("bin")

# Corpus relative paths
corpus_dir = Path(os.environ.get("CORPUS_DIR", ""))
work_dir = Path("sparv-workdir")
log_dir = "logs"
source_dir = "source"
export_dir = Path("export")
config_file = "config.yaml"
