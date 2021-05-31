"""Word frequency list generation."""

from sparv.api import Config

from . import stats_export

__config__ = [
    Config("stats_export.include_all_compounds", default=False,
           description="Whether to include compound analyses for every word or just for the words that are lacking "
                       "a sense annotation"),
    Config("stats_export.delimiter", default="\t", description="Delimiter separating columns"),
    Config("stats_export.cutoff", default=1,
           description="The minimum frequency a word must have in order to be included in the result")
]
