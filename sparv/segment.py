# -*- coding: utf-8 -*-

import os.path
import re
import nltk
import pickle
import sparv.util as util
import sparv.saldo as saldo
try:
    from . import crf  # for CRF++ models
except ImportError:
    pass


def do_segmentation(text, element, out, chunk, segmenter, existing_segments=None, model=None, no_pickled_model=False):
    """Segment all "chunks" (e.g. sentences) into smaller "tokens" (e.g. words),
    and annotate them as "element" (e.g. w).
    Segmentation is done by the given "segmenter"; some segmenters take
    an extra argument which is a pickled "model" object.
    """
    if model:
        if not no_pickled_model:
            with open(model, "rb") as M:
                model = pickle.load(M, encoding='UTF-8')
        segmenter_args = (model,)
    else:
        segmenter_args = ()
    assert segmenter in SEGMENTERS, "Available segmenters: %s" % ", ".join(sorted(SEGMENTERS))
    segmenter = SEGMENTERS[segmenter]
    segmenter = segmenter(*segmenter_args)
    assert hasattr(segmenter, "span_tokenize"), "Segmenter needs a 'span_tokenize' method: %r" % segmenter

    corpus_text, anchor2pos, pos2anchor = util.read_corpus_text(text)

    # First we read the chunks and partition the text into spans
    # E.g., "one two <s>three four</s> five <s>six</s>"
    #   ==> ["one two ", "three four", " five ", "six"]
    #   (but using spans (pairs of anchors) instead of strings)

    positions = set()
    for c in chunk.split():
        CHUNK = util.read_annotation(c)
        positions = positions.union(set(anchor2pos[anchor] for edge in CHUNK
                                    for span in util.edgeSpans(edge) for anchor in span))
    positions = sorted(set([0, len(corpus_text)]) | positions)
    chunk_spans = list(zip(positions, positions[1:]))

    if existing_segments:
        OUT = util.read_annotation(existing_segments)
        token_spans = sorted((anchor2pos[start], anchor2pos[end]) for edge in OUT
                             for (start, end) in util.edgeSpans(edge))
        for n, (chunkstart, chunkend) in enumerate(chunk_spans[:]):
            for tokenstart, tokenend in token_spans:
                if tokenend <= chunkstart:
                    continue
                if tokenstart >= chunkend:
                    break
                if chunkstart != tokenstart:
                    chunk_spans.append((chunkstart, tokenstart))
                chunkstart = tokenend
                chunk_spans[n] = (chunkstart, chunkend)
        chunk_spans.sort()
        util.log.info("Reorganized into %d chunks" % len(chunk_spans))
    else:
        OUT = {}

    # Now we can segment each chunk span into tokens
    for start, end in chunk_spans:
        for spanstart, spanend in segmenter.span_tokenize(corpus_text[start:end]):
            spanstart += start
            spanend += start
            if corpus_text[spanstart:spanend].strip():
                span = pos2anchor[spanstart], pos2anchor[spanend]
                edge = util.mkEdge(element, span)
                OUT[edge] = None

    util.write_annotation(out, OUT)


def build_token_wordlist(saldo_model, out, segmenter, model=None, no_pickled_model=False):
    """Build a list of words from a SALDO model, to help BetterTokenizer."""

    if model:
        if not no_pickled_model:
            with open(model, "rb") as M:
                model = pickle.load(M)
        segmenter_args = (model, True)
    else:
        segmenter_args = ()
    assert segmenter in SEGMENTERS, "Available segmenters: %s" % ", ".join(sorted(SEGMENTERS))
    segmenter = SEGMENTERS[segmenter]
    segmenter = segmenter(*segmenter_args)
    assert hasattr(segmenter, "span_tokenize"), "Segmenter needs a 'span_tokenize' method: %r" % segmenter

    wordforms = set()

    # Skip strings already handled by the tokenizer.
    # Also skip words ending in comma (used by some multi word expressions in SALDO).
    with open(saldo_model, "rb") as F:
        lexicon = pickle.load(F)
        for w in lexicon:
            w2 = list(map(saldo._split_triple, lexicon[w]))
            mwu_extras = [contw for w3 in w2 for cont in w3[2] for contw in cont if contw not in lexicon]
            for wf in mwu_extras + [w]:
                spans = list(segmenter.span_tokenize(wf))
                if len(spans) > 1 and not wf.endswith(","):
                    wordforms.add(wf)

    with open(out, mode="w", encoding="utf-8") as outfile:
        outfile.write("\n".join(sorted(wordforms)))


