"""Functions for reading and displaying plugin information."""

import json
import re
import sys
import urllib.request

import iso639
from pkg_resources import Requirement, iter_entry_points
from rich import box
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from sparv import __version__
import sparv
from sparv.core import paths
from sparv.core.console import console
from sparv.core.misc import get_logger

logger = get_logger(__name__)
SYSTEM_PYTHON = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"


def load_manifests(url):
    """Get manifests from url and handle errors."""
    req = urllib.request.Request(url)
    try:
        r = urllib.request.urlopen(req).read()
        data = json.loads(r.decode())
        if len(data) < 1:
            console.print(f"\n[red]Something went wrong. No plugins found![/red]")
            exit(1)
        return data
    except (urllib.error.URLError, urllib.error.HTTPError):
        console.print(f"\n[red]Failed to retrieve plugin manifests from '{url}'![/red]")
        exit(1)
    except json.decoder.JSONDecodeError:
        console.print(f"\n[red]Failed to retrieve plugin manifests due to invalid JSON![/red]")
        exit(1)
    except Exception as e:
        console.print(f"\n[red]Failed to retrieve plugin manifests! Reason:\n{e}[/red]", highlight=False)
        exit(1)


def parse_manifest(manifest, installed_plugins):
    """Parse a plugin manifest and add information."""
    # Go through versions and collect info
    all_versions = {}
    for version_dict in manifest.get("versions"):
        for k, v in manifest.items():
            if k == "versions":
                continue
            version_dict[k] = v
        python_compatible, sparv_compatible = valid_version(version_dict.get("python_requires"),
                                                            version_dict.get("sparv_pipeline_requires"))
        version_dict["python_compatible"] = python_compatible
        version_dict["sparv_compatible"] = sparv_compatible
        version_dict["compatible"] = python_compatible and sparv_compatible
        all_versions[version_dict["version"]] = version_dict
    sorted_versions = sorted(all_versions.keys(), reverse=True)

    # Check if plugin is installed
    if manifest["name"] in installed_plugins:
        installed_version = installed_plugins[manifest["name"]]
    else:
        installed_version = None

    # Check compatibiliy and newest version
    compatible_versions = [v for v in sorted_versions if all_versions[v]["compatible"]]
    newest_version = sorted_versions[0]
    if all_versions[newest_version]["compatible"]:
        newest_compatible = newest_version
    else:
        for v in compatible_versions:
            if all_versions[v]["compatible"]:
                newest_compatible = v
                break

    return {
        "installed_version": installed_version,
        "compatible_versions": compatible_versions,
        "newest_compatible": newest_compatible,
        "versions": all_versions
    }


