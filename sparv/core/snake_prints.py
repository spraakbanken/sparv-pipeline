"""Printing functions for Snakefile."""
import json
from typing import List

from rich import box
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from sparv.core import config, registry, snake_utils
from sparv.core.console import console


def prettyprint_yaml(in_dict):
    """Pretty-print YAML."""
    from rich.syntax import Syntax
    from sparv.api.util.misc import dump_yaml
    yaml_str = dump_yaml(in_dict, resolve_alias=True, sort_keys=True)
    # Print syntax highlighted
    console.print(Syntax(yaml_str, "yaml", background_color="default"))


def print_modules_summary(snake_storage: snake_utils.SnakeStorage, json_output: bool = False) -> None:
    """Print a summary of all annotation modules."""
    all_module_types = {
        "annotators": snake_storage.all_annotators,
        "importers": snake_storage.all_importers,
        "exporters": snake_storage.all_exporters,
        "installers": snake_storage.all_installers,
        "uninstallers": snake_storage.all_uninstallers
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
        console.print(json.dumps(modules_data, indent=4, sort_keys=True))
    else:
        console.print()
        table = Table(title="Available modules", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_column(no_wrap=True)
        table.add_column()

        for module_type in modules_data:
            table.add_row(f"[b]{module_type.upper()}[/b]")
            for module, module_data in modules_data[module_type].items():
                table.add_row("  " + module, module_data["description"])
            table.add_row()
        console.print(table)
        console.print(
            "For more details about a specific module run [green]'sparv modules \\[module name]'[/green].",
            highlight=False
        )
        console.print(
            "For more details about all modules of a specific type run "
            "[green]'sparv modules --\\[module type]'[/green].",
            highlight=False
        )


def print_modules_info(
    module_types: List[str],
    module_names: List[str],
    snake_storage: snake_utils.SnakeStorage,
    reverse_config_usage: dict,
    json_output: bool = False,
    include_params: bool = False
) -> None:
    """Print full info for chosen module_types and module_names."""
    all_module_types = {
        "annotators": snake_storage.all_annotators,
        "importers": snake_storage.all_importers,
        "exporters": snake_storage.all_exporters,
        "installers": snake_storage.all_installers,
        "uninstallers": snake_storage.all_uninstallers
    }

    if not module_types or "all" in module_types:
        module_types = all_module_types.keys()

    module_names = [n.lower() for n in module_names]
    modules_data = {}
    invalid_modules = set(module_names)

    for module_type in module_types:
        modules = all_module_types.get(module_type)

        # Filter modules
        if module_names:
            modules = {k: v for k, v in modules.items() if k in module_names}
            invalid_modules = invalid_modules - modules.keys()

        if not modules:
            continue

        modules_data[module_type] = {}

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

            for f_name in sorted(modules[module_name]):
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
                        f_data["annotations"][f_ann[0].name] = {"description": f_ann[1]}
                        if f_ann[0].cls:
                            f_data["annotations"][f_ann[0].name]["class"] = f_ann[0].cls

                # Config variables
                if f_config := reverse_config_usage.get(f"{module_name}:{f_name}"):
                    f_data["config"] = {config_key[0]: config_key[1] for config_key in sorted(f_config)}

                # Parameters. Always include parameters for custom annotators.
                if (include_params and params) or "custom_annotator" in f_data:
                    f_data["parameters"] = {}
                    for p, (default, typ, li, optional) in params.items():
                        f_data["parameters"][p] = {
                            "optional": optional,
                            "type": f"list[{typ.__name__}]" if li else typ.__name__,
                            "default": default
                        }
                module_data["functions"][f_name] = f_data

                if module_type == "exporters":
                    f_data["exports"] = modules[module_name][f_name].get("exports", [])

            modules_data[module_type][module_name] = module_data

    if json_output:
        if invalid_modules:
            modules_data["UNKNOWN_MODULES"] = list(invalid_modules)
        console.print(json.dumps(modules_data, indent=4))
    else:
        print_modules(modules_data)
        if invalid_modules:
            console.print(
                "[red]Module{} not found: {}[/red]".format(
                    "s" if len(invalid_modules) > 1 else "", ", ".join(invalid_modules)
                )
            )


def print_modules(modules_data: dict) -> None:
    """Print module information."""
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
            justify="left"  # Fill entire width
        )
        console.print()

        for i, (module_name, module_data) in enumerate(modules.items()):
            if i:
                console.print(Rule())

            # Module name header
            console.print(f"\n[bright_black]:[/][dim]:[/]: [b]{module_name.upper()}[/b]\n")

            # Module description
            if "description" in module_data:
                console.print(Padding(module_data["description"], (0, 4, 1, 4)))

            for f_name, f_data in module_data["functions"].items():
                # Function name and description
                console.print(
                    Padding(
                        Panel(
                            f"[b]{f_name.upper()}[/b]\n[i]{f_data['description']}[/i]",
                            box=left_line,
                            padding=(0, 1),
                            border_style="bright_green"
                        ),
                        (0, 2)
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
                        border_style="bright_black"
                    )
                    table.add_column(no_wrap=True)
                    table.add_column()
                    for f_ann, ann_data in f_data["annotations"].items():
                        table.add_row(
                            f"• {f_ann}"
                            + (f"\n  [i dim]class:[/] <{ann_data['class']}>" if "class" in ann_data else ""),
                            ann_data["description"]
                        )
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
                        border_style="bright_black"
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
                        border_style="bright_black"
                    )
                    table.add_column(no_wrap=True)
                    table.add_column()
                    for config_key, config_desc in f_data["config"].items():
                        table.add_row("• " + config_key, config_desc or "")
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
                        border_style="bright_black"
                    )
                    table.add_column(no_wrap=True)
                    table.add_column()
                    for p, p_data in f_data["parameters"].items():
                        opt_str = "(optional) " if p_data.get("optional") else ""
                        typ_str = p_data["type"]
                        def_str = f", default: {p_data['default']!r}" if p_data["default"] is not None else ""
                        table.add_row("• " + p, f"{opt_str}{typ_str}{def_str}")
                    console.print(Padding(table, (0, 0, 0, 4)))
                console.print()


