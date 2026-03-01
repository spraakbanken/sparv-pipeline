"""Part of Speech annotation using Hunpos."""

import re

from sparv.api import (
    Annotation,
    Binary,
    Config,
    Model,
    ModelOutput,
    Output,
    SparvErrorMessage,
    annotator,
    get_logger,
    modelbuilder,
    util,
)
from sparv.api.util.tagsets import tagmappings

logger = get_logger(__name__)

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1


@annotator("Part-of-speech annotation with morphological descriptions", language=["swe"])
def msdtag(
    out: Output = Output(
        "<token>:hunpos.msd", cls="token:msd", description="Part-of-speeches with morphological descriptions"
    ),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
    binary: Binary = Binary("[hunpos.binary]"),
    model: Model = Model("[hunpos.model]"),
    morphtable: Model | None = Model("[hunpos.morphtable]"),
    patterns: Model | None = Model("[hunpos.patterns]"),
    tag_mapping: str | None = Config("hunpos.tag_mapping"),
    encoding: str = Config("hunpos.encoding"),
) -> None:
    """POS/MSD tag modern Swedish texts using the Hunpos tagger.

    Args:
        out: Output annotation for part-of-speech with morphological descriptions.
        word: Input word annotation.
        sentence: Input sentence annotation.
        binary: Path to the Hunpos binary.
        model: Path to the Hunpos model.
        morphtable: Optional path to the morphtable model.
        patterns: Optional path to the patterns file.
        tag_mapping: Optional tag mapping for the POS tags.
        encoding: Encoding to use when communicating with the Hunpos binary.
    """
    main(
        out,
        word,
        sentence,
        binary,
        model,
        morphtable=morphtable,
        patterns=patterns,
        tag_mapping=tag_mapping,
        encoding=encoding,
    )


@annotator("Part-of-speech annotation with morphological descriptions for older Swedish", language=["swe-1800"])
def msdtag_hist(
    out: Output = Output(
        "<token>:hunpos.msd_hist", cls="token:msd", description="Part-of-speeches with morphological descriptions"
    ),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
    binary: Binary = Binary("[hunpos.binary]"),
    model: Model = Model("[hunpos.model_hist]"),
    morphtable: Model | None = Model("[hunpos.morphtable_hist]"),
    tag_mapping: str | None = Config("hunpos.tag_mapping_hist"),
    encoding: str = Config("hunpos.encoding"),
) -> None:
    """POS/MSD tag modern Swedish texts using the Hunpos tagger.

    Args:
        out: Output annotation for part-of-speech with morphological descriptions.
        word: Input word annotation.
        sentence: Input sentence annotation.
        binary: Path to the Hunpos binary.
        model: Path to the Hunpos model.
        morphtable: Optional path to the morphtable model.
        tag_mapping: Optional tag mapping for the POS tags.
        encoding: Encoding to use when communicating with the Hunpos binary.
    """
    main(
        out,
        word,
        sentence,
        binary,
        model,
        morphtable=morphtable,
        patterns=None,
        tag_mapping=tag_mapping,
        encoding=encoding,
    )


