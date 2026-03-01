"""Printing functions for Snakefile."""

import json
import operator
from typing import Any

import typing_inspect
import yaml
from rich import box
from rich.markup import escape
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table

from sparv.api.util.misc import dump_yaml
from sparv.core import config, registry, snake_utils
from sparv.core.console import console


def prettyprint_yaml(in_dict: dict) -> None:
    """Pretty-print YAML.

    Args:
        in_dict: Dictionary to print.
    """
    yaml_str = dump_yaml(in_dict, resolve_alias=True, sort_keys=True)
    # Print syntax highlighted
    console.print(Syntax(yaml_str, "yaml", background_color="default"))


def print_modules_summary(snake_storage: snake_utils.SnakeStorage, json_output: bool = False) -> None:
    """Print a summary of all annotation modules.

    Args:
        snake_storage: SnakeStorage object.
        json_output: Print output as JSON.
    """
    all_module_types = {
        "annotators": snake_storage.all_annotators,
        "importers": snake_storage.all_importers,
        "exporters": snake_storage.all_exporters,
        "installers": snake_storage.all_installers,
        "uninstallers": snake_storage.all_uninstallers,
    }

    modules_data = {k: {} for k in all_module_types}
    for module_type, modules in all_module_types.items():
        for module_name in sorted(modules.keys()):
            if module_name.startswith("custom."):
                description = get_custom_module_description(module_name)
            else:
                description = registry.modules[module_name].description or ""
            modules_data[module_type][module_name] = {"description": description}

    if json_output:
        console.print(json.dumps(modules_data, indent=4, sort_keys=True), soft_wrap=True)
    else:
        console.print()
        table = Table(title="Available modules", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_column(no_wrap=True)
        table.add_column()

        for module_type, module_type_data in modules_data.items():
            table.add_row(f"[b]{module_type.upper()}[/b]")
            for module, module_data in module_type_data.items():
                table.add_row(f"  {module}", module_data["description"].split("\n")[0])
            table.add_row()
        console.print(table)
        console.print(
            "For more details about a specific module run [green]'sparv modules \\[module name]'[/green].",
            highlight=False,
        )
        console.print(
            "For more details about all modules of a specific type run "
            "[green]'sparv modules --\\[module type]'[/green].",
            highlight=False,
        )


def print_modules_info(
    module_types: list[str],
    module_names: list[str],
    snake_storage: snake_utils.SnakeStorage,
    reverse_config_usage: dict,
    json_output: bool = False,
    include_params: bool = False,
) -> None:
    """Print full info for chosen module_types and module_names.

    Args:
        module_types: List of module types to print.
        module_names: List of module names to print.
        snake_storage: SnakeStorage object.
        reverse_config_usage: Dictionary with config usage.
        json_output: Print output as JSON.
        include_params: Include parameters in output.
    """
    all_module_types = {
        "annotators": snake_storage.all_annotators,
        "importers": snake_storage.all_importers,
        "exporters": snake_storage.all_exporters,
        "installers": snake_storage.all_installers,
        "uninstallers": snake_storage.all_uninstallers,
    }

    def quoted_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
        """Surround YAML strings with quotes, and escape them for Rich."""  # noqa: DOC201
        return dumper.represent_scalar("tag:yaml.org,2002:str", escape(data), style="'")

    def tuple_representer(dumper: yaml.Dumper, data: tuple) -> yaml.SequenceNode:
        """Handle tuples when dumping YAML."""  # noqa: DOC201
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data)

    def get_name(obj: Any) -> str:
        """Get the name of a type using __name__, falling back to its string representation.

        Args:
            obj: The object to get the name from.

        Returns:
            The name of the object.
        """
        return getattr(obj, "__name__", str(obj))

    yaml.add_representer(str, quoted_representer)
    yaml.add_representer(tuple, tuple_representer)

    if not module_types or "all" in module_types:
        module_types = all_module_types.keys()

    modules_data = {}
    invalid_modules = set()
    invalid_functions = {}
    selected_modules = {}

    if module_names:
        for m in module_names:
            module, _, function = m.partition(":")
            selected_modules.setdefault(module, set())
            if function:
                selected_modules[module].add(function)
        invalid_modules = set(selected_modules.keys())
        invalid_functions = {k: set(v) for k, v in selected_modules.items()}

    for module_type in module_types:
        modules = all_module_types.get(module_type)

        # Filter modules
        if module_names:
            modules = {k: v for k, v in modules.items() if k in selected_modules}
            invalid_modules -= modules.keys()

        if not modules:
            continue

        module_type_data = {}

        for module_name in sorted(modules):
            module_data = {"functions": {}}

            # Module description
            description = None
            if registry.modules[module_name].description:
                description = registry.modules[module_name].description
            elif module_name.startswith("custom."):
                description = get_custom_module_description(module_name)
            if description:
                module_data["description"] = description

            if module_names and selected_modules[module_name]:
                functions = sorted(f for f in modules[module_name] if f in selected_modules[module_name])
                invalid_functions[module_name] -= set(functions)
            else:
                functions = sorted(modules[module_name])

            for f_name in functions:
                f_data = {"description": modules[module_name][f_name]["description"]}

                # Get parameters
                if snake_storage.all_custom_annotators.get(module_name, {}).get(f_name):
                    f_data["custom_annotator"] = True
                    params = snake_storage.all_custom_annotators[module_name][f_name].get("params", {})
                else:
                    params = modules[module_name][f_name].get("params", {})

                # Annotations
                if f_anns := modules[module_name][f_name].get("annotations", {}):
                    f_data["annotations"] = {}
                    for f_ann in sorted(f_anns):
                        f_data["annotations"][f_ann[0].original_name] = {"description": f_ann[1]}
                        if f_ann[0].cls:
                            f_data["annotations"][f_ann[0].original_name]["class"] = f_ann[0].cls
                        if f_ann[0].name != f_ann[0].original_name:
                            f_data["annotations"][f_ann[0].original_name]["resolved_name"] = f_ann[0].name

                # Config variables
                if f_config := reverse_config_usage.get(f"{module_name}:{f_name}"):
                    f_data["config"] = {}
                    for config_key in sorted(f_config):
                        config_info = {}
                        if config_object := config.get_config_object(config_key):
                            config_info["description"] = config_object.description
                            datatypes = []

                            if config_object.datatype is not None:
                                # Datatype is either a single type or a union of types
                                if typing_inspect.is_union_type(config_object.datatype):
                                    cfg_datatypes = typing_inspect.get_args(config_object.datatype)
                                else:
                                    cfg_datatypes = [config_object.datatype]

                                for cfg_datatype in cfg_datatypes:
                                    if cfg_datatype is str:
                                        datatypes.append(cfg_datatype.__name__)
                                        if config_object.choices:
                                            config_info["choices"] = (
                                                config_object.choices()
                                                if callable(config_object.choices)
                                                else config_object.choices
                                            )
                                        if config_object.pattern:
                                            config_info["pattern"] = config_object.pattern
                                    elif cfg_datatype in {int, float}:
                                        datatypes.append(cfg_datatype.__name__)
                                        if config_object.min_value is not None:
                                            config_info["min_value"] = config_object.min_value
                                        if config_object.max_value is not None:
                                            config_info["max_value"] = config_object.max_value
                                    elif cfg_datatype is list or typing_inspect.get_origin(cfg_datatype) is list:
                                        args = typing_inspect.get_args(cfg_datatype)
                                        if args:
                                            if typing_inspect.is_union_type(args[0]):
                                                args_inner = typing_inspect.get_args(args[0])
                                                datatypes.append(f"list[{' | '.join(get_name(a) for a in args_inner)}]")
                                            else:
                                                datatypes.append(f"list[{get_name(args[0])}]")
                                        else:
                                            datatypes.append("list")
                                    else:
                                        datatypes.append(get_name(cfg_datatype))

                            if config_object.default is not None:
                                config_info["default"] = config_object.default

                            if datatypes:
                                config_info["datatype"] = datatypes

                        f_data["config"][config_key] = config_info

                # Parameters. Always include parameters for custom annotators.
                if (include_params and params) or "custom_annotator" in f_data:
                    f_data["parameters"] = {}
                    for p, (default, typ, li, optional) in params.items():
                        f_data["parameters"][p] = {
                            "optional": optional,
                            "type": f"list[{get_name(typ)}]" if li else (get_name(typ)),
                            "default": default,
                        }
                module_data["functions"][f_name] = f_data

                if module_type == "exporters":
                    f_data["exports"] = modules[module_name][f_name].get("exports", [])

            if module_data["functions"]:
                module_type_data[module_name] = module_data

        if module_type_data:
            modules_data[module_type] = module_type_data

    if module_names:
        invalid_functions = [
            f"{m}:{f}" for m in invalid_functions for f in invalid_functions[m] if m not in invalid_modules
        ]

    if json_output:
        if module_names:
            if invalid_modules:
                modules_data["UNKNOWN_MODULES"] = list(invalid_modules)
            if invalid_functions:
                modules_data["UNKNOWN_FUNCTIONS"] = list(invalid_functions)

        console.print(json.dumps(modules_data, indent=4), soft_wrap=True)
    else:
        _print_modules(modules_data)
        if invalid_modules:
            console.print(
                "[red]unknown module{}: {}[/red]".format(
                    "s" if len(invalid_modules) > 1 else "", ", ".join(invalid_modules)
                )
            )
        if invalid_functions:
            console.print(
                "[red]Unknown function{}: {}[/red]".format(
                    "s" if len(invalid_functions) > 1 else "", ", ".join(invalid_functions)
                )
            )


