"""Main Sparv executable."""

import argparse
import sys
from pathlib import Path

import snakemake
from snakemake.logging import logger

from sparv import __version__
from sparv.core import log_handler, paths, setup
from sparv.core.paths import sparv_path

# Check Python version
if sys.version_info < (3, 6, 1):
    raise Exception("Python 3.6.1 or higher is required.")


class CustomArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with custom help message and better handling of misspelled commands."""

    def __init__(self, *args, **kwargs):
        """Init parser."""
        no_help = kwargs.pop("no_help", False)
        # Don't add default help message
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        # Add our own help message unless the (sub)parser is created with the no_help argument
        if not no_help:
            self.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    def _check_value(self, action, value):
        """Check if command is valid, and if not, try to guess what the user meant."""
        if action.choices is not None and value not in action.choices:
            # Check for possible misspelling
            import difflib
            close_matches = difflib.get_close_matches(value, action.choices, n=1)
            if close_matches:
                message = f"unknown command: '{value}' - maybe you meant '{close_matches[0]}'"
            else:
                choices = ", ".join(map(repr, action.choices))
                message = f"unknown command: '{value}' (choose from {choices})"
            raise argparse.ArgumentError(action, message)


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter for argparse, silencing subparser lists."""

    def _format_action(self, action):
        result = super()._format_action(action)
        if isinstance(action, argparse._SubParsersAction):
            return ""
        return result


