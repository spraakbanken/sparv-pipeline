"""Functions for parsing the Sparv configuration files."""

import copy
import os
import yaml
from sparv.core import paths

DEFAULT_CONFIG = os.path.join(paths.sparv_path, "..", paths.default_config_file)

# Dict holding full configuration
config = {}


def load_config(config_file: str):
    """Read config file and parse as YAML."""

    # Read defalult config
    with open(DEFAULT_CONFIG) as f:
        default_config = yaml.load(f, Loader=yaml.FullLoader)

    with open(config_file) as f:
        user_config = yaml.load(f, Loader=yaml.FullLoader)

    # Merge default and corpus config
    combined_config = merge_configs(copy.deepcopy(user_config), default_config)

    # Merge with config, overriding existing values
    global config
    config = merge_configs(combined_config, config)


def get(name: str, default=None):
    """Get value from config. If 'name' is missing and 'default' is supplied, add to config."""
    config.setdefault(name, default)
    return config[name]


def extend_config(new_config):
    """Extend existing config with new values for missing keys."""
    merge_configs(config, new_config)


def merge_configs(user, default):
    """Merge user config with default config, letting user values override default values."""
    if isinstance(user, dict) and isinstance(default, dict):
        for k, v in default.items():
            if k not in user:
                user[k] = v
            else:
                user[k] = merge_configs(user[k], v)
    return user
