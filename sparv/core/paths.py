"""Paths used by Sparv."""
import os
from pathlib import Path

sparv_path = Path(__file__).parent.parent
pipeline_path = Path(sparv_path).parent

# Internal paths
modules_dir = "modules"
models_dir = "models"
bin_dir = "bin"

# Corpus relative paths
corpus_dir = os.environ.get("CORPUS_DIR", "")
annotation_dir = "annotations"
source_dir = "original"
export_dir = "export"
config_file = "config.yaml"
default_config_file = "config_default.yaml"

# CWB variables
cwb_encoding = os.environ.get("CWB_ENCODING", "utf8")
cwb_datadir = os.environ.get("CWB_DATADIR")
cwb_registry = os.environ.get("CWB_REGISTRY")


def get_model_path(name: str):
    """Get full path to model file."""
    return os.path.join(pipeline_path, models_dir, name)


def get_bin_path(name: str):
    """Get full path to binary file."""
    return os.path.join(pipeline_path, bin_dir, name)
