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
         sentences: AnnotationCommonData = AnnotationCommonData("cwb.sentencecount"),
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


@annotator("sentencecount file for .info")
def info_sentences(out: OutputCommonData = OutputCommonData("cwb.sentencecount"),
                   sentence: AnnotationAllDocs = AnnotationAllDocs("<sentence>"),
                   docs: AllDocuments = AllDocuments()):
    """Determine how many sentences there are in the corpus."""
    # Read sentence annotation and count the sentences
    sentence_count = 0
    for doc in docs:
        try:
            sentence_count += len(list(sentence.read_spans(doc)))
        except FileNotFoundError:
            pass

    if sentence_count == 0:
        log.info("No sentence information found in corpus")

    # Write sentencecount data
    out.write(str(sentence_count))


@annotator("datefirst and datelast files for .info", order=1)
def info_date(corpus: Corpus = Corpus(),
              out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst"),
              out_datelast: OutputCommonData = OutputCommonData("cwb.datelast"),
              corpus_data_file: ExportInput = ExportInput("[cwb.corpus_registry]/[metadata.id]"),
              datefrom: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.datefrom"),
              dateto: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.dateto"),
              timefrom: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.timefrom"),
              timeto: AnnotationAllDocs = AnnotationAllDocs("[dateformat.out_annotation]:dateformat.timeto"),
              remove_namespaces: bool = Config("export.remove_module_namespaces", False),
              cwb_bin_path: Config = Config("cwb.bin_path", ""),
              registry: str = Config("cwb.corpus_registry")):
    """Create datefirst and datelast file (needed for .info file)."""
    def fix_name(name: str):
        """Remove invalid characters from annotation names and optionally remove namespaces."""
        if remove_namespaces:
            prefix, part, suffix = name.partition(":")
            suffix = suffix.split(".")[-1]
            name = prefix + part + suffix
        return name.replace(":", "_")

    def _parse_cwb_output(output):
        lines = output.decode("utf8").split("\n")
        values = ["%s %s" % (line.split("\t")[1], line.split("\t")[2]) for line in lines if line.split("\t")[-1]]
        # Fix dates with less than 8 digits (e.g. 800 --> 0800), needed by strptime
        values = ["%s %s" % (v.split()[0].zfill(8), v.split()[1]) for v in values]
        # Convert to dates and sort, then convert to human readable format
        values = sorted([datetime.strptime(v, "%Y%m%d %H%M%S") for v in values])
        return [v.strftime("%Y-%m-%d %H:%M:%S") for v in values]

    # Get date and time annotation names
    datefrom_name = fix_name(datefrom.name)
    timefrom_name = fix_name(timefrom.name)
    dateto_name = fix_name(dateto.name)
    timeto_name = fix_name(timeto.name)

    # Get datefirst and write to file
    datefirst_args = ["-r", registry, "-q", corpus, datefrom_name, timefrom_name]
    datefirst_out, _ = util.system.call_binary(os.path.join(cwb_bin_path, "cwb-scan-corpus"), datefirst_args)
    datefirst = _parse_cwb_output(datefirst_out)[0]
    out_datefirst.write(str(datefirst))

    # Get datelast and write to file
    datelast_args = ["-r", registry, "-q", corpus, dateto_name, timeto_name]
    datelast_out, _ = util.system.call_binary(os.path.join(cwb_bin_path, "cwb-scan-corpus"), datelast_args)
    datelast = _parse_cwb_output(datelast_out)[-1]
    out_datelast.write(str(datelast))


@annotator("Empty datefirst and datelast files for .info", order=2)
def info_date_unknown(out_datefirst: OutputCommonData = OutputCommonData("cwb.datefirst"),
                      out_datelast: OutputCommonData = OutputCommonData("cwb.datelast")):
    """Create empty datefirst and datelast file (needed for .info file) if corpus has no date information."""
    log.info("No date information found in corpus")

    # Write datefirst and datelast files
    out_datefirst.write("")
    out_datelast.write("")
