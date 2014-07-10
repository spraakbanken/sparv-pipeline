# -*- coding: utf-8 -*-

import util
import xml.etree.cElementTree as etree

SENT_SEP = "\n"
TOK_SEP = " "
TAG_SEP = ":"
AFFIX = "|"


def tag_NER(out_NER, word, sentence, encoding=util.UTF8):
    """Tag NERs using HFST-SweNER.
    """

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    word_file = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(word_file[tokid] for tokid in sent)
                          for sent in sentences)
    stdout, _ = util.system.call_binary("runNer-pm", [], stdin, encoding=encoding, verbose=True)
    out_dict = {}
    
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        xml_sent = "<sroot>" + tagged_sent + "</sroot>"
        root = etree.fromstring(xml_sent.encode("utf-8"))
        i = 0
        for child in root.getiterator():
            start_id = sent[i].strip('w:').split('-')[0]
            tag = child.tag if not child.tag == "sroot" else ""
            text = child.text.strip() if child.text else None
            if text:
                i += len(text.split(TOK_SEP))
                if tag:
                    end_id = sent[i-1].split('-')[-1]
                    out_dict["ne:" + "-".join([start_id, end_id])] = TAG_SEP.join([tag, child.get("TYPE"), child.get("SBT")])
            tail = child.tail.strip() if child.tail else None
            if tail:
                i += len(tail.strip().split(TOK_SEP))


    util.write_annotation(out_NER, out_dict)


if __name__ == '__main__':
    util.run.main(tag_NER)
