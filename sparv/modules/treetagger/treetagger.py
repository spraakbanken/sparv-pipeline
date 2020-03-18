"""Process tokens with treetagger."""
import sparv.util as util

SENT_SEP = "\n<eos>\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1
LEM_COLUMN = 2


def tt_proc(doc, model, tt_binary, out_pos, out_msd, out_lemma, word, sentence, lang, encoding=util.UTF8):
    """POS/MSD tag and lemmatize using the TreeTagger.

    - model is the binary TreeTagger model file
    - tt_binary provides the path to the TreeTagger executable
    - out_pos, out_msd and out_lem are the resulting annotation files
    - word and sentence are existing annotation files
    - lang is the two-letter language code of the language to be analyzed
    """
    sentences, orphans = util.get_children(doc, sentence, word)
    word_annotation = list(util.read_annotation(doc, word))
    stdin = SENT_SEP.join(TOK_SEP.join(word_annotation[token_index] for token_index in sent)
                          for sent in sentences)
    args = ["-token", "-lemma", "-cap-heuristics", "-no-unknown", "-eos-tag", "<eos>", model]

    stdout, _ = util.system.call_binary(tt_binary, args, stdin, encoding=encoding, verbose=True)

    # Write pos and msd annotations.
    out_pos_annotation = util.create_empty_attribute(doc, word_annotation)
    out_msd_annotation = util.create_empty_attribute(doc, word_annotation)
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            out_msd_annotation[token_id] = tag
            out_pos_annotation[token_id] = util.msd_to_pos.convert(tag, lang)
    util.write_annotation(doc, out_msd, out_msd_annotation)
    util.write_annotation(doc, out_pos, out_pos_annotation)

    # Write lemma annotations.
    out_lemma_annotation = util.create_empty_attribute(doc, word_annotation)
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            lem = tagged_token.strip().split(TAG_SEP)[LEM_COLUMN]
            out_lemma_annotation[token_id] = lem
    util.write_annotation(doc, out_lemma, out_lemma_annotation)

if __name__ == '__main__':
    util.run.main(tt_proc)
