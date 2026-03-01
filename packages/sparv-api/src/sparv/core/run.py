"""Used to run Sparv modules from the command line.

This is currently not maintained and is partially hidden from the user.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import logging
import sys

from sparv.api.classes import Annotation, AnnotationData, Config, Output, OutputData, SourceFilename
from sparv.core import io, log_handler, registry
from sparv.core.paths import paths


def main(argv: list[str] | None = None, log_level: str = "info") -> None:
    """Parse command line arguments and execute the requested Sparv module.

    Args:
        argv: List of command-line arguments.
        log_level: Log level.
    """
    # Set up logging
    logging.basicConfig(
        format=log_handler.LOG_FORMAT, datefmt=log_handler.DATE_FORMAT, level=log_level.upper(), stream=sys.stdout
    )

    modules_path = f"sparv.{paths.modules_dir}"

    if argv is None:
        argv = sys.argv[1:]

    available_modules = sorted(registry.find_modules(no_import=True, find_custom=True))

    module_parser = argparse.ArgumentParser(prog="sparv run-module")
    subparsers = module_parser.add_subparsers(dest="module")
    subparsers.required = True

    for module in available_modules:
        subparsers.add_parser(module, add_help=False)

    module_args, rest_args = module_parser.parse_known_args(argv)
    module_name = module_args.module

    # Import module, which will add available functions to annotators registry
    importlib.import_module(f"{modules_path}.{module_name}")
    registry.add_module_to_registry(module, module_name, skip_language_check=True)

    parser = argparse.ArgumentParser(
        prog=f"sparv run-module {module_name}",
        epilog="note: Annotation classes and configuration variables are not available "
        "when running annotators independently. Complete names must be used.",
    )
    subparsers = parser.add_subparsers(dest="_annotator", help="Annotator function")
    subparsers.required = True

    needs_source_types = (Annotation, AnnotationData, Output, OutputData)  # Types that need a source file value

    for f_name in registry.modules[module_name].functions:
        annotator = registry.modules[module_name].functions[f_name]
        f = annotator["function"]
        subparser = subparsers.add_parser(
            f_name, formatter_class=argparse.ArgumentDefaultsHelpFormatter, help=annotator["description"]
        )
        subparser.set_defaults(f_=f)
        required_args = subparser.add_argument_group("required named arguments")
        needs_source = False
        has_source = False
        for parameter in inspect.signature(f).parameters.items():
            param_ann = parameter[1].annotation
            param_default = parameter[1].default
            is_optional = False
            if param_ann != inspect.Parameter.empty:
                arg_type, _is_list, is_optional = registry.get_type_hint_type(param_ann)
                # arg_type = arg_type if arg_type in (str, int, bool) else None
            else:
                arg_type = None
            if arg_type in needs_source_types:
                needs_source = True
            if arg_type == SourceFilename:
                has_source = True
            required = param_default == inspect.Parameter.empty
            f_args = {"type": arg_type}
            if not required:
                # Check if the default value is of a type we can handle when running a single module alone
                if (arg_type in {str, int, bool} and not isinstance(param_default, Config)) or param_default is None:
                    # We can handle this
                    f_args["default"] = param_default
                    if arg_type is bool and param_default is False:
                        f_args["action"] = "store_true"
                        del f_args["type"]
                else:  # noqa: PLR5501
                    # We can't handle this type of default value
                    # If the type hint is Optional, set default to None, otherwise make required
                    if is_optional:
                        f_args["default"] = None
                    else:
                        required = True
            if required:
                required_args.add_argument(f"--{parameter[0]}", required=True, **f_args)
            else:
                subparser.add_argument(f"--{parameter[0]}", help=" ", **f_args)

        subparser.set_defaults(has_source_=has_source)
        if not has_source and needs_source:
            required_args.add_argument("--source-file", required=True, type=str)

        subparser.add_argument(
            "--sparv-compression",
            type=str,
            help="Compression to use for sparv-workdir files",
            nargs="?",
            default=io.compression,
        )

    args = parser.parse_args(rest_args)

    if "sparv_compression" in args:
        io.compression = args.sparv_compression

    arguments = {}
    source_file = args.source_file if "source_file" in args else None
    has_source = args.has_source_ if "has_source_" in args else False
    for k, v in vars(args).items():
        if k in {"f_", "_annotator", "has_source_", "sparv_compression"}:
            continue
        if not has_source and k == "source_file":
            continue
        # Add source value if the type requires it
        if type(v) in needs_source_types:
            v.source_file = source_file
        arguments[k] = v

    args.f_(**arguments)


if __name__ == "__main__":
    main()
