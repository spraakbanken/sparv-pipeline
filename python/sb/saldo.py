# -*- coding: utf-8 -*-

"""
A very simple lemmatizer based on Saldo.
"""

import util
import os
import itertools
import cPickle as pickle

def lemmatize(word, msd, out, model, delimiter=" ", affix="", precision=":%.3f", filter=None):
    """Use the Saldo lexicon model to lemmatize pos-tagged words.
      - word, msd are existing annotations for wordforms and part-of-speech
      - out is the resulting annotation file
      - model is the Saldo model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
      - precision is a format string for how to print the precision for each lemma
        (use empty string for no precision)
      - filter is an optional filter, currently there are the following values:
        max: only use the lemmas that are most probable
        first: only use one lemma; one of the most probable
    """
    lexicon = SaldoLexicon(model)
    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)
    OUT = {}
    for tokid, theword in WORD.iteritems():
        msdtag = MSD[tokid]
        lemma_msdtags = lexicon.lookup(theword)
        lemma_precisions = [(get_precision(lemma, msdtag, msdtags), lemma)
                  for (lemma, msdtags) in lemma_msdtags]
        lemma_precisions = normalize_precision(lemma_precisions)
        lemma_precisions.sort(reverse=True)
        if filter and lemma_precisions:
            if filter == "first":
                lemma_precisions = lemma_precisions[:1]
            elif filter == "max":
                maxprec = lemma_precisions[0][0]
                ismax = lambda lemprec: lemprec[0] >= maxprec - PRECISION_DIFF
                lemma_precisions = itertools.takewhile(ismax, lemma_precisions)
        if precision:
            lemmainfo = [lemma + precision % prec
                         for (prec, lemma) in lemma_precisions]
        else:
            lemmainfo = [lemma for (prec, lemma) in lemma_precisions]
        OUT[tokid] = affix + delimiter.join(lemmainfo) + affix
    util.write_annotation(out, OUT)


# The minimun precision difference for two lemmas to be considered equal
PRECISION_DIFF = 0.01


def get_precision(lemma, msd, msdtags):
    """
    A very simple way of calculating the precision of a Saldo lemma:
    if the the word's msdtag is among the lemma's possible msdtags,
    we return a high value (0.75), otherwise a low value (0.25).
    """
    return (0.5 if msd is None else
            0.75 if msd in msdtags else
            0.25)


def normalize_precision(lemmas):
    """Normalize the rankings in the lemma list so that the sum is 1."""
    total_precision = sum(prec for (prec, _lemma) in lemmas)
    return [(prec/total_precision, lemma) for (prec, lemma) in lemmas]


######################################################################
# Different kinds of lexica

class SaldoLexicon(object):
    """A lexicon for Saldo lookups.
    It is initialized from a Pickled file, or a space-separated text file.
    """
    def __init__(self, saldofile, verbose=True):
        if verbose: util.log.info("Reading Saldo lexicon: %s", saldofile)
        if saldofile.endswith('.pickle'):
            with open(saldofile, "rb") as F:
                self.lexicon = pickle.load(F)
        else:
            lexicon = self.lexicon = {}
            with open(saldofile, "rb") as F:
                for line in F:
                    row = line.decode(util.UTF8).split()
                    word = row.pop(0)
                    lexicon[word] = row
        if verbose: util.log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word):
        """Lookup a word in the lexicon.
        Returns a list of (lemma, list-of-pos-tags).
        """
        lemma_tag_pairs = self.lexicon.get(word) or self.lexicon.get(word.lower()) or []
        return map(_split_lemmatagpair, lemma_tag_pairs)

    @staticmethod
    def save_to_picklefile(saldofile, lexicon, protocol=1, verbose=True):
        """Save a Saldo lexicon to a Pickled file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {lemma: set(possible tags)}}
        """
        if verbose: util.log.info("Saving Saldo lexicon in Pickle format")
        picklex = {}
        for word in lexicon:
            lemmas = [POSTAG_DELIM.join([lemma] + sorted(postags))
                      for lemma, postags in lexicon[word].items()]
            picklex[word] = sorted(lemmas)
        with open(saldofile, "wb") as F:
            pickle.dump(picklex, F, protocol=protocol)
        if verbose: util.log.info("OK, saved")

    @staticmethod
    def save_to_textfile(saldofile, lexicon, verbose=True):
        """Save a Saldo lexicon to a space-separated text file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {lemma: set(possible tags)}}
        """
        if verbose: util.log.info("Saving Saldo lexicon in text format")
        with open(saldofile, "w") as F:
            for word in sorted(lexicon):
                lemmas = [POSTAG_DELIM.join([lemma] + sorted(postags))
                          for lemma, postags in lexicon[word].items()]
                print >>F, " ".join([word] + lemmas).encode(util.UTF8)
        if verbose: util.log.info("OK, saved")


