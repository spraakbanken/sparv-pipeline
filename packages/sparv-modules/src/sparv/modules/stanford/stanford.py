"""Use Stanford Parser to analyse English text.

Requires Stanford CoreNLP version 4.0.0 (https://stanfordnlp.github.io/CoreNLP/history.html).
May work with newer versions.
Please download, unzip and place contents inside sparv-pipeline/bin/stanford_parser.
License for Stanford CoreNLP: GPL2 https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from sparv.api import Annotation, BinaryDir, Config, Language, Output, Text, annotator, get_logger, util
from sparv.api.util.tagsets import pos_to_upos

logger = get_logger(__name__)


@annotator(
    "Parse and annotate with Stanford Parser",
    language=["eng"],
    config=[
        Config(
            "stanford.bin", default="stanford_parser", description="Path to directory containing Stanford executables"
        )
    ],
)
def annotate(
    corpus_text: Text = Text(),
    lang: Language = Language(),
    text: Annotation = Annotation("<text>"),
    out_sentence: Output = Output("stanford.sentence", cls="sentence", description="Sentence segments"),
    out_token: Output = Output("stanford.token", cls="token", description="Token segments"),
    out_baseform: Output = Output("<token>:stanford.baseform", description="Baseforms from Stanford Parser"),
    out_upos: Output = Output("<token>:stanford.upos", cls="token:upos", description="Part-of-speeches in UD"),
    out_pos: Output = Output(
        "<token>:stanford.pos", cls="token:pos", description="Part-of-speeches from Stanford Parser"
    ),
    out_ne: Output = Output(
        "<token>:stanford.ne_type",
        cls="token:named_entity_type",
        description="Named entitiy types from Stanford Parser",
    ),
    out_deprel: Output = Output(
        "<token>:stanford.deprel", cls="token:deprel", description="Dependency relations to the head"
    ),
    out_dephead_ref: Output = Output(
        "<token>:stanford.dephead_ref",
        cls="token:dephead_ref",
        description="Sentence-relative positions of the dependency heads",
    ),
    binary: BinaryDir = BinaryDir("[stanford.bin]"),
) -> None:
    """Use Stanford Parser to parse and annotate text.

    Args:
        corpus_text: The corpus text.
        lang: Language of the text.
        text: Text annotation.
        out_sentence: Output sentence segments.
        out_token: Output token segments.
        out_baseform: Output baseforms from Stanford Parser.
        out_upos: Output part-of-speeches in UD.
        out_pos: Output part-of-speeches from Stanford Parser.
        out_ne: Output named entity types from Stanford Parser.
        out_deprel: Output dependency relations to the head.
        out_dephead_ref: Output sentence-relative positions of the dependency heads.
        binary: Path to directory containing Stanford executables.
    """
    args = [
        "-cp",
        binary + "/*",
        "edu.stanford.nlp.pipeline.StanfordCoreNLP",
        "-annotators",
        "tokenize,ssplit,pos,lemma,depparse,ner",
        # The output columns are taken from edu.stanford.nlp.ling.AnnotationLookup:
        "-output.columns",
        "idx,current,lemma,pos,ner,headidx,deprel,BEGIN_POS,END_POS",
        "-outputFormat",
        "conll",
    ]

    # Read corpus_text and text_spans
    text_data = corpus_text.read()
    text_spans = list(text.read_spans())

    sentence_segments = []
    all_tokens = []

    with tempfile.TemporaryDirectory() as tmpdirstr:
        tmpdir = Path(tmpdirstr)
        logger.debug("Creating temporary directoty: %s", tmpdir)

        # Write all texts to temporary files
        filelist = tmpdir / "filelist.txt"
        with filelist.open("w", encoding="utf-8") as f:
            for nr, (start, end) in enumerate(text_spans):
                filename = tmpdir / f"text-{nr}.txt"
                print(filename, file=f)
                with filename.open("w", encoding="utf-8") as f2:
                    print(text_data[start:end], file=f2)
                logger.debug(
                    "Writing text %d (%d-%d): %r...%r --> %s",
                    nr,
                    start,
                    end,
                    text_data[start : start + 20],
                    text_data[end - 20 : end],
                    filename.name,
                )

        # Call the Stanford parser with all the text files
        args += ["-filelist", filelist]
        args += ["-outputDirectory", tmpdir]
        util.system.call_binary("java", arguments=args)

        # Read and parse each of the output files
        for nr, (start, end) in enumerate(text_spans):
            filename = tmpdir / f"text-{nr}.txt.conll"
            output = filename.read_text(encoding="utf-8")
            logger.debug(
                "Reading text %d (%d-%d): %s --> %r...%r", nr, start, end, filename.name, output[:20], output[-20:]
            )
            processed_sentences = _parse_output(output, lang, start)

            for sentence in processed_sentences:
                logger.debug("Parsed: %s", " ".join(f"{tok.baseform}/{tok.pos}" for tok in sentence))
                for token in sentence:
                    all_tokens.append(token)
                    if token.word != text_data[token.start : token.end]:
                        logger.warning(
                            "Stanford word (%r) differs from surface word (%r), using the Stanford word",
                            token.word,
                            text_data[token.start : token.end],
                        )
                sentence_segments.append((sentence[0].start, sentence[-1].end))

    # Write annotations
    out_sentence.write(sentence_segments)
    out_token.write([(t.start, t.end) for t in all_tokens])
    out_baseform.write([t.baseform for t in all_tokens])
    out_upos.write([t.upos for t in all_tokens])
    out_pos.write([t.pos for t in all_tokens])
    out_ne.write([t.ne for t in all_tokens])
    out_dephead_ref.write([t.dephead_ref for t in all_tokens])
    out_deprel.write([t.deprel for t in all_tokens])


@annotator("Annotate tokens with IDs relative to their sentences", language=["eng"])
def make_ref(
    out: Output = Output("<token>:stanford.ref", cls="token:ref", description="Token IDs relative to their sentences"),
    sentence: Annotation = Annotation("<sentence>"),
    token: Annotation = Annotation("<token>"),
) -> None:
    """Annotate tokens with IDs relative to their sentences.

    Args:
        out: Output annotation with token positions relative to their sentences.
        sentence: Sentence annotation.
        token: Token annotation.
    """
    from sparv.modules.misc import number  # noqa: PLC0415

    number.number_relative(out, sentence, token)


def _parse_output(stdout: str, lang: Language, add_to_index: int) -> list:
    """Parse the CoNLL format output from the Stanford Parser.

    Args:
        stdout: The output from the Stanford Parser in CoNLL format.
        lang: Language of the text.
        add_to_index: Offset to add to the token spans.

    Returns:
        List of sentences, each containing a list of Token objects.
    """
    sentences = []
    sentence = []
    for line in stdout.split("\n"):
        # Empty lines == new sentence
        if not line.strip():
            if sentence:
                sentences.append(sentence)
                sentence = []
        # Create new word with attributes
        else:
            # -output.columns from the parser (see the args to the parser, in annotate() above):
            (
                ref,  # idx
                word,  # current
                lemma,  # lemma
                pos,  # pos
                named_entity,  # ner
                dephead_ref,  # headidx
                deprel,  # deprel
                start,  # BEGIN_POS
                end,  # END_POS
            ) = line.split("\t")
            upos = pos_to_upos(pos, lang, "Penn")
            if named_entity == "O":  # O = empty name tag
                named_entity = ""
            if dephead_ref == "0":  # 0 = empty dephead
                dephead_ref = ""
            start, end = (add_to_index + int(i) for i in [start, end])
            token = Token(ref, word, pos, upos, lemma, named_entity, dephead_ref, deprel, start, end)
            sentence.append(token)

    return sentences


@dataclass(slots=True)
class Token:
    """Object to store annotation information for a token."""

    ref: str
    word: str
    pos: str
    upos: str
    baseform: str
    ne: str
    dephead_ref: str
    deprel: str
    start: int
    end: int
