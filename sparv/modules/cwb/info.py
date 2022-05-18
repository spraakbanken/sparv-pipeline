"""Create or edit .info file."""

import time
from datetime import datetime

from sparv.api import (AllSourceFilenames, AnnotationAllSourceFiles, AnnotationCommonData, Config, Export,
                       OutputCommonData, SparvErrorMessage, annotator, exporter, get_logger)

logger = get_logger(__name__)


@exporter("CWB .info file")
def info(out: Export = Export("cwb.encoded/data/.info"),
         sentences: AnnotationCommonData = AnnotationCommonData("misc.<sentence>_count"),
         firstdate: AnnotationCommonData = AnnotationCommonData("cwb.datefirst"),
         lastdate: AnnotationCommonData = AnnotationCommonData("cwb.datelast"),
         resolution: AnnotationCommonData = AnnotationCommonData("dateformat.resolution"),
         protected: bool = Config("korp.protected"),
         korp_modes: list = Config("korp.modes")):
    """Create CWB .info file."""
    create_info_file(sentences, firstdate, lastdate, resolution, protected, korp_modes, out)


@exporter("CWB .info file for scrambled corpus")
def info_scrambled(out: Export = Export("cwb.encoded_scrambled/data/.info"),
                   sentences: AnnotationCommonData = AnnotationCommonData("misc.<sentence>_count"),
                   firstdate: AnnotationCommonData = AnnotationCommonData("cwb.datefirst"),
                   lastdate: AnnotationCommonData = AnnotationCommonData("cwb.datelast"),
                   resolution: AnnotationCommonData = AnnotationCommonData("dateformat.resolution"),
                   protected: bool = Config("korp.protected"),
                   korp_modes: list = Config("korp.modes")):
    """Create CWB .info file for scrambled corpus."""
    create_info_file(sentences, firstdate, lastdate, resolution, protected, korp_modes, out)


def create_info_file(sentences: AnnotationCommonData, firstdate: AnnotationCommonData, lastdate: AnnotationCommonData,
                     resolution: AnnotationCommonData, protected: bool, korp_modes: list,
                     out: Export):
    """Create .info file."""
    content = []
    protected_str = str(protected).lower()

    for key, value_obj in [("Sentences", sentences),
                           ("FirstDate", firstdate),
                           ("LastDate", lastdate),
                           ("DateResolution", resolution),
                           ("Updated", time.strftime("%Y-%m-%d")),
                           ("Protected", protected_str),
                           ("KorpModes", ",".join(korp_modes))]:
        if isinstance(value_obj, AnnotationCommonData):
            value = value_obj.read()
        else:
            value = value_obj

        content.append("%s: %s\n" % (key, value))

    # Write .info file
    with open(out, "w", encoding="utf-8") as o:
        o.writelines(content)

    logger.info("Exported: %s", out)


@annotator("datefirst and datelast files for .info", order=1)
def info_date(source_files: AllSourceFilenames = AllSourceFilenames(),
              out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst"),
              out_datelast: OutputCommonData = OutputCommonData("cwb.datelast"),
              datefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.datefrom"),
              dateto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.dateto"),
              timefrom: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.timefrom"),
              timeto: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[dateformat.out_annotation]:dateformat.timeto")):
    """Create datefirst and datelast file (needed for .info file)."""
    first_date = None
    last_date = None

    for file in source_files:
        from_dates = sorted((int(x[0]), x[1]) for x in datefrom.read_attributes(file, (datefrom, timefrom)) if x[0])
        if from_dates and (first_date is None or from_dates[0] < first_date):
            first_date = from_dates[0]
        to_dates = sorted((int(x[0]), x[1]) for x in dateto.read_attributes(file, (dateto, timeto)) if x[0])
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
def info_date_unknown(out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst"),
                      out_datelast: OutputCommonData = OutputCommonData("cwb.datelast")):
    """Create empty datefirst and datelast file (needed for .info file) if corpus has no date information."""
    logger.info("No date information found in corpus")

    # Write datefirst and datelast files
    out_datefirst.write("")
    out_datelast.write("")
