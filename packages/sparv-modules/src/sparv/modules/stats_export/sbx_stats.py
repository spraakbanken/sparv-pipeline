"""SBX specific annotation and export functions related to the stats export."""

from pathlib import Path

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationAllSourceFiles,
    Config,
    Corpus,
    Export,
    ExportInput,
    MarkerOptional,
    Output,
    OutputMarker,
    SparvErrorMessage,
    annotator,
    exporter,
    get_logger,
    installer,
    uninstaller,
    util,
)

from .stats_export import freq_list
from .utils import compress

logger = get_logger(__name__)


@annotator("Extract the complemgram with the highest score", language=["swe"])
def best_complemgram(
    complemgram: Annotation = Annotation("<token>:saldo.complemgram"),
    out: Output = Output(
        "<token>:stats_export.complemgram_best", description="Complemgram annotation with highest score"
    ),
) -> None:
    """Extract the complemgram with the highest score.

    Args:
        complemgram: The input complemgram annotation.
        out: The output complemgram annotation.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.best_from_set(out, complemgram, is_sorted=True)


@annotator("Extract the sense with the highest score", language=["swe"])
def best_sense(
    sense: Annotation = Annotation("<token>:wsd.sense"),
    out: Output = Output("<token>:stats_export.sense_best", description="Sense annotation with highest score"),
) -> None:
    """Extract the sense annotation with the highest score.

    Args:
        sense: The input sense annotation.
        out: The output sense annotation.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.best_from_set(out, sense, is_sorted=True)


@annotator("Extract the first baseform annotation from a set of baseforms", language=["swe"])
def first_baseform(
    baseform: Annotation = Annotation("<token:baseform>"),
    out: Output = Output("<token>:stats_export.baseform_first", description="First baseform from a set of baseforms"),
) -> None:
    """Extract the first baseform annotation from a set of baseforms.

    Args:
        baseform: The input baseform annotation.
        out: The output baseform annotation.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.first_from_set(out, baseform)


@annotator("Extract the first lemgram annotation from a set of lemgrams", language=["swe"])
def first_lemgram(
    lemgram: Annotation = Annotation("<token:lemgram>"),
    out: Output = Output("<token>:stats_export.lemgram_first", description="First lemgram from a set of lemgrams"),
) -> None:
    """Extract the first lemgram annotation from a set of lemgrams.

    Args:
        lemgram: The input lemgram annotation.
        out: The output lemgram annotation.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.first_from_set(out, lemgram)


@annotator("Get the best complemgram if the token is lacking a sense annotation", language=["swe"])
def conditional_best_complemgram(
    complemgrams: Annotation = Annotation("<token>:stats_export.complemgram_best"),
    sense: Annotation = Annotation("<token:sense>"),
    out_complemgrams: Output = Output(
        "<token>:stats_export.complemgram_best_cond", description="Compound analysis using lemgrams"
    ),
) -> None:
    """Get the best complemgram if the token is lacking a sense annotation.

    Args:
        complemgrams: The input complemgram annotation.
        sense: The input sense annotation.
        out_complemgrams: The output complemgram annotation.
    """
    all_annotations = list(complemgrams.read_attributes((complemgrams, sense)))
    short_complemgrams = []
    for complemgram, sense_val in all_annotations:
        if sense_val and sense_val != "|":
            complemgram = ""  # noqa: PLW2901
        short_complemgrams.append(complemgram)
    out_complemgrams.write(short_complemgrams)


