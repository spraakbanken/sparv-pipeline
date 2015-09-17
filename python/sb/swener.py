# -*- coding: utf-8 -*-

import util
import xml.etree.cElementTree as etree

RESTART_THRESHOLD_LENGTH = 64000
SENT_SEP = "\n"
TOK_SEP = " "
TAG_SEP = ":"

def tag_ne(out_ne_ex, out_ne_type, out_ne_subtype, word, sentence, encoding=util.UTF8, process_dict=None):
    """
    Tag named entities using HFST-SweNER.
    SweNER is either run in an already started process defined in
    process_dict, or a new process is started(default)
    - out_ne_ex, out_ne_type and out_ne_subtype are resulting annotation files for the named entities
    - word and sentence are existing annotation files for wordforms and sentences
    - process_dict should never be set from the command line
    """

    if process_dict is None:
        process = swenerstart("", encoding, verbose=True)
    else:
        process = process_dict['process']
        # If process seems dead, spawn a new one
        if process.stdin.closed or process.stdout.closed or process.poll():
            util.system.kill_process(process)
            process = swenerstart("", encoding, verbose=True)
            process_dict['process'] = process

    # Collect all text
    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    word_file = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(word_file[tokid] for tokid in sent)
                          for sent in sentences)

    stdin = stdin.replace("&", "&amp;")
    stdin = stdin.replace(">", "&gt;")
    stdin = stdin.replace("<", "&lt;")
    stdin = stdin.replace("%", "&#37;")


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
    stdout, _ = process.communicate(stdin.encode(encoding))
    
    # # stdout, _ = util.system.call_binary("runNer-pm", [], stdin.encode(encoding), encoding=encoding, verbose=True)
    # # stdout = stdout.encode(encoding)

    parse_swener_output(sentences, stdout, out_ne_ex, out_ne_type, out_ne_subtype)


def parse_swener_output(sentences, output, out_ne_ex, out_ne_type, out_ne_subtype):
    """Parse the SweNER output and write annotation files."""

    out_ex_dict = {}
    out_type_dict = {}
    out_subtype_dict = {}
    
    # Loop through the NE-tagged sentences and parse each one with ElemenTree
    for sent, tagged_sent in zip(sentences, output.strip().split(SENT_SEP)):
        xml_sent = "<sroot>" + tagged_sent + "</sroot>"
        root = etree.fromstring(xml_sent)
        
        # Init token counter; needed to get start_id and end_id
        i = 0  
        
        for child in root.iter():
            start_id = util.edgeStart(sent[i])

            # If current child has text, increase token counter
            if child.text:
                i += len(child.text.strip().split(TOK_SEP))
                
                # Extract NE tags and save them in dictionaries
                if child.tag != "sroot":
                    end_id = util.edgeEnd(sent[i-1])
                    edge = util.mkEdge('ne', [start_id, end_id])
                    out_ex_dict[edge] = child.tag
                    out_type_dict[edge] = child.get("TYPE")
                    out_subtype_dict[edge] = child.get("SBT")
                    # out_ex_dict[edge] = TAG_SEP.join([tag, child.get("TYPE"), child.get("SBT")])
                    
                    # If this child has a tail and it doesn't start with a space, the tagger has split a token in two
                    if child.tail and child.tail.strip() and not child.tail[:1] == " ":
                        i -= 1

            # If current child has text in the tail, increase token counter
            if child.tail and child.tail.strip():
                i += len(child.tail.strip().split(TOK_SEP))

    # Write annotations
    util.write_annotation(out_ne_ex, out_ex_dict)
    util.write_annotation(out_ne_type, out_type_dict)
    util.write_annotation(out_ne_subtype, out_subtype_dict)


def swenerstart(stdin, encoding, verbose):
    """Start a SweNER process and return it."""
    return util.system.call_binary("runNer-pm", [], stdin, encoding=encoding, verbose=verbose, return_command=True)


if __name__ == '__main__':
    util.run.main(tag_ne)