######################################################################
# Punkt word tokenizer

class ModifiedLanguageVars(nltk.tokenize.punkt.PunktLanguageVars):
    """Slight modification to handle unicode quotation marks and other
    punctuation."""
    # http://nltk.googlecode.com/svn/trunk/doc/api/nltk.tokenize.punkt.PunktLanguageVars-class.html
    # http://nltk.googlecode.com/svn/trunk/doc/api/nltk.tokenize.punkt-pysrc.html#PunktLanguageVars

    # Excludes some characters from starting word tokens
    _re_word_start = r'''[^\(\"\'‘’–—“”»\`\\{\/\[:;&\#\*@\)}\]\-,…]'''
    # Characters that cannot appear within words
    _re_non_word_chars = r'(?:[?!)\"“”»–—\\;\/}\]\*:\'‘’\({\[…%])'
    # Used to realign punctuation that should be included in a sentence although it follows the period (or ?, !).
    re_boundary_realignment = re.compile(r'[“”"\')\]}]+?(?:\s+|(?=--)|$)', re.MULTILINE)

    def __init__(self):
        pass


class ModifiedPunktWordTokenizer(object):
    def __init__(self):
        self.lang_vars = ModifiedLanguageVars()
        self.is_post_sentence_token = self.lang_vars.re_boundary_realignment
        self.is_punctuated_token = re.compile(r"\w.*\.$", re.UNICODE)
        self.abbreviations = {"a.a", "a.d", "agr", "a.k.a", "alt", "ang", "anm", "art", "avd", "avl", "b.b", "betr",
                              "b.g", "b.h", "bif", "bl.a", "b.r.b", "b.t.w", "civ.ek", "civ.ing", "co", "dir", "div",
                              "d.m", "doc", "dr", "d.s", "d.s.o", "d.v", "d.v.s", "d.y", "dåv", "d.ä", "e.a.g", "e.d", "eftr", "eg",
                              "ekon", "e.kr", "dyl", "e.d", "em", "e.m", "enl", "e.o", "etc", "e.u", "ev", "ex", "exkl", "f",
                              "farm", "f.d", "ff", "fig", "f.k", "f.kr", "f.m", "f.n", "forts", "fr", "fr.a", "fr.o.m", "f.v.b",
                              "f.v.t", "f.ö", "följ", "föreg", "förf", "gr", "g.s", "h.h.k.k.h.h", "h.k.h", "h.m", "ill",
                              "inkl", "i.o.m", "st.f", "jur", "kand", "kap", "kl", "lb", "leg", "lic", "lisp", "m.a.a",
                              "mag", "m.a.o", "m.a.p", "m.fl", "m.h.a", "m.h.t", "milj", "m.m", "m.m.d", "mom", "m.v.h",
                              "möjl", "n.b", "näml", "nästk", "o", "o.d", "odont", "o.dyl", "omkr", "o.m.s", "op", "ordf",
                              "o.s.a", "o.s.v", "pers", "p.gr", "p.g.a", "pol", "prel", "prof", "rc", "ref", "resp", "r.i.p",
                              "rst", "s.a.s", "sek", "sekr", "sid", "sign", "sistl", "s.k", "sk", "skålp", "s.m", "s.m.s", "sp",
                              "spec", "s.st", "st", "stud", "särsk", "tab", "tekn", "tel", "teol", "t.ex", "tf", "t.h",
                              "tim", "t.o.m", "tr", "trol", "t.v", "u.p.a", "urspr", "utg", "v", "w", "v.d", "å.k",
                              "ä.k.s", "äv", "ö.g", "ö.h", "ök", "övers"}

    def span_tokenize(self, text):
        begin = 0
        for w in self.tokenize(text):
            begin = text.find(w, begin)
            yield begin, begin + len(w)
            begin += len(w)

    def tokenize(self, sentence):
        words = list(self.lang_vars.word_tokenize(sentence))
        if not words:
            return words
        pos = len(words) - 1

        # split sentence-final . from the final word
        # i.e., "peter." "piper." ")" => "peter." "piper" "." ")"
        # but not "t.ex." => "t.ex" "."
        while pos >= 0 and self.is_post_sentence_token.match(words[pos]):
            pos -= 1
        endword = words[pos]
        if self.is_punctuated_token.search(endword):
            endword = endword[:-1]
            if endword not in self.abbreviations:
                words[pos] = endword
                words.insert(pos + 1, ".")

        return words


