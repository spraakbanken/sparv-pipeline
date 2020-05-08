"""Main Sparv executable."""

import argparse
import os
import sys

import snakemake
from snakemake.logging import logger

from sparv import __version__
from sparv.core import progressbar, paths
from sparv.core.paths import sparv_path

# Check Python version
if sys.version_info < (3, 6):
    raise Exception("Python 3.6+ is required.")


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
    parser = argparse.ArgumentParser(prog="sparv",
                                     description="Sparv Pipeline",
                                     allow_abbrev=False,
                                     formatter_class=CustomHelpFormatter)

    parser.add_argument("-v", "--version", action="version", version=f"Sparv Pipeline v{__version__}")
    parser.add_argument("-d", "--dir", help="Specify corpus directory")
    description = [
        "",
        "Annotating a corpus:",
        "   run              Annotate a corpus and generate export files",
        "   install          Annotate and install corpus on remote server",
        "   clean            Remove output directories",
        "                    (by default only the annotations directory)",
        "",
        "Inspecting corpus details:",
        "   config           Display the corpus config",
        "   files            List available input files",
        "",
        "Setting up the Sparv pipeline:",
        # "   create-config    Run config wizard to create a corpus config",
        "   build-models     Download and build all Sparv models",
        # "   install-plugin   (?)",
        "",
        "Advanced commands:",
        "   run-rule         Create specified annotation(s)",
        "   create-file      Create specified annotation file(s)",
        "   run-module       Run annotator module independently",
        "   annotations      (?) List available modules and annotations",
        "",
        "See 'sparv <command> -h' for help with a specific command"
    ]
    subparsers = parser.add_subparsers(dest="command", title="commands", metavar="<command>", description="\n".join(description))
    subparsers.required = True

    # Annotate
    # TODO: Make it impossible to run anything else than exports?
    run_parser = subparsers.add_parser("run", description="Annotate a corpus and generate export files")
    run_parser.add_argument("-e", "--export", nargs="*", default=["xml_export:pretty"], metavar="<export>",
                            help="The type of export format to generate")
    run_parser.add_argument("--list-exports", action="store_true", help="List available export formats")

    install_parser = subparsers.add_parser("install")

    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("--export", action="store_true", help="Remove export directory")
    clean_parser.add_argument("--all", action="store_true", help="Remove both annotations and export directories")

    # Inspect
    subparsers.add_parser("config")
    subparsers.add_parser("files")

    # Setup
    models_parser = subparsers.add_parser("build-models")

    # Advanced commands
    subparsers.add_parser("run-module", add_help=False)

    runrule_parser = subparsers.add_parser("run-rule")
    runrule_parser.add_argument("targets", nargs="*", default=["list_targets"], help="Annotation(s) or annotation file(s) to create")
    runrule_parser.add_argument("--list-targets", action="store_true", help="List available targets")
    # TODO: subparsers.add_parser("create-file")
    subparsers.add_parser("annotations", help="List available annotations and classes")

    # Add common arguments
    for subparser in [run_parser, install_parser, models_parser, runrule_parser]:
        subparser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow")
        subparser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel",
                               default=1)
    for subparser in [run_parser, runrule_parser]:
        subparser.add_argument("-d", "--doc", nargs="+", default=[],
                               help="When target is an annotation, only annotate specified input document(s)")
        subparser.add_argument("-l", "--log", action="store_true", help="Show log instead of progress bar")
        subparser.add_argument("--debug", action="store_true", help="Show debug messages")

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
    # TODO: Allow some commands to be run without config file. Needs changes in Snakefile.
    # if args.command not in ("create-config", "build-models"):
    if not os.path.isfile(os.path.join(args.dir or os.getcwd(), paths.config_file)):
        print(f"No config file ({paths.config_file}) found in working directory.")
        sys.exit(1)

    snakemake_args = {"workdir": args.dir}
    config = {"run_by_sparv": True}
    use_progressbar = True
    simple_target = False

    if args.command in ("annotations", "config", "files", "clean"):
        snakemake_args["targets"] = [args.command]
        simple_target = True
        if args.command == "clean":
            config["export"] = args.export
            config["all"] = args.all

    elif args.command in ("run-rule", "run", "install", "build-models"):
        snakemake_args.update({
            "dryrun": args.dry_run,
            "cores": args.cores
        })

        # Command: run-rule
        if args.command == "run-rule":
            snakemake_args.update({"targets": args.targets})
            if args.list_targets or snakemake_args["targets"] == ["list_targets"]:
                snakemake_args["targets"] = ["list_targets"]
                simple_target = True
        # Command: run
        elif args.command == "run":
            if args.list_exports:
                snakemake_args["targets"] = ["list_exports"]
                simple_target = True
            else:
                print("Exporting corpus to: %s" % ", ".join(args.export))
                snakemake_args.update({"targets": args.export})
        # Command: install
        elif args.command == "install":
            snakemake_args.update({"targets": ["install_annotated_corpus"]})
        # Command: build-models
        elif args.command == "build-models":
            snakemake_args.update({"targets": ["build_models"]})

        # Command: run, run-rule
        if args.command in ("run", "run-rule"):
            config.update({"debug": args.debug, "doc": args.doc, "log": args.log})
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
        progress = progressbar.ProgressLogger()
        snakemake_args["log_handler"] = [progress.log_handler]
    else:
        # Use minimal log handler
        snakemake_args["log_handler"] = [progressbar.minimal_log_handler]

    # Run Snakemake
    snakemake.snakemake(os.path.join(sparv_path, "core", "Snakefile"), config=config, **snakemake_args)

    if use_progressbar:
        progress.stop()


if __name__ == "__main__":
    main()