def main(
    out: Output,
    word: Annotation,
    sentence: Annotation,
    binary: str,
    model: Model,
    morphtable: Model | None = None,
    patterns: Model | None = None,
    tag_mapping: str | None = None,
    encoding: str = util.constants.UTF8,
) -> None:
    """POS/MSD tag using the Hunpos tagger.

    Args:
        out: Output annotation for part-of-speech with morphological descriptions.
        word: Input word annotation.
        sentence: Input sentence annotation.
        binary: Path to the Hunpos binary.
        model: Path to the Hunpos model.
        morphtable: Optional path to the morphtable model.
        patterns: Optional path to the patterns file.
        tag_mapping: Optional tag mapping for the POS tags.
        encoding: Encoding to use when communicating with the Hunpos binary.
    """
    if isinstance(tag_mapping, str) and tag_mapping:
        tag_mapping = tagmappings.mappings[tag_mapping]
    elif not tag_mapping:
        tag_mapping = {}

    pattern_list = []

    if patterns:
        with patterns.path.open(encoding="utf-8") as pat:
            for line in pat:
                if line.strip() and not line.startswith("#"):
                    name, pattern, tags = line.strip().split("\t", 2)
                    pattern_list.append((name, re.compile(f"^{pattern}$"), tags))

    def replace_word(w: str) -> str:
        """Replace word with alias if word matches a regex pattern.

        Args:
            w: The word to check against the patterns.

        Returns:
            The word if no pattern matches, or the alias if a pattern matches.
        """
        for p in pattern_list:
            if re.match(p[1], w):
                return f"[[{p[0]}]]"
        return w

    sentences, _orphans = sentence.get_children(word)
    token_word = list(word.read())
    stdin = SENT_SEP.join(
        TOK_SEP.join(replace_word(token_word[token_index]) for token_index in sent) for sent in sentences
    )
    args = [model.path]
    if morphtable:
        args.extend(["-m", morphtable.path])
    stdout, _ = util.system.call_binary(binary, args, stdin, encoding=encoding)

    out_annotation = word.create_empty_attribute()
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP), strict=True):
        for token_index, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP), strict=True):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            tag = tag_mapping.get(tag, tag)
            out_annotation[token_index] = tag

    out.write(out_annotation)


@annotator("Extract POS from MSD", language=["swe", "swe-1800"])
def postag(
    out: Output = Output("<token>:hunpos.pos", cls="token:pos", description="Part-of-speech tags"),
    msd: Annotation = Annotation("<token:msd>"),
) -> None:
    """Extract POS from MSD.

    Args:
        out: Output annotation for part-of-speech tags.
        msd: Input annotation with morphological descriptions.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.select(out, msd, index=0, separator=".")


@modelbuilder("Hunpos model", language=["swe"])
def hunpos_model(
    model: ModelOutput = ModelOutput("hunpos/suc3_suc-tags_default-setting_utf8.model"),
    binary: Binary = Binary("[hunpos.binary]"),
) -> None:
    """Download the Hunpos model.

    Args:
        model: Output model file.
        binary: Path to the Hunpos binary.

    Raises:
        SparvErrorMessage: If the Hunpos binary is not found or the model does not work correctly.
    """

    def test_hunpos(model: ModelOutput) -> None:
        """Test the Hunpos model with a sample input.

        Args:
            model: The Hunpos model to test.

        Raises:
            SparvErrorMessage: If the model does not work correctly.
        """
        stdin = TOK_SEP.join(["jag", "och", "du"]) + SENT_SEP
        stdout, _ = util.system.call_binary(binary, [model.path], stdin, encoding="UTF-8")
        logger.debug("Output from 'hunpos-tag' with test input:\n%s", stdout)
        if stdout.split() != ["jag", "PN.UTR.SIN.DEF.SUB", "och", "KN", "du", "PN.UTR.SIN.DEF.SUB"]:
            raise SparvErrorMessage("Hunpos model does not work correctly.")

    # Run "hunpos-tag -h" to check what version was installed
    stdout, _ = util.system.call_binary(binary, ["-h"], allow_error=True)
    logger.debug("Output from 'hunpos-tag -h': %s", stdout)
    # Search for keyword "--verbose" in help message
    if "--verbose" in stdout.decode():
        model.download(
            "https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_suc-tags_default-setting_utf8-mivoq.model"
        )
    else:
        model.download(
            "https://github.com/spraakbanken/sparv-models/raw/master/hunpos/suc3_suc-tags_default-setting_utf8.model"
        )

    try:
        logger.info("Testing Hunpos model")
        test_hunpos(model)
    except (RuntimeError, OSError):
        model.remove()
        raise SparvErrorMessage(
            "Hunpos does not seem to be working on your system with any of the available models."
        ) from None
