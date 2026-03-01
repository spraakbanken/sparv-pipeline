"""Settings related to core Sparv functionality."""

from sparv.api import Config
from sparv.core.io import compression

__config__ = [
    Config(
        "sparv.compression",
        default=compression,
        description="Compression to use for files in work-dir ('none', 'gzip', 'bzip2' or 'lzma'. Default: 'gzip')",
        datatype=str,
        choices=("none", "gzip", "bzip2", "lzma"),
    )
]
