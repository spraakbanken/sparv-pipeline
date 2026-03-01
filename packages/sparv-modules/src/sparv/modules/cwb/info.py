"""Create or edit .info file."""

import time
from datetime import datetime
from pathlib import Path

from sparv.api import (
    AllSourceFilenames,
    AnnotationAllSourceFiles,
    AnnotationCommonData,
    Config,
    Export,
    OutputCommonData,
    SparvErrorMessage,
    annotator,
    exporter,
    get_logger,
)

logger = get_logger(__name__)


@exporter("CWB .info file")
def info(
    out: Export = Export("cwb.encoded/data/.info"),
    sentences: AnnotationCommonData = AnnotationCommonData("misc.<sentence>_count"),
    firstdate: AnnotationCommonData = AnnotationCommonData("cwb.datefirst"),
    lastdate: AnnotationCommonData = AnnotationCommonData("cwb.datelast"),
    resolution: AnnotationCommonData = AnnotationCommonData("dateformat.resolution"),
    protected: bool = Config("korp.protected"),
) -> None:
    """Create CWB .info file.

    Args:
        out: Output file path for the .info file.
        sentences: Annotation containing the number of sentences in the corpus.
        firstdate: Annotation containing the first date in the corpus.
        lastdate: Annotation containing the last date in the corpus.
        resolution: Annotation containing the date resolution.
        protected: Boolean indicating if the corpus is protected.
    """
    create_info_file(sentences, firstdate, lastdate, resolution, protected, out)


@exporter("CWB .info file for scrambled corpus")
def info_scrambled(
    out: Export = Export("cwb.encoded_scrambled/data/.info"),
    sentences: AnnotationCommonData = AnnotationCommonData("misc.<sentence>_count"),
    firstdate: AnnotationCommonData = AnnotationCommonData("cwb.datefirst"),
    lastdate: AnnotationCommonData = AnnotationCommonData("cwb.datelast"),
    resolution: AnnotationCommonData = AnnotationCommonData("dateformat.resolution"),
    protected: bool = Config("korp.protected"),
) -> None:
    """Create CWB .info file for scrambled corpus.

    Args:
        out: Output file path for the .info file.
        sentences: Annotation containing the number of sentences in the corpus.
        firstdate: Annotation containing the first date in the corpus.
        lastdate: Annotation containing the last date in the corpus.
        resolution: Annotation containing the date resolution.
        protected: Boolean indicating if the corpus is protected.
    """
    create_info_file(sentences, firstdate, lastdate, resolution, protected, out)


def create_info_file(
    sentences: AnnotationCommonData,
    firstdate: AnnotationCommonData,
    lastdate: AnnotationCommonData,
    resolution: AnnotationCommonData,
    protected: bool,
    out: Export,
) -> None:
    """Create .info file.

    Args:
        sentences: Annotation containing the number of sentences in the corpus.
        firstdate: Annotation containing the first date in the corpus.
        lastdate: Annotation containing the last date in the corpus.
        resolution: Annotation containing the date resolution.
        protected: Boolean indicating if the corpus is protected.
        out: Output file path for the .info file.
    """
    content = []
    protected_str = str(protected).lower()

    for key, value_obj in [
        ("Sentences", sentences),
        ("FirstDate", firstdate),
        ("LastDate", lastdate),
        ("DateResolution", resolution),
        ("Updated", time.strftime("%Y-%m-%d")),
        ("Protected", protected_str),
    ]:
        value = value_obj.read() if isinstance(value_obj, AnnotationCommonData) else value_obj

        content.append(f"{key}: {value}\n")

    # Write .info file
    with Path(out).open("w", encoding="utf-8") as o:
        o.writelines(content)

    logger.info("Exported: %s", out)


@annotator("datefirst and datelast files for .info", order=1)
def info_date(
    source_files: AllSourceFilenames = AllSourceFilenames(),
    out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst", description="The earliest date in the corpus"),
    out_datelast: OutputCommonData = OutputCommonData("cwb.datelast", description="The latest date in the corpus"),
    datefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.datefrom"),
    dateto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.dateto"),
    timefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.timefrom"),
    timeto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.timeto"),
) -> None:
    """Create datefirst and datelast file (needed for .info file).

    Args:
        source_files: List of source files.
        out_datefirst: Output file path for the datefirst file.
        out_datelast: Output file path for the datelast file.
        datefrom: Annotation containing the date from information.
        dateto: Annotation containing the date to information.
        timefrom: Annotation containing the time from information.
        timeto: Annotation containing the time to information.

    Raises:
        SparvErrorMessage: If the corpus is configured as having date information, but no dates were found.
    """
    first_date = None
    last_date = None

    for file in source_files:
        from_dates = sorted((int(x[0]), x[1]) for x in datefrom(file).read_attributes((datefrom, timefrom)) if x[0])
        if from_dates and (first_date is None or from_dates[0] < first_date):
            first_date = from_dates[0]
        to_dates = sorted((int(x[0]), x[1]) for x in dateto(file).read_attributes((dateto, timeto)) if x[0])
        if to_dates and (last_date is None or to_dates[-1] > last_date):
            last_date = to_dates[-1]

    if not first_date or not last_date:
        raise SparvErrorMessage("Corpus is configured as having date information, but no dates were found.")

    # Parse and re-format dates (zero-padding dates with less than 8 digits, needed by strptime)
    first_date_d = datetime.strptime(f"{str(first_date[0]).zfill(8)} {first_date[1]}", "%Y%m%d %H%M%S")
    first_date_formatted = first_date_d.strftime("%Y-%m-%d %H:%M:%S")
    last_date_d = datetime.strptime(f"{str(last_date[0]).zfill(8)} {last_date[1]}", "%Y%m%d %H%M%S")
    last_date_formatted = last_date_d.strftime("%Y-%m-%d %H:%M:%S")

    out_datefirst.write(first_date_formatted)
    out_datelast.write(last_date_formatted)


@annotator("Empty datefirst and datelast files for .info", order=2)
def info_date_unknown(
    out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst", description="Empty string"),
    out_datelast: OutputCommonData = OutputCommonData("cwb.datelast", description="Empty string"),
) -> None:
    """Create empty datefirst and datelast file (needed for .info file) if corpus has no date information.

    Args:
        out_datefirst: Output file path for the datefirst file.
        out_datelast: Output file path for the datelast file.
    """
    logger.info("No date information found in corpus")

    # Write datefirst and datelast files
    out_datefirst.write("")
    out_datelast.write("")
