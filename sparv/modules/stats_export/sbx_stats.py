"""SBX specific annotation and export functions related to the stats export."""

from sparv.api import (AllSourceFilenames, Annotation, AnnotationAllSourceFiles, Config, Export, ExportInput, Output,
                       OutputCommonData, annotator, exporter, get_logger, installer, util)

from .stats_export import freq_list

logger = get_logger(__name__)


@annotator("Extract the complemgram with the highest score", language=["swe"])
def best_complemgram(
        out: Output = Output("<token>:stats_export.complemgram_best", description="Complemgram annotation with highest score"),
        complemgram: Annotation = Annotation("<token>:saldo.complemgram")):
    """Extract the complemgram with the highest score."""
    from sparv.modules.misc import misc
    misc.best_from_set(out, complemgram, is_sorted=True)


@annotator("Extract the sense with the highest score", language=["swe"])
def best_sense(
        out: Output = Output("<token>:stats_export.sense_best", description="Sense annotation with highest score"),
        sense: Annotation = Annotation("<token>:wsd.sense")):
    """Extract the sense annotation with the highest score."""
    from sparv.modules.misc import misc
    misc.best_from_set(out, sense, is_sorted=True)


@annotator("Extract the first baseform annotation from a set of baseforms", language=["swe"])
def first_baseform(
        out: Output = Output("<token>:stats_export.baseform_first", description="First baseform from a set of baseforms"),
        baseform: Annotation = Annotation("<token:baseform>")):
    """Extract the first baseform annotation from a set of baseforms."""
    from sparv.modules.misc import misc
    misc.first_from_set(out, baseform)


@annotator("Extract the first lemgram annotation from a set of lemgrams", language=["swe"])
def first_lemgram(
        out: Output = Output("<token>:stats_export.lemgram_first", description="First lemgram from a set of lemgrams"),
        lemgram: Annotation = Annotation("<token>:saldo.lemgram")):
    """Extract the first lemgram annotation from a set of lemgrams."""
    from sparv.modules.misc import misc
    misc.first_from_set(out, lemgram)


@annotator("Get the best complemgram if the token is lacking a sense annotation", language=["swe"])
def conditional_best_complemgram(
    out_complemgrams: Output = Output("<token>:stats_export.complemgram_best_cond",
                                      description="Compound analysis using lemgrams"),
    complemgrams: Annotation= Annotation("<token>:stats_export.complemgram_best"),
    sense: Annotation = Annotation("<token:sense>")):
    """Get the best complemgram if the token is lacking a sense annotation."""
    all_annotations = list(complemgrams.read_attributes((complemgrams, sense)))
    short_complemgrams = []
    for complemgram, sense in all_annotations:
        if sense and sense != "|":
            complemgram = ""
        short_complemgrams.append(complemgram)
    out_complemgrams.write(short_complemgrams)


