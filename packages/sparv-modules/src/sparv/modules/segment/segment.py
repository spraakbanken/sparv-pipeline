"""Segmentation mostly based on NLTK."""

import inspect
import itertools
import pickle
import re
from collections.abc import Generator
from pathlib import Path

import nltk

from sparv.api import Annotation, Config, Model, ModelOutput, Output, Text, annotator, get_logger, modelbuilder, util
from sparv.modules.saldo.saldo_model import split_triple

try:
    from . import crf  # for CRF++ models
except ImportError:
    pass

logger = get_logger(__name__)


@annotator(
    "Automatic tokenization",
    config=[
        Config(
            "segment.token_segmenter",
            default="better_word",
            description="Token segmenter to use",
            datatype=str,
            choices=lambda: sorted(SEGMENTERS),
        ),
        Config(
            "segment.token_chunk",
            default="<sentence>",
            description="Text chunk (annotation) to use as input when tokenizing",
            datatype=str,
        ),
        Config("segment.existing_tokens", description="Optional existing token annotation", datatype=str),
        Config(
            "segment.tokenizer_config",
            default="segment/bettertokenizer.sv",
            description="Path to tokenizer config",
            datatype=str,
        ),
        Config(
            "segment.token_list",
            default="segment/bettertokenizer.sv.saldo-tokens",
            description="Path to optional token list file",
            datatype=str,
        ),
    ],
)
def tokenize(
    text: Text = Text(),
    out: Output = Output("segment.token", cls="token", description="Token segments"),
    chunk: Annotation = Annotation("[segment.token_chunk]"),
    segmenter: str = Config("segment.token_segmenter"),
    existing_segments: Annotation | None = Annotation("[segment.existing_tokens]"),
    model: Model | None = Model("[segment.tokenizer_config]"),
    token_list: Model | None = Model("[segment.token_list]"),
) -> None:
    """Tokenize text."""
    do_segmentation(
        text=text,
        out=out,
        chunk=chunk,
        segmenter=segmenter,
        existing_segments=existing_segments,
        model=model,
        token_list=token_list,
    )


@annotator(
    "Automatic segmentation of sentences",
    config=[
        Config(
            "segment.sentence_segmenter",
            default="punkt_sentence",
            description="Sentence segmenter to use",
            datatype=str,
            choices=lambda: sorted(SEGMENTERS),
        ),
        Config(
            "segment.sentence_chunk",
            default="<paragraph>, <text>",
            description="Text chunk (annotation) to use as input when segmenting",
            datatype=str,
        ),
        Config("segment.existing_sentences", description="Optional existing sentence annotation", datatype=str),
        Config(
            "segment.sentence_model",
            default="segment/punkt-nltk-svenska.pickle",
            description="Path to model",
            datatype=str,
        ),
    ],
)
def sentence(
    text: Text = Text(),
    out: Output = Output("segment.sentence", cls="sentence", description="Sentence segments"),
    chunk: Annotation | None = Annotation("[segment.sentence_chunk]"),
    segmenter: str = Config("segment.sentence_segmenter"),
    existing_segments: Annotation | None = Annotation("[segment.existing_sentences]"),
    model: Model | None = Model("[segment.sentence_model]"),
) -> None:
    """Split text into sentences."""
    do_segmentation(
        text=text, out=out, chunk=chunk, segmenter=segmenter, existing_segments=existing_segments, model=model
    )


@annotator(
    "Automatic segmentation of paragraphs",
    config=[
        Config(
            "segment.paragraph_segmenter",
            default="blanklines",
            description="Paragraph segmenter to use",
            datatype=str,
            choices=lambda: sorted(SEGMENTERS),
        ),
        Config(
            "segment.paragraph_chunk",
            default="<text>",
            description="Text chunk (annotation) to use as input when segmenting",
            datatype=str,
        ),
        Config("segment.existing_paragraphs", description="Optional existing paragraph annotation", datatype=str),
    ],
)
def paragraph(
    text: Text = Text(),
    out: Output = Output("segment.paragraph", cls="paragraph", description="Paragraph segments"),
    chunk: Annotation | None = Annotation("[segment.paragraph_chunk]"),
    segmenter: str = Config("segment.paragraph_segmenter"),
    existing_segments: Annotation | None = Annotation("[segment.existing_paragraphs]"),
    model: Model | None = None,
) -> None:
    """Split text into paragraphs."""
    do_segmentation(
        text=text, out=out, chunk=chunk, segmenter=segmenter, existing_segments=existing_segments, model=model
    )


