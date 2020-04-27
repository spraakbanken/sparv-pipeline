"""Main Sparv executable."""

import argparse
import os
import sys

import snakemake
from snakemake.logging import logger

from sparv import __version__
from sparv.core import progressbar
from sparv.core.paths import sparv_path

# Check Python version
if sys.version_info < (3, 6):
    raise Exception("Python 3.6+ is required.")


def main():
    """Run Sparv pipeline.

    Main entry point for Sparv pipeline.
    """
    # Set up command line arguments
    parser = argparse.ArgumentParser(prog="sparv",
                                     description="Sparv Pipeline",
                                     allow_abbrev=False)

    parser.add_argument("--version", action="version", version=f"Sparv Pipeline v{__version__}")
    parser.add_argument("-d", "--dir", help="Specify corpus directory.")

    subparsers = parser.add_subparsers(dest="command", title="commands")
    subparsers.required = True

    target_parser = subparsers.add_parser("target", help="Create specified annotation(s) or annotation file(s).")
    target_parser.add_argument("targets", nargs="*", help="Annotation(s) or annotation file(s) to create.")
    target_parser.add_argument("-f", "--file", nargs="+", default=[],
                               help="When target is an annotation, only annotate specified input file(s).")
    target_parser.add_argument("-j", "--cores", type=int, metavar="N", help="Use at most N cores in parallel.",
                               default=1)
    target_parser.add_argument("-l", "--log", action="store_true", help="Show log instead of progress bar.")
    target_parser.add_argument("-n", "--dry-run", action="store_true", help="Only dry-run the workflow.")
    target_parser.add_argument("--list-targets", action="store_true", help="List available targets.")
    target_parser.add_argument("--debug", action="store_true", help="Show debug messages.")

    clean_parser = subparsers.add_parser("clean",
                                         help="Remove output directories (by default only the annotations directory).")
    clean_parser.add_argument("--export", action="store_true", help="Remove export directory.")

    subparsers.add_parser("files", help="List available input files.")
    subparsers.add_parser("annotations", help="List available modules and annotations.")
    subparsers.add_parser("config", help="Display corpus config.")
    subparsers.add_parser("run", help="Run annotator module independently.", add_help=False)

    # Parse arguments. We allow unknown arguments for the 'run' command which is handled separately.
    args, unknown_args = parser.parse_known_args(args=None if sys.argv[1:] else ["--help"])

    # The 'run' command in handled by a separate script
    if args.command == "run":
        from sparv.core import run
        run.main(unknown_args)
        sys.exit()
    else:
        args = parser.parse_args()

    snakemake_args = {"workdir": args.dir}
    config = {"run_by_sparv": True}
    use_progressbar = True
    simple_target = False

    if args.command in ("annotations", "config", "files", "clean"):
        snakemake_args["targets"] = [args.command]
        simple_target = True
        if args.command == "clean":
            config["export"] = args.export
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
