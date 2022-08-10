"""Printing functions for Snakefile."""

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
    yaml_str = config.dump_config(in_dict, resolve_alias=True, sort_keys=True)
    # Print syntax highlighted
    console.print(Syntax(yaml_str, "yaml", background_color="default"))


def print_module_summary(snake_storage):
    """Print a summary of all annotation modules."""
    all_module_types = {
        "annotators": snake_storage.all_annotators,
        "importers": snake_storage.all_importers,
        "exporters": snake_storage.all_exporters,
        "installers": snake_storage.all_installers
    }

    print()
    table = Table(title="Available modules", box=box.SIMPLE, show_header=False, title_justify="left")
    table.add_column(no_wrap=True)
    table.add_column()

    for module_type, modules in all_module_types.items():
        table.add_row(f"[b]{module_type.upper()}[/b]")
        for module_name in sorted(modules.keys()):
            description = registry.modules[module_name].description or ""
            if module_name.startswith("custom."):
                description = get_custom_module_description(module_name)
            table.add_row("  " + module_name, description)
        table.add_row()
    console.print(table)
    console.print("For more details about a specific module run [green]'sparv modules \\[module name]'[/green].",
                  highlight=False)
    console.print(
        "For more details about all modules of a specific type run [green]'sparv modules --\\[module type]'[/green].",
        highlight=False)


def print_module_info(module_types, module_names, snake_storage, reverse_config_usage):
    """Wrap module printing functions: print correct info for chosen module_types and module_names."""
    all_module_types = {
        "annotators": snake_storage.all_annotators,
        "importers": snake_storage.all_importers,
        "exporters": snake_storage.all_exporters,
        "installers": snake_storage.all_installers
    }

    if not module_types or "all" in module_types:
        module_types = all_module_types.keys()

    module_names = [n.lower() for n in module_names]

    # Print module info for all chosen module_types
    if not module_names:
        for module_type in module_types:
            modules = all_module_types.get(module_type)
            print_modules(modules, module_type, reverse_config_usage, snake_storage)

    # Print only info for chosen module_names
    else:
        invalid_modules = module_names
        for module_type in module_types:
            modules = all_module_types.get(module_type)
            modules = dict((k, v) for k, v in modules.items() if k in module_names)
            if modules:
                invalid_modules = [m for m in invalid_modules if m not in modules.keys()]
                print_modules(modules, module_type, reverse_config_usage, snake_storage)
        if invalid_modules:
            console.print("[red]Module{} not found: {}[/red]".format("s" if len(invalid_modules) > 1 else "",
                                                                     ", ".join(invalid_modules)))


def print_modules(modules: dict, module_type: str, reverse_config_usage: dict, snake_storage: snake_utils.SnakeStorage,
                  print_params: bool = False):
    """Print module information."""
    custom_annotations = snake_storage.all_custom_annotators

    # Box styles
    left_line = box.Box("    \n┃   \n┃   \n┃   \n┃   \n┃   \n┃   \n    ")
    minimal = box.Box("    \n  │ \n╶─┼╴\n  │ \n╶─┼╴\n╶─┼╴\n  │ \n    \n")
    box_style = minimal

    # Module type header
    print()
    console.print(f"  [b]{module_type.upper()}[/b]", style="reverse", justify="left")  # 'justify' to fill entire width
    print()

    for i, module_name in enumerate(sorted(modules)):
        if i:
            console.print(Rule())

        # Module name header
        console.print(f"\n[bright_black]:[/][dim]:[/]: [b]{module_name.upper()}[/b]\n")

        # Module description
        description = None
        if registry.modules[module_name].description:
            description = registry.modules[module_name].description
        elif module_name.startswith("custom."):
            description = get_custom_module_description(module_name)
        if description:
            console.print(Padding(description, (0, 4, 1, 4)))

        for f_name in sorted(modules[module_name]):
            # Function name and description
            f_desc = modules[module_name][f_name]["description"]
            console.print(Padding(Panel(f"[b]{f_name.upper()}[/b]\n[i]{f_desc}[/i]", box=left_line, padding=(0, 1),
                                        border_style="bright_green"), (0, 2)))

            # Get parameters. Always print these for custom annotations
            params = modules[module_name][f_name].get("params", {})
            custom_params = None
            if custom_annotations.get(module_name, {}).get(f_name):
                custom_params = custom_annotations[module_name][f_name].get("params", {})
                params = custom_params

            # Annotations
            f_anns = modules[module_name][f_name].get("annotations", {})
            if f_anns:
                this_box_style = box_style if any(a[1] for a in f_anns) else box.SIMPLE
                table = Table(title="[b]Annotations[/b]", box=this_box_style, show_header=False,
                              title_justify="left", padding=(0, 2), pad_edge=False, border_style="bright_black")
                table.add_column(no_wrap=True)
                table.add_column()
                for f_ann in sorted(f_anns):
                    table.add_row("• " + f_ann[0].name + (
                        f"\n  [i dim]class:[/] <{f_ann[0].cls}>" if f_ann[0].cls else ""),
                        f_ann[1] or "")
                console.print(Padding(table, (0, 0, 0, 4)))
            elif custom_params:
                # Print info about custom annotators
                this_box_style = box_style if any(a[1] for a in f_anns) else box.SIMPLE
                table = Table(title="[b]Annotations[/b]", box=this_box_style, show_header=False,
                              title_justify="left", padding=(0, 2), pad_edge=False, border_style="bright_black")
                table.add_column()
                table.add_row("In order to use this annotator you first need to declare it in the 'custom_annotations' "
                              "section of your corpus configuration and specify its arguments.")
                console.print(Padding(table, (0, 0, 0, 4)))

            # Config variables
            f_config = reverse_config_usage.get(f"{module_name}:{f_name}")
            if f_config:
                console.print()
                table = Table(title="[b]Configuration variables used[/b]", box=box_style, show_header=False,
                              title_justify="left", padding=(0, 2), pad_edge=False, border_style="bright_black")
                table.add_column(no_wrap=True)
                table.add_column()
                for config_key in sorted(f_config):
                    table.add_row("• " + config_key[0], config_key[1] or "")
                console.print(Padding(table, (0, 0, 0, 4)))

            # Parameters
            if (print_params and params) or custom_params:
                table = Table(title="[b]Parameters[/b]", box=box_style, show_header=False, title_justify="left",
                              padding=(0, 2), pad_edge=False, border_style="bright_black")
                table.add_column(no_wrap=True)
                table.add_column()
                for p, (default, typ, li, optional) in params.items():
                    opt_str = "(optional) " if optional else ""
                    typ_str = "list of " + typ.__name__ if li else typ.__name__
                    def_str = f", default: {repr(default)}" if default is not None else ""
                    table.add_row("• " + p, f"{opt_str}{typ_str}{def_str}")
                console.print(Padding(table, (0, 0, 0, 4)))
            print()


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