def do_segmentation(
    text: Text,
    out: Output,
    segmenter: str,
    chunk: Annotation | None = None,
    existing_segments: Annotation | None = None,
    model: Model | None = None,
    token_list: Model | None = None,
) -> None:
    """Segment all chunks (e.g. sentences) into smaller "tokens" (e.g. words), and annotate them as "element" (e.g. w).

    Segmentation is done by the given "segmenter"; some segmenters take
    an extra argument which is a pickled "model" object.
    """
    assert segmenter in SEGMENTERS, f"Available segmenters: {', '.join(sorted(SEGMENTERS))}"
    segmenter = SEGMENTERS[segmenter]

    segmenter_args = {}
    if model and "model" in inspect.getfullargspec(segmenter).args:
        if model.path.suffix in {".pickle", ".pkl"}:
            with model.path.open("rb") as m:
                model_arg = pickle.load(m, encoding="UTF-8")
        else:
            model_arg = model.path
        segmenter_args["model"] = model_arg
    if token_list and "token_list" in inspect.getfullargspec(segmenter).args:
        segmenter_args["token_list"] = token_list.path

    segmenter = segmenter(**segmenter_args)
    assert hasattr(segmenter, "span_tokenize"), f"Segmenter needs a 'span_tokenize' method: {segmenter!r}"

    corpus_text = text.read()

    # First we read the chunks and partition the text into spans
    # E.g., "one two <s>three four</s> five <s>six</s>"
    #   ==> ["one two ", "three four", " five ", "six"]
    #   (but using spans (pairs of anchors) instead of strings)

    positions = set()
    chunk_spans = chunk.read_spans() if chunk else []
    positions = positions.union({pos for span in chunk_spans for pos in span})
    positions = sorted({0, len(corpus_text)} | positions)
    chunk_spans = list(itertools.pairwise(positions))

    if existing_segments:
        segments = list(existing_segments.read_spans())
        for n, (chunk_start, chunk_end) in enumerate(chunk_spans[:]):
            for segment_start, segment_end in segments:
                if segment_end <= chunk_start:
                    continue
                if segment_start >= chunk_end:
                    break
                if chunk_start != segment_start:
                    chunk_spans.append((chunk_start, segment_start))
                chunk_start = segment_end  # noqa: PLW2901
                chunk_spans[n] = (chunk_start, chunk_end)
        chunk_spans.sort()
        logger.info("Reorganized into %d chunks", len(chunk_spans))
    else:
        segments = []

    total_chunks = len(chunk_spans)
    progress_total = min(100, total_chunks + 1)  # At least 2 steps, max 100
    logger.progress(total=progress_total)

    # Now we can segment each chunk span into tokens
    for i, (start, end) in enumerate(chunk_spans):
        for spanstart, spanend in segmenter.span_tokenize(corpus_text[start:end]):
            spanstart += start  # noqa: PLW2901
            spanend += start  # noqa: PLW2901
            if corpus_text[spanstart:spanend].strip():
                span = (spanstart, spanend)
                segments.append(span)
        if i % max(1, total_chunks // (progress_total - 1)) == 0 or i == total_chunks - 1:
            logger.progress()

    segments.sort()
    out.write(segments)
    logger.progress()


@modelbuilder("Model for PunktSentenceTokenizer", language=["swe"])
def download_punkt_model(out: ModelOutput = ModelOutput("segment/punkt-nltk-svenska.pickle")) -> None:
    """Download model for use with PunktSentenceTokenizer.

    Args:
        out: The model to output.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/segment/punkt-nltk-svenska.pickle")


@modelbuilder("Model for BetterWordTokenizer", language=["swe"])
def download_bettertokenizer(out: ModelOutput = ModelOutput("segment/bettertokenizer.sv")) -> None:
    """Download model for use with BetterWordTokenizer.

    Args:
        out: The model to output.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/segment/bettertokenizer.sv")


@modelbuilder(
    "Token list for BetterWordTokenizer",
    language=["swe"],
    config=[
        Config(
            "segment.token_wordlist_segmenter",
            "better_word",
            description="Segmenter to use when building wordlist",
            datatype=str,
            choices=lambda: sorted(SEGMENTERS),
        )
    ],
)
def build_tokenlist(
    saldo_model: Model = Model("saldo/saldo.pickle"),
    out: ModelOutput = ModelOutput("segment/bettertokenizer.sv.saldo-tokens"),
    segmenter: str = Config("segment.token_wordlist_segmenter"),
    model: Model = Model("segment/bettertokenizer.sv"),
) -> None:
    """Build a list of words from a SALDO model, to help BetterWordTokenizer.

    Args:
        saldo_model: The SALDO model to use.
        out: The output token list.
        segmenter: The segmenter to use.
        model: BetterWordTokenizer config file.
    """
    segmenter_args = []
    if model:
        if model.path.suffix in {".pickle", ".pkl"}:
            with model.path.open("rb") as m:
                model_arg = pickle.load(m)
        else:
            model_arg = model.path
        segmenter_args.append(model_arg)
    assert segmenter in SEGMENTERS, f"Available segmenters: {', '.join(sorted(SEGMENTERS))}"
    segmenter = SEGMENTERS[segmenter]
    segmenter = segmenter(*segmenter_args)
    assert hasattr(segmenter, "span_tokenize"), f"Segmenter needs a 'span_tokenize' method: {segmenter!r}"

    wordforms = set()

    # Skip strings already handled by the tokenizer.
    # Also skip words ending in comma (used by some multi-word expressions in SALDO).
    with saldo_model.path.open("rb") as f:
        lexicon = pickle.load(f)
        for w in lexicon:
            w2 = list(map(split_triple, lexicon[w]))
            mwu_extras = [contw for w3 in w2 for cont in w3[2] for contw in cont if contw not in lexicon]
            for wf in [*mwu_extras, w]:
                spans = list(segmenter.span_tokenize(wf))
                if len(spans) > 1 and not wf.endswith(","):
                    wordforms.add(wf)

    out.write("\n".join(sorted(wordforms)))


######################################################################


def train_punkt_segmenter(
    textfiles: str | list[str], modelfile: str, encoding: str = util.constants.UTF8, protocol: int = -1
) -> None:
    """Train a Punkt sentence tokenizer.

    Args:
        textfiles: List of text files to train on.
        modelfile: Path to the output model file.
        encoding: Encoding of the text files.
        protocol: Pickle protocol to use.
    """
    if isinstance(textfiles, str):
        textfiles = textfiles.split()

    logger.info("Reading files")
    text = ""
    for filename in textfiles:
        with Path(filename).open(encoding=encoding) as stream:
            text += stream.read()
    logger.info("Training model")
    trainer = nltk.tokenize.PunktTrainer(text, verbose=True)
    logger.info("Saving pickled model")
    params = trainer.get_params()
    with Path(modelfile).open("wb") as stream:
        pickle.dump(params, stream, protocol=protocol)
    logger.info("OK")


######################################################################


class LinebreakTokenizer(nltk.RegexpTokenizer):
    """Tokenizer that separates tokens by line breaks (based on NLTK's RegexpTokenizer)."""

    def __init__(self) -> None:
        """Initialize class."""
        nltk.RegexpTokenizer.__init__(self, r"\s*\n\s*", gaps=True)


class PunctuationTokenizer(nltk.RegexpTokenizer):
    """A very simple sentence tokenizer, separating sentences on every .!? no matter the context.

    Use only when PunktSentenceTokenizer does not work, for example when there's no whitespace after punctuation.
    """

    def __init__(self) -> None:
        """Initialize class."""
        nltk.RegexpTokenizer.__init__(self, r"[\.!\?]\s*", gaps=True)

    def span_tokenize(self, s: str) -> list:
        """Tokenize s and return list with tokens.

        Args:
            s: The string to tokenize.

        Returns:
            List of tuples with start and end positions of tokens.
        """
        result = []
        spans = nltk.RegexpTokenizer.span_tokenize(self, s)
        temp = [0, 0]

        for start, _ in spans:
            temp[1] = start
            result.append(tuple(temp))
            temp[0] = start

        temp[1] = len(s)
        result.append(tuple(temp))

        return result


class BetterWordTokenizer:
    """A word tokenizer based on the PunktWordTokenizer code.

    Heavily modified to add support for custom regular expressions, wordlists, and external configuration files.
    http://nltk.googlecode.com/svn/trunk/doc/api/nltk.tokenize.punkt.PunktSentenceTokenizer-class.html
    """

    # Format for the complete regular expression to be used for tokenization
    _word_tokenize_fmt = r"""(
        %(misc)s
        |
        %(multi)s
        |
        (?:(?:(?<=^)|(?<=\s))%(number)s(?=\s|$))  # Numbers with decimal mark
        |
        (?=[^%(start)s])
        (?:%(tokens)s%(abbrevs)s(?<=\s)(?:[^\.\s]+\.){2,}|\S+?)  # Accept word characters until end is found
        (?= # Sequences marking a word's end
            \s|                                 # White-space
            $|                                  # End-of-string
            (?:[%(within)s])|%(multi)s|         # Punctuation
            [%(end)s](?=$|\s|(?:[%(within)s])|%(multi)s)  # Misc characters if at end of word
        )
        |
        \S
    )"""

    # Used to realign punctuation that should be included in a sentence although it follows the period (or ?, !).
    re_boundary_realignment = re.compile(r'[“”"\')\]}]+?(?:\s+|(?=--)|$)', re.MULTILINE)

    re_punctuated_token = re.compile(r"\w.*\.$", re.UNICODE)

    def __init__(self, model: Path, token_list: Path | None = None) -> None:
        """Parse configuration file (model) and token_list (if supplied).

        Args:
            model: The model to use.
            token_list: Optional token list file.

        Raises:
            ValueError: If the configuration file is not valid.
        """
        self.case_sensitive = False
        self.patterns = {"misc": [], "tokens": []}
        self.abbreviations = set()
        in_abbr = False

        if token_list:
            with token_list.open(encoding="UTF-8") as saldotokens:
                self.patterns["tokens"] = [re.escape(t.strip()) for t in saldotokens]

        with model.open(encoding="UTF-8") as conf:
            for line in conf:
                if line.startswith("#") or not line.strip():
                    continue
                if not in_abbr:
                    if not in_abbr and line.strip() == "abbreviations:":
                        in_abbr = True
                        continue
                    try:
                        key, val = line.strip().split(None, 1)
                    except ValueError as e:
                        logger.error("Error parsing configuration file: %s", line)
                        raise e
                    key = key[:-1]

                    if key == "case_sensitive":
                        self.case_sensitive = val.lower() == "true"
                    elif key.startswith("misc_"):
                        self.patterns["misc"].append(val)
                    elif key in {"start", "within", "end"}:
                        self.patterns[key] = re.escape(val)
                    elif key in {"multi", "number"}:
                        self.patterns[key] = val
                    # For backwards compatibility
                    elif key == "token_list":
                        pass
                    else:
                        raise ValueError(f"Unknown option: {key}")
                else:
                    self.abbreviations.add(line.strip())

    def _word_tokenizer_re(self) -> re.Pattern:
        """Compile and return a regular expression for word tokenization.

        Returns:
            The compiled regular expression.
        """
        try:
            return self._re_word_tokenizer
        except AttributeError:
            modifiers = (re.UNICODE | re.VERBOSE) if self.case_sensitive else (re.UNICODE | re.VERBOSE | re.IGNORECASE)
            self._re_word_tokenizer = re.compile(
                self._word_tokenize_fmt
                % {
                    "tokens": ("(?:" + "|".join(self.patterns["tokens"]) + ")|") if self.patterns["tokens"] else "",
                    "abbrevs": ("(?:" + "|".join(re.escape(a + ".") for a in self.abbreviations) + ")|")
                    if self.abbreviations
                    else "",
                    "misc": "|".join(self.patterns["misc"]),
                    "number": self.patterns["number"],
                    "within": self.patterns["within"],
                    "multi": self.patterns["multi"],
                    "start": self.patterns["start"],
                    "end": self.patterns["end"],
                },
                modifiers,
            )
            return self._re_word_tokenizer

    def word_tokenize(self, s: str) -> list[str]:
        """Tokenize a string to split off punctuation other than periods.

        Args:
            s: The string to tokenize.

        Returns:
            List of tokens.
        """
        words = self._word_tokenizer_re().findall(s)
        if not words:
            return words
        pos = len(words) - 1

        # Split sentence-final . from the final word.
        # i.e., "peter." "piper." ")" => "peter." "piper" "." ")"
        # but not "t.ex." => "t.ex" "."
        while pos >= 0 and self.re_boundary_realignment.match(words[pos]):
            pos -= 1
        endword = words[pos]
        if self.re_punctuated_token.search(endword):
            endword = endword[:-1]
            if endword not in self.abbreviations:
                words[pos] = endword
                words.insert(pos + 1, ".")

        return words

    def span_tokenize(self, s: str) -> Generator[tuple[int, int]]:
        """Tokenize s and return list of spans.

        Args:
            s: The string to tokenize.

        Yields:
            Tuples with start and end positions of tokens.
        """
        begin = 0
        for w in self.word_tokenize(s):
            begin = s.find(w, begin)
            yield begin, begin + len(w)
            begin += len(w)


class PunktSentenceTokenizer(nltk.PunktSentenceTokenizer):
    """A simple subclass of nltk.PunktSentenceTokenizer to add the required 'model' parameter."""

    def __init__(self, model: Path) -> None:
        """Initialize class."""
        super().__init__(str(model))


class CRFTokenizer:
    """Tokenization based on Conditional Random Fields.

    Implemented for Old Swedish, see crf.py for more details.
    """

    def __init__(self, model: Path) -> None:
        """Initialize class."""
        self.model = str(model)

    def span_tokenize(self, s: str) -> list:
        """Tokenize s and return list with tokens.

        Args:
            s: The string to tokenize.

        Returns:
            List of tuples with start and end positions of tokens.
        """
        return crf.segment(s, self.model)


class FSVParagraphSplitter:
    """A paragraph splitter for old Swedish."""

    @staticmethod
    def span_tokenize(s: str) -> list:
        """Tokenize s and return list with tokens.

        Args:
            s: The string to tokenize.

        Returns:
            List of tuples with start and end positions of tokens.
        """
        spans = []
        temp = [0, 0]
        first = True
        for i in range(len(s)):
            if not first:
                new_para = re.search(r"^\.*§", s[i:])
                if new_para:
                    spans.append((temp[0], i))
                    temp[0] = i
                    first = True
            else:
                first = False
            temp[1] = i

        temp[1] = len(s)
        spans.append(tuple(temp))

        return spans


SEGMENTERS = {
    "whitespace": nltk.WhitespaceTokenizer,
    "linebreaks": LinebreakTokenizer,
    "blanklines": nltk.BlanklineTokenizer,
    "punkt_sentence": PunktSentenceTokenizer,
    "punctuation": PunctuationTokenizer,
    "better_word": BetterWordTokenizer,
    "crf_tokenizer": CRFTokenizer,
    "simple_word_punkt": nltk.WordPunctTokenizer,
    "fsv_paragraph": FSVParagraphSplitter,
}
