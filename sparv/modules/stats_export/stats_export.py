"""Build word frequency list."""

import csv
from collections import defaultdict

from sparv.api import (AllSourceFilenames, AnnotationAllSourceFiles, Config, Export, ExportInput, OutputCommonData, exporter,
                       get_logger, installer, util)

logger = get_logger(__name__)


@exporter("Corpus word frequency list", language=["swe"], order=1)
def freq_list(source_files: AllSourceFilenames = AllSourceFilenames(),
              word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
              msd: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:msd>"),
              baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
              sense: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:sense>"),
              lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:saldo.lemgram"),
              complemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:saldo.complemgram"),
              out: Export = Export("frequency_list/stats_[metadata.id].csv"),
              delimiter: str = Config("stats_export.delimiter"),
              cutoff: int = Config("stats_export.cutoff"),
              include_all_compounds: bool = Config("stats_export.include_all_compounds")):
    """Create a word frequency list for the entire corpus.

    Args:
        source_files (list, optional): The source files belonging to this corpus. Defaults to AllSourceFilenames.
        word (str, optional): Word annotations. Defaults to AnnotationAllSourceFiles("<token:word>").
        msd (str, optional): MSD annotations. Defaults to AnnotationAllSourceFiles("<token:msd>").
        baseform (str, optional): Baseform annotations. Defaults to AnnotationAllSourceFiles("<token:baseform>").
        sense (str, optional): Sense annotations. Defaults to AnnotationAllSourceFiles("<token:sense>").
        lemgram (str, optional): Lemgram annotations. Defaults to AnnotationAllSourceFiles("<token>:saldo.lemgram").
        complemgram (str, optional): Compound lemgram annotations.
            Defaults to AnnotationAllSourceFiles("<token>:saldo.complemgram").
        out (str, optional): The output word frequency file. Defaults to Export("frequency_list/[metadata.id].csv").
        delimiter (str, optional): Column delimiter to use in the csv. Defaults to Config("stats_export.delimiter").
        cutoff (int, optional): The minimum frequency a word must have in order to be included in the result.
            Defaults to Config("stats_export.cutoff").
        include_all_compounds (bool, optional): Whether to include compound analyses for every word
            or just for the words that are lacking a sense annotation.
            Defaults to Config("stats_export.include_all_compounds").
    """
    freq_dict = defaultdict(int)

    for source_file in source_files:
        tokens = word.read_attributes(source_file, [word, msd, baseform, sense, lemgram, complemgram])
        update_freqs(tokens, freq_dict, include_all_compounds)

    write_csv(out, freq_dict, delimiter, cutoff)


@exporter("Corpus word frequency list (without Swedish annotations)", order=2)
def freq_list_simple(source_files: AllSourceFilenames = AllSourceFilenames(),
                     word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
                     pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
                     baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
                     out: Export = Export("frequency_list/stats_[metadata.id].csv"),
                     delimiter: str = Config("stats_export.delimiter"),
                     cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations."""
    freq_dict = defaultdict(int)

    for source_file in source_files:
        simple_tokens = word.read_attributes(source_file, [word, pos, baseform])

        # Add empty annotations for sense, lemgram and complemgram
        tokens = []
        for w, p, b in simple_tokens:
            tokens.append((w, p, b, "|", "|", "|"))
        update_freqs(tokens, freq_dict)

    write_csv(out, freq_dict, delimiter, cutoff)


@exporter("Corpus word frequency list for Old Swedish (without part-of-speech)", language=["swe-fsv"], order=3)
def freq_list_fsv(source_files: AllSourceFilenames = AllSourceFilenames(),
                  word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
                  baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
                  lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:lemgram>"),
                  out: Export = Export("frequency_list/stats_[metadata.id].csv"),
                  delimiter: str = Config("stats_export.delimiter"),
                  cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations."""
    freq_dict = defaultdict(int)

    for source_file in source_files:
        simple_tokens = word.read_attributes(source_file, [word, baseform, lemgram])

        # Add empty annotations for sense, lemgram and complemgram
        tokens = []
        for w, b, lem in simple_tokens:
            tokens.append((w, "", b, "|", lem, "|"))
        update_freqs(tokens, freq_dict, include_all_lemgrams=True, include_all_baseforms=True)

    write_csv(out, freq_dict, delimiter, cutoff)


def update_freqs(tokens, freq_dict, include_all_compounds=False, include_all_lemgrams=False, include_all_baseforms=False):
    """Extract annotation info and update frequencies."""
    for word, msd, baseform, sense, lemgram, complemgram in tokens:
        if "|" in baseform and not include_all_baseforms:
            baseform = baseform.split("|")[1]
        sense = sense.split("|")[1].split(":")[0]
        if not include_all_lemgrams:
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
    logger.info("Exported: %s", out)


@installer("Install word frequency list on remote host", config=[
    Config("stats_export.remote_host", "", description="Remote host to install to"),
    Config("stats_export.remote_dir", "", description="Path on remote host to install to")
])
def install_freq_list(freq_list: ExportInput = ExportInput("frequency_list/stats_[metadata.id].csv"),
                      out: OutputCommonData = OutputCommonData("stats_export.install_freq_list_marker"),
                      host: str = Config("stats_export.remote_host"),
                      target_dir: str = Config("stats_export.remote_dir")):
    """Install frequency list on server by rsyncing."""
    util.install.install_file(freq_list, host, target_dir)
    out.write("")
