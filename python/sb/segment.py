# -*- coding: utf-8 -*-

import re
import util
import nltk
import cPickle as pickle

def do_segmentation(text, element, out, chunk, segmenter, existing_segments=None, model=None):
    """Segment all "chunks" (e.g. sentences) into smaller "tokens" (e.g. words),
    and annotate them as "element" (e.g. w).
    Segmentation is done by the given "segmenter"; some segmenters take
    an extra argument which is a pickled "model" object.
    """
    if model:
        with open(model, "rb") as M:
            model = pickle.load(M)
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
    CHUNK = util.read_annotation(chunk)
    positions = set(anchor2pos[anchor] for edge in CHUNK
                    for span in util.edgeSpans(edge) for anchor in span)
    positions = sorted(set([0,len(corpus_text)]) | positions)
    chunk_spans = zip(positions, positions[1:])

    if existing_segments:
        OUT = util.read_annotation(existing_segments)
        token_spans = sorted((anchor2pos[start], anchor2pos[end]) for edge in OUT
                             for (start, end) in util.edgeSpans(edge))
        for n, (chunkstart, chunkend) in enumerate(chunk_spans[:]):
            for tokenstart, tokenend in token_spans:
                if tokenend <= chunkstart: continue
                if tokenstart >= chunkend: break
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


######################################################################
# Punkt word tokenizer

class ModifiedPunktWordTokenizer(object):
    def __init__(self, punkt_params):
        assert isinstance(punkt_params, nltk.tokenize.punkt.PunktParameters), "Not a punkt model: %r" % punkt_params
        segmenter = nltk.PunktSentenceTokenizer(punkt_params)
        self.lang_vars = segmenter._lang_vars
        self.is_post_sentence_token = self.lang_vars.re_boundary_realignment
        self.is_punctuated_token = re.compile(r"\w.*\.$", re.UNICODE)
        self.is_quoted_token = re.compile(r"^\'.*[\w\.]", re.UNICODE)
        self.abbreviations = segmenter._params.abbrev_types

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
                words.insert(pos+1, ".")
        
        # a hack for splitting ' from beginning of words
        # (which the default Punkt English tokenizer doesn't do)
        # i.e., "'hej" => "'" "hej"
        # we do it backwards since we are modifying the list in place
        while pos >= 0:
            word = words[pos]
            if self.is_quoted_token.match(word):
                words[pos] = word[1:]
                words.insert(pos, "'")
            pos -= 1
                
        return words


######################################################################
# Training a Punkt sentence tokenizer

PICKLE_PROTOCOL = 2

def train_punkt_segmenter(textfiles, modelfile, encoding=util.UTF8):
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
        pickle.dump(params, stream, PICKLE_PROTOCOL)
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

SEGMENTERS = dict(whitespace = nltk.WhitespaceTokenizer,
                  linebreaks = LinebreakTokenizer,
                  blanklines = nltk.BlanklineTokenizer,
                  punkt_sentence = nltk.PunktSentenceTokenizer,
                  punkt_word = ModifiedPunktWordTokenizer,
                  punctuation = PunctuationTokenizer
                  )

if not do_segmentation.__doc__:
    do_segmentation.__doc__ = ""
do_segmentation.__doc__ += "The following segmenters are available: %s" % ", ".join(sorted(SEGMENTERS))


if __name__ == '__main__':
    util.run.main(do_segmentation)
