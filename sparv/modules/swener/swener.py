"""Named entity tagging with SweNER."""

import re
import xml.etree.ElementTree as etree
import xml.sax.saxutils

import sparv.util as util
from sparv import Annotation, Document, Output, annotator

RESTART_THRESHOLD_LENGTH = 64000
SENT_SEP = "\n"
TOK_SEP = " "


@annotator("Named entity tagging with SweNER")
def annotate(doc: str = Document,
             out_ne: str = Output("swener.ne", cls="named_entity", description="Named entity segments from SweNER"),
             out_ne_ex: str = Output("swener.ne:swener.ex", description="Named entity expressions from from SweNER"),
             out_ne_type: str = Output("swener.ne:swener.type", description="Named entity types from from SweNER"),
             out_ne_subtype: str = Output("swener.ne:swener.subtype", description="Named entity sub types from from SweNER"),
             out_ne_name: str = Output("swener.ne:swener.name", description="Names in SweNER named entities"),
             word: str = Annotation("<token:word>"),
             sentence: str = Annotation("<sentence>"),
             token: str = Annotation("<token>"),
             process_dict=None):
    """Tag named entities using HFST-SweNER.

    SweNER is either run in an already started process defined in
    process_dict, or a new process is started(default)
    - doc, word, sentence, token: existing annotations
    - out_ne_ex, out_ne_type, out_ne_subtype: resulting annotation files for the named entities
    - process_dict is used in the catapult and should never be set from the command line
    """
    if process_dict is None:
        process = swenerstart("", util.UTF8, verbose=False)
    # else:
    #     process = process_dict["process"]
    #     # If process seems dead, spawn a new one
    #     if process.stdin.closed or process.stdout.closed or process.poll():
    #         util.system.kill_process(process)
    #         process = swenerstart("", encoding, verbose=False)
    #         process_dict["process"] = process

    # Get sentence annotation
    sentences, _orphans = util.get_children(doc, sentence, token, orphan_alert=True)

    # Collect all text
    word_annotation = list(util.read_annotation(doc, word))
    stdin = SENT_SEP.join(TOK_SEP.join(word_annotation[token_index] for token_index in sent)
                          for sent in sentences)
    # Escape <, > and &
    stdin = xml.sax.saxutils.escape(stdin)

    # keep_process = len(stdin) < RESTART_THRESHOLD_LENGTH and process_dict is not None
    # util.log.info("Stdin length: %s, keep process: %s", len(stdin), keep_process)

    # if process_dict is not None:
    #     process_dict["restart"] = not keep_process

    # # Does not work as of now since swener does not have an interactive mode
    # if keep_process:
    #     # Chatting with swener: send a SENT_SEP and read correct number of lines
    #     stdin_fd, stdout_fd = process.stdin, process.stdout
    #     stdin_fd.write(stdin.encode(encoding) + SENT_SEP)
    #     stdin_fd.flush()
    #     stout = stdout_fd.readlines()

    # else:
    # Otherwise use communicate which buffers properly
    # util.log.info("STDIN %s %s", type(stdin.encode(encoding)), stdin.encode(encoding))
    stdout, _ = process.communicate(stdin.encode(util.UTF8))
    # util.log.info("STDOUT %s %s", type(stdout.decode(encoding)), stdout.decode(encoding))

    parse_swener_output(doc, sentences, token, stdout.decode(util.UTF8), out_ne, out_ne_ex, out_ne_type, out_ne_subtype,
                        out_ne_name)


def parse_swener_output(doc, sentences, token, output, out_ne, out_ne_ex, out_ne_type, out_ne_subtype, out_ne_name):
    """Parse the SweNER output and write annotation files."""
    out_ne_spans = []
    out_ex = []
    out_type = []
    out_subtype = []
    out_name = []

    token_spans = list(util.read_annotation_spans(doc, token))

    # Loop through the NE-tagged sentences and parse each one with ElemenTree
    for sent, tagged_sent in zip(sentences, output.strip().split(SENT_SEP)):
        xml_sent = "<sroot>" + tagged_sent + "</sroot>"

        # Filter out tags on the format <EnamexXxxXxx> since they seem to always overlap with <ENAMEX> elements,
        # making the XML invalid.
        xml_sent = re.sub(r"</?Enamex[^>\s]+>", "", xml_sent)
        try:
            root = etree.fromstring(xml_sent)
        except:
            util.log.warning("Error parsing sentence. Skipping.")
            continue

        # Init token counter; needed to get start_pos and end_pos
        i = 0
        previous_end = 0
        children = list(root.iter())

        try:
            for count, child in enumerate(children):
                start_pos = token_spans[sent[i]][0]
                start_i = i

                # If current child has text, increase token counter
                if child.text:
                    i += len(child.text.strip().split(TOK_SEP))

                    # Extract NE tags and save them in lists
                    if child.tag != "sroot":
                        if start_i < previous_end:
                            pass
                            # util.log.warning("Overlapping NE elements found; discarding one.")
                        else:
                            end_pos = token_spans[sent[i - 1]][1]
                            previous_end = i
                            span = (start_pos, end_pos)
                            out_ne_spans.append(span)
                            out_ex.append(child.tag)
                            out_type.append(child.get("TYPE"))
                            out_subtype.append(child.get("SBT"))
                            out_name.append(child.text)

                        # If this child has a tail and it doesn't start with a space, or if it has no tail at all
                        # despite not being the last child, it means this NE ends in the middle of a token.
                        if (child.tail and child.tail.strip() and not child.tail[0] == " ") or (
                                not child.tail and count < len(children) - 1):
                            i -= 1
                            # util.log.warning("Split token returned by name tagger.")

                # If current child has text in the tail, increase token counter
                if child.tail and child.tail.strip():
                    i += len(child.tail.strip().split(TOK_SEP))

                if (child.tag == "sroot" and child.text and not child.text[-1] == " ") or (
                        child.tail and not child.tail[-1] == " "):
                    # The next NE would start in the middle of a token, so decrease the counter by 1
                    i -= 1
        except IndexError:
            util.log.warning("Error parsing sentence. Skipping.")
            continue

    # Write annotations
    util.write_annotation(doc, out_ne, out_ne_spans)
    util.write_annotation(doc, out_ne_ex, out_ex)
    util.write_annotation(doc, out_ne_type, out_type)
    util.write_annotation(doc, out_ne_subtype, out_subtype)
    util.write_annotation(doc, out_ne_name, out_name)


def swenerstart(stdin, encoding, verbose):
    """Start a SweNER process and return it."""
    return util.system.call_binary("hfst-swener", [], stdin, encoding=encoding, verbose=verbose, return_command=True)