def list_plugins():
    """Print all supported plugins."""
    manifests = load_manifests(paths.plugins_url)
    # installed_plugins = get_installed_plugins()
    installed_plugins = []
    incompatible_ones = []
    installed_uptodate_ones = []
    installed_outdated_ones = []

    print()
    table = Table(title="Available Sparv plugins", box=box.SIMPLE, show_header=False, title_justify="left")
    for pl in sorted(manifests, key=lambda x: x["name"]):
        data = parse_manifest(pl, installed_plugins)
        installed_v = data["installed_version"]
        newest_compatible = data["newest_compatible"]
        # Feature the version that is installed or the newest compatible version
        featured = data["versions"].get(installed_v, None) or data["versions"].get(newest_compatible, None)
        if data["installed_version"]:
            if installed_v == newest_compatible:
                installed_uptodate_ones.append(data["versions"][installed_v])
            else:
                installed_outdated_ones.append((data["versions"][installed_v], newest_compatible))

        elif data["versions"].get(newest_compatible, None):
            featured = data["versions"].get(newest_compatible, None)
            table.add_row(featured["name"], featured["description"])
        else:
            incompatible_ones.append(data["versions"][0])
    if len(table.rows):
        console.print(table)
        print()
    else:
        console.print("[green]There are no new plugins for you to install![/green]\n")

    # List plugins that should be updated
    if installed_outdated_ones:
        console.print("[i]The following plugin{} should be updated:[/i]".format(
            "s" if len(installed_outdated_ones) > 1 else ""))
        table = Table("", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_row("[b]Name[/b]", "[b]Description[/b]", "[b]Most recent version[/b]", "[b]Installed version[/b]")
        for plugin, newest_version in installed_outdated_ones:
            table.add_row(f"[red]{plugin['name']}[/red]", plugin["description"], newest_version, plugin["version"])
        console.print(table)
        print()

    # List installed plugins that are up-to-date
    if installed_uptodate_ones:
        console.print("[i]The following plugin{} {} installed and up-to-date:[/i]".format(
            "s" if len(installed_uptodate_ones) > 1 else "",
            "are" if len(installed_uptodate_ones) > 1 else "is"))
        table = Table("", box=box.SIMPLE, show_header=False, title_justify="left")
        for plugin in installed_uptodate_ones:
            table.add_row(f"[green]{plugin['name']}[/green]", plugin["description"])
        console.print(table)
        print()

    # List incompatible plugins
    if incompatible_ones:
        console.print("[i]The following plugin{} {} incompatible with your system:[/i]".format(
            "s" if len(incompatible_ones) > 1 else "",
            "are" if len(incompatible_ones) > 1 else "is"))
        table = Table("", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_row("[b]Name[/b]", "[b]Description[/b]", "[b]Python requirement[/b]", "[b]Sparv requirement[/b]")
        for plugin in incompatible_ones:
            table.add_row(plugin.get("name"),
                          plugin.get("description"),
                          plugin.get("python_requires") if plugin["python_compatible"] else
                              f"[red]{plugin.get('python_requires')}[/red]",
                          plugin.get("sparv_pipeline_requires") if plugin["sparv_compatible"] else
                              f"[red]{plugin.get('sparv_pipeline_requires')}[/red]")
        console.print(table)

    console.print("For more details about a specific plugin run [green]'sparv plugins \\[plugin name]'[/green].\n",
                  highlight=False)


def plugin_info(plugin_names):
    """Print info about a specific plugin."""
    manifests = load_manifests(paths.plugins_url)
    plugins = dict((obj["name"], obj) for obj in manifests)
    missing_plugins = []
    installed = get_installed_plugins()
    padding = (0, 4, 1, 4)
    for i, plugin_name in enumerate(plugin_names):
        plugin = plugins.get(plugin_name)
        if not plugin:
            missing_plugins.append(plugin_name)
        else:
            # Plugin name header
            console.print(f"\n[bright_black]:[/][dim]:[/]: [b]{plugin.get('name').upper()}[/b]\n", highlight=False)

            # Compatibility info
            python_compatible, sparv_compatible = valid_version(plugin.get("python_requires"),
                                                                           plugin.get("sparv_pipeline_requires"))
            if not (python_compatible and sparv_compatible):
                console.print(Padding(Text.from_markup(
                    "[red]This plugin is not compatible with your system. "
                    "Requires {0}{1}{2}. You have {3}{1}{4}.[/red]".format(
                        "Python version " + plugin.get("python_requires") if not python_compatible else "",
                        " and " if not python_compatible and not sparv_compatible else "",
                        "Sparv Pipeline version " + plugin.get("sparv_pipeline_requires") if not sparv_compatible
                            else "",
                        "Python v " + SYSTEM_PYTHON if not python_compatible else "",
                        "Sparv Pipeline v " + __version__ if not sparv_compatible else "")
                ), padding))

            # Plugin description
            console.print(Padding(plugin.get("description"), padding))
            if plugin.get("long_description"):
                console.print(Padding(plugin.get("long_description").replace("\n", " "), padding))

            # Info table
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), pad_edge=False,
                          border_style="bright_black")
            table.add_row("author", f"{plugin.get('author')} ({plugin.get('author_email')})")
            table.add_row("source", f"{plugin.get('source')}")
            table.add_row("version", f"{plugin.get('version')}")
            table.add_row("license", f"{plugin.get('license')}")
            if plugin.get("languages"):
                langs = []
                for lang in plugin.get("languages"):
                    if lang in iso639.languages.part3:
                        langs.append(iso639.languages.get(part3=lang).name)
                    else:
                        langs.append(lang)
                langs = ", ".join(sorted(langs))
                table.add_row("supported languages", langs)
            console.print(Padding(table, (0, 0, 0, 3)))

            # Install info
            if plugin["name"] not in installed:
                if python_compatible and sparv_compatible:
                    console.print(Padding(f"Install with: `pipx inject sparv-pipeline {plugin.get('install_pointer')}`",
                                          padding))
            else:
                console.print(Padding("[green]✓ This plugin is installed![/green]\nUninstall with: "
                                      f"`pipx runpip sparv-pipeline uninstall {plugin['name']}`", padding))

            # Additional software info
            if plugin.get("requires_additional_installs", False):
                console.print(Padding("⚠  This plugin requires additional software to be installed.\n",
                              padding))

            # Print separator
            if i < len(plugin_names) - 1 or missing_plugins:
                console.print(Rule())

    if missing_plugins:
        console.print("\n[red]The following plugin{} {} not found: {}[/red]\n".format(
            "s" if len(missing_plugins) > 1 else "",
            "were" if len(missing_plugins) > 1 else "was",
            ", ".join(missing_plugins)))


def valid_version(python_version, sparv_version):
    """Check if this plugin's Python and Sparv versions are compatible with the running versions."""
    python_compatible = sparv_compatible = True
    if SYSTEM_PYTHON not in Requirement(f"python{python_version}"):
        python_compatible = False
    if __version__ not in Requirement(f"sparv-pipeline{sparv_version}"):
        sparv_compatible = False
    return python_compatible, sparv_compatible


def get_installed_plugins():
    """Get installed Sparv plugins and their version numbers."""
    installed_plugins = {}
    for entry_point in iter_entry_points("sparv.plugin"):
        installed_plugins[entry_point.dist.project_name] = entry_point.dist.version
    return installed_plugins
