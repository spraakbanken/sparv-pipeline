"""Functions for setting up the Sparv data dir and config."""
import filecmp
import os
import pathlib
import shutil
import sys
from typing import Optional

import appdirs
import pkg_resources
from rich.padding import Padding
from rich.prompt import Confirm

from sparv import __version__
from sparv.core import config, paths
from sparv.core.console import console

VERSION_FILE = "version"


def check_sparv_version() -> Optional[bool]:
    """Check if the Sparv data dir is outdated.

    Returns:
        True if up to date, False if outdated, None if version file is missing.
    """
    data_dir = paths.get_data_path()
    version_file = (data_dir / VERSION_FILE)
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8") == __version__
    return None


def copy_resource_files(data_dir: pathlib.Path):
    """Copy resource files to data dir."""
    resources_dir = pathlib.Path(pkg_resources.resource_filename("sparv", "resources"))

    for f in resources_dir.rglob("*"):
        rel_f = f.relative_to(resources_dir)
        if f.is_dir():
            (data_dir / rel_f).mkdir(parents=True, exist_ok=True)
        else:
            # Check if file already exists in data dir
            if (data_dir / rel_f).is_file():
                # Only copy if files are different
                if not filecmp.cmp(f, (data_dir / rel_f)):
                    shutil.copy((data_dir / rel_f), (data_dir / rel_f.parent / (rel_f.name + ".bak")))
                    console.print(f"{rel_f} has been updated and a backup was created")
                    shutil.copy(f, data_dir / rel_f)
            else:
                shutil.copy(f, data_dir / rel_f)


def reset():
    """Remove the data dir config file."""
    if paths.sparv_config_file.is_file():
        data_dir = paths.read_sparv_config().get("sparv_data")
        try:
            # Delete config file
            paths.sparv_config_file.unlink()
            # Delete config dir if empty
            if not any(paths.sparv_config_file.parent.iterdir()):
                paths.sparv_config_file.parent.rmdir()
        except:
            console.print("An error occurred while trying to reset the configuration.")
            sys.exit(1)
        console.print("Sparv's data directory information has been reset.")
        if data_dir and pathlib.Path(data_dir).is_dir():
            console.print(f"The data directory itself has not been removed, and is still available at:\n{data_dir}")
    else:
        console.print("Nothing to reset.")


def run(sparv_datadir: Optional[str] = None):
    """Query user about data dir path unless provided by argument, and populate path with files."""
    default_dir = pathlib.Path(appdirs.user_data_dir("sparv"))
    current_dir = paths.get_data_path()
    path: pathlib.Path
    using_env = bool(os.environ.get(paths.data_dir_env))

    if sparv_datadir:
        # Specifying a path on the command line will perform the setup using that path, even if the environment
        # variable is set
        using_env = False
        path = pathlib.Path(sparv_datadir)
    else:
        console.print(
            "\n[b]Sparv Data Directory Setup[/b]\n\n"
            f"Current data directory: [green]{current_dir or '<not set>'}[/green]\n\n"
            "Sparv needs a place to store its configuration files, language models and other data. "
            "After selecting the directory you want to use for this purpose, Sparv will populate it with a default "
            "config file and presets. Any existing files in the target directory will be backed up. Any previous "
            "backups will be overwritten.")
        console.print(Padding(
            "[b]Tip:[/b] This process can also be completed non-interactively. Run 'sparv setup --help' for details. "
            f"You may also override the data directory setting using the environment variable '{paths.data_dir_env}'.",
            (1, 4)))

        if using_env:
            try:
                cont = Confirm.ask(
                    f"[b red]NOTE:[/b red] Sparv's data directory is currently set to '{current_dir}' using the "
                    f"environment variable '{paths.data_dir_env}'. This variable takes precedence over any previous "
                    f"path set using this setup process. To change the path, either edit the environment variable, or "
                    f"delete the variable and rerun the setup command.\n"
                    "Do you want to continue the setup process using the above path?")
            except KeyboardInterrupt:
                console.print("\nSetup interrupted.")
                sys.exit()
            if not cont:
                console.print("\nSetup aborted.")
                sys.exit()
            path = current_dir
        else:
            # Ask user for path
            if current_dir:
                msg = f" Leave empty to continue using '{current_dir}':"
            else:
                msg = f" Leave empty to use the default which is '{default_dir}':"

            try:
                console.print(f"Enter the path to the directory you want to use.{msg}")
                path_str = input().strip()
            except KeyboardInterrupt:
                console.print("\nSetup interrupted.")
                sys.exit()
            if path_str:
                path = pathlib.Path(path_str)
            else:
                if current_dir:
                    path = current_dir
                else:
                    path = default_dir

    try:
        # Expand any "~"
        path = path.expanduser()
        # Create directories
        dirs = [paths.bin_dir.name, paths.config_dir.name, paths.models_dir.name]
        path.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (path / d).mkdir(exist_ok=True)
    except:
        console.print(
            "\nAn error occurred while trying to create the directories. "
            "Make sure the path you entered is correct, and that you have the necessary read/write permissions.")
        sys.exit(1)

    if not using_env:
        # Save data dir setting to config file
        config_dict = {
            "sparv_data": str(path)
        }

        paths.sparv_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(paths.sparv_config_file, "w", encoding="utf-8") as f:
            f.write(config.dump_config(config_dict))

    copy_resource_files(path)

    # Save Sparv version number to a file in data dir
    (path / VERSION_FILE).write_text(__version__, encoding="utf-8")

    console.print(f"\nSetup completed. The Sparv data directory is set to '{path}'.")
