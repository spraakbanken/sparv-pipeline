"""Part of Speech annotation using Hunpos."""

import re
from typing import Optional

from sparv.api import (Annotation, Binary, Config, Model, ModelOutput, Output, SparvErrorMessage, annotator, get_logger,
                       modelbuilder, util)
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1


@annotator("Part-of-speech annotation with morphological descriptions", language=["swe"])
def msdtag(out: Output = Output("<token>:hunpos.msd", cls="token:msd",
                                description="Part-of-speeches with morphological descriptions"),
           word: Annotation = Annotation("<token:word>"),
           sentence: Annotation = Annotation("<sentence>"),
           binary: Binary = Binary("[hunpos.binary]"),
           model: Model = Model("[hunpos.model]"),
           morphtable: Optional[Model] = Model("[hunpos.morphtable]"),
           patterns: Optional[Model] = Model("[hunpos.patterns]"),
           tag_mapping: Optional[str] = Config("hunpos.tag_mapping"),
           encoding: str = Config("hunpos.encoding")):
    """POS/MSD tag modern Swedish texts using the Hunpos tagger."""
    main(out, word, sentence, binary, model, morphtable=morphtable, patterns=patterns, tag_mapping=tag_mapping,
         encoding=encoding)


@annotator("Part-of-speech annotation with morphological descriptions for older Swedish", language=["swe-1800"])
def msdtag_hist(out: Output = Output("<token>:hunpos.msd_hist", cls="token:msd",
                                     description="Part-of-speeches with morphological descriptions"),
                word: Annotation = Annotation("<token:word>"),
                sentence: Annotation = Annotation("<sentence>"),
                binary: Binary = Binary("[hunpos.binary]"),
                model: Model = Model("[hunpos.model_hist]"),
                morphtable: Optional[Model] = Model("[hunpos.morphtable_hist]"),
                tag_mapping: Optional[str] = Config("hunpos.tag_mapping_hist"),
                encoding: str = Config("hunpos.encoding")):
    """POS/MSD tag modern Swedish texts using the Hunpos tagger."""
    main(out, word, sentence, binary, model, morphtable=morphtable, patterns=None, tag_mapping=tag_mapping,
         encoding=encoding)


def main(out, word, sentence, binary, model, morphtable=None, patterns=None, tag_mapping=None,
         encoding=util.constants.UTF8):
    """POS/MSD tag using the Hunpos tagger."""
    if isinstance(tag_mapping, str) and tag_mapping:
        tag_mapping = tagmappings.mappings[tag_mapping]
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


@annotator("Extract POS from MSD", language=["swe", "swe-1800"])
def postag(out: Output = Output("<token>:hunpos.pos", cls="token:pos", description="Part-of-speech tags"),
           msd: Annotation = Annotation("<token:msd>")):
    """Extract POS from MSD."""
    from sparv.modules.misc import misc
    misc.select(out, msd, index=0, separator=".")


@modelbuilder("Hunpos model", language=["swe"])
def hunpos_model(model: ModelOutput = ModelOutput("hunpos/suc3_suc-tags_default-setting_utf8.model"),
                 binary: Binary = Binary("[hunpos.binary]")):
    """Download the Hunpos model."""

    def test_hunpos(model):
        stdin = TOK_SEP.join(["jag", "och", "du"]) + SENT_SEP
        util.system.call_binary(binary, [model.path], stdin, encoding="UTF-8")

    tmp_model = Model("hunpos/hunpos-model.tmp")
    reg_model = "https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_suc-tags_default-setting_utf8.model"
    mac_model = "https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_suc-tags_default-setting_utf8-mac.model"

    # Download the regular Hunpos model and test it by running hunpos on a single test sentence
    tmp_model.download(reg_model)
    try:
        logger.info("Testing regular Hunpos model")
        test_hunpos(tmp_model)
    except (RuntimeError, OSError):
        # Download the MacOS hunpos model and test again
        tmp_model.remove()
        tmp_model.download(mac_model)
        try:
            logger.info("Testing MacOS Hunpos model")
            test_hunpos(tmp_model)
        except RuntimeError:
            raise SparvErrorMessage(
                "Hunpos does not seem to be working on your system with any of the available models.")

    # Rename and Clean up
    tmp_model.rename(model.path)
    tmp_model.remove()
