"""Functions for setting up the Sparv data directory and config."""

from __future__ import annotations

import filecmp
import importlib.resources
import os
import pathlib
import shutil

import appdirs
from rich.padding import Padding
from rich.prompt import Confirm
from sparv.api.util.misc import dump_yaml
from sparv.core.console import console
from sparv.core.paths import paths

VERSION_FILE = "version"


def check_sparv_version(expected_version: str) -> bool | None:
    """Check if the Sparv data directory is up to date.

    Returns:
        True if up to date, False if outdated, None if the version file is missing.
    """
    data_dir = paths.get_data_path()
    version_file = data_dir / VERSION_FILE  # type: ignore
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8") == expected_version
    return None


def copy_resource_files(data_dir: pathlib.Path) -> None:
    """Copy resource files to the data directory.

    Args:
        data_dir: Path to the data directory.
    """
    resources_dir = importlib.resources.files("sparv") / "resources"
    with importlib.resources.as_file(resources_dir) as path:
        for f in path.rglob("*"):
            rel_f = f.relative_to(resources_dir)  # type: ignore
            if f.is_dir():
                (data_dir / rel_f).mkdir(parents=True, exist_ok=True)
            elif (data_dir / rel_f).is_file():
                # Do not overwrite default config file
                if paths.default_config_file == (data_dir / rel_f):
                    continue
                # Only copy if files are different
                if not filecmp.cmp(f, (data_dir / rel_f)):
                    shutil.copy(data_dir / rel_f, data_dir / rel_f.parent / f"{rel_f.name}.bak")
                    console.print(f"{rel_f} has been updated and a backup was created")
                    shutil.copy(f, data_dir / rel_f)
            else:
                shutil.copy(f, data_dir / rel_f)


def reset() -> bool:
    """Remove the data directory config file.

    Returns:
        True if the reset was successful, False otherwise.
    """
    if paths.sparv_config_file.is_file():
        data_dir = paths.read_sparv_config().get("sparv_data")
        try:
            # Delete config file
            paths.sparv_config_file.unlink()
            # Delete config dir if empty
            if not any(paths.sparv_config_file.parent.iterdir()):
                paths.sparv_config_file.parent.rmdir()
        except Exception:
            console.print("An error occurred while trying to reset the configuration.")
            return False
        console.print("Sparv's data directory information has been reset.")
        if data_dir and pathlib.Path(data_dir).is_dir():
            console.print(
                f"The data directory itself has not been removed, and is still available at:\n{data_dir}", width=80
            )
    else:
        console.print("Nothing to reset.")
    return True


def run(version: str, sparv_datadir: str | None = None) -> bool:
    """Query the user about the data directory path unless provided by argument, and populate the path with files.

    Args:
        sparv_datadir: Path to the data directory.

    Returns:
        True if the setup was successful, False otherwise.
    """
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
        env_message = " (set via environment variable)" if using_env else ""
        console.print(
            "\n[b]Sparv Data Directory Setup[/b]\n\n"
            f"Current data directory: [green]{current_dir or '<not set>'}[/green]{env_message}\n\n"
            "Sparv needs a place to store its configuration files, language models and other data. "
            "After selecting the directory you want to use for this purpose, Sparv will populate it with presets and "
            "an empty default configuration file. Any existing presets will be overwritten, but your existing "
            "configuration file will be preserved. Backup copies of any overwritten files will be created in the same "
            "directory.",
            width=80,
        )
        console.print(
            Padding(
                "[b]Tip:[/b] This process can also be completed non-interactively. Run 'sparv setup --help' for "
                "details. You may also override the data directory setting using the environment variable "
                f"'{paths.data_dir_env}'.",
                (1, 4),
            ),
            width=80,
        )

        if using_env and current_dir:
            try:
                console.print(
                    f"[b red]NOTE:[/b red] Sparv's data directory is currently set to '{current_dir}' using the "
                    f"environment variable '{paths.data_dir_env}'. This variable takes precedence over any previous "
                    f"path set using this setup process. To change the path, either edit the environment variable, or "
                    f"delete the variable and rerun the setup command.\n\n",
                    width=80,
                )
                cont = Confirm.ask(
                    "Do you want to continue the setup process using the above path? (This will not change the data "
                    "directory setting, only setup the contents of the directory specified by the environment "
                    "variable.)",
                )
            except KeyboardInterrupt:
                console.print("\nSetup interrupted.")
                return False
            if not cont:
                console.print("\nSetup aborted.")
                return False
            path = current_dir
        else:
            # Ask user for path
            if current_dir:
                msg = f" Leave empty to continue using '{current_dir}':"
            else:
                msg = f" Leave empty to use the default which is '{default_dir}':"

            try:
                console.print(f"Enter the path to the directory you want to use.{msg}", width=80)
                path_str = input().strip()
            except KeyboardInterrupt:
                console.print("\nSetup interrupted.")
                return False
            path = pathlib.Path(path_str) if path_str else current_dir or default_dir

    try:
        # Expand any "~" and make the path absolute
        path = path.expanduser().resolve()
        # Create directories
        dirs = [paths.bin_dir.name, paths.config_dir.name, paths.models_dir.name]  # type: ignore
        path.mkdir(parents=True, exist_ok=True)
        for d in dirs:
            (path / d).mkdir(exist_ok=True)
    except Exception:
        console.print(
            "\nAn error occurred while trying to create the directories. "
            "Make sure the path you entered is correct, and that you have the necessary read/write permissions.",
            width=80,
        )
        return False

    if not using_env:
        # Save data directory setting to config file
        config_dict = {"sparv_data": str(path)}

        paths.sparv_config_file.parent.mkdir(parents=True, exist_ok=True)
        with paths.sparv_config_file.open("w", encoding="utf-8") as f:
            f.write(dump_yaml(config_dict))

    copy_resource_files(path)

    # Save Sparv version number to a file in data directory
    (path / VERSION_FILE).write_text(version, encoding="utf-8")

    console.print(f"\nSetup completed. The Sparv data directory is set to '{path}'.", width=80)
    return True
