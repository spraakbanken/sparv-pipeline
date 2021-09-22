"""Word frequency list generation."""

from sparv.api import Config

from . import stats_export, sbx_stats

__config__ = [
    Config("stats_export.annotations", description="Sparv annotations to include."),
    Config("stats_export.source_annotations",
           description="List of annotations and attributes from the source data to include. None will be included by "
                       "default."),
    Config("stats_export.delimiter", default="\t", description="Delimiter separating columns"),
    Config("stats_export.cutoff", default=1,
           description="The minimum frequency a word must have in order to be included in the result"),
    Config("stats_export.remote_host", "", description="Remote host to install to"),
    Config("stats_export.remote_dir", "", description="Path on remote host to install to")
]
