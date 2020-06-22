"""Main Sparv executable."""

import argparse
import sys
from pathlib import Path

import snakemake
from snakemake.logging import logger

from sparv import __version__, util
from sparv.core import log_handler, paths
from sparv.core.paths import sparv_path

# Check Python version
if sys.version_info < (3, 6):
    raise Exception("Python 3.6+ is required.")


class CustomArgumentParser(argparse.ArgumentParser):
    """ArgumentParser with custom help message."""

    def __init__(self, *args, **kwargs):
        no_help = kwargs.pop("no_help", False)
        # Don't add default help message
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        # Add our own help message unless the (sub)parser is created with the no_help argument
        if not no_help:
            self.add_argument("-h", "--help", action="help", help="Show this help message and exit")


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
        "   install          Annotate and install corpus on remote server",
        "   clean            Remove output directories",
        "",
        "Inspecting corpus details:",
        "   config           Display the corpus config",
        "   files            List available input files",
        "",
        "Setting up the Sparv pipeline:",
        # "   create-config    Run config wizard to create a corpus config",
        "   build-models     Download and build the Sparv models",
        # "   install-plugin   (?)",
        "",
        "Advanced commands:",
        "   run-rule         Create specified annotation(s)",
        "   create-file      Create specified file(s)",
        "   run-module       Run annotator module independently",
        "   annotations      (?) List available modules and annotations",
        "   presets          List available annotation presets",
        "",
        "See 'sparv <command> -h' for help with a specific command"
    ]
    subparsers = parser.add_subparsers(dest="command", title="commands", metavar="<command>",
                                       description="\n".join(description))
    subparsers.required = True

    # Annotate
    run_parser = subparsers.add_parser("run", description="Annotate a corpus and generate export files.")
    run_parser.add_argument("-o", "--output", nargs="*", default=["xml_export:pretty"], metavar="<output>",
                            help="The type of output format to generate")
    run_parser.add_argument("-l", "--list", action="store_true", help="List available output formats")

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("-l", "--list", action="store_true", help="List installations to be made")

    clean_parser = subparsers.add_parser("clean", description="Remove output directories (by default only the "
                                                              "annotations directory).")
    clean_parser.add_argument("--export", action="store_true", help="Remove export directory")
    clean_parser.add_argument("--all", action="store_true", help="Remove both annotations and export directories")

    # Inspect
    conifg_parser = subparsers.add_parser("config", description="Display the corpus configuration.")
    conifg_parser.add_argument("options", nargs="*", default=[], help="Specific options(s) in config to display.")
    subparsers.add_parser("files", description="List available input files that can be annotated by Sparv.")

    # Setup
    models_parser = subparsers.add_parser("build-models",
                                          description=("Download and build the Sparv models. "
                                                       "If this command is not run before annotating, "
                                                       "the models will be downloaded and built as needed. "
                                                       "This will make things slower when annotating a corpus "
                                                       "for the first time."))
    models_parser.add_argument("-l", "--list", action="store_true", help="List available models")
    models_parser.add_argument("--language", help="Language (ISO 639-3) if different from current corpus language")

    # Advanced commands
    subparsers.add_parser("run-module", no_help=True)

    runrule_parser = subparsers.add_parser("run-rule", description="Create specified annotation(s).")
    runrule_parser.add_argument("targets", nargs="*", default=["list"],
                                help="Annotation(s) to create")
    runrule_parser.add_argument("-l", "--list", action="store_true", help="List available targets")
    runrule_parser.add_argument("-w", "--wildcards", nargs="*", metavar="WILDCARD",
                                help="Supply values for wildcards using the format 'name=value'")
    createfile_parser = subparsers.add_parser("create-file", description=("Create specified file(s). "
                                              "The full path must be supplied and wildcards must be replaced."))
    createfile_parser.add_argument("targets", nargs="*", default=["list"], help="File(s) to create")
    createfile_parser.add_argument("-l", "--list", action="store_true", help="List available files that can be created")
    subparsers.add_parser("annotations", description="List available annotations and classes.")
    subparsers.add_parser("presets", description="Display all available annotation presets.")

    # Add common arguments
    for subparser in [run_parser, install_parser, models_parser, runrule_parser, createfile_parser]:
        subparser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow")
        subparser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel",
                               default=1)
    for subparser in [run_parser, runrule_parser]:
        subparser.add_argument("-d", "--doc", nargs="+", default=[], help="Only annotate specified input document(s)")
    for subparser in [run_parser, runrule_parser, createfile_parser]:
        subparser.add_argument("--log", action="store_true", help="Show log instead of progress bar")
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
        run.main(unknown_args)
        sys.exit()
    else:
        args = parser.parse_args()

    # Check that a corpus config file is available in the working dir
    if args.command not in ("create-config", "build-models"):
        if not Path(args.dir or Path.cwd(), paths.config_file).is_file():
            print(f"No config file ({paths.config_file}) found in working directory.")
            sys.exit(1)

    snakemake_args = {"workdir": args.dir}
    config = {"run_by_sparv": True}
    use_progressbar = True
    simple_target = False

    if args.command in ("annotations", "config", "files", "clean", "presets"):
        snakemake_args["targets"] = [args.command]
        simple_target = True
        if args.command == "clean":
            config["export"] = args.export
            config["all"] = args.all
        if args.command == "config" and args.options:
            config["options"] = args.options

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
            else:
                print(f"{util.Color.GREEN}Exporting corpus to {', '.join(args.output)}{util.Color.RESET}")
                snakemake_args["targets"] = args.output
        # Command: install
        elif args.command == "install":
            if args.list:
                snakemake_args["targets"] = ["list_installs"]
            else:
                snakemake_args["targets"] = ["install_annotated_corpus"]
        # Command: build-models
        elif args.command == "build-models":
            config["language"] = args.language
            if args.list:
                snakemake_args["targets"] = ["list_models"]
            else:
                snakemake_args["targets"] = ["build_models"]

        # Command: run, run-rule, create-file
        if args.command in ("run", "run-rule", "create-file"):
            config.update({"debug": args.debug, "doc": vars(args).get("doc", []), "log": args.log,
                           "targets": snakemake_args["targets"]})
            if args.log:
                use_progressbar = False

    if simple_target:
        # Disable progressbar for simple targets, and force Snakemake to use threads to prevent unnecessary processes
        use_progressbar = False
        snakemake_args["force_use_threads"] = True

    # Disable Snakemake's default log handler
    logger.log_handler = []

    if use_progressbar:
        # Use progress bar log handler
        progress = log_handler.LogHandler(progressbar=True)
        snakemake_args["log_handler"] = [progress.log_handler]
    else:
        # Use minimal log handler
        progress = log_handler.LogHandler(summary=not simple_target)
        snakemake_args["log_handler"] = [progress.log_handler]

    # Run Snakemake
    success = snakemake.snakemake(sparv_path / "core" / "Snakefile", config=config, **snakemake_args)

    progress.stop()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
