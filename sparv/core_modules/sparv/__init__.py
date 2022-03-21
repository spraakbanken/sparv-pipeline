"""Settings related to core Sparv functionality."""

from sparv.api import Config

__config__ = [
    Config("sparv.compression",
           description="Compression to use for files in work-dir ('none', 'gzip', 'bzip2' or 'lzma'. Default: gzip)")
]
