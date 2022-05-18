"""Use Stanford Parser to analyse English text.

Requires Stanford CoreNLP version 4.0.0 (https://stanfordnlp.github.io/CoreNLP/history.html).
May work with newer versions.
Please download, unzip and place contents inside sparv-pipeline/bin/stanford_parser.
License for Stanford CoreNLP: GPL2 https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""

import tempfile
from pathlib import Path

from sparv.api import Annotation, BinaryDir, Config, Language, Output, Text, annotator, get_logger, util
from sparv.api.util.tagsets import pos_to_upos

logger = get_logger(__name__)


@annotator("Parse and annotate with Stanford Parser", language=["eng"], config=[
    Config("stanford.bin", default="stanford_parser", description="Path to directory containing Stanford executables")
])
def annotate(corpus_text: Text = Text(),
             lang: Language = Language(),
             text: Annotation = Annotation("<text>"),
             out_sentence: Output = Output("stanford.sentence", cls="sentence", description="Sentence segments"),
             out_token: Output = Output("stanford.token", cls="token", description="Token segments"),
             out_baseform: Output = Output("<token>:stanford.baseform", description="Baseforms from Stanford Parser"),
             out_upos: Output = Output("<token>:stanford.upos", cls="token:upos", description="Part-of-speeches in UD"),
             out_pos: Output = Output("<token>:stanford.pos", cls="token:pos",
                                      description="Part-of-speeches from Stanford Parser"),
             out_ne: Output = Output("<token>:stanford.ne_type", cls="token:named_entity_type",
                                     description="Named entitiy types from Stanford Parser"),
             out_deprel: Output = Output("<token>:stanford.deprel", cls="token:deprel",
                                         description="Dependency relations to the head"),
             out_dephead_ref: Output = Output("<token>:stanford.dephead_ref", cls="token:dephead_ref",
                                              description="Sentence-relative positions of the dependency heads"),
             binary: BinaryDir = BinaryDir("[stanford.bin]")):
    """Use Stanford Parser to parse and annotate text."""
    args = ["-cp", binary + "/*", "edu.stanford.nlp.pipeline.StanfordCoreNLP",
            "-annotators", "tokenize,ssplit,pos,lemma,depparse,ner",
            # The output columns are taken from edu.stanford.nlp.ling.AnnotationLookup:
            "-output.columns", "idx,current,lemma,pos,ner,headidx,deprel,BEGIN_POS,END_POS",
            "-outputFormat", "conll"]

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
        with open(filelist, "w", encoding="utf-8") as LIST:
            for nr, (start, end) in enumerate(text_spans):
                filename = tmpdir / f"text-{nr}.txt"
                print(filename, file=LIST)
                with open(filename, "w", encoding="utf-8") as F:
                    print(text_data[start:end], file=F)
                logger.debug("Writing text %d (%d-%d): %r...%r --> %s", nr, start, end,
                             text_data[start:start + 20], text_data[end - 20:end], filename.name)

        # Call the Stanford parser with all the text files
        args += ["-filelist", filelist]
        args += ["-outputDirectory", tmpdir]
        util.system.call_binary("java", arguments=args)

        # Read and parse each of the output files
        for nr, (start, end) in enumerate(text_spans):
            filename = tmpdir / f"text-{nr}.txt.conll"
            with open(filename, encoding="utf-8") as F:
                output = F.read()
            logger.debug("Reading text %d (%d-%d): %s --> %r...%r", nr, start, end,
                         filename.name, output[:20], output[-20:])
            processed_sentences = _parse_output(output, lang, start)

            for sentence in processed_sentences:
                logger.debug("Parsed: %s", " ".join(f"{tok.baseform}/{tok.pos}" for tok in sentence))
                for token in sentence:
                    all_tokens.append(token)
                    if token.word != text_data[token.start:token.end]:
                        logger.warning("Stanford word (%r) differs from surface word (%r), using the Stanford word",
                                       token.word, text_data[token.start:token.end])
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
def make_ref(out: Output = Output("<token>:stanford.ref", cls="token:ref",
                                  description="Token IDs relative to their sentences"),
             sentence: Annotation = Annotation("<sentence>"),
             token: Annotation = Annotation("<token>")):
    """Annotate tokens with IDs relative to their sentences."""
    from sparv.modules.misc import number
    number.number_relative(out, sentence, token)


def _parse_output(stdout, lang, add_to_index):
    """Parse the CoNLL format output from the Stanford Parser."""
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
            # idx, current, lemma, pos, ner,          headidx,     deprel, BEGIN_POS, END_POS
            ref,   word,    lemma, pos, named_entity, dephead_ref, deprel, start,     end     = line.split("\t")
            upos = pos_to_upos(pos, lang, "Penn")
            if named_entity == "O":  # O = empty name tag
                named_entity = ""
            if dephead_ref == "0":  # 0 = empty dephead
                dephead_ref = ""
            start, end = [add_to_index + int(i) for i in [start, end]]
            token = Token(ref, word, pos, upos, lemma, named_entity, dephead_ref, deprel, start, end)
            sentence.append(token)

    return sentences


class Token:
    """Object to store annotation information for a token."""

    def __init__(self, ref, word, pos, upos, baseform, ne, dephead_ref, deprel, start, end):
        """Set attributes."""
        self.ref = ref
        self.word = word
        self.pos = pos
        self.upos = upos
        self.baseform = baseform
        self.ne = ne
        self.dephead_ref = dephead_ref
        self.deprel = deprel
        self.start = start
        self.end = end