def main():
    """Run Sparv pipeline (main entry point for Sparv)."""

    # Set up command line arguments
    parser = CustomArgumentParser(prog="sparv",
                                  description="Sparv Pipeline",
                                  allow_abbrev=False,
                                  formatter_class=CustomHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"Sparv Pipeline v{__version__}",
                        help="Show Sparv's version number and exit")
    parser.add_argument("-d", "--dir", help="Specify corpus directory")
    description = [
        "",
        "Annotating a corpus:",
        "   run              Annotate a corpus and generate export files",
        "   install          Install a corpus",
        "   clean            Remove output directories",
        "",
        "Inspecting corpus details:",
        "   config           Display the corpus config",
        "   files            List available corpus documents (input for Sparv)",
        "",
        "Show annotation info:",
        "   modules          List available modules and annotations",
        "   presets          List available annotation presets",
        "   classes          List available annotation classes",
        "",
        "Setting up the Sparv pipeline:",
        "   setup            Set up the Sparv data directory",
        "   wizard           Run config wizard to create a corpus config",
        "   build-models     Download and build the Sparv models",
        "",
        "Advanced commands:",
        "   run-rule         Run specified rule(s) for creating annotations",
        "   create-file      Create specified file(s)",
        "   run-module       Run annotator module independently",
        "",
        "See 'sparv <command> -h' for help with a specific command",
        "For full documentation, visit https://spraakbanken.gu.se/sparv/docs/"
    ]
    subparsers = parser.add_subparsers(dest="command", title="commands", metavar="<command>",
                                       description="\n".join(description))
    subparsers.required = True

    # Annotate
    run_parser = subparsers.add_parser("run", description="Annotate a corpus and generate export files.")
    run_parser.add_argument("output", nargs="*", default=[], help="The type of output format to generate")
    run_parser.add_argument("-l", "--list", action="store_true", help="List available output formats")

    install_parser = subparsers.add_parser("install", description="Install a corpus.")
    install_parser.add_argument("type", nargs="*", default=[], help="The type of installation to perform")
    install_parser.add_argument("-l", "--list", action="store_true", help="List installations to be made")

    clean_parser = subparsers.add_parser("clean", description="Remove output directories (by default only the "
                                                              "sparv-workdir directory).")
    clean_parser.add_argument("--export", action="store_true", help="Remove export directory")
    clean_parser.add_argument("--logs", action="store_true", help="Remove logs directory")
    clean_parser.add_argument("--all", action="store_true", help="Remove workdir, export and logs directories")

    # Inspect
    config_parser = subparsers.add_parser("config", description="Display the corpus configuration.")
    config_parser.add_argument("options", nargs="*", default=[], help="Specific options(s) in config to display")
    subparsers.add_parser("files", description="List available corpus documents that can be annotated by Sparv.")

    # Annotation info
    modules_parser = subparsers.add_parser("modules", description="List available modules and annotations.")
    modules_parser.add_argument("--annotators", action="store_true", help="List info for annotators")
    modules_parser.add_argument("--importers", action="store_true", help="List info for importers")
    modules_parser.add_argument("--exporters", action="store_true", help="List info for exporters")
    modules_parser.add_argument("--installers", action="store_true", help="List info for installers")
    modules_parser.add_argument("--all", action="store_true", help="List info for all module types")
    modules_parser.add_argument("names", nargs="*", default=[], help="Specific module(s) to display")

    subparsers.add_parser("presets", description="Display all available annotation presets.")
    subparsers.add_parser("classes", description="Display all available annotation classes.")

    # Setup
    setup_parser = subparsers.add_parser("setup", description="Set up the Sparv data directory. Run without arguments "
                                                              "for interactive setup.")
    setup_parser.add_argument("-d", "--dir", help="Directory to use as Sparv data directory")

    models_parser = subparsers.add_parser("build-models",
                                          description=("Download and build the Sparv models. "
                                                       "If this command is not run before annotating, "
                                                       "the models will be downloaded and built as needed. "
                                                       "This will make things slower when annotating a corpus "
                                                       "for the first time."))
    models_parser.add_argument("model", nargs="*", default=[],
                               help="The model to be built (if omitted all models will be built).")
    models_parser.add_argument("-l", "--list", action="store_true", help="List available models")
    models_parser.add_argument("--language", help="Language (ISO 639-3) if different from current corpus language")
    subparsers.add_parser("wizard", description="Run config wizard to create a corpus config")

    # Advanced commands
    runmodule = subparsers.add_parser("run-module", no_help=True)
    runmodule.add_argument("--log", metavar="LOGLEVEL", help="Set the log level (default: 'info')", default="info",
                           choices=["debug", "info", "warning", "error", "critical"])

    runrule_parser = subparsers.add_parser("run-rule", description="Run specified rule(s) for creating annotations.")
    runrule_parser.add_argument("targets", nargs="*", default=["list"],
                                help="Annotation(s) to create")
    runrule_parser.add_argument("-l", "--list", action="store_true", help="List available rules")
    runrule_parser.add_argument("-w", "--wildcards", nargs="*", metavar="WILDCARD",
                                help="Supply values for wildcards using the format 'name=value'")
    createfile_parser = subparsers.add_parser("create-file", description=("Create specified file(s). "
                                              "The full path must be supplied and wildcards must be replaced."))
    createfile_parser.add_argument("targets", nargs="*", default=["list"], help="File(s) to create")
    createfile_parser.add_argument("-l", "--list", action="store_true", help="List available files that can be created")

    # Add common arguments
    for subparser in [run_parser, install_parser, models_parser, runrule_parser, createfile_parser]:
        subparser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow")
        subparser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel",
                               default=1)
    for subparser in [run_parser, runrule_parser]:
        subparser.add_argument("-d", "--doc", nargs="+", default=[], help="Only annotate specified input document(s)")
    for subparser in [run_parser, runrule_parser, createfile_parser, models_parser, install_parser]:
        subparser.add_argument("--log", metavar="LOGLEVEL", const="info", help="Set the log level (default: 'warning')",
                               nargs="?", choices=["debug", "info", "warning", "error", "critical"])
        subparser.add_argument("--log-to-file", metavar="LOGLEVEL", const="info",
                               help="Set log level for logging to file (default: 'warning')",
                               nargs="?", choices=["debug", "info", "warning", "error", "critical"])
        subparser.add_argument("--debug", action="store_true", help="Show debug messages")

    # Backward compatibility
    if len(sys.argv) > 1 and sys.argv[1] == "make":
        print("No rule to make target")
        sys.exit(1)

    # Parse arguments. We allow unknown arguments for the "run-module" command which is handled separately.
    args, unknown_args = parser.parse_known_args(args=None if sys.argv[1:] else ["--help"])

    # The "run-module" command is handled by a separate script
    if args.command == "run-module":
        from sparv.core import run
        run.main(unknown_args, log_level=args.log)
        sys.exit()
    else:
        args = parser.parse_args()

    if args.command not in ("setup",):
        # Make sure that Sparv data dir is set
        if not paths.get_data_path():
            print(f"The path to Sparv's data directory needs to be configured, either by running 'sparv setup' or by "
                  f"setting the environment variable '{paths.data_dir_env}'.")
            sys.exit(1)

        # Check if Sparv data dir is outdated (or not properly set up yet)
        version_check = setup.check_sparv_version()
        if version_check is None:
            print("The Sparv data directory has been configured but not yet set up completely. Run 'sparv setup' to "
                  "complete the process.")
            sys.exit(1)
        elif not version_check:
            print("Sparv has been updated and Sparv's data directory may need to be upgraded. Please run the "
                  "'sparv setup' command.")
            sys.exit(1)

    if args.command == "setup":
        setup.run(args.dir)
        sys.exit(0)
    elif args.command == "wizard":
        from sparv.core.wizard import Wizard
        wizard = Wizard()
        wizard.run()
        sys.exit(0)

    # Check that a corpus config file is available in the working dir
    if args.command not in ("build-models",):
        if not Path(args.dir or Path.cwd(), paths.config_file).is_file():
            print(f"No config file ({paths.config_file}) found in working directory.")
            sys.exit(1)

    snakemake_args = {"workdir": args.dir}
    config = {"run_by_sparv": True}
    simple_target = False
    log_level = ""
    log_file_level = ""

    if args.command in ("modules", "config", "files", "clean", "presets", "classes"):
        snakemake_args["targets"] = [args.command]
        simple_target = True
        if args.command == "clean":
            config["export"] = args.export
            config["logs"] = args.logs
            config["all"] = args.all
        if args.command == "config" and args.options:
            config["options"] = args.options
        if args.command == "modules":
            config["types"] = []
            if args.names:
                config["names"] = args.names
            for t in ["annotators", "importers", "exporters", "installers", "all"]:
                if getattr(args, t):
                    config["types"].append(t)

    elif args.command in ("run-rule", "create-file", "run", "install", "build-models"):
        snakemake_args.update({
            "dryrun": args.dry_run,
            "cores": args.cores
        })
        # Never show progress bar for list commands
        if args.list:
            simple_target = True

        # Command: run-rule
        if args.command == "run-rule":
            snakemake_args["targets"] = args.targets
            if args.wildcards:
                config["wildcards"] = args.wildcards
            if args.list or snakemake_args["targets"] == ["list"]:
                snakemake_args["targets"] = ["list_targets"]
                simple_target = True
        # Command: create-file
        if args.command == "create-file":
            snakemake_args["targets"] = args.targets
            if args.list or snakemake_args["targets"] == ["list"]:
                snakemake_args["targets"] = ["list_files"]
                simple_target = True
        # Command: run
        elif args.command == "run":
            if args.list:
                snakemake_args["targets"] = ["list_exports"]
            elif args.output:
                snakemake_args["targets"] = args.output
            else:
                snakemake_args["targets"] = ["export_corpus"]
        # Command: install
        elif args.command == "install":
            if args.list:
                snakemake_args["targets"] = ["list_installs"]
            else:
                config["install_types"] = args.type
                snakemake_args["targets"] = ["install_corpus"]
        # Command: build-models
        elif args.command == "build-models":
            config["language"] = args.language
            if args.list:
                snakemake_args["targets"] = ["list_models"]
            elif args.model:
                snakemake_args["targets"] = args.model
            else:
                snakemake_args["targets"] = ["build_models"]

        # Command: run, run-rule, create-file
        if args.command in ("run", "run-rule", "create-file", "build-models", "install"):
            log_level = args.log or "warning"
            log_file_level = args.log_to_file or "warning"
            config.update({"debug": args.debug,
                           "doc": vars(args).get("doc", []),
                           "log_level": log_level,
                           "log_file_level": log_file_level,
                           "targets": snakemake_args["targets"]})

    if simple_target:
        # Force Snakemake to use threads to prevent unnecessary processes for simple targets
        snakemake_args["force_use_threads"] = True

    # Disable Snakemake's default log handler and use our own
    logger.log_handler = []
    progress = log_handler.LogHandler(progressbar=not simple_target, log_level=log_level, log_file_level=log_file_level)
    snakemake_args["log_handler"] = [progress.log_handler]

    config["log_server"] = progress.log_server

    # Run Snakemake
    success = snakemake.snakemake(sparv_path / "core" / "Snakefile", config=config, **snakemake_args)

    progress.stop()
    progress.cleanup()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
