"""Part of Speech annotation using Hunpos."""

import re

import sparv.util as util
from sparv import Annotation, Document, Model, Output, annotator

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1


@annotator("Part-of-speech annotation with morphological descriptions", language=["swe"])
def msdtag(doc: str = Document,
           model: str = Model("hunpos/hunpos.suc3.suc-tags.default-setting.utf8.model"),
           out: str = Output("<token>:hunpos.msd", cls="token:msd", description="Part-of-speeches with morphological descriptions"),
           word: str = Annotation("<token:word>"),
           sentence: str = Annotation("<sentence>"),
           tag_mapping=None,
           morphtable: str = Model("hunpos/hunpos.saldo.suc-tags.morphtable"),
           patterns: str = Model("hunpos/hunpos.suc.patterns"),
           encoding: str = util.UTF8):
    """POS/MSD tag using the Hunpos tagger."""
    if isinstance(tag_mapping, str) and tag_mapping:
        tag_mapping = util.tagsets.__dict__[tag_mapping]
    elif tag_mapping is None or tag_mapping == "":
        tag_mapping = {}

    pattern_list = []

    if patterns:
        with open(patterns, mode="r", encoding="utf-8") as pat:
            for line in pat:
                if line.strip() and not line.startswith("#"):
                    name, pattern, tags = line.strip().split("\t", 2)
                    pattern_list.append((name, re.compile("^%s$" % pattern), tags))

    def replace_word(w):
        """Replace word with alias if word matches a regex pattern."""
        for p in pattern_list:
            if re.match(p[1], w):
                return "[[%s]]" % p[0]
        return w

    sentences, _orphans = util.parent.get_children(doc, sentence, word)
    token_word = list(util.read_annotation(doc, word))
    stdin = SENT_SEP.join(TOK_SEP.join(replace_word(token_word[token_index]) for token_index in sent)
                          for sent in sentences)
    args = [model]
    if morphtable:
        args.extend(["-m", morphtable])
    stdout, _ = util.system.call_binary("hunpos-tag", args, stdin, encoding=encoding)

    out_annotation = util.create_empty_attribute(doc, word)
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_index, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            tag = tag_mapping.get(tag, tag)
            out_annotation[token_index] = tag

    util.write_annotation(doc, out, out_annotation)


@annotator("Extract POS from MSD", language=["swe"])
def postag(doc: str = Document,
           out: str = Output("<token>:hunpos.pos", cls="token:pos", description="Part-of-speech tags"),
           msd: str = Annotation("<token>:hunpos.msd")):
    """Extract POS from MSD."""
    from sparv.modules.misc import misc
    misc.select(doc, out, msd, index=0, separator=".")
