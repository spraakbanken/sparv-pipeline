"""Functions for setting up the Sparv data dir and config."""

import pathlib
import shutil
import sys

import appdirs
import pkg_resources
import yaml

from sparv import __version__
from sparv.core import paths


def copy_resource_files(data_dir, backup: bool = True):
    """Copy resource files to data dir."""
    data_dir = pathlib.Path(data_dir)
    resources_dir = pathlib.Path(pkg_resources.resource_filename("sparv", "resources"))

    for f in resources_dir.rglob("*"):
        rel_f = f.relative_to(resources_dir)
        if f.is_dir():
            (data_dir / rel_f).mkdir(parents=True, exist_ok=True)
        else:
            if backup and (data_dir / rel_f).is_file():
                shutil.copy((data_dir / rel_f), (data_dir / rel_f.parent / (rel_f.name + ".bak")))
            shutil.copy(f, data_dir / rel_f)


def query_user():
    """Query user about data dir path."""
    default_dir = appdirs.user_data_dir("sparv")
    current_dir = paths.get_data_path()

    if current_dir:
        msg = f"Leave empty to continue using '{current_dir}'."
    else:
        msg = "Leave empty to use the default which is '{}'.".format(appdirs.user_data_dir("sparv"))

    path = input(f"Sparv needs a place to store its configuration files, language models and other data. Enter the "
                 f"path to the directory you want to use. {msg}\n").strip()
    reused = False
    if not path:
        if current_dir:
            reused = True
            path = current_dir
        else:
            path = default_dir
    path = pathlib.Path(path)

    try:
        # Create directories
        dirs = [paths.bin_dir.name, paths.config_dir.name, paths.models_dir.name]
        path.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (path / d).mkdir(exist_ok=True)
    except:
        print("\nAn error occurred while trying to create the directories. "
              "Make sure the path you entered is correct, and that you have the neccessary read/write permissions.")
        sys.exit(1)

    config_dict = {
        "sparv_data": str(path),
        "version": __version__
    }

    # Save path to YAML file
    paths.sparv_config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(paths.sparv_config_file, "w") as f:
        yaml.dump(config_dict, f)

    backup = False
    if reused:
        # If directory already exists, ask if the user wants to backup any existing files
        while True:
            backup = input("A default config file and presets will be copied to this directory. Do you want to create "
                           "backups of any existing files? Previous backups will be overwritten. [y/n]").strip().lower()
            if backup and backup in "yn":
                backup = backup == "y"
                break

    copy_resource_files(path, backup)

    created_msg = f" and the following directory has been created:\n{path}" if not reused else "."

    print(f"\nSettings have been saved{created_msg}")