######################################################################
# Training a Punkt sentence tokenizer

def train_punkt_segmenter(textfiles, modelfile, encoding=util.UTF8, protocol=-1):
    if isinstance(textfiles, str):
        textfiles = textfiles.split()

    util.log.info("Reading files")
    text = u""
    for filename in textfiles:
        with open(filename) as stream:
            text += stream.read().decode(encoding)
    util.log.info("Training model")
    trainer = nltk.tokenize.PunktTrainer(text, verbose=True)
    util.log.info("Saving pickled model")
    params = trainer.get_params()
    with open(modelfile, "wb") as stream:
        pickle.dump(params, stream, protocol=protocol)
    util.log.info("OK")


######################################################################

class LinebreakTokenizer(nltk.RegexpTokenizer):
    def __init__(self):
        nltk.RegexpTokenizer.__init__(self, r'\s*\n\s*', gaps=True)


class PunctuationTokenizer(nltk.RegexpTokenizer):
    """ A very simple sentence tokenizer, separating sentences on
    every .!? no matter the context. Use only when PunktSentenceTokenizer
    does not work, for example when there's no whitespace after punctuation. """

    def __init__(self):
        nltk.RegexpTokenizer.__init__(self, r"[\.!\?]\s*", gaps=True)

    def span_tokenize(self, s):
        result = []
        spans = nltk.RegexpTokenizer.span_tokenize(self, s)
        first = True
        temp = [0, 0]

        for start, _ in spans:
            if not first:
                temp[1] = start
                result.append(tuple(temp))
            temp[0] = start
            first = False

        temp[1] = len(s)
        result.append(tuple(temp))

        return result


