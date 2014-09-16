# -*- coding: utf-8 -*-

import util.tagsets

SENT_SEP = "\n<eos>\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1
LEM_COLUMN = 2

def tt_proc(model, out_pos, out_lem, word, sentence, tag_mapping=None, encoding=util.UTF8):
    """POS/MSD tag using the TreeTagger.
    """
    if isinstance(tag_mapping, basestring) and tag_mapping:
        tag_mapping = util.tagsets.__dict__[tag_mapping]
    elif tag_mapping is None or tag_mapping == "":
        tag_mapping = {}

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(WORD[tokid] for tokid in sent)
                          for sent in sentences)
    args = ["-token", "-lemma", "-cap-heuristics", "-no-unknown", "-eos-tag", "<eos>", model]

    stdout, _ = util.system.call_binary("tree-tagger", args, stdin, encoding=encoding, verbose=True)

	# Write pos annotations.
    OUT = {}
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            tag = tag_mapping.get(tag, tag)
            OUT[token_id] = tag
    util.write_annotation(out_pos, OUT)

    # Write lemma annotations.
    OUT = {}
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            lem = tagged_token.strip().split(TAG_SEP)[LEM_COLUMN]
            lem = tag_mapping.get(tag, tag)
            OUT[token_id] = lem
    util.write_annotation(out_lem, OUT)

if __name__ == '__main__':
    util.run.main(tt_proc)
