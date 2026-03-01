"""Paths used by Sparv."""

from __future__ import annotations

import os
from pathlib import Path

import appdirs
import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


class SparvPaths:
    """Paths used by Sparv."""

    def __init__(self) -> None:
        """Initialize paths."""
        # Path to the 'sparv' package
        self.sparv_path = Path(__file__).parent.parent

        # Config file containing path to Sparv data directory
        self.sparv_config_file = Path(appdirs.user_config_dir("sparv"), "config.yaml")
        self.autocomplete_cache = Path(appdirs.user_config_dir("sparv"), "autocomplete")

        # Package-internal paths
        self.modules_dir = "modules"
        self.core_modules_dir = "core_modules"

        # Sparv data path (to be read from config)
        self.data_dir = None
        # Environment variable to override data path from config
        self.data_dir_env = "SPARV_DATADIR"

        # Data resource paths (below data_dir)
        self.config_dir = self.get_data_path("config")
        self.default_config_file = self.get_data_path(self.config_dir / "config_default.yaml")
        self.presets_dir = self.get_data_path(self.config_dir / "presets")
        self.models_dir = self.get_data_path("models")
        self.bin_dir = self.get_data_path("bin")

        # Corpus-relative paths
        self.corpus_dir = Path(os.environ.get("CORPUS_DIR", ""))
        self.work_dir = Path("sparv-workdir")
        self.log_dir = Path("logs")
        self.source_dir = "source"
        self.export_dir = Path("export")
        self.config_file = "config.yaml"

    def read_sparv_config(self) -> dict:
        """Get Sparv data path from the config file.

        Returns:
            dict: Sparv config data.
        """
        data = {}
        if self.sparv_config_file.is_file():
            try:
                with self.sparv_config_file.open(encoding="utf-8") as f:
                    data = yaml.load(f, Loader=SafeLoader)
            except Exception:
                data = {}
        return data

    def get_data_path(self, subpath: str | Path = "") -> Path | None:
        """Get the location of the directory containing Sparv models, binaries, and other files.

        Args:
            subpath: Optional subpath to append to the data directory.

        Returns:
            Path to the data directory or data directory subpath.
        """
        # Environment variable overrides config
        if not self.data_dir and (
            data_dir_str := os.environ.get(self.data_dir_env) or self.read_sparv_config().get("sparv_data")
        ):
            self.data_dir = Path(data_dir_str).expanduser().resolve()

        if subpath:
            return self.data_dir / subpath if self.data_dir else Path(subpath)
        return self.data_dir


paths = SparvPaths()