def _print_modules(modules_data: dict) -> None:
    """Pretty print module information.

    Args:
        modules_data: Dictionary with module information.
    """
    # Box styles
    left_line = box.Box("    \n┃   \n┃   \n┃   \n┃   \n┃   \n┃   \n    ")
    minimal = box.Box("    \n  │ \n╶─┼╴\n  │ \n╶─┼╴\n╶─┼╴\n  │ \n    \n")
    box_style = minimal

    for module_type, modules in modules_data.items():
        # Module type header
        console.print()
        console.print(
            f"  [b]{module_type.upper()}[/b]",
            style="reverse",
            justify="left",  # Fill entire width
        )
        console.print()

        for i, (module_name, module_data) in enumerate(modules.items()):
            if i:
                console.print(Rule())

            # Module name header
            console.print(f"\n[bright_black]:[/][dim]:[/]: [b]{module_name.upper()}[/b]\n")

            # Module description
            if "description" in module_data:
                console.print(Padding(escape(module_data["description"]), (0, 4, 1, 4)))

            for f_name, f_data in module_data["functions"].items():
                # Function name and description
                console.print(
                    Padding(
                        Panel(
                            f"[b]{f_name.upper()}[/b]\n[i]{escape(f_data['description'])}[/i]",
                            box=left_line,
                            padding=(0, 1),
                            border_style="bright_green",
                        ),
                        (0, 2),
                    )
                )

                # Annotations
                if "annotations" in f_data:
                    this_box_style = box_style if any(a[1] for a in f_data["annotations"]) else box.SIMPLE
                    table = Table(
                        title="[b]Annotations[/b]",
                        box=this_box_style,
                        show_header=False,
                        title_justify="left",
                        padding=(0, 2),
                        pad_edge=False,
                        border_style="bright_black",
                    )
                    table.add_column(no_wrap=True)
                    table.add_column()
                    for f_ann, ann_data in f_data["annotations"].items():
                        table.add_row(f"• {escape(f_ann)}", escape(ann_data["description"] or ""))
                        if "resolved_name" in ann_data or "class" in ann_data:
                            inner_table = Table(show_header=False, padding=(0, 1, 0, 0), box=None)
                            inner_table.add_column(justify="left", style="i dim")
                            if "resolved_name" in ann_data:
                                inner_table.add_row("resolved name:", ann_data["resolved_name"])
                            if "class" in ann_data:
                                inner_table.add_row("class:", f"<{ann_data['class']}>")
                            table.add_row("", Padding(inner_table, (0, 0, 0, 2)))
                    console.print(Padding(table, (0, 0, 0, 4)))
                elif "custom_annotator" in f_data:
                    # Print info about custom annotators
                    this_box_style = box_style if any(a[1] for a in f_data["parameters"]) else box.SIMPLE
                    table = Table(
                        title="[b]Annotations[/b]",
                        box=this_box_style,
                        show_header=False,
                        title_justify="left",
                        padding=(0, 2),
                        pad_edge=False,
                        border_style="bright_black",
                    )
                    table.add_column()
                    table.add_row(
                        "In order to use this annotator you first need to declare it in the 'custom_annotations' "
                        "section of your corpus configuration and specify its arguments."
                    )
                    console.print(Padding(table, (0, 0, 0, 4)))

                # Config variables
                if "config" in f_data:
                    console.print()
                    table = Table(
                        title="[b]Configuration variables used[/b]",
                        box=box_style,
                        show_header=False,
                        title_justify="left",
                        padding=(0, 2),
                        pad_edge=False,
                        border_style="bright_black",
                    )
                    table.add_column(no_wrap=True)
                    table.add_column()
                    for config_key, config_info in f_data["config"].items():
                        table.add_row(
                            f"• {escape(config_key)}",
                            escape(config_info.get("description", "[i dim]No description available[/]")),
                        )
                        if "datatype" in config_info:
                            inner_table = Table(show_header=False, padding=(0, 1, 0, 0), box=None)
                            inner_table.add_column(justify="left", style="i dim")
                            inner_table.add_row(
                                f"type{'s' if len(config_info['datatype']) > 1 else ''}:",
                                f"{escape(' | '.join(config_info['datatype']))}",
                            )

                            presentation = {
                                "str": {
                                    "pattern": "regexp",
                                    "min_len": "min length",
                                    "max_len": "max length",
                                },
                                "int": {
                                    "min_value": "min",
                                    "max_value": "max",
                                },
                                "float": {
                                    "min_value": "min",
                                    "max_value": "max",
                                },
                            }

                            for datatype in config_info["datatype"]:
                                if datatype in presentation:
                                    for key in presentation[datatype]:
                                        if key in config_info:
                                            inner_table.add_row(
                                                f"{presentation[datatype][key]}:",
                                                yaml.dump(config_info[key], default_flow_style=True)
                                                .strip()
                                                .removesuffix("\n..."),
                                            )

                            if "choices" in config_info:
                                choices = yaml.dump(config_info["choices"], default_flow_style=True, width=9999)[1:-2]
                                inner_table.add_row("values:", escape(choices))
                            if "default" in config_info:
                                inner_table.add_row(
                                    "default:",
                                    yaml.dump(config_info["default"], default_flow_style=True)
                                    .strip()
                                    .removesuffix("\n..."),
                                )

                            table.add_row("", Padding(inner_table, (0, 0, 0, 2)))
                    console.print(Padding(table, (0, 0, 0, 4)))

                # Parameters
                if "parameters" in f_data:
                    table = Table(
                        title="[b]Parameters[/b]",
                        box=box_style,
                        show_header=False,
                        title_justify="left",
                        padding=(0, 2),
                        pad_edge=False,
                        border_style="bright_black",
                    )
                    table.add_column(no_wrap=True)
                    table.add_column()
                    for p, p_data in f_data["parameters"].items():
                        opt_str = "(optional) " if p_data.get("optional") else ""
                        typ_str = p_data["type"]
                        def_str = f", default: {p_data['default']!r}" if p_data["default"] is not None else ""
                        table.add_row("• " + p, escape(f"{opt_str}{typ_str}{def_str}"))
                    console.print(Padding(table, (0, 0, 0, 4)))
                console.print()


