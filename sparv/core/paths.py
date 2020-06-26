"""Paths used by Sparv."""
import os
from pathlib import Path

sparv_path = Path(__file__).parent.parent
pipeline_path = Path(sparv_path).parent

# Internal paths
config_dir = Path("config")
modules_dir = "modules"
models_dir = Path("models")
bin_dir = "bin"

# Corpus relative paths
corpus_dir = Path(os.environ.get("CORPUS_DIR", ""))
annotation_dir = Path("annotations")
log_dir = annotation_dir / ".log"
source_dir = "original"
export_dir = Path("export")
config_file = "config.yaml"

default_config_file = config_dir / "config_default.yaml"
presets_dir = config_dir / "presets"

# CWB variables
cwb_encoding = os.environ.get("CWB_ENCODING", "utf8")
cwb_datadir = os.environ.get("CWB_DATADIR")
corpus_registry = os.environ.get("CORPUS_REGISTRY")


def get_bin_path(name: str):
    """Get full path to binary file."""
    return pipeline_path / bin_dir / name