def print_annotation_classes():
    """Print info about annotation classes."""
    print()
    table = Table(box=box.SIMPLE, show_header=False, title_justify="left")
    table.add_column(no_wrap=True)
    table.add_column()

    table.add_row("[b]Available annotation classes[/b]")
    table.add_row("  [i]Class[/i]", "[i]Annotation[/i]")
    for annotation_class, anns in sorted(registry.annotation_classes["module_classes"].items()):
        table.add_row("  " + annotation_class, "\n".join(sorted(set(anns), key=anns.index)))

    if registry.annotation_classes["config_classes"]:
        table.add_row()
        table.add_row("[b]Classes set in config[/b]")
        table.add_row("  [i]Class[/i]", "[i]Annotation[/i]")
        for annotation_class, ann in registry.annotation_classes["config_classes"].items():
            table.add_row("  " + annotation_class, ann)

    if registry.annotation_classes["implicit_classes"]:
        table.add_row()
        table.add_row("[b]Class values inferred from annotation usage[/b]")
        table.add_row("  [i]Class[/i]", "[i]Annotation[/i]")
        for annotation_class, ann in registry.annotation_classes["implicit_classes"].items():
            table.add_row("  " + annotation_class, ann)

    console.print(table)


def print_languages():
    """Print all supported languages."""
    print()
    table = Table(title="Supported languages", box=box.SIMPLE, show_header=False, title_justify="left")
    full_langs = dict((k, v) for k, v in registry.languages.items() if "-" not in k)
    for language, name in sorted(full_langs.items(), key=lambda x: x[1]):
        table.add_row(name, language)
    console.print(table)

    sub_langs = dict((k, v) for k, v in registry.languages.items() if "-" in k)
    if sub_langs:
        print()
        table = Table(title="Supported language varieties", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_row("[b]Name[/b]", "[b]Language[/b]", "[b]Variety[/b]")
        for language, name in sorted(sub_langs.items(), key=lambda x: x[1]):
            lang, _, sublang = language.partition("-")
            table.add_row(name, lang, sublang)
        console.print(table)


def get_custom_module_description(name):
    """Return string with description for custom modules."""
    return "Custom module from corpus directory ({}.py).".format(name.split(".")[1])


def print_installers(snake_storage, uninstall: bool = False):
    """Print list of installers or uninstallers."""
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
        print()
        table = Table(title=f"Selected {prefix}installations", box=box.SIMPLE, show_header=False, title_justify="left")
        table.add_column(no_wrap=True)
        table.add_column()
        for target, desc in sorted(selected_installations):
            table.add_row(target, desc)
        console.print(table)

    if other_installations:
        print()
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

    extra = "If the 'uninstall' setting is not set, any uninstallers connected to the installers in the 'install' " \
            "section will be used instead." if uninstall else ""

    console.print(f"[i]Note:[/i] Use the '{prefix}install' section in your corpus configuration to select what "
                  f"{prefix}installations should be performed when running 'sparv {prefix}install' without arguments. "
                  f"{extra}")