def print_annotation_classes() -> None:
    """Print info about annotation classes."""
    console.print()
    table = Table(box=box.SIMPLE, show_header=False, title_justify="left")
    table.add_column(no_wrap=True)
    table.add_column()

    table.add_row("[b]Available annotation classes[/b]")
    table.add_row("  [i]Class[/i]", "[i]Annotation[/i]")
    for annotation_class, anns in sorted(registry.annotation_classes["module_classes"].items()):
        table.add_row(f"  {annotation_class}", "\n".join(sorted(set(anns), key=anns.index)))

    if registry.annotation_classes["config_classes"]:
        table.add_row()
        table.add_row("[b]Classes set in config[/b]")
        table.add_row("  [i]Class[/i]", "[i]Annotation[/i]")
        for annotation_class, ann in registry.annotation_classes["config_classes"].items():
            table.add_row(f"  {annotation_class}", ann)

    if registry.annotation_classes["implicit_classes"]:
        table.add_row()
        table.add_row("[b]Class values inferred from annotation usage[/b]")
        table.add_row("  [i]Class[/i]", "[i]Annotation[/i]")
        for annotation_class, ann in registry.annotation_classes["implicit_classes"].items():
            table.add_row(f"  {annotation_class}", ann)

    console.print(table)


def print_languages() -> None:
    """Print all supported languages."""
    console.print()
    table = Table(title="Supported languages", box=box.SIMPLE, show_header=False, title_justify="left")
    full_langs = {k: v for k, v in registry.languages.items() if "-" not in k}
    for language, name in sorted(full_langs.items(), key=operator.itemgetter(1)):
        table.add_row(name, language)
    console.print(table)

    if sub_langs := {k: v for k, v in registry.languages.items() if "-" in k}:
        console.print()
        table = Table(title="Supported language varieties", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_row("[b]Name[/b]", "[b]Language[/b]", "[b]Variety[/b]")
        for language, name in sorted(sub_langs.items(), key=operator.itemgetter(1)):
            lang, _, sublang = language.partition("-")
            table.add_row(name, lang, sublang)
        console.print(table)


def get_custom_module_description(name: str) -> str:
    """Return a string with the description for custom modules.

    Args:
        name: Name of the custom module.
    """
    return f"Custom module from the corpus directory ({name.split('.')[1]}.py)."


def print_installers(snake_storage: snake_utils.SnakeStorage, uninstall: bool = False) -> None:
    """Print a list of installers or uninstallers.

    Args:
        snake_storage: SnakeStorage object.
        uninstall: Print uninstallers instead of installers.
    """
    if uninstall:
        targets = snake_storage.uninstall_targets
        prefix = "un"
        config_list = config.get("uninstall")
        if config_list is None:
            config_install = config.get("install", [])
            config_list = [u for t, _, u in snake_storage.install_targets if t in config_install and u]
    else:
        targets = snake_storage.install_targets
        prefix = ""
        config_list = config.get("install", [])

    selected_installations = [(t, d) for t, d, *_ in targets if t in config_list]
    other_installations = [(t, d) for t, d, *_ in targets if t not in config_list]

    if selected_installations:
        console.print()
        table = Table(title=f"Selected {prefix}installations", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_column(no_wrap=True)
        table.add_column()
        for target, desc in sorted(selected_installations):
            table.add_row(target, desc)
        console.print(table)

    if other_installations:
        console.print()
        if selected_installations:
            title = f"Other available {prefix}installations"
        else:
            title = f"Available {prefix}installations"
        table = Table(title=title, box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_column(no_wrap=True)
        table.add_column()
        for target, desc in sorted(other_installations):
            table.add_row(target, desc)
        console.print(table)

    extra = (
        (
            "If the 'uninstall' setting is not set, any uninstallers connected to the installers in the 'install' "
            "section will be used instead."
        )
        if uninstall
        else ""
    )

    console.print(
        f"[i]Note:[/i] Use the '{prefix}install' section in your corpus configuration to select which "
        f"{prefix}installations should be performed when running 'sparv {prefix}install' without arguments. "
        f"{extra}"
    )
