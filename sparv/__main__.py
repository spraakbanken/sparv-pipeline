"""Main Sparv executable."""
import argparse
import sys
from pathlib import Path

# PYTHON_ARGCOMPLETE_OK
import argcomplete

from sparv import __version__

# Check Python version
if sys.version_info < (3, 9, 0):
    print("Python 3.9 or newer is required.")
    sys.exit(1)


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


class Completer:
    """Reads and returns cached autocompletion data."""

    def __init__(self, completion_type):
        self.type = completion_type

    def __call__(self, parsed_args, **kwargs):
        # Read config file to find corpus language
        config_file = Path(parsed_args.dir or Path.cwd(), "config.yaml")
        cache_data = {}

        if config_file.is_file():
            import appdirs
            import yaml
            try:
                from yaml import CSafeLoader as SafeLoader
            except ImportError:
                from yaml import SafeLoader

            with open(config_file, encoding="utf-8") as f:
                data = yaml.load(f, Loader=SafeLoader)
            language = data.get("metadata", {}).get("language")

            cache_file = Path(appdirs.user_config_dir("sparv"), "autocomplete")

            if cache_file.is_file():
                import pickle
                try:
                    with open(cache_file, "rb") as cache:
                        cache_data = pickle.load(cache)
                        if not language:
                            language = cache_data.get("default_language")
                        cache_data = cache_data.get(language, {})
                except EOFError:  # Cache placeholder created but not yet populated
                    pass

            # run-rule includes everything
            if self.type == "annotate":
                return [v for t in cache_data.values() for v in t]

            return cache_data.get(self.type, [])


class SortedCompletionFinder(argcomplete.CompletionFinder):
    """Custom CompletionFinder that sorts the completions.

    We use this instead of letting bash sort the completions, to sort flags separately.
    """

    def filter_completions(self, completions: list):
        completions = super().filter_completions(completions)
        completions.sort()
        return completions


