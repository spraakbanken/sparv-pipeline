"""Create or edit .info file."""

import logging
import time
from datetime import datetime

import sparv.util as util
from sparv import AllDocuments, Annotation, Config, Corpus, Export, ExportInput, Output, annotator, exporter
from sparv.core import paths

log = logging.getLogger(__name__)


@exporter("CWB .info file")
def info(out: str = Export("[cwb.cwb_datadir]/[id]/.info", absolute_path=True),
         sentences: str = Annotation("cwb.sentencecount", data=True, common=True),
         firstdate: str = Annotation("cwb.datefirst", data=True, common=True),
         lastdate: str = Annotation("cwb.datelast", data=True, common=True),
         protected: bool = Config("korp.protected", False)):
    """Save information to the file specified by 'out'."""
    content = []
    protected = str(util.strtobool(protected)).lower()

    for key, value_obj, is_annotation in [("Sentences", sentences, True),
                                          ("FirstDate", firstdate, True),
                                          ("LastDate", lastdate, True),
                                          ("Updated", time.strftime("%Y-%m-%d"), False),
                                          ("Protected", protected, False)]:
        if is_annotation:
            value = util.read_common_data(value_obj)
        else:
            value = value_obj

        content.append("%s: %s\n" % (key, value))

    # Write .info file
    with open(out, "w") as o:
        o.writelines(content)

    log.info("Exported: %s", out)


@annotator("sentencecount file for .info")
def info_sentences(out: str = Output("cwb.sentencecount", data=True, common=True),
                   sentence: str = Annotation("<sentence>", all_docs=True),
                   docs: list = AllDocuments):
    """Determine how many sentences there are in the corpus."""
    # Read sentence annotation and count the sentences
    sentence_count = 0
    for doc in docs:
        try:
            sentence_count += len(list(util.read_annotation_spans(doc, sentence)))
        except FileNotFoundError:
            pass

    if sentence_count == 0:
        log.info("No sentence information found in corpus")

    # Write sentencecount data
    util.write_common_data(out, str(sentence_count))
    log.info("Wrote: %s", out)


@annotator("datefirst and datelast files for .info")
def info_date(corpus: str = Corpus,
              out_datefirst: str = Output("cwb.datefirst", data=True, common=True),
              out_datelast: str = Output("cwb.datelast", data=True, common=True),
              corpus_data_file: str = ExportInput("[cwb.corpus_registry]/[id]"),
              datefrom: str = Annotation("[dateformat.out_annotation=<text>]:dateformat.datefrom", all_docs=True),
              dateto: str = Annotation("[dateformat.out_annotation=<text>]:dateformat.dateto", all_docs=True),
              timefrom: str = Annotation("[dateformat.out_annotation=<text>]:dateformat.timefrom", all_docs=True),
              timeto: str = Annotation("[dateformat.out_annotation=<text>]:dateformat.timeto", all_docs=True),
              remove_namespaces: bool = Config("remove_export_namespaces", False),
              registry: str = Config("cwb.corpus_registry")):
    """Create datefirst and datelast file (needed for .info file)."""
    def _fix_name(name: str):
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

    # Get datefrom and timefrom annotation names
    datefrom = _fix_name(datefrom)
    timefrom = _fix_name(timefrom)
    dateto = _fix_name(dateto)
    timeto = _fix_name(timeto)

    # Get datefirst and write to file
    datefirst_args = ["-r", registry, "-q", corpus, datefrom, timefrom]
    datefirst_out, _ = util.system.call_binary("cwb-scan-corpus", datefirst_args)
    datefirst = _parse_cwb_output(datefirst_out)[0]
    util.write_common_data(out_datefirst, str(datefirst))
    log.info("Wrote: %s", out_datefirst)

    # Get datelast and write to file
    datelast_args = ["-r", registry, "-q", corpus, dateto, timeto]
    datelast_out, _ = util.system.call_binary("cwb-scan-corpus", datelast_args)
    datelast = _parse_cwb_output(datelast_out)[-1]
    util.write_common_data(out_datelast, str(datelast))
    log.info("Wrote: %s", out_datelast)


# TODO: This rule should activate if the above info_date cannot be run (due to lacking date info in corpus)
# @exporter("empty datefirst and datelast files for .info", ruleorder=1)
# def info_date_unknown(out_datefirst: str = Export("info/datefirst"),
#                       out_datelast: str = Export("info/datelast")):
#     """Create empty datefirst and datelast file (needed for .info file) if corpus has no date information."""
#     log.info("No date information found in corpus")

#     # Write datefirst file
#     with open(out_datefirst, "w") as f:
#         f.write("")
#     log.info("Exported: %s", out_datefirst)

#     # Write datelast file
#     with open(out_datelast, "w") as f:
#         f.write("")
#     log.info("Exported: %s", out_datelast)