@exporter("Corpus word frequency list", language=["swe"], order=1)
def sbx_freq_list(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    msd: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:msd>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    sense: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.sense_best"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.lemgram_first"),
    complemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles(
                                            "<token>:stats_export.complemgram_best_cond"),
    out: Export = Export("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for the entire corpus.

    Args:
        source_files (list, optional): The source files belonging to this corpus. Defaults to AllSourceFilenames.
        word (str, optional): Word annotations. Defaults to AnnotationAllSourceFiles("<token:word>").
        token (str, optional): Token span annotations. Defaults to AnnotationAllSourceFiles("<token>").
        msd (str, optional): MSD annotations. Defaults to AnnotationAllSourceFiles("<token:msd>").
        baseform (str, optional): Annotations with first baseform from each set.
            Defaults to AnnotationAllSourceFiles("<token:baseform>").
        sense (str, optional): Best sense annotations. Defaults to AnnotationAllSourceFiles("<token:sense>").
        lemgram (str, optional): Annotations with first lemgram from each set.
            Defaults to AnnotationAllSourceFiles("<token>:saldo.lemgram").
        complemgram (str, optional): Conditional best compound lemgram annotations.
            Defaults to AnnotationAllSourceFiles("<token>:saldo.complemgram").
        out (str, optional): The output word frequency file.
            Defaults to Export("stats_export.frequency_list_sbx/[metadata.id].csv").
        delimiter (str, optional): Column delimiter to use in the csv. Defaults to Config("stats_export.delimiter").
        cutoff (int, optional): The minimum frequency a word must have in order to be included in the result.
            Defaults to Config("stats_export.cutoff").
    """
    annotations = [(word, "token"), (msd, "POS"), (baseform, "lemma"), (sense, "SALDO sense"), (lemgram, "lemgram"),
                   (complemgram, "compound")]

    freq_list(source_files=source_files, word=word, token=token, annotations=annotations, source_annotations=[],
              out=out, sparv_namespace="", source_namespace="", delimiter=delimiter, cutoff=cutoff)


@exporter("Corpus word frequency list", language=["swe"])
def sbx_freq_list_date(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    msd: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:msd>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    sense: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.sense_best"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.lemgram_first"),
    complemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles(
                                            "<token>:stats_export.complemgram_best_cond"),
    date: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.datetime_from]"),
    out: Export = Export("stats_export.frequency_list_sbx_date/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for the entire corpus.

    Args:
        source_files (list, optional): The source files belonging to this corpus. Defaults to AllSourceFilenames.
        word (str, optional): Word annotations. Defaults to AnnotationAllSourceFiles("<token:word>").
        token (str, optional): Token span annotations. Defaults to AnnotationAllSourceFiles("<token>").
        msd (str, optional): MSD annotations. Defaults to AnnotationAllSourceFiles("<token:msd>").
        baseform (str, optional): Annotations with first baseform from each set.
            Defaults to AnnotationAllSourceFiles("<token:baseform>").
        sense (str, optional): Best sense annotations. Defaults to AnnotationAllSourceFiles("<token:sense>").
        lemgram (str, optional): Annotations with first lemgram from each set.
            Defaults to AnnotationAllSourceFiles("<token>:saldo.lemgram").
        complemgram (str, optional): Conditional best compound lemgram annotations.
            Defaults to AnnotationAllSourceFiles("<token>:saldo.complemgram").
        date (str, optional): date annotation
        out (str, optional): The output word frequency file.
            Defaults to Export("stats_export.frequency_list_sbx_date/[metadata.id].csv").
        delimiter (str, optional): Column delimiter to use in the csv. Defaults to Config("stats_export.delimiter").
        cutoff (int, optional): The minimum frequency a word must have in order to be included in the result.
            Defaults to Config("stats_export.cutoff").
    """
    annotations = [(word, "token"), (msd, "POS"), (baseform, "lemma"), (sense, "SALDO sense"), (lemgram, "lemgram"),
                   (complemgram, "compound"), (date, "date")]

    freq_list(source_files=source_files, word=word, token=token, annotations=annotations, source_annotations=[],
              out=out, sparv_namespace="", source_namespace="", delimiter=delimiter, cutoff=cutoff)


@exporter("Corpus word frequency list (without Swedish annotations)", language=["swe"], order=2)
def sbx_freq_list_simple_swe(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    out: Export = Export("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations."""
    annotations = [(word, "token"), (pos, "POS"), (baseform, "lemma")]

    freq_list(source_files=source_files, word=word, token=token, annotations=annotations, source_annotations=[],
              out=out, sparv_namespace="", source_namespace="", delimiter=delimiter, cutoff=cutoff)


@exporter("Corpus word frequency list (without Swedish annotations)", order=3)
def sbx_freq_list_simple(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
    out: Export = Export("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations."""
    annotations = [(word, "token"), (pos, "POS"), (baseform, "lemma")]

    freq_list(source_files=source_files, word=word, token=token, annotations=annotations, source_annotations=[],
              out=out, sparv_namespace="", source_namespace="", delimiter=delimiter, cutoff=cutoff)


@exporter("Corpus word frequency list for Old Swedish (without part-of-speech)", language=["swe-fsv"], order=4)
def sbx_freq_list_fsv(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:lemgram>"),
    out: Export = Export("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff")):
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations."""
    annotations = [(word, "token"), (baseform, "lemma"), (lemgram, "lemgram")]

    freq_list(source_files=source_files, word=word, token=token, annotations=annotations, source_annotations=[],
              out=out, sparv_namespace="", source_namespace="", delimiter=delimiter, cutoff=cutoff)


@installer("Install SBX word frequency list on remote host")
def install_sbx_freq_list(
    freq_list: ExportInput = ExportInput("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    out: OutputCommonData = OutputCommonData("stats_export.install_sbx_freq_list_marker"),
    host: str = Config("stats_export.remote_host"),
    target_dir: str = Config("stats_export.remote_dir")):
    """Install frequency list on server by rsyncing."""
    util.install.install_file(freq_list, host, target_dir)
    out.write("")


@installer("Install SBX word frequency list with dates on remote host")
def install_sbx_freq_list_date(
    freq_list: ExportInput = ExportInput("stats_export.frequency_list_sbx_date/stats_[metadata.id].csv"),
    out: OutputCommonData = OutputCommonData("stats_export.install_sbx_freq_list_date_marker"),
    host: str = Config("stats_export.remote_host"),
    target_dir: str = Config("stats_export.remote_dir")):
    """Install frequency list on server by rsyncing."""
    util.install.install_file(freq_list, host, target_dir)
    out.write("")
