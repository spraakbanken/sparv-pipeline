"""Main Sparv executable."""
import argparse
import os
import sys

import snakemake
from snakemake.logging import logger

from sparv.core import progressbar
from sparv.core.paths import sparv_path

# Set up command line arguments
parser = argparse.ArgumentParser(prog="sparv",
                                 description="Sparv Pipeline",
                                 allow_abbrev=False)

subparsers = parser.add_subparsers(dest="command", title="commands")
subparsers.required = True

target_parser = subparsers.add_parser("target", help="Create specified annotation(s) or annotation file(s).")
target_parser.add_argument("targets", nargs="*", help="Annotation(s) or annotation file(s) to create.")
target_parser.add_argument("--dir", help="Path to working directory.")
target_parser.add_argument("--file", nargs="+", default=[],
                           help="When target is an annotation, only annotate specified input file(s).")
target_parser.add_argument("--cores", type=int, help="Number of cores to use.", default=1)
target_parser.add_argument("--log", action="store_true", help="Show log instead of progress bar.")
target_parser.add_argument("--dry-run", action="store_true", help="Only dry-run the workflow.")
target_parser.add_argument("--list-targets", action="store_true", help="List available targets.")
target_parser.add_argument("--debug", action="store_true", help="Show debug messages.")

files_parser = subparsers.add_parser("files", help="List available input files.")
annotations_parser = subparsers.add_parser("annotations", help="List available modules and annotations.")
config_parser = subparsers.add_parser("config", help="Display corpus config.")
run_parser = subparsers.add_parser("run", help="Run annotator module independently.", add_help=False)

# Parse arguments. We allow unknown arguments for the 'run' command which is handled separately.
args, unknown_args = parser.parse_known_args(args=None if sys.argv[1:] else ["--help"])

if args.command == "run":
    from sparv.core import run
    run.main(unknown_args)
    sys.exit()
else:
    args = parser.parse_args()

snakemake_args = {}
config = {}
use_progressbar = False

if args.command in ("annotations", "config", "files"):
    snakemake_args["targets"] = [args.command]
    snakemake_args["force_use_threads"] = True
elif args.command == "target":
    use_progressbar = True
    snakemake_args = {
        "workdir": args.dir,
        "dryrun": args.dry_run,
        "cores": args.cores,
        "targets": args.targets
    }
    if args.list_targets:
        snakemake_args["targets"].append("list_targets")
        # Suppress some of the chatty output when only printing targets
        if len(snakemake_args["targets"]) == 1:
            snakemake_args["force_use_threads"] = True
            use_progressbar = False
    config = {"debug": args.debug, "file": args.file, "log": args.log}
    # List available targets if no target was specified
    if not snakemake_args["targets"]:
        use_progressbar = False
        print("\nNo targets provided!\n")
        snakemake_args["targets"].append("list_targets")
        snakemake_args["force_use_threads"] = True
    if args.log:
        use_progressbar = False

snakemake_args["config"] = config

if use_progressbar:
    # Create progress bar log handler
    progress = progressbar.ProgressLogger()

    # Disable Snakemake's default log handler
    logger.log_handler = []

    snakemake_args["log_handler"] = [progress.log_handler]

# Run Snakemake
snakemake.snakemake(os.path.join(sparv_path, "core", "Snakefile"), **snakemake_args)

if use_progressbar:
    progress.stop()
