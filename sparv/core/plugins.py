"""Functions for reading and displaying plugin information."""

import sys

import iso639
import yaml
from pkg_resources import Requirement, iter_entry_points
from rich import box
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from sparv import __version__
from sparv.core import paths
from sparv.core.console import console
from sparv.core.misc import SparvErrorMessage, get_logger

logger = get_logger(__name__)
SYSTEM_PYTHON = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"


def load_manifests(yaml_file):
    """Read YAML file and handle errors."""
    try:
        with open(yaml_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.parser.ParserError as e:
        raise SparvErrorMessage("Could not parse the plugin manifests file:\n" + str(e))
    except yaml.scanner.ScannerError as e:
        raise SparvErrorMessage("An error occurred while reading the plugin manifests file:\n" + str(e))
    except FileNotFoundError:
        raise SparvErrorMessage(f"Could not find the plugin manifests")

    return data or {}


def list_plugins():
    """Print all supported plugins."""
    print()
    manifests = load_manifests(paths.plugins_manifest)
    installed = get_installed_plugins()
    incompatible_plugins = []
    table = Table(title="Supported Sparv plugins", box=box.SIMPLE, show_header=False, title_justify="left")
    for plugin in sorted(manifests, key=lambda x: x["name"]):
        python_compatible, sparv_compatible= valid_version(plugin.get("python_requires"),
                                                            plugin.get("sparv_pipeline_requires"))
        if not (python_compatible and sparv_compatible):
            incompatible_plugins.append((plugin, python_compatible, sparv_compatible))
        else:
            table.add_row(f"[green]{plugin['name']}[/green]" if plugin["name"] in installed else plugin["name"],
                          plugin["description"],)
    console.print(table)

    if incompatible_plugins:
        console.print("\n[i]The following plugin{} {} not compatible with your system:[/i]".format(
            "s" if len(incompatible_plugins) > 1 else "",
            "are" if len(incompatible_plugins) > 1 else "is"))
        table = Table("", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_row("[b]Name[/b]", "[b]Description[/b]", "[b]Python requirement[/b]", "[b]Sparv requirement[/b]")
        for plugin, python_comp, sparv_comp in incompatible_plugins:
            table.add_row(plugin.get("name"),
                          plugin.get("description"),
                          plugin.get("python_requires") if python_comp else
                              f"[red]{plugin.get('python_requires')}[/red]",
                          plugin.get("sparv_pipeline_requires") if sparv_comp else
                              f"[red]{plugin.get('sparv_pipeline_requires')}[/red]")
        console.print(table)



def plugin_info(plugin_names):
    """Print info about a specific plugin."""
    manifests = load_manifests(paths.plugins_manifest)
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
            table.add_row("source", f"{plugin.get('url')}")
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
                console.print(Padding("[cyan]This plugin requires additional software to be installed.[/cyan]\n",
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
