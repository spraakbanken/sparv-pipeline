# -*- coding: utf-8 -*-
import sparv.util as util

SENT_SEP = "\n<eos>\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1
LEM_COLUMN = 2


def tt_proc(model, tt_binary, out_pos, out_msd, out_lem, word, sentence, lang, encoding=util.UTF8):
    """POS/MSD tag and lemmatize using the TreeTagger.
    - model is the binary TreeTagger model file
    - tt_binary provides the path to the TreeTagger executable
    - out_pos, out_msd and out_lem are the resulting annotation files
    - word and sentence are existing annotation files
    - lang is the two-letter language code of the language to be analyzed
    """

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(WORD[tokid] for tokid in sent)
                          for sent in sentences)
    args = ["-token", "-lemma", "-cap-heuristics", "-no-unknown", "-eos-tag", "<eos>", model]

    stdout, _ = util.system.call_binary(tt_binary, args, stdin, encoding=encoding, verbose=True)

    # Write pos and msd annotations.
    OUT_POS = {}
    OUT_MSD = {}
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            OUT_MSD[token_id] = tag
            OUT_POS[token_id] = util.msd_to_pos.convert(tag, lang)
    util.write_annotation(out_msd, OUT_MSD)
    util.write_annotation(out_pos, OUT_POS)

    # Write lemma annotations.
    OUT_LEM = {}
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            lem = tagged_token.strip().split(TAG_SEP)[LEM_COLUMN]
            OUT_LEM[token_id] = lem
    util.write_annotation(out_lem, OUT_LEM)

if __name__ == '__main__':
    util.run.main(tt_proc)
