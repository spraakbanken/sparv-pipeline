"""Plain text export."""

from sparv.api import Config

from . import text_export

__config__ = [
    Config(
        "text_export.filename",
        default="{file}_export.txt",
        description="Filename pattern for resulting plain text files, with '{file}' representing the source name.",
        datatype=str,
        pattern=r".*\{file\}.*",
    )
]
