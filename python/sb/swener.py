# -*- coding: utf-8 -*-

import util
import xml.etree.cElementTree as etree

SENT_SEP = "\n"
TOK_SEP = " "
TAG_SEP = ":"

def tag_ne(out_ne_ex, out_ne_type, out_ne_subtype, word, sentence, encoding=util.UTF8):
    """Tag named entities using HFST-SweNER.
    - out_ne_ex, out_ne_type and out_ne_subtype are resulting annotation files for the named entities
    - word and sentence are existing annotation files for wordforms and sentences
    """

    # collect all text
    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    word_file = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(word_file[tokid] for tokid in sent)
                          for sent in sentences)

    # perform NE recognition on every sentence
    stdout, _ = util.system.call_binary("runNer-pm", [], stdin, encoding=encoding, verbose=True)
    out_ex_dict = {}
    out_type_dict = {}
    out_subtype_dict = {}
    
    # loop through the NE-tagged sentences and parse each one with ElemenTree
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        xml_sent = "<sroot>" + tagged_sent + "</sroot>"
        root = etree.fromstring(xml_sent.encode(encoding))
        
        # init token counter; needed to get start_id and end_id
        i = 0  
        
        for child in root.iter():
            start_id = util.edgeStart(sent[i])

            # if current child has text, increase token counter
            if child.text:
                i += len(child.text.strip().split(TOK_SEP))
                
                # extract NE tags and save them in dictionaries
                if child.tag != "sroot":
                    end_id = util.edgeEnd(sent[i-1])
                    edge = util.mkEdge('ne', [start_id, end_id])
                    out_ex_dict[edge] = child.tag
                    out_type_dict[edge] = child.get("TYPE")
                    out_subtype_dict[edge] = child.get("SBT")
                    # out_ex_dict[edge] = TAG_SEP.join([tag, child.get("TYPE"), child.get("SBT")])

            # if current child has text in the tail, increase token counter
            if child.tail and child.tail.strip():
                i += len(child.tail.strip().split(TOK_SEP))

    # write annotations
    util.write_annotation(out_ne_ex, out_ex_dict)
    util.write_annotation(out_ne_type, out_type_dict)
    util.write_annotation(out_ne_subtype, out_subtype_dict)


if __name__ == '__main__':
    util.run.main(tag_ne)
