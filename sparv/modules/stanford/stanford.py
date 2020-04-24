"""Use Stanford Parser to analyse English text.

Needs Stanford CoreNLP version 4.0.0 (https://stanfordnlp.github.io/CoreNLP/history.html).
May work with newer versions.
Please download, unzip and place contents inside sparv-pipeline/bin/stanford_parser.
License for Stanford CoreNLP: GPL2 https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""

import re

import sparv.util as util
from sparv import Annotation, Binary, Document, Language, Output, annotator


@annotator("Parse and annotate with Stanford Parser")
def annotate(doc: str = Document,
             lang: str = Language,
             text: str = Annotation("<text>"),
             out_sentence: str = Output("stanford.sentence", cls="sentence", description="Sentence segments"),
             out_token: str = Output("stanford.token", cls="token", description="Token segments"),
             out_word: str = Output("<token>:stanford.word", cls="token:word", description="Token strings"),
             out_ref: str = Output("<token>:stanford.ref", description="Token ID relative to sentence"),
             out_baseform: str = Output("<token>:stanford.baseform", description="Baseforms from Stanford Parser"),
             out_pos: str = Output("<token>:stanford.pos", description="Part-of-speeches in UD"),
             out_msd: str = Output("<token>:stanford.msd", description="Part-of-speeches from Stanford Parser"),
             out_ne: str = Output("<token>:stanford.ne", description="Named entitiy types from Stanford Parser"),
             out_deprel: str = Output("<token>:stanford.deprel", description="Dependency relations to the head"),
             out_dephead_ref: str = Output("<token>:stanford.dephead_ref",
                                           description="Sentence-relative positions of the dependency heads"),
             binary: str = Binary("[stanford.bin=stanford_parser]")):
    """Use Stanford Parser to parse and annotate text."""
    args = ["-cp", binary + "/*", "edu.stanford.nlp.pipeline.StanfordCoreNLP",
            "-annotators", "tokenize,ssplit,pos,lemma,depparse,ner",
            "-outputFormat", "conll"]
    process = util.system.call_binary("java", arguments=args, return_command=True)

    # Read corpus_text and text_spans
    corpus_text = util.read_corpus_text(doc)
    text_spans = util.read_annotation_spans(doc, text)

    sentence_segments = []
    all_tokens = []

    # Go through text elements and parse them with Stanford Parser
    for text_span in text_spans:
        inputtext = corpus_text[text_span[0]:text_span[1]]
        stdout, _ = process.communicate(inputtext.encode(util.UTF8))
        processed_sentences = _parse_output(stdout.decode(util.UTF8), lang)

        # Go through output and try to match tokens with input text to get correct spans
        index_counter = text_span[0]
        for sentence in processed_sentences:
            for token in sentence:
                all_tokens.append(token)
                # Get token span
                match = re.match(r"\s*(%s)" % re.escape(token.word), inputtext)
                span = match.span(1)
                token.start = span[0] + index_counter
                token.end = span[1] + index_counter
                # Forward inputtext
                inputtext = inputtext[span[1]:]
                index_counter += span[1]
            # Extract sentence span for current sentence
            sentence_segments.append((sentence[0].start, sentence[-1].end))

    # Write annotations
    util.write_annotation(doc, out_sentence, sentence_segments)
    util.write_annotation(doc, out_token, [(t.start, t.end) for t in all_tokens])
    util.write_annotation(doc, out_ref, [t.ref for t in all_tokens])
    util.write_annotation(doc, out_word, [t.word for t in all_tokens])
    util.write_annotation(doc, out_baseform, [t.baseform for t in all_tokens])
    util.write_annotation(doc, out_pos, [t.pos for t in all_tokens])
    util.write_annotation(doc, out_msd, [t.msd for t in all_tokens])
    util.write_annotation(doc, out_ne, [t.ne for t in all_tokens])
    util.write_annotation(doc, out_dephead_ref, [t.dephead_ref for t in all_tokens])
    util.write_annotation(doc, out_deprel, [t.deprel for t in all_tokens])


def _parse_output(stdout, lang):
    """Parse the conll format output from the Standford Parser."""
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
            fields = line.split("\t")
            ref = fields[0]
            word = fields[1]
            lemma = fields[2]
            msd = fields[3]
            pos = util.msd_to_pos.convert(msd, lang)
            named_entity = fields[4] if fields[4] != "O" else ""  # O = empty name tag
            deprel = fields[6]
            dephead_ref = fields[5] if fields[4] != "0" else ""  # 0 = empty dephead
            token = Token(ref, word, msd, pos, lemma, named_entity, dephead_ref, deprel)
            sentence.append(token)

    return sentences


class Token(object):
    """Object to store annotation information for a token."""

    def __init__(self, ref, word, msd, pos, baseform, ne, dephead_ref, deprel, start=-1, end=-1):
        """Set attributes."""
        self.ref = ref
        self.word = word
        self.msd = msd
        self.pos = pos
        self.baseform = baseform
        self.ne = ne
        self.dephead_ref = dephead_ref
        self.deprel = deprel
        self.start = start
        self.end = end
