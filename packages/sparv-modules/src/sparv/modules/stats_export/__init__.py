"""Word frequency list generation."""

from sparv.api import Config

from . import sbx_stats, stats_export

__config__ = [
    Config("stats_export.annotations", description="Sparv annotations to include.", datatype=list[str]),
    Config(
        "stats_export.source_annotations",
        description="List of annotations and attributes from the source data to include. None will be included by "
        "default.",
        datatype=list[str],
    ),
    Config("stats_export.delimiter", default="\t", description="Delimiter separating columns", datatype=str),
    Config(
        "stats_export.cutoff",
        default=1,
        description="The minimum frequency a word must have in order to be included in the result",
        datatype=int,
    ),
    Config(
        "stats_export.remote_host",
        description="Remote host or SVN repository (prefixed with 'svn+') to install to",
        datatype=str,
    ),
    Config("stats_export.remote_dir", description="Path on remote host to install to", datatype=str),
    Config(
        "stats_export.compression",
        default="zip",
        description="Compression method to use",
        datatype=str,
        choices=["zip", "bz2"],
    ),
]
