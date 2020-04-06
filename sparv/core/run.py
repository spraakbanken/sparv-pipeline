"""Used to run Sparv modules from the command line."""

import argparse
import importlib
import inspect
import sys
from typing import Union

from sparv.core import paths, registry
from sparv.util.classes import Annotation, Output, Model, Binary, Config, Document, AllDocuments, ExportAnnotations


def main(argv=None):
    """Parse command line arguments and execute the requested Sparv module."""
    modules_path = ".".join(("sparv", paths.modules_dir))

    if argv is None:
        argv = sys.argv[1:]

    available_modules = sorted(registry.find_modules(paths.sparv_path, no_import=True))

    module_parser = argparse.ArgumentParser(prog="sparv run", add_help=False)
    module_parser.add_argument("module", choices=available_modules, help="Module name")

    module_args, rest_args = module_parser.parse_known_args(argv)
    module_name = module_args.module

    # Import module, which will add available functions to annotators registry
    importlib.import_module(".".join((modules_path, module_name)))

    parser = argparse.ArgumentParser(prog="sparv run " + module_name,
        epilog="note: Annotation classes and configuration variables are not available "
                                            "when running annotators independently. Complete names must be used.")
    subparsers = parser.add_subparsers(dest="annotator", help="Annotator function")
    subparsers.required = True

    for f_name in registry.annotators[module_name]:
        f, description, *_ = registry.annotators[module_name][f_name]
        subparser = subparsers.add_parser(f_name)
        subparser.set_defaults(f_=f)
        required_args = subparser.add_argument_group("required named arguments")
        for parameter in inspect.signature(f).parameters.items():
            param_ann = parameter[1].annotation
            if not param_ann == inspect.Parameter.empty:
                arg_type = param_ann if type(param_ann) in (str, int, bool) else None
            else:
                arg_type = None
            required = parameter[1].default == inspect.Parameter.empty
            if not required:
                # Check if the default argument is of a type we can't handle when running a single module alone
                for t in (Annotation, Output, Model, Binary, Config, Document, AllDocuments, ExportAnnotations):
                    if registry.dig(t, parameter[1].default):
                        required = True
                        break

                if required:
                    # If the type hint is Optional, set default to None and make parameter optional
                    # TODO: Replace the below with the following when upgrading to Python 3.8:
                    #  typing.get_origin(param_ann) is typing.Union and \
                    #             type(None) in typing.get_args(param_ann)
                    if (getattr(param_ann, "__origin__", None) is Union and type(None) in getattr(param_ann,
                                                                                                  "__args__",
                                                                                                  ())):
                        subparser.add_argument("--" + parameter[0], type=arg_type, default=None)
                        required = False
                else:
                    subparser.add_argument("--" + parameter[0], type=arg_type)
            if required:
                required_args.add_argument("--" + parameter[0], type=arg_type, required=True)

    args = parser.parse_args(rest_args)

    arguments = {k: v for k, v in vars(args).items() if v is not None and k not in ("f_", "annotator")}
    args.f_(**arguments)


if __name__ == "__main__":
    main()
