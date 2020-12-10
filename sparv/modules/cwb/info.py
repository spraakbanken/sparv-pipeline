"""Create or edit .info file."""

import logging
import os
import time
from datetime import datetime

import sparv.util as util
from sparv import (AllDocuments, Config, Corpus, Export, ExportInput, annotator, exporter,
                   AnnotationAllDocs, OutputCommonData, AnnotationCommonData)

log = logging.getLogger(__name__)


@exporter("CWB .info file")
def info(out: Export = Export("[cwb.cwb_datadir]/[metadata.id]/.info", absolute_path=True),
         sentences: AnnotationCommonData = AnnotationCommonData("misc.<sentence>_count"),
         firstdate: AnnotationCommonData = AnnotationCommonData("cwb.datefirst"),
         lastdate: AnnotationCommonData = AnnotationCommonData("cwb.datelast"),
         resolution: AnnotationCommonData = AnnotationCommonData("dateformat.resolution"),
         protected: bool = Config("korp.protected")):
    """Save information to the file specified by 'out'."""
    content = []
    protected_str = str(protected).lower()

    for key, value_obj in [("Sentences", sentences),
                           ("FirstDate", firstdate),
                           ("LastDate", lastdate),
                           ("DateResolution", resolution),
                           ("Updated", time.strftime("%Y-%m-%d")),
                           ("Protected", protected_str)]:
        if isinstance(value_obj, AnnotationCommonData):
            value = value_obj.read()
        else:
            value = value_obj

        content.append("%s: %s\n" % (key, value))

    # Write .info file
    with open(out, "w") as o:
        o.writelines(content)

    log.info("Exported: %s", out)


@annotator("datefirst and datelast files for .info", order=1)
def info_date(docs: AllDocuments = AllDocuments(),
              out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst"),
              out_datelast: OutputCommonData = OutputCommonData("cwb.datelast"),
              datefrom: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.datefrom"),
              dateto: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.dateto"),
              timefrom: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.timefrom"),
              timeto: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.timeto")):
    """Create datefirst and datelast file (needed for .info file)."""
    first_date = None
    last_date = None

    for doc in docs:
        from_dates = sorted((int(x[0]), x[1]) for x in datefrom.read_attributes(doc, (datefrom, timefrom)))
        if first_date is None or from_dates[0] < first_date:
            first_date = from_dates[0]
        to_dates = sorted((int(x[0]), x[1]) for x in dateto.read_attributes(doc, (dateto, timeto)))
        if last_date is None or to_dates[-1] > last_date:
            last_date = to_dates[-1]

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
    log.info("No date information found in corpus")

    # Write datefirst and datelast files
    out_datefirst.write("")
    out_datelast.write("")