def main():
    """Run Sparv Pipeline (main entry point for Sparv)."""

    # Set up command line arguments
    parser = CustomArgumentParser(prog="sparv",
                                  description="Sparv Pipeline",
                                  allow_abbrev=False,
                                  formatter_class=CustomHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"Sparv Pipeline v{__version__}",
                        help="Show Sparv's version number and exit")
    parser.add_argument("-d", "--dir", help="Specify corpus directory")

    # Help messages for subparsers
    help = {
        "run": "Annotate a corpus and generate export files",
        "install": "Install a corpus",
        "uninstall": "Uninstall a corpus",
        "clean": {
            "short": "Remove output directories",
            "long": "Remove output directories (by default only the sparv-workdir directory)"
        },
        "config": "Display the corpus configuration",
        "files": "List available corpus source files that can be annotated by Sparv",
        "modules": "List available modules and annotations",
        "presets": "List available annotation presets",
        "classes": "List available annotation classes",
        "languages": "List supported languages",
        "setup": {
            "short": "Set up the Sparv data directory",
            "long": "Set up the Sparv data directory. Run without arguments for interactive setup."
        },
        "wizard": "Run config wizard to create a corpus config",
        "build-models": {
            "short": "Download and build the Sparv models (optional)",
            "long": (
                "Download and build the Sparv models. This is optional, as models will be downloaded and built "
                "automatically the first time they are needed."
            )
        },
        "run-module": "Run annotator module independently",
        "run-rule": "Run specified rule(s) for creating annotations",
        "create-file": {
            "short": "Create specified file(s)",
            "long": "Create specified file(s). The full path must be supplied and wildcards must be replaced."
        },
        "preload": "Preload annotators and models",
        "autocomplete": "Enable tab completion in bash/zsh",
        "schema": "Print a JSON schema for the Sparv config format"
    }

    description = [
        "",
        "Annotating a corpus:",
        f"   run              {help['run']}",
        f"   install          {help['install']}",
        f"   uninstall        {help['uninstall']}",
        f"   clean            {help['clean']['short']}",
        "",
        "Inspecting corpus details:",
        f"   config           {help['config']}",
        f"   files            {help['files']}",
        "",
        "Show annotation info:",
        f"   modules          {help['modules']}",
        f"   presets          {help['presets']}",
        f"   classes          {help['classes']}",
        f"   languages        {help['languages']}",
        "",
        "Setting up the Sparv Pipeline:",
        f"   setup            {help['setup']['short']}",
        f"   wizard           {help['wizard']}",
        f"   build-models     {help['build-models']['short']}",
        "",
        "Advanced commands:",
        f"   run-rule         {help['run-rule']}",
        f"   create-file      {help['create-file']['short']}",
        f"   run-module       {help['run-module']}",
        f"   preload          {help['preload']}",
        f"   autocomplete     {help['autocomplete']}",
        f"   schema           {help['schema']}",
        "",
        "See 'sparv <command> -h' for help with a specific command",
        "For full documentation, visit https://spraakbanken.gu.se/sparv/docs/"
    ]
    subparsers = parser.add_subparsers(dest="command", title="commands", metavar="<command>",
                                       description="\n".join(description))
    subparsers.required = True

    # Annotate
    run_parser = subparsers.add_parser("run", help=help["run"], description=help["run"])
    run_parser.add_argument(
        "output", nargs="*", default=[], help="The type of output format to generate",
    ).completer = Completer("export")
    run_parser.add_argument("-l", "--list", action="store_true", help="List available output formats")

    install_parser = subparsers.add_parser("install", help=help["install"], description=help["install"])
    install_parser.add_argument(
        "type", nargs="*", default=[], help="The type of installation to perform"
    ).completer = Completer("install")
    install_parser.add_argument("-l", "--list", action="store_true", help="List installations to be made")

    uninstall_parser = subparsers.add_parser("uninstall", help=help["uninstall"], description=help["uninstall"])
    uninstall_parser.add_argument(
        "type", nargs="*", default=[], help="The type of uninstallation to perform"
    ).completer = Completer("uninstall")
    uninstall_parser.add_argument("-l", "--list", action="store_true", help="List uninstallations to be made")

    clean_parser = subparsers.add_parser("clean", help=help["clean"]["short"], description=help["clean"]["long"])
    clean_parser.add_argument("-e", "--export", action="store_true", help="Remove export directory")
    clean_parser.add_argument("-l", "--logs", action="store_true", help="Remove logs directory")
    clean_parser.add_argument("-a", "--all", action="store_true", help="Remove workdir, export and logs directories")

    # Inspect
    config_parser = subparsers.add_parser("config", help=help["config"], description=help["config"])
    config_parser.add_argument("options", nargs="*", default=[], help="Specific options(s) in config to display")

    subparsers.add_parser("files", help=help["files"], description=help["files"])

    # Annotation info
    modules_parser = subparsers.add_parser("modules", help=help["modules"], description=help["modules"])
    modules_parser.add_argument("--annotators", action="store_true", help="List info for annotators")
    modules_parser.add_argument("--importers", action="store_true", help="List info for importers")
    modules_parser.add_argument("--exporters", action="store_true", help="List info for exporters")
    modules_parser.add_argument("--installers", action="store_true", help="List info for installers")
    modules_parser.add_argument("--uninstallers", action="store_true", help="List info for uninstallers")
    modules_parser.add_argument("--all", action="store_true", help="List info for all module types")
    modules_parser.add_argument("--json", action="store_true", help="Print output in JSON format")
    modules_parser.add_argument("names", nargs="*", default=[], help="Specific module(s) or annotator(s) to display")

    subparsers.add_parser("presets", help=help["presets"], description=help["presets"])
    subparsers.add_parser("classes", help=help["classes"], description=help["classes"])
    subparsers.add_parser("languages", help=help["languages"], description=help["languages"])

    # Setup
    setup_parser = subparsers.add_parser("setup", help=help["setup"]["short"], description=help["setup"]["long"])
    setup_parser.add_argument("-d", "--dir", help="Directory to use as Sparv data directory")
    setup_parser.add_argument("--reset", action="store_true", help="Reset data directory setting.")

    models_parser = subparsers.add_parser(
        "build-models",
        help=help["build-models"]["short"],
        description=help["build-models"]["long"]
    )
    models_parser.add_argument(
        "model", nargs="*", default=[], help="The model(s) to be built"
    ).completer = Completer("model")
    models_parser.add_argument("-l", "--list", action="store_true", help="List available models")
    models_parser.add_argument("--language", help="Language (ISO 639-3) if different from current corpus language")
    models_parser.add_argument("--all", action="store_true", help="Build all models for the current language")

    subparsers.add_parser("wizard", help=help["wizard"], description=help["wizard"])

    # Advanced commands
    runmodule = subparsers.add_parser(
        "run-module",
        no_help=True,
        help=help["run-module"],
        description=help["run-module"]
    )
    runmodule.add_argument("--log", metavar="LOGLEVEL", help="Set the log level (default: 'info')", default="info",
                           choices=["debug", "info", "warning", "error", "critical"])

    runrule_parser = subparsers.add_parser("run-rule", help=help["run-rule"], description=help["run-rule"])
    runrule_parser.add_argument("targets", nargs="*", default=["list"],
                                help="Annotation(s) to create").completer = Completer("annotate")
    runrule_parser.add_argument("-l", "--list", action="store_true", help="List available rules")
    runrule_parser.add_argument("-w", "--wildcards", nargs="*", metavar="WILDCARD",
                                help="Supply values for wildcards using the format 'name=value'")
    runrule_parser.add_argument("--force", action="store_true", help="Force recreation of target")

    createfile_parser = subparsers.add_parser(
        "create-file",
        help=help["create-file"]["short"],
        description=help["create-file"]["long"]
    )
    createfile_parser.add_argument("targets", nargs="*", default=["list"], help="File(s) to create")
    createfile_parser.add_argument("-l", "--list", action="store_true", help="List available files that can be created")
    createfile_parser.add_argument("--force", action="store_true", help="Force recreation of target")

    preloader_parser = subparsers.add_parser("preload", help=help["preload"], description=help["preload"])
    preloader_parser.add_argument("preload_command", nargs="?", default="start", choices=["start", "stop"])
    preloader_parser.add_argument("--socket", default="sparv.socket", help="Path to socket file")
    preloader_parser.add_argument("-j", "--processes", help="Number of processes to use", default=1, type=int)
    preloader_parser.add_argument("-l", "--list", action="store_true", help="List annotators available for preloading")

    autocomplete_parser = subparsers.add_parser(
        "autocomplete",
        help=help["autocomplete"],
        description=help["autocomplete"]
    )
    autocomplete_parser.add_argument("--enable", action="store_true", help="Output script to be sourced in bash/zsh")
    autocomplete_parser.add_argument("--enable-old", action="store_true",
                                     help="Output script to be sourced in bash, for bash version 4.3 and below")

    schema_parser = subparsers.add_parser("schema", help=help["schema"], description=help["schema"])
    schema_parser.add_argument("--compact", action="store_true", help="Don't indent output")


    # Add common arguments
    for subparser in [run_parser, runrule_parser]:
        subparser.add_argument("-f", "--file", nargs="+", default=[], help="Only annotate specified input file(s)")
    for subparser in [run_parser, runrule_parser, createfile_parser, models_parser, install_parser, uninstall_parser]:
        subparser.add_argument("-n", "--dry-run", action="store_true",
                               help="Print summary of tasks without running them")
        subparser.add_argument("-j", "--cores", type=int, nargs="?", const=0, metavar="N",
                               help="Use at most N cores in parallel; if N is omitted, use all available CPU cores",
                               default=1)
        subparser.add_argument("-k", "--keep-going", action="store_true",
                               help="Keep going with independent tasks if a task fails")
        subparser.add_argument("--log", metavar="LOGLEVEL", const="info",
                               help="Set the log level (default: 'warning' if --log is not specified, "
                                    "'info' if LOGLEVEL is not specified)",
                               nargs="?", choices=["debug", "info", "warning", "error"])
        subparser.add_argument("--log-to-file", metavar="LOGLEVEL", const="info",
                               help="Set log level for logging to file (default: 'warning' if --log-to-file is not "
                                    "specified, 'info' if LOGLEVEL is not specified)",
                               nargs="?", choices=["debug", "info", "warning", "error"])
        subparser.add_argument("--stats", action="store_true", help="Show summary of time spent per annotator")
        subparser.add_argument("--json-log", action="store_true", help="Use JSON format for logging")
        subparser.add_argument("--debug", action="store_true", help="Show debug messages")
        subparser.add_argument("--socket", help="Path to socket file created by the 'preload' command")
        subparser.add_argument("--force-preloader", action="store_true",
                               help="Try to wait for preloader when it's busy")
        subparser.add_argument("--simple", action="store_true", help="Show less details while running")

    # Add extra arguments to 'run' that we want to come last
    run_parser.add_argument("--unlock", action="store_true", help="Unlock the working directory")

    # Backward compatibility
    if len(sys.argv) > 1 and sys.argv[1] == "make":
        print("No rule to make target")
        sys.exit(1)

    # Handle autocompletion
    SortedCompletionFinder()(parser)

    # Parse arguments. We allow unknown arguments for the "run-module" command which is handled separately.
    args, unknown_args = parser.parse_known_args(args=None if sys.argv[1:] else ["--help"])

    # The "run-module" command is handled by a separate script
    if args.command == "run-module":
        from sparv.core import run
        run.main(unknown_args, log_level=args.log)
        sys.exit()
    elif args.command == "autocomplete":
        if args.enable or args.enable_old:
            import appdirs
            try:
                # Create empty autocomplete cache if it doesn't exist
                # The cache contents will only be populated if this file exists
                Path(appdirs.user_config_dir("sparv"), "autocomplete").touch()
            except FileNotFoundError:
                pass
            complete_arguments = ["-o nospace", "-o default", "-o bashdefault"]
            if args.enable:
                complete_arguments.append("-o nosort")
            print(argcomplete.shellcode(["sparv"], complete_arguments=complete_arguments))
        else:
            print(
                "To enable tab autocompletion for Sparv in bash or zsh, source the output of the 'sparv autocomplete "
                "--enable' command in your shell by running the following:\n\n"
                '    eval "$(sparv autocomplete --enable)"\n\n'
                "To enable permanently, add the above line to ~/.bashrc (for bash) or ~/.zshrc (for zsh) by running "
                "one of the following commands in your terminal:\n\n"
                "    echo 'eval \"$(sparv autocomplete --enable)\"' >> ~/.bashrc\n"
                "    echo 'eval \"$(sparv autocomplete --enable)\"' >> ~/.zshrc\n\n"
                "For bash version 4.3 and below, use the flag '--enable-old' instead.\n\n"
                "For zsh, instead of editing ~/.zshrc, you can save the output of the command to a file in "
                "one of the directories in $fpath.\n\n"
                "Note: Autocompletion of some arguments, such as available exporters, will not be available until some "
                "part of the Sparv pipeline (e.g. 'sparv run') has been run at least once since enabling "
                "autocompletion."
            )
        sys.exit(0)
    else:
        import snakemake
        from snakemake.logging import logger
        from snakemake.utils import available_cpu_count

        from sparv.core import log_handler, paths, setup
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
        if args.reset:
            setup.reset()
        else:
            setup.run(args.dir)
        sys.exit(0)
    elif args.command == "wizard":
        from sparv.core.wizard import Wizard
        wizard = Wizard()
        wizard.run()
        sys.exit(0)

    # Check that a corpus config file is available in the working dir
    try:
        config_exists = Path(args.dir or Path.cwd(), paths.config_file).is_file()
    except PermissionError as e:
        print(f"{e.strerror}: {e.filename!r}")
        sys.exit(1)

    if args.command not in {"autocomplete", "build-models", "languages", "schema"}:
        if not config_exists:
            print(f"No config file ({paths.config_file}) found in working directory.")
            sys.exit(1)
    # For the 'build-models' command there needs to be a config file or a language parameter
    elif args.command == "build-models":
        if not config_exists and not args.language:
            print("Models are built for a specific language. Please provide one with the --language param or run this "
                  f"from a directory that has a config file ({paths.config_file}).")
            sys.exit(1)

    snakemake_args = {
        "workdir": args.dir,
        "rerun_triggers": ["mtime", "input"],  # Rerun based on file modification times and changes to the set of input files
        "force_incomplete": True  # Always rerun incomplete files
    }
    config = {"run_by_sparv": True}
    simple_target = False
    log_level = ""
    log_file_level = ""
    json_log = False
    simple_mode = False
    stats = False
    pass_through = False
    dry_run = False
    keep_going = False

    if args.command in {"modules", "config", "files", "clean", "presets", "classes", "languages", "preload", "schema"}:
        snakemake_args["targets"] = [args.command]
        simple_target = True
        if args.command == "clean":
            config["export"] = args.export
            config["logs"] = args.logs
            config["all"] = args.all
        elif args.command == "config" and args.options:
            config["options"] = args.options
        elif args.command == "modules":
            config["types"] = []
            config["json"] = args.json
            if args.names:
                config["names"] = args.names
            for t in ["annotators", "importers", "exporters", "installers", "uninstallers", "all"]:
                if getattr(args, t):
                    config["types"].append(t)
        elif args.command == "preload":
            config["socket"] = str(Path(args.socket).resolve())
            config["preloader"] = True
            config["processes"] = args.processes
            config["preload_command"] = args.preload_command
            config["targets"] = ["preload"]
            if args.list:
                snakemake_args["targets"] = ["preload_list"]
        elif args.command == "schema":
            config["targets"] = ["schema"]
            config["compact"] = args.compact
            # For the schema we include modules from all languages
            config["language"] = "__all__"

    elif args.command in {"run", "run-rule", "create-file", "install", "uninstall", "build-models"}:
        try:
            cores = args.cores or available_cpu_count()
        except NotImplementedError:
            cores = 1
        snakemake_args.update({
            "dryrun": args.dry_run,
            "cores": cores,
            "keepgoing": args.keep_going,
            "resources": {"threads": args.cores}
        })
        # Never show progress bar for list commands or dry run
        if args.list or args.dry_run:
            simple_target = True

        stats = args.stats
        dry_run = args.dry_run
        keep_going = args.keep_going

        # Command: run
        if args.command == "run":
            if args.unlock:
                snakemake_args["unlock"] = args.unlock
                simple_target = True
                pass_through = True
            if args.list:
                snakemake_args["targets"] = ["list_exports"]
            elif args.output:
                snakemake_args["targets"] = args.output
            else:
                snakemake_args["targets"] = ["export_corpus"]
        # Command: run-rule
        elif args.command == "run-rule":
            snakemake_args["targets"] = args.targets
            if args.wildcards:
                config["wildcards"] = args.wildcards
            if args.list or snakemake_args["targets"] == ["list"]:
                snakemake_args["targets"] = ["list_targets"]
                simple_target = True
            elif args.force:
                # Rename all-files-rule to the related regular rule
                snakemake_args["forcerun"] = [t.replace(":", "::") for t in args.targets]
        # Command: create-file
        elif args.command == "create-file":
            snakemake_args["targets"] = args.targets
            if args.list or snakemake_args["targets"] == ["list"]:
                snakemake_args["targets"] = ["list_files"]
                simple_target = True
            elif args.force:
                snakemake_args["forcerun"] = args.targets
        # Command: install
        elif args.command == "install":
            if args.list:
                snakemake_args["targets"] = ["list_installs"]
            else:
                config["install_types"] = args.type
                snakemake_args["targets"] = ["install_corpus"]
        # Command: uninstall
        elif args.command == "uninstall":
            if args.list:
                snakemake_args["targets"] = ["list_uninstalls"]
            else:
                config["uninstall_types"] = args.type
                snakemake_args["targets"] = ["uninstall_corpus"]
        # Command: build-models
        elif args.command == "build-models":
            config["language"] = args.language
            if args.model:
                snakemake_args["targets"] = args.model
            elif args.all:
                snakemake_args["targets"] = ["build_models"]
            else:
                snakemake_args["targets"] = ["list_models"]
                simple_target = True

        log_level = args.log or "warning"
        log_file_level = args.log_to_file or "warning"
        json_log = args.json_log
        simple_mode = args.simple
        socket = args.socket

        if socket:
            # Convert to absolute path, to work together with --dir
            socket_path = Path(socket).resolve()
            if not socket_path.is_socket():
                print(f"Socket file '{socket}' doesn't exist or isn't a socket.")
                sys.exit(1)
            socket = str(socket_path)

        config.update({"debug": args.debug,
                       "file": vars(args).get("file", []),
                       "log_level": log_level,
                       "log_file_level": log_file_level,
                       "socket": socket,
                       "force_preloader": args.force_preloader,
                       "targets": snakemake_args["targets"],
                       "threads": args.cores})

    if simple_target:
        # Force Snakemake to use threads to prevent unnecessary processes for simple targets
        snakemake_args["force_use_threads"] = True

    # Disable Snakemake's default log handler and use our own
    logger.log_handler = []
    progress = log_handler.LogHandler(
        progressbar=not (simple_target or json_log),
        log_level=log_level,
        log_file_level=log_file_level,
        simple=simple_mode,
        stats=stats,
        pass_through=pass_through,
        dry_run=dry_run,
        keep_going=keep_going,
        json=json_log,
    )
    snakemake_args["log_handler"] = [progress.log_handler]

    config["log_server"] = progress.log_server

    # Run Snakemake
    success = snakemake.snakemake(paths.sparv_path / "core" / "Snakefile", config=config, **snakemake_args)

    progress.stop()
    progress.cleanup()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