@exporter("Corpus word frequency list", language=["swe"])
def sbx_freq_list(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    msd: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:msd>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    sense: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.sense_best"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.lemgram_first"),
    complemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.complemgram_best_cond"),
    out: Export = Export("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
) -> None:
    """Create a word frequency list for the entire corpus.

    Args:
        source_files: The source files belonging to this corpus.
        word: Word annotations.
        token: Token span annotations.
        msd: MSD annotations.
        baseform: Annotations with first baseform from each set.
        sense: Best sense annotations.
        lemgram: Annotations with first lemgram from each set.
        complemgram: Conditional best compound lemgram annotations.
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    annotations = [
        (word, "token"),
        (msd, "POS"),
        (baseform, "lemma"),
        (sense, "SALDO sense"),
        (lemgram, "lemgram"),
        (complemgram, "compound"),
    ]

    freq_list(
        source_files=source_files,
        word=word,
        token=token,
        annotations=annotations,
        source_annotations=[],
        out=out,
        sparv_namespace="",
        source_namespace="",
        delimiter=delimiter,
        cutoff=cutoff,
    )


@exporter("Corpus word frequency list (compressed)", language=["swe"])
def sbx_freq_list_compressed(
    stats_file: ExportInput = ExportInput("stats_export.frequency_list_sbx/stats_[metadata.id].csv"),
    out_file: Export = Export("stats_export.frequency_list_sbx/stats_[metadata.id].csv.[stats_export.compression]"),
    compression: str = Config("stats_export.compression"),
) -> None:
    """Compress statistics file.

    Args:
        stats_file: Path to statistics file.
        out_file: Path to output file.
        compression: The compression method to use.
    """
    compress(stats_file, out_file, compression)


@exporter("Corpus word frequency list with dates", language=["swe"])
def sbx_freq_list_date(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    msd: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:msd>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    sense: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.sense_best"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.lemgram_first"),
    complemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.complemgram_best_cond"),
    date: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.date_pretty"),
    out: Export = Export("stats_export.frequency_list_sbx_date/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
) -> None:
    """Create a word frequency list for the entire corpus.

    Args:
        source_files: The source files belonging to this corpus.
        word: Word annotations.
        token: Token span annotations.
        msd: MSD annotations.
        baseform: Annotations with first baseform from each set.
        sense: Best sense annotations.
        lemgram: Annotations with first lemgram from each set.
        complemgram: Conditional best compound lemgram annotations.
        date: date annotation
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    annotations = [
        (word, "token"),
        (msd, "POS"),
        (baseform, "lemma"),
        (sense, "SALDO sense"),
        (lemgram, "lemgram"),
        (complemgram, "compound"),
        (date, "date"),
    ]

    freq_list(
        source_files=source_files,
        word=word,
        token=token,
        annotations=annotations,
        source_annotations=[],
        out=out,
        sparv_namespace="",
        source_namespace="",
        delimiter=delimiter,
        cutoff=cutoff,
    )


@exporter("Corpus word frequency list with dates (compressed)", language=["swe"])
def sbx_freq_list_date_compressed(
    stats_file: ExportInput = ExportInput("stats_export.frequency_list_sbx_date/stats_[metadata.id].csv"),
    out_file: Export = Export(
        "stats_export.frequency_list_sbx_date/stats_[metadata.id].csv.[stats_export.compression]"
    ),
    compression: str = Config("stats_export.compression"),
) -> None:
    """Compress statistics file with dates.

    Args:
        stats_file: Path to statistics file.
        out_file: Path to output file.
        compression: The compression method to use.
    """
    compress(stats_file, out_file, compression)