class BetterWordTokenizer(object):
    """
    A word tokenizer based on the PunktWordTokenizer code, heavily modified to add support for
    custom regular expressions, wordlists, and external configuration files.
    http://nltk.googlecode.com/svn/trunk/doc/api/nltk.tokenize.punkt.PunktSentenceTokenizer-class.html
    """

    # Format for the complete regular expression to be used for tokenization
    _word_tokenize_fmt = r'''(
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
    )'''

    # Used to realign punctuation that should be included in a sentence although it follows the period (or ?, !).
    re_boundary_realignment = re.compile(r'[“”"\')\]}]+?(?:\s+|(?=--)|$)', re.MULTILINE)

    re_punctuated_token = re.compile(r"\w.*\.$", re.UNICODE)

    def __init__(self, configuration_file, skip_tokenlist=False):
        # Parse configuration file
        self.case_sensitive = False
        self.patterns = {"misc": [], "tokens": []}
        self.abbreviations = set()
        in_abbr = False
        with open(configuration_file, encoding="UTF-8") as conf:
            for line in conf:
                if line.startswith("#") or not line.strip():
                    continue
                if not in_abbr:
                    if not in_abbr and line.strip() == "abbreviations:":
                        in_abbr = True
                        continue
                    else:
                        try:
                            key, val = line.strip().split(None, 1)
                        except ValueError as e:
                            print("Error parsing configuration file:", line)
                            raise e
                        key = key[:-1]

                        if key == "token_list":
                            if skip_tokenlist:
                                continue
                            if not val.startswith("/"):
                                val = os.path.join(os.path.dirname(configuration_file), val)
                            with open(val, encoding="UTF-8") as saldotokens:
                                self.patterns["tokens"] = [re.escape(t.strip()) for t in saldotokens.readlines()]
                        elif key == "case_sensitive":
                            self.case_sensitive = (val.lower() == "true")
                        elif key.startswith("misc_"):
                            self.patterns["misc"].append(val)
                        elif key in ("start", "within", "end"):
                            self.patterns[key] = re.escape(val)
                        elif key in ("multi", "number"):
                            self.patterns[key] = val
                        else:
                            raise ValueError("Unknown option: %s" % key)
                else:
                    self.abbreviations.add(line.strip())

    def _word_tokenizer_re(self):
        """Compiles and returns a regular expression for word tokenization"""
        try:
            return self._re_word_tokenizer
        except AttributeError:
            modifiers = (re.UNICODE | re.VERBOSE) if self.case_sensitive else (re.UNICODE | re.VERBOSE | re.IGNORECASE)
            self._re_word_tokenizer = re.compile(
                self._word_tokenize_fmt %
                {
                    'tokens':   ("(?:" + "|".join(self.patterns["tokens"]) + ")|") if self.patterns["tokens"] else "",
                    'abbrevs':  ("(?:" + "|".join(re.escape(a + ".") for a in self.abbreviations) + ")|") if self.abbreviations else "",
                    'misc':     "|".join(self.patterns["misc"]),
                    'number':   self.patterns["number"],
                    'within':   self.patterns["within"],
                    'multi':    self.patterns["multi"],
                    'start':    self.patterns["start"],
                    'end':      self.patterns["end"]
                },
                modifiers
            )
            return self._re_word_tokenizer

    def word_tokenize(self, s):
        """Tokenize a string to split off punctuation other than periods"""
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

    def span_tokenize(self, s):
        begin = 0
        for w in self.word_tokenize(s):
            begin = s.find(w, begin)
            yield begin, begin + len(w)
            begin += len(w)


class CRFTokenizer(object):
    """ Tokenization based on Conditional Random Fields
        Implemented for Old Swedish, see crf.py for more details"""

    def __init__(self, model):
        self.model = model

    def span_tokenize(self, s):
        return crf.segment(s, self.model)


class FSVParagraphSplitter(object):
    """ A paragraph splitter for old Swedish. """

    def __init__(self):
        pass

    def span_tokenize(self, s):
        spans = []
        temp = [0, 0]
        first = True
        for i in range(len(s)):
            if not first:
                new_para = re.search(u'^\.*§', s[i:])
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


######################################################################

SEGMENTERS = dict(whitespace=nltk.WhitespaceTokenizer,
                  linebreaks=LinebreakTokenizer,
                  blanklines=nltk.BlanklineTokenizer,
                  punkt_sentence=nltk.PunktSentenceTokenizer,
                  punkt_word=ModifiedPunktWordTokenizer,
                  punctuation=PunctuationTokenizer,
                  better_word=BetterWordTokenizer,
                  crf=CRFTokenizer,
                  simple_word_punkt=nltk.WordPunctTokenizer,
                  fsv_paragraph=FSVParagraphSplitter
                  )

if not do_segmentation.__doc__:
    do_segmentation.__doc__ = ""
do_segmentation.__doc__ += "The following segmenters are available: %s" % ", ".join(sorted(SEGMENTERS))


if __name__ == '__main__':
    util.run.main(do_segmentation,
                  train_punkt_segmenter=train_punkt_segmenter,
                  build_token_wordlist=build_token_wordlist)
