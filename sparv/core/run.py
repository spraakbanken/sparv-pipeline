"""Used to run Sparv modules from the command line."""

import argparse
import importlib
import inspect
import logging
import sys

from sparv.core import log_handler, paths, registry
from sparv.util.classes import Annotation, AnnotationData, Config, Document, Output, OutputData


def main(argv=None, log_level: str = "info"):
    """Parse command line arguments and execute the requested Sparv module."""

    # Set up logging
    logging.basicConfig(format=log_handler.LOG_FORMAT, datefmt=log_handler.DATE_FORMAT, level=log_level.upper(),
                        stream=sys.stdout)

    modules_path = ".".join(("sparv", paths.modules_dir))

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
    importlib.import_module(".".join((modules_path, module_name)))

    parser = argparse.ArgumentParser(prog="sparv run-module " + module_name,
                                     epilog="note: Annotation classes and configuration variables are not available "
                                            "when running annotators independently. Complete names must be used.")
    subparsers = parser.add_subparsers(dest="_annotator", help="Annotator function")
    subparsers.required = True

    needs_doc_types = (Annotation, AnnotationData, Output, OutputData)  # Types that need a doc value

    for f_name in registry.modules[module_name].functions:
        annotator = registry.modules[module_name].functions[f_name]
        f = annotator["function"]
        subparser = subparsers.add_parser(f_name, formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                          help=annotator["description"])
        subparser.set_defaults(f_=f)
        required_args = subparser.add_argument_group("required named arguments")
        needs_doc = False
        has_doc = False
        for parameter in inspect.signature(f).parameters.items():
            param_ann = parameter[1].annotation
            param_default = parameter[1].default
            is_optional = False
            if not param_ann == inspect.Parameter.empty:
                arg_type, _is_list, is_optional = registry.get_type_hint_type(param_ann)
                # arg_type = arg_type if arg_type in (str, int, bool) else None
            else:
                arg_type = None
            if arg_type in needs_doc_types:
                needs_doc = True
            if arg_type == Document:
                has_doc = True
            required = param_default == inspect.Parameter.empty
            f_args = {"type": arg_type}
            if not required:
                # Check if the default value is of a type we can handle when running a single module alone
                if (arg_type in (str, int, bool) and not isinstance(param_default, Config)) or param_default is None:
                    # We can handle this
                    f_args["default"] = param_default
                    if arg_type == bool and param_default is False:
                        f_args["action"] = "store_true"
                        del f_args["type"]
                else:
                    # We can't handle this type of default value
                    # If the type hint is Optional, set default to None, otherwise make required
                    if is_optional:
                        f_args["default"] = None
                    else:
                        required = True
            if required:
                required_args.add_argument("--" + parameter[0], required=True, **f_args)
            else:
                subparser.add_argument("--" + parameter[0], help=" ", **f_args)

        subparser.set_defaults(has_doc_=has_doc)
        if not has_doc and needs_doc:
            required_args.add_argument("--doc", required=True, type=str)

    args = parser.parse_args(rest_args)

    arguments = {}
    doc = args.doc if "doc" in args else None
    has_doc = args.has_doc_ if "has_doc_" in args else False
    for k, v in vars(args).items():
        if k in ("f_", "_annotator", "has_doc_"):
            continue
        if not has_doc and k in "doc":
            continue
        # Add doc value if the type requires it
        if type(v) in needs_doc_types:
            v.doc = doc
        arguments[k] = v

    args.f_(**arguments)


if __name__ == "__main__":
    main()
