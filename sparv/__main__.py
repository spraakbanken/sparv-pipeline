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


def main():
    """Run Sparv pipeline (main entry point for Sparv)."""
    # Set up command line arguments
    parser = argparse.ArgumentParser(prog="sparv",
                                     description="Sparv Pipeline",
                                     allow_abbrev=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("-v", "--version", action="version", version=f"Sparv Pipeline v{__version__}")
    parser.add_argument("-d", "--dir", help="Specify corpus directory.")
    description = [
        "",
        "Annotating a corpus:",
        "   run              Generate corpus export",
        "   install          Install annotated corpus on remote server",
        "   clean            Remove output directories",
        "                    (by default only the annotations directory)",
        "",
        "Inspecting a corpus:",
        "   config           Display the corpus config",
        "   files            List available input files",
        "",
        "Setting up the Sparv pipeline:",
        "   create-config    Run config wizard to create a corpus config",
        "   build-models     Download and build all Sparv models",
        # "   install-plugin   (?)",
        "",
        "Advanced commands:",
        "   run-module       Run annotator module independently",
        "   run-rule         Create specified annotation(s)",
        "   create-file      Create specified annotation file(s).",
        "   annotations      (?) List available modules and annotations",
    ]
    subparsers = parser.add_subparsers(dest="command", title="commands", description="\n".join(description))
    subparsers.required = True

    # Annotate
    # TODO: subparsers.add_parser("run")
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel.",
                                default=1)
    install_parser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow.")

    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("--export", action="store_true", help="Remove export directory.")
    clean_parser.add_argument("--all", action="store_true", help="Remove both annotations and export directories.")

    # Inspect
    subparsers.add_parser("config")
    subparsers.add_parser("files")

    # Setup
    models_parser = subparsers.add_parser("build-models")
    models_parser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel.",
                               default=1)
    models_parser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow.")

    # Advanced commands
    subparsers.add_parser("run-module", add_help=False)
    # TODO: subparsers.add_parser("run-rule")
    # TODO: subparsers.add_parser("create-file")
    subparsers.add_parser("annotations")

    # TODO: Divide into "run", "run-rule", "create-file"
    target_parser = subparsers.add_parser("target")
    target_parser.add_argument("targets", nargs="*", help="Annotation(s) or annotation file(s) to create.")
    target_parser.add_argument("-d", "--doc", nargs="+", default=[],
                               help="When target is an annotation, only annotate specified input document(s).")
    target_parser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel.",
                               default=1)
    target_parser.add_argument("-l", "--log", action="store_true", help="Show log instead of progress bar.")
    target_parser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow.")
    target_parser.add_argument("--list-targets", action="store_true", help="List available targets.")
    target_parser.add_argument("--debug", action="store_true", help="Show debug messages.")

    # Parse arguments. We allow unknown arguments for the 'run' command which is handled separately.
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
    elif args.command == "target":
        snakemake_args.update({
            "dryrun": args.dry_run,
            "cores": args.cores,
            "targets": args.targets
        })

        config.update({"debug": args.debug, "file": args.file, "log": args.log})

        if args.list_targets:
            snakemake_args["targets"] = ["list_targets"]
            simple_target = True
        elif not snakemake_args["targets"]:
            # List available targets if no target was specified
            snakemake_args["targets"] = ["list_targets"]
            print("\nNo targets provided!\n")
            simple_target = True

        if args.log:
            use_progressbar = False

    elif args.command == "install":
        snakemake_args.update({
            "dryrun": args.dry_run,
            "cores": args.cores,
            "targets": ["install_annotated_corpus"]
        })

    elif args.command == "build-models":
        snakemake_args.update({
            "dryrun": args.dry_run,
            "cores": args.cores,
            "targets": ["build_models"]
        })

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