# This is a delimiter that hopefully is never found in a lemma or in a POS tag:
POSTAG_DELIM = "^"

def _split_lemmatagpair(lemma_tags):
    lemma_tags = lemma_tags.split(POSTAG_DELIM)
    lemma = lemma_tags.pop(0)
    return lemma, lemma_tags


######################################################################
# converting between different file formats

def read_json(json, lemma_key='head', tagset='SUC', verbose=True):
    """Read the json version of Saldo.
    Return a lexicon dictionary, {wordform: {lemma: set(possible tags)}}
     - lemma_key is the json key for the lemma (currently: 'head' for baseform or 'id' for lemgram)
     - tagset is the tagset for the possible tags (currently: 'SUC', 'Parole', 'Saldo')
    """
    import cjson
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower())
    if verbose: util.log.info("Reading JSON lexicon")
    lexicon = {}
    with open(json, "r") as F:
        for line in F:
            item = cjson.decode(line.decode(util.UTF8))
            word, lemma, pos, param, inhs = item['word'], item[lemma_key], item['pos'], item['param'], item['inhs']
            saldotag = " ".join([pos] + inhs + [param])
            tags = tagmap.get(saldotag)
            if tags:
                lexicon.setdefault(word, {}).setdefault(lemma, set()).update(tags)
    test_lemmas(lexicon)
    if verbose: util.log.info("OK, read")
    return lexicon

def read_xml(xml, value_element='gf', tagset='SUC', verbose=True):
    """Read the XML version of Saldo.
    Return a lexicon dictionary, {wordform: {value: set(possible tags)}}
     - value_element is the XML element for the value (currently: 'gf' for baseform, 'lem' for lemgram or 'saldo' for SALDO id)
     - tagset is the tagset for the possible tags (currently: 'SUC', 'Parole', 'Saldo')
     
    Does not handle multi word entries yet, but we don't keep them anyway.
    """
    value_element = value_element.replace("head", "gf").replace("id", "lem")
    import xml.etree.cElementTree as cet
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower())
    if verbose: util.log.info("Reading XML lexicon")
    lexicon = {}
    
    context = cet.iterparse(xml, events=("start", "end"))
    context = iter(context)
    event, root = context.next()
    i = 0
    for event, elem in context:
        i += 1
        if event == "end":
            if elem.tag == 'LexicalEntry':
                valuelist = elem.findall(value_element)
                if valuelist:
                    value = "|".join(v.text for v in valuelist)
                else:
                    assert False, "Missing value"
                    value = "UNKNOWN"
                pos = elem.findtext("pos")
                inhs = elem.findtext("inhs")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()
                table = elem.find("table")
                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")
                    saldotag = " ".join([pos] + inhs + [param])
                    tags = tagmap.get(saldotag)
                    if tags:
                        lexicon.setdefault(word, {}).setdefault(value, set()).update(tags)
            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()
    
    test_lemmas(lexicon)
    if verbose: util.log.info("OK, read")
    return lexicon
    

def save_to_cstlemmatizer(cstfile, lexicon, encoding="latin-1", verbose=True):
    """Save a JSON lexicon as an external file that can be used for
    training the CST lemmatizer. The default encoding of the resulting
    file is ISO-8859-1 (Latin-1).
    """
    if verbose: util.log.info("Saving CST lexicon")
    with open(cstfile, "w") as F:
        for word in sorted(lexicon):
            for lemma in sorted(lexicon[word]):
                for postag in sorted(lexicon[word][lemma]):
                    # the order between word, lemma, postag depends on
                    # the argument -c to cstlemma, this order is -cBFT:
                    line = "%s\t%s\t%s" % (word, lemma, postag)
                    print >> F, line.encode(encoding)
    if verbose: util.log.info("OK, saved")


######################################################################
# additional utilities

def extract_tags(lexicon):
    """Extract the set of all tags that are used in a lexicon.
    The input lexicon should be a dict:
      - lexicon = {wordform: {lemma: set(possible tags)}}
    """
    tags = set()
    for lemmas in lexicon.values():
        tags.update(*lemmas.values())
    return tags


def test_lemmas(lexicon):
    for key in testwords:
        util.log.output("%s = %s", key, lexicon.get(key))

testwords = [u"äggtoddyarna",
             u"Linköpingsbors",
             u"katabatiska",
             u"väg-",
             u"formar",
             u"in"]


######################################################################

if __name__ == '__main__':
    util.run.main(lemmatize, read_xml=read_xml)