@exporter("Corpus word frequency list (without Swedish annotations)", language=["swe"], order=1)
def sbx_freq_list_simple_swe(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    out: Export = Export("stats_export.frequency_list_sbx_simple/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
) -> None:
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations.

    Args:
        source_files: The source files belonging to this corpus.
        token: Token span annotations.
        word: Word annotations.
        pos: Part-of-speech annotations.
        baseform: Annotations with first baseform from each set.
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    annotations = [(word, "token"), (pos, "POS"), (baseform, "lemma")]

    freq_list(
        source_files=source_files,
        word=word,
        token=token,
        annotations=annotations,
        source_annotations=[],
        out=out,
        sparv_namespace="",
        source_namespace="",
        delimiter=delimiter,
        cutoff=cutoff,
    )


@exporter("Corpus word frequency list (without Swedish annotations, compressed)", language=["swe"], order=1)
def sbx_freq_list_simple_swe_compressed(
    stats_file: ExportInput = ExportInput("stats_export.frequency_list_sbx_simple/stats_[metadata.id].csv"),
    out_file: Export = Export(
        "stats_export.frequency_list_sbx_simple/stats_[metadata.id].csv.[stats_export.compression]"
    ),
    compression: str = Config("stats_export.compression"),
) -> None:
    """Compress simple Swedish statistics file.

    Args:
        stats_file: Path to statistics file.
        out_file: Path to output file.
        compression: The compression method to use.
    """
    compress(stats_file, out_file, compression)


@exporter("Corpus word frequency list (without Swedish annotations)", order=2)
def sbx_freq_list_simple(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
    out: Export = Export("stats_export.frequency_list_sbx_simple/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
) -> None:
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations.

    Args:
        source_files: The source files belonging to this corpus.
        token: Token span annotations.
        word: Word annotations.
        pos: Part-of-speech annotations.
        baseform: Annotations with first baseform from each set.
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    annotations = [(word, "token"), (pos, "POS"), (baseform, "lemma")]

    freq_list(
        source_files=source_files,
        word=word,
        token=token,
        annotations=annotations,
        source_annotations=[],
        out=out,
        sparv_namespace="",
        source_namespace="",
        delimiter=delimiter,
        cutoff=cutoff,
    )


@exporter("Corpus word frequency list (without Swedish annotations, compressed)", order=2)
def sbx_freq_list_simple_compressed(
    stats_file: ExportInput = ExportInput("stats_export.frequency_list_sbx_simple/stats_[metadata.id].csv"),
    out_file: Export = Export(
        "stats_export.frequency_list_sbx_simple/stats_[metadata.id].csv.[stats_export.compression]"
    ),
    compression: str = Config("stats_export.compression"),
) -> None:
    """Compress simple statistics file.

    Args:
        stats_file: Path to statistics file.
        out_file: Path to output file.
        compression: The compression method to use.
    """
    compress(stats_file, out_file, compression)


@exporter("Corpus word frequency list for Swedish from the 1800's", language=["swe-1800"])
def sbx_freq_list_1800(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    msd: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:msd>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.baseform_first"),
    sense: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:hist.sense"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.lemgram_first"),
    complemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>:stats_export.complemgram_best_cond"),
    out: Export = Export("stats_export.frequency_list_sbx_1800/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
) -> None:
    """Create a word frequency list for the entire corpus.

    Args:
        source_files: The source files belonging to this corpus.
        word: Word annotations.
        token: Token span annotations.
        msd: MSD annotations.
        baseform: Annotations with first baseform from each set.
        sense: Best sense annotations.
        lemgram: Annotations with first lemgram from each set.
        complemgram: Conditional best compound lemgram annotations.
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    annotations = [
        (word, "token"),
        (msd, "POS"),
        (baseform, "lemma"),
        (sense, "SALDO sense"),
        (lemgram, "lemgram"),
        (complemgram, "compound"),
    ]

    freq_list(
        source_files=source_files,
        word=word,
        token=token,
        annotations=annotations,
        source_annotations=[],
        out=out,
        sparv_namespace="",
        source_namespace="",
        delimiter=delimiter,
        cutoff=cutoff,
    )


@exporter("Corpus word frequency list for Swedish from the 1800's (compressed)", language=["swe-1800"])
def sbx_freq_list_1800_compressed(
    stats_file: ExportInput = ExportInput("stats_export.frequency_list_sbx_1800/stats_[metadata.id].csv"),
    out_file: Export = Export(
        "stats_export.frequency_list_sbx_1800/stats_[metadata.id].csv.[stats_export.compression]"
    ),
    compression: str = Config("stats_export.compression"),
) -> None:
    """Compress 1800's Swedish statistics file.

    Args:
        stats_file: Path to statistics file.
        out_file: Path to output file.
        compression: The compression method to use.
    """
    compress(stats_file, out_file, compression)


@exporter("Corpus word frequency list for Old Swedish (without part-of-speech)", language=["swe-fsv"])
def sbx_freq_list_fsv(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
    lemgram: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:lemgram>"),
    out: Export = Export("stats_export.frequency_list_sbx_fsv/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
) -> None:
    """Create a word frequency list for a corpus without sense, lemgram and complemgram annotations.

    Args:
        source_files: The source files belonging to this corpus.
        token: Token span annotations.
        word: Word annotations.
        baseform: Annotations with first baseform from each set.
        lemgram: Annotations with first lemgram from each set.
        out: The output word frequency file.
        delimiter: Column delimiter to use in the csv.
        cutoff: The minimum frequency a word must have in order to be included in the result.
    """
    annotations = [(word, "token"), (baseform, "lemma"), (lemgram, "lemgram")]

    freq_list(
        source_files=source_files,
        word=word,
        token=token,
        annotations=annotations,
        source_annotations=[],
        out=out,
        sparv_namespace="",
        source_namespace="",
        delimiter=delimiter,
        cutoff=cutoff,
    )


@exporter("Corpus word frequency list for Old Swedish (without part-of-speech, compressed)", language=["swe-fsv"])
def sbx_freq_list_fsv_compressed(
    stats_file: ExportInput = ExportInput("stats_export.frequency_list_sbx_fsv/stats_[metadata.id].csv"),
    out_file: Export = Export("stats_export.frequency_list_sbx_fsv/stats_[metadata.id].csv.[stats_export.compression]"),
    compression: str = Config("stats_export.compression"),
) -> None:
    """Compress Old Swedish statistics file.

    Args:
        stats_file: Path to statistics file.
        out_file: Path to output file.
        compression: The compression method to use.
    """
    compress(stats_file, out_file, compression)


for inst in (
    {"suffix": "", "description": "", "extension": ""},
    {
        "suffix": "_compressed",
        "dir_suffix": "",
        "description": " (compressed)",
        "extension": ".[stats_export.compression]",
    },
    {"suffix": "_date", "description": " with dates", "extension": ""},
    {
        "suffix": "_date_compressed",
        "dir_suffix": "",
        "description": " with dates (compressed)",
        "extension": ".[stats_export.compression]",
    },
    {"suffix": "_simple", "description": " (without Swedish annotations)", "extension": ""},
    {
        "suffix": "_simple_compressed",
        "dir_suffix": "_simple",
        "description": " (without Swedish annotations, compressed)",
        "extension": ".[stats_export.compression]",
    },
    {"suffix": "_fsv", "description": " for Old Swedish (without part-of-speech)", "extension": ""},
    {
        "suffix": "_fsv_compressed",
        "dir_suffix": "_fsv",
        "description": " for Old Swedish (without part-of-speech, compressed)",
        "extension": ".[stats_export.compression]",
    },
    {"suffix": "_1800", "description": " for Swedish from the 1800's", "extension": ""},
    {
        "suffix": "_1800_compressed",
        "dir_suffix": "_1800",
        "description": " for Swedish from the 1800's (compressed)",
        "extension": ".[stats_export.compression]",
    },
):

    @installer(
        f"Install SBX word frequency list{inst['description']} on remote host",
        name=f"install_sbx_freq_list{inst['suffix']}",
        uninstaller=f"stats_export:uninstall_sbx_freq_list{inst['suffix']}",
    )
    def install_sbx_freq_list(
        freq_list: ExportInput = ExportInput(
            f"stats_export.frequency_list_sbx{inst.get('dir_suffix', inst['suffix'])}/"
            f"stats_[metadata.id].csv{inst['extension']}"
        ),
        marker: OutputMarker = OutputMarker(f"stats_export.install_sbx_freq_list{inst['suffix']}_marker"),
        uninstall_marker: MarkerOptional = MarkerOptional(
            f"stats_export.uninstall_sbx_freq_list{inst['suffix']}_marker"
        ),
        host: str | None = Config("stats_export.remote_host"),
        target_dir: str = Config("stats_export.remote_dir"),
    ) -> None:
        """Install frequency list on server by rsyncing, or install to an SVN repository.

        Args:
            freq_list: Path to frequency list.
            marker: Output marker.
            uninstall_marker: Uninstall marker.
            host: Remote host.
            target_dir: Remote directory.

        Raises:
            SparvErrorMessage: If neither host nor target directory is specified.
        """
        if not target_dir:
            raise SparvErrorMessage("Target directory must be specified.")
        if host and host.startswith("svn+"):
            url = host.rstrip("/") + "/" + Path(freq_list).name
            util.install.install_svn(freq_list, url, remove_existing=True)
        else:
            util.install.install_path(freq_list, host, target_dir)
        uninstall_marker.remove()
        marker.write()


for uninst in (
    {"suffix": "", "description": "", "compressed": False},
    {"suffix": "_compressed", "description": " (compressed)", "compressed": True},
    {"suffix": "_date", "description": " with dates", "compressed": False},
    {"suffix": "_date_compressed", "description": " with dates (compressed)", "compressed": True},
    {"suffix": "_simple", "description": " (without Swedish annotations)", "compressed": False},
    {"suffix": "_simple_compressed", "description": " (without Swedish annotations, compressed)", "compressed": True},
    {"suffix": "_fsv", "description": " for Old Swedish (without part-of-speech)", "compressed": False},
    {
        "suffix": "_fsv_compressed",
        "description": " for Old Swedish (without part-of-speech, compressed)",
        "compressed": True,
    },
    {"suffix": "_1800", "description": " for Swedish from the 1800's", "compressed": False},
    {"suffix": "_1800_compressed", "description": " for Swedish from the 1800's (compressed)", "compressed": True},
):

    @uninstaller(
        f"Uninstall SBX word frequency list{uninst['description']}", name=f"uninstall_sbx_freq_list{uninst['suffix']}"
    )
    def uninstall_sbx_freq_list(
        corpus_id: Corpus = Corpus(),
        marker: OutputMarker = OutputMarker(f"stats_export.uninstall_sbx_freq_list{uninst['suffix']}_marker"),
        install_marker: MarkerOptional = MarkerOptional(f"stats_export.install_sbx_freq_list{uninst['suffix']}_marker"),
        host: str | None = Config("stats_export.remote_host"),
        remote_dir: str = Config("stats_export.remote_dir"),
        compression: str = Config("stats_export.compression"),
        use_compression: bool = uninst["compressed"],
    ) -> None:
        """Uninstall SBX word frequency list.

        Args:
            corpus_id: The corpus ID.
            marker: Output marker.
            install_marker: Install marker.
            host: Remote host.
            remote_dir: Remote directory.
            compression: The compression method used.
            use_compression: Whether the file to uninstall is compressed.

        Raises:
            SparvErrorMessage: If neither host nor remote directory is specified.
        """
        if not remote_dir:
            raise SparvErrorMessage("Remote directory must be specified.")

        uninstall_file = f"stats_{corpus_id}.csv" + (f".{compression}" if use_compression else "")
        if host and host.startswith("svn+"):
            url = host.rstrip("/") + "/" + uninstall_file
            util.install.uninstall_svn(url)
        else:
            remote_dir = remote_dir or ""
            remote_file = Path(remote_dir) / uninstall_file
            logger.info("Removing SBX word frequency file %s%s", host + ":" if host else "", remote_file)
            util.install.uninstall_path(remote_file, host)
        install_marker.remove()
        marker.write()
