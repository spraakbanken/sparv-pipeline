"""Build word frequency list."""

import csv
import logging
from collections import defaultdict

import sparv.util as util
from sparv import AllDocuments, Annotation, Corpus, Export, exporter, Config

log = logging.getLogger(__name__)


@exporter("Corpus word frequency list", language=["swe"],
          config=[Config("stats_export.delimiter", default="\t"),
                  Config("stats_export.cutoff", default=1),
                  Config("stats_export.include_all_compounds", default=False)])
def freq_list(corpus: str = Corpus,
              docs: list = AllDocuments,
              word: str = Annotation("<token:word>", all_docs=True),
              msd: str = Annotation("<token>:hunpos.msd", all_docs=True),
              baseform: str = Annotation("<token:baseform>", all_docs=True),
              sense: str = Annotation("<token:sense>", all_docs=True),
              lemgram: str = Annotation("<token>:saldo.lemgram", all_docs=True),
              complemgram: str = Annotation("<token>:saldo.complemgram", all_docs=True),
              out: str = Export("frequency_list/stats_[id].csv"),
              delimiter: str = Config("stats_export.delimiter"),
              cutoff: int = Config("stats_export.cutoff"),
              include_all_compounds: bool = Config("stats_export.include_all_compounds")):
    """Create a word frequency list for the entire corpus.

    Args:
        corpus (str, optional): The corpus ID. Defaults to Corpus.
        docs (list, optional): The documents belonging to this corpus. Defaults to AllDocuments.
        word (str, optional): Word annotations. Defaults to Annotation("<token:word>", all_docs=True).
        msd (str, optional): MSD annotations. Defaults to Annotation("<token>:hunpos.msd", all_docs=True).
        baseform (str, optional): Baseform annotations. Defaults to Annotation("<token:baseform>", all_docs=True).
        sense (str, optional): Sense annotations. Defaults to Annotation("<token:sense>", all_docs=True).
        lemgram (str, optional): Lemgram annotations. Defaults to Annotation("<token>:saldo.lemgram", all_docs=True).
        complemgram (str, optional): Compound lemgram annotations.
            Defaults to Annotation("<token>:saldo.complemgram", all_docs=True).
        out (str, optional): The output word frequency file. Defaults to Export("frequency_list/[id].csv").
        delimiter (str, optional): Column delimiter to use in the csv. Defaults to Config("stats_export.delimiter").
        cutoff (int, optional): The minimum frequency a word must have in order to be included in the result.
            Defaults to Config("stats_export.cutoff").
        include_all_compounds (bool, optional): Whether to include compound analyses for every word
            or just for the words that are lacking a sense annotation.
            Defaults to Config("stats_export.include_all_compounds").
    """
    freq_dict = defaultdict(int)

    for doc in docs:
        tokens = util.read_annotation_attributes(doc, [word, msd, baseform, sense, lemgram, complemgram])
        update_freqs(tokens, freq_dict, include_all_compounds)

    with open(out, "w") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=delimiter)
        csv_writer.writerow(["token", "POS", "lemma", "SALDO sense", "lemgram", "compound", "count"])
        for (wordform, msd, lemma, sense, lemgram, complemgram), freq in sorted(freq_dict.items(), key=lambda x: -x[1]):
            if cutoff and cutoff > freq:
                break
            csv_writer.writerow([wordform, msd, lemma, sense, lemgram, complemgram, freq])
    log.info("Exported: %s", out)


def update_freqs(tokens, freq_dict, include_all_compounds):
    """Extract annotation info and update frequencies."""
    for word, msd, baseform, sense, lemgram, complemgram in tokens:
        baseform = baseform.split("|")[1]
        sense = sense.split("|")[1].split(":")[0]
        lemgram = lemgram.split("|")[1].split(":")[0]
        complemgram = complemgram.split("|")[1].split(":")[0]
        if not include_all_compounds:
            if sense:
                complemgram = ""
        freq_dict[(word, msd, baseform, sense, lemgram, complemgram)] += 1
