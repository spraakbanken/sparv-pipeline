"""Functions related to Sparv development."""

from pathlib import Path

from rich.pretty import pprint

from sparv.core import config, io, snake_utils
from sparv.core.console import console


def inspect_workdir_file(filename: str, compression: str | None = None) -> bool:
    """Inspect a file in the working directory.

    Args:
        filename: The name of the file to inspect.

    Returns:
        Whether the inspection was successful.
    """
    file_path = Path(filename)
    if not file_path.is_file():
        console.print(f"File '{filename}' does not exist.")
        return False

    def read_and_print() -> None:
        """Read and print the file content."""
        data = next(io.read_annotation_file(file_path, is_data=True))
        if isinstance(data, str):
            console.print(data)
        else:
            pprint(data)

    if compression:
        io.compression = compression

    # First try to read file without loading config
    try:
        read_and_print()
    except Exception:
        if compression:
            # If compression was specified, do not try to read again
            console.print(f"Failed to read file using compression setting {compression!r}.")
            return False

        # Try to load config and get compression setting
        config_missing = snake_utils.load_config({})
        compression = config.get("sparv.compression")

        if config_missing or not compression:
            console.print("Failed to read file. Try specifying compression type using the --compression option.")
            return False

        io.compression = compression

        try:
            read_and_print()
        except Exception:
            console.print(f"Failed to read file using compression setting {compression!r} from config.")
            return False

    return True
