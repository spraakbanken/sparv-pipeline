# -*- coding: utf-8 -*-
import re
import xml.sax.saxutils
import xml.etree.cElementTree as etree
import sparv.util as util

RESTART_THRESHOLD_LENGTH = 64000
SENT_SEP = "\n"
TOK_SEP = " "


def tag_ne(out_ne_ex, out_ne_type, out_ne_subtype, out_ne_name, word, sentence, encoding=util.UTF8, process_dict=None):
    """
    Tag named entities using HFST-SweNER.
    SweNER is either run in an already started process defined in
    process_dict, or a new process is started(default)
    - out_ne_ex, out_ne_type and out_ne_subtype are resulting annotation files for the named entities
    - word and sentence are existing annotation files for wordforms and sentences
    - process_dict should never be set from the command line
    """

    if process_dict is None:
        process = swenerstart("", encoding, verbose=False)
    # else:
    #     process = process_dict['process']
    #     # If process seems dead, spawn a new one
    #     if process.stdin.closed or process.stdout.closed or process.poll():
    #         util.system.kill_process(process)
    #         process = swenerstart("", encoding, verbose=False)
    #         process_dict['process'] = process

    # Collect all text
    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    word_file = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(word_file[tokid] for tokid in sent)
                          for sent in sentences)
    # Escape <, > and &
    stdin = xml.sax.saxutils.escape(stdin)

    # keep_process = len(stdin) < RESTART_THRESHOLD_LENGTH and process_dict is not None
    # util.log.info("Stdin length: %s, keep process: %s", len(stdin), keep_process)

    # if process_dict is not None:
    #     process_dict['restart'] = not keep_process

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
    stdout, _ = process.communicate(stdin.encode(encoding))
    # util.log.info("STDOUT %s %s", type(stdout.decode(encoding)), stdout.decode(encoding))

    parse_swener_output(sentences, stdout.decode(encoding), out_ne_ex, out_ne_type, out_ne_subtype, out_ne_name)


def parse_swener_output(sentences, output, out_ne_ex, out_ne_type, out_ne_subtype, out_ne_name):
    """Parse the SweNER output and write annotation files."""

    out_ex_dict = {}
    out_type_dict = {}
    out_subtype_dict = {}
    out_name_dict = {}

    # Loop through the NE-tagged sentences and parse each one with ElemenTree
    for sent, tagged_sent in zip(sentences, output.strip().split(SENT_SEP)):
        xml_sent = "<sroot>" + tagged_sent + "</sroot>"

        # Filter out tags on the format <EnamexXxxXxx> since they seem to always overlap with <ENAMEX> elements,
        # making the XML invalid.
        xml_sent = re.sub(r'</?Enamex[^>\s]+>', '', xml_sent)
        try:
            root = etree.fromstring(xml_sent)
        except:
            util.log.warning("Error parsing sentence. Skipping.")
            continue

        # Init token counter; needed to get start_id and end_id
        i = 0
        previous_end = 0
        children = list(root.iter())

        try:

            for count, child in enumerate(children):
                start_id = util.edgeStart(sent[i])
                start_i = i

                # If current child has text, increase token counter
                if child.text:
                    i += len(child.text.strip().split(TOK_SEP))

                    # Extract NE tags and save them in dictionaries
                    if child.tag != "sroot":
                        if start_i < previous_end:
                            pass
                            # util.log.warning("Overlapping NE elements found; discarding one.")
                        else:
                            end_id = util.edgeEnd(sent[i - 1])
                            previous_end = i
                            edge = util.mkEdge('ne', [start_id, end_id])
                            out_ex_dict[edge] = child.tag
                            out_type_dict[edge] = child.get("TYPE")
                            out_subtype_dict[edge] = child.get("SBT")
                            out_name_dict[edge] = child.text

                        # If this child has a tail and it doesn't start with a space, or if it has no tail at all despite not being the last child,
                        # it means this NE ends in the middle of a token.
                        if (child.tail and child.tail.strip() and not child.tail[0] == " ") or (not child.tail and count < len(children) - 1):
                            i -= 1
                            # util.log.warning("Split token returned by name tagger.")

                # If current child has text in the tail, increase token counter
                if child.tail and child.tail.strip():
                    i += len(child.tail.strip().split(TOK_SEP))

                if (child.tag == "sroot" and child.text and not child.text[-1] == " ") or (child.tail and not child.tail[-1] == " "):
                    # The next NE would start in the middle of a token, so decrease the counter by 1
                    i -= 1
        except IndexError:
            util.log.warning("Error parsing sentence. Skipping.")
            continue

    # Write annotations
    util.write_annotation(out_ne_ex, out_ex_dict)
    util.write_annotation(out_ne_type, out_type_dict)
    util.write_annotation(out_ne_subtype, out_subtype_dict)
    util.write_annotation(out_ne_name, out_name_dict)


def swenerstart(stdin, encoding, verbose):
    """Start a SweNER process and return it."""
    return util.system.call_binary("hfst-swener", [], stdin, encoding=encoding, verbose=verbose, return_command=True)


if __name__ == '__main__':
    util.run.main(tag_ne)
