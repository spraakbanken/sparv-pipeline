"""Named entity tagging with SweNER."""

import re
import xml.etree.ElementTree as etree
import xml.sax.saxutils

from sparv.api import Annotation, Binary, Config, Output, SparvErrorMessage, annotator, get_logger, util

logger = get_logger(__name__)

RESTART_THRESHOLD_LENGTH = 64000
SENT_SEP = "\n"
TOK_SEP = " "


@annotator("Named entity tagging with SweNER", language=["swe"],
           config=[Config("swener.binary", default="hfst-swener", description="SweNER executable")])
def annotate(out_ne: Output = Output("swener.ne", cls="named_entity", description="Named entity segments from SweNER"),
             out_ne_ex: Output = Output("swener.ne:swener.ex", description="Named entity expressions from SweNER"),
             out_ne_type: Output = Output("swener.ne:swener.type", cls="named_entity:type",
                                          description="Named entity types from SweNER"),
             out_ne_subtype: Output = Output("swener.ne:swener.subtype", cls="named_entity:subtype",
                                             description="Named entity sub types from SweNER"),
             out_ne_name: Output = Output("swener.ne:swener.name", cls="named_entity:name",
                                          description="Names in SweNER named entities"),
             word: Annotation = Annotation("<token:word>"),
             sentence: Annotation = Annotation("<sentence>"),
             token: Annotation = Annotation("<token>"),
             binary: Binary = Binary("[swener.binary]"),
             process_dict=None):
    """Tag named entities using HFST-SweNER.

    SweNER is either run in an already started process defined in
    process_dict, or a new process is started(default)
    - word, sentence, token: existing annotations
    - out_ne_ex, out_ne_type, out_ne_subtype: resulting annotation files for the named entities
    - process_dict is used in the catapult and should never be set from the command line
    """
    # if process_dict is None:
    process = swenerstart(binary, "", util.constants.UTF8, verbose=False)
    # else:
    #     process = process_dict["process"]
    #     # If process seems dead, spawn a new one
    #     if process.stdin.closed or process.stdout.closed or process.poll():
    #         util.system.kill_process(process)
    #         process = swenerstart("", encoding, verbose=False)
    #         process_dict["process"] = process

    # Get sentence annotation
    sentences, _orphans = sentence.get_children(token, orphan_alert=True)

    # Collect all text
    word_annotation = list(word.read())
    stdin = SENT_SEP.join(TOK_SEP.join(word_annotation[token_index] for token_index in sent)
                          for sent in sentences)
    # Escape <, > and &
    stdin = xml.sax.saxutils.escape(stdin)

    # keep_process = len(stdin) < RESTART_THRESHOLD_LENGTH and process_dict is not None
    # logger.info("Stdin length: %s, keep process: %s", len(stdin), keep_process)

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
    # logger.info("STDIN %s %s", type(stdin.encode(encoding)), stdin.encode(encoding))
    stdout, stderr = process.communicate(stdin.encode(util.constants.UTF8))
    if process.returncode > 0:
        raise SparvErrorMessage(f"An error occurred while running HFST-SweNER:\n\n{stderr.decode()}")
    # logger.info("STDOUT %s %s", type(stdout.decode(encoding)), stdout.decode(encoding))

    parse_swener_output(sentences, token, stdout.decode(util.constants.UTF8), out_ne, out_ne_ex, out_ne_type,
                        out_ne_subtype, out_ne_name)


def parse_swener_output(sentences: list, token: Annotation, output, out_ne: Output, out_ne_ex: Output,
                        out_ne_type: Output, out_ne_subtype: Output, out_ne_name: Output):
    """Parse the SweNER output and write annotation files."""
    out_ne_spans = []
    out_ex = []
    out_type = []
    out_subtype = []
    out_name = []

    token_spans = list(token.read_spans())

    # Loop through the NE-tagged sentences and parse each one with ElemenTree
    for sent, tagged_sent in zip(sentences, output.strip().split(SENT_SEP)):
        xml_sent = "<sroot>" + tagged_sent + "</sroot>"

        # Filter out tags on the format <EnamexXxxXxx> since they seem to always overlap with <ENAMEX> elements,
        # making the XML invalid.
        xml_sent = re.sub(r"</?Enamex[^>\s]+>", "", xml_sent)
        try:
            root = etree.fromstring(xml_sent)
        except:
            logger.warning("Error parsing sentence. Skipping.")
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
                            # logger.warning("Overlapping NE elements found; discarding one.")
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
                            # logger.warning("Split token returned by name tagger.")

                # If current child has text in the tail, increase token counter
                if child.tail and child.tail.strip():
                    i += len(child.tail.strip().split(TOK_SEP))

                if (child.tag == "sroot" and child.text and not child.text[-1] == " ") or (
                        child.tail and not child.tail[-1] == " "):
                    # The next NE would start in the middle of a token, so decrease the counter by 1
                    i -= 1
        except IndexError:
            logger.warning("Error parsing sentence. Skipping.")
            continue

    # Write annotations
    out_ne.write(out_ne_spans)
    out_ne_ex.write(out_ex)
    out_ne_type.write(out_type)
    out_ne_subtype.write(out_subtype)
    out_ne_name.write(out_name)


def swenerstart(binary, stdin, encoding, verbose):
    """Start a SweNER process and return it."""
    return util.system.call_binary(binary, [], stdin, encoding=encoding, verbose=verbose, return_command=True)
