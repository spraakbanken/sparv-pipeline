"""Part of Speech annotation using Hunpos."""

import re

import sparv.util as util
from sparv import Annotation, Binary, Config, Model, ModelOutput, Output, annotator, modelbuilder

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1


@annotator("Part-of-speech annotation with morphological descriptions", language=["swe"], config=[
           Config("hunpos.binary", default="hunpos-tag"),
           Config("hunpos.model", default="hunpos/suc3_suc-tags_default-setting_utf8.model"),
           Config("hunpos.morphtable", default="hunpos/saldo_suc-tags.morphtable"),
           Config("hunpos.patterns", default="hunpos/suc.patterns")
           ])
def msdtag(out: Output = Output("<token>:hunpos.msd", cls="token:msd",
                                description="Part-of-speeches with morphological descriptions"),
           word: Annotation = Annotation("<token:word>"),
           sentence: Annotation = Annotation("<sentence>"),
           binary: Binary = Binary("[hunpos.binary]"),
           model: Model = Model("[hunpos.model]"),
           morphtable: Model = Model("[hunpos.morphtable]"),
           patterns: Model = Model("[hunpos.patterns]"),
           tag_mapping=None,
           encoding: str = util.UTF8):
    """POS/MSD tag using the Hunpos tagger."""
    if isinstance(tag_mapping, str) and tag_mapping:
        tag_mapping = util.tagsets.__dict__[tag_mapping]
    elif tag_mapping is None or tag_mapping == "":
        tag_mapping = {}

    pattern_list = []

    if patterns:
        with open(patterns.path, encoding="utf-8") as pat:
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

    sentences, _orphans = sentence.get_children(word)
    token_word = list(word.read())
    stdin = SENT_SEP.join(TOK_SEP.join(replace_word(token_word[token_index]) for token_index in sent)
                          for sent in sentences)
    args = [model.path]
    if morphtable:
        args.extend(["-m", morphtable.path])
    stdout, _ = util.system.call_binary(binary, args, stdin, encoding=encoding)

    out_annotation = word.create_empty_attribute()
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_index, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            tag = tag_mapping.get(tag, tag)
            out_annotation[token_index] = tag

    out.write(out_annotation)


@annotator("Extract POS from MSD", language=["swe"])
def postag(out: Output = Output("<token>:hunpos.pos", cls="token:pos", description="Part-of-speech tags"),
           msd: Annotation = Annotation("<token>:hunpos.msd")):
    """Extract POS from MSD."""
    from sparv.modules.misc import misc
    misc.select(out, msd, index=0, separator=".")


@annotator("Convert hunpos SUC tags to UPOS", language=["swe"])
def upostag(out: Output = Output("<token>:hunpos.upos", cls="token:upos", description="Part-of-speeches in UD"),
            pos: Annotation = Annotation("<token>:hunpos.pos")):
    """Convert hunpos SUC tags to UPOS."""
    pos_tags = pos.read()
    out_annotation = []

    for tag in pos_tags:
        out_annotation.append(util.convert_to_upos(tag, "swe", "SUC"))

    out.write(out_annotation)


@modelbuilder("Hunpos model", language=["swe"])
def hunpos_model(model: ModelOutput = ModelOutput("hunpos/suc3_suc-tags_default-setting_utf8.model")):
    """Download the Hunpos model."""
    model.download(
        "https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_suc-tags_default-setting_utf8.model")
