"""Build word frequency list."""

import csv
import logging
from collections import defaultdict

from sparv import AllDocuments, AnnotationAllDocs, Corpus, Export, exporter, Config

log = logging.getLogger(__name__)


@exporter("Corpus word frequency list", language=["swe"], order=1, config=[
    Config("stats_export.include_all_compounds", default=False,
           description="Whether to include compound analyses for every word or just for the words that are lacking "
                       "a sense annotation")
])
def freq_list(corpus: Corpus = Corpus(),
              docs: AllDocuments = AllDocuments(),
              word: AnnotationAllDocs = AnnotationAllDocs("<token:word>"),
              msd: AnnotationAllDocs = AnnotationAllDocs("<token:msd>"),
              baseform: AnnotationAllDocs = AnnotationAllDocs("<token:baseform>"),
              sense: AnnotationAllDocs = AnnotationAllDocs("<token:sense>"),
              lemgram: AnnotationAllDocs = AnnotationAllDocs("<token>:saldo.lemgram"),
              complemgram: AnnotationAllDocs = AnnotationAllDocs("<token>:saldo.complemgram"),
              out: Export = Export("frequency_list/stats_[metadata.id].csv"),
              delimiter: str = Config("stats_export.delimiter"),
              cutoff: int = Config("stats_export.cutoff"),
              include_all_compounds: bool = Config("stats_export.include_all_compounds")):
    """Create a word frequency list for the entire corpus.

    Args:
        corpus (str, optional): The corpus ID. Defaults to Corpus.
        docs (list, optional): The documents belonging to this corpus. Defaults to AllDocuments.
        word (str, optional): Word annotations. Defaults to AnnotationAllDocs("<token:word>").
        msd (str, optional): MSD annotations. Defaults to AnnotationAllDocs("<token:msd>").
        baseform (str, optional): Baseform annotations. Defaults to AnnotationAllDocs("<token:baseform>").
        sense (str, optional): Sense annotations. Defaults to AnnotationAllDocs("<token:sense>").
        lemgram (str, optional): Lemgram annotations. Defaults to AnnotationAllDocs("<token>:saldo.lemgram").
        complemgram (str, optional): Compound lemgram annotations.
            Defaults to AnnotationAllDocs("<token>:saldo.complemgram").
        out (str, optional): The output word frequency file. Defaults to Export("frequency_list/[metadata.id].csv").
        delimiter (str, optional): Column delimiter to use in the csv. Defaults to Config("stats_export.delimiter").
        cutoff (int, optional): The minimum frequency a word must have in order to be included in the result.
            Defaults to Config("stats_export.cutoff").
        include_all_compounds (bool, optional): Whether to include compound analyses for every word
            or just for the words that are lacking a sense annotation.
            Defaults to Config("stats_export.include_all_compounds").
    """
    freq_dict = defaultdict(int)

    for doc in docs:
        tokens = word.read_attributes(doc, [word, msd, baseform, sense, lemgram, complemgram])
        update_freqs(tokens, freq_dict, include_all_compounds)

    write_csv(out, freq_dict, delimiter, cutoff)


@exporter("Corpus word frequency list (withouth Swedish annotations)", order=2, config=[
    Config("stats_export.delimiter", default="\t", description="Delimiter separating columns"),
    Config("stats_export.cutoff", default=1,
           description="The minimum frequency a word must have in order to be included in the result"),
])
def freq_list_simple(corpus: Corpus = Corpus(),
                     docs: AllDocuments = AllDocuments(),
                     word: AnnotationAllDocs = AnnotationAllDocs("<token:word>"),
                     pos: AnnotationAllDocs = AnnotationAllDocs("<token:pos>"),
                     baseform: AnnotationAllDocs = AnnotationAllDocs("<token:baseform>"),
                     out: Export = Export("frequency_list/stats_[metadata.id].csv"),
                     delimiter: str = Config("stats_export.delimiter"),
                     cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations."""
    freq_dict = defaultdict(int)

    for doc in docs:
        simple_tokens = word.read_attributes(doc, [word, pos, baseform])

        # Add empty annotations for sense, lemgram and complemgram
        tokens = []
        for w, p, b in simple_tokens:
            tokens.append((w, p, b, "|", "|", "|"))
        update_freqs(tokens, freq_dict)

    write_csv(out, freq_dict, delimiter, cutoff)


def update_freqs(tokens, freq_dict, include_all_compounds=False):
    """Extract annotation info and update frequencies."""
    for word, msd, baseform, sense, lemgram, complemgram in tokens:
        if "|" in baseform:
            baseform = baseform.split("|")[1]
        sense = sense.split("|")[1].split(":")[0]
        lemgram = lemgram.split("|")[1].split(":")[0]
        complemgram = complemgram.split("|")[1].split(":")[0]
        if not include_all_compounds:
            if sense:
                complemgram = ""
        freq_dict[(word, msd, baseform, sense, lemgram, complemgram)] += 1


def write_csv(out, freq_dict, delimiter, cutoff):
    """Write csv file."""
    with open(out, "w") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=delimiter)
        csv_writer.writerow(["token", "POS", "lemma", "SALDO sense", "lemgram", "compound", "count"])
        for (wordform, msd, lemma, sense, lemgram, complemgram), freq in sorted(freq_dict.items(), key=lambda x: -x[1]):
            if cutoff and cutoff > freq:
                break
            csv_writer.writerow([wordform, msd, lemma, sense, lemgram, complemgram, freq])
    log.info("Exported: %s", out)
