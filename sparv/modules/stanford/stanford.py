"""Use Stanford Parser to analyse English text.

Requires Stanford CoreNLP version 4.0.0 (https://stanfordnlp.github.io/CoreNLP/history.html).
May work with newer versions.
Please download, unzip and place contents inside sparv-pipeline/bin/stanford_parser.
License for Stanford CoreNLP: GPL2 https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""

import re

import sparv.util as util
from sparv import Annotation, BinaryDir, Config, Language, Output, Text, annotator


@annotator("Parse and annotate with Stanford Parser", language=["eng"], config=[
    Config("stanford.bin", default="stanford_parser", description="Path to directory containing Stanford executables")
])
def annotate(corpus_text: Text = Text(),
             lang: Language = Language(),
             text: Annotation = Annotation("<text>"),
             out_sentence: Output = Output("stanford.sentence", cls="sentence", description="Sentence segments"),
             out_token: Output = Output("stanford.token", cls="token", description="Token segments"),
             out_word: Output = Output("<token>:stanford.word", cls="token:word", description="Token strings"),
             out_ref: Output = Output("<token>:stanford.ref", description="Token ID relative to sentence"),
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
            "-outputFormat", "conll"]
    process = util.system.call_binary("java", arguments=args, return_command=True)

    # Read corpus_text and text_spans
    text_data = corpus_text.read()
    text_spans = text.read_spans()

    sentence_segments = []
    all_tokens = []

    # Go through text elements and parse them with Stanford Parser
    for text_span in text_spans:
        inputtext = text_data[text_span[0]:text_span[1]]
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
    out_sentence.write(sentence_segments)
    out_token.write([(t.start, t.end) for t in all_tokens])
    out_ref.write([t.ref for t in all_tokens])
    out_word.write([t.word for t in all_tokens])
    out_baseform.write([t.baseform for t in all_tokens])
    out_upos.write([t.upos for t in all_tokens])
    out_pos.write([t.pos for t in all_tokens])
    out_ne.write([t.ne for t in all_tokens])
    out_dephead_ref.write([t.dephead_ref for t in all_tokens])
    out_deprel.write([t.deprel for t in all_tokens])


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
            pos = fields[3]
            upos = util.tagsets.pos_to_upos(pos, lang, "Penn")
            named_entity = fields[4] if fields[4] != "O" else ""  # O = empty name tag
            deprel = fields[6]
            dephead_ref = fields[5] if fields[4] != "0" else ""  # 0 = empty dephead
            token = Token(ref, word, pos, upos, lemma, named_entity, dephead_ref, deprel)
            sentence.append(token)

    return sentences


class Token:
    """Object to store annotation information for a token."""

    def __init__(self, ref, word, pos, upos, baseform, ne, dephead_ref, deprel, start=-1, end=-1):
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
