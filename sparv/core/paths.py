"""Paths used by Sparv."""
import os
from pathlib import Path

sparv_path = Path(__file__).parent.parent
pipeline_path = Path(sparv_path).parent

# Internal paths
config_dir = "config"
modules_dir = "modules"
models_dir = "models"
bin_dir = "bin"

# Corpus relative paths
corpus_dir = os.environ.get("CORPUS_DIR", "")
annotation_dir = "annotations"
source_dir = "original"
export_dir = "export"
config_file = "config.yaml"

default_config_file = os.path.join(config_dir, "config_default.yaml")
presets_dir = os.path.join(config_dir, "presets")

# CWB variables
cwb_encoding = os.environ.get("CWB_ENCODING", "utf8")
cwb_datadir = os.environ.get("CWB_DATADIR")
corpus_registry = os.environ.get("CORPUS_REGISTRY")


def get_bin_path(name: str):
    """Get full path to binary file (platform independent)."""
    components = name.split("/")
    return os.path.join(pipeline_path, bin_dir, *components)
