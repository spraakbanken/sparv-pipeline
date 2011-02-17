# -*- coding: utf-8 -*-

"""
Adds annotations from Saldo.
"""

import util
import itertools
import cPickle as pickle

def annotate(word, msd, sentence, reference, out, model, delimiter="|", affix="|", precision=":%.3f", filter=None):
    """Use the Saldo lexicon model to annotate pos-tagged words.
      - word, msd are existing annotations for wordforms and part-of-speech
      - sentence is an existing annotation for sentences and their children (words)
      - reference is an existing annotation for word references, to be used when
        annotating multi-word units
      - out is the resulting annotation file
      - model is the Saldo model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
      - precision is a format string for how to print the precision for each annotation
        (use empty string for no precision)
      - filter is an optional filter, currently there are the following values:
        max: only use the annotations that are most probable
        first: only use one annotation; one of the most probable
    """
    lexicon = SaldoLexicon(model)
    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)
    REF = util.read_annotation(reference)
    OUT = {}
    outstack = {}
    
    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    
    #tok_word = WORD.iteritems()
    #order_dict = util.read_annotation(order)
    #tok_word = sorted(tok_word, key=lambda x: order_dict.get(x[0]))
    #for tokid, theword in tok_word:
    
    for sent in sentences:
        for tokid in sent:
            theword = WORD[tokid]
    
            msdtag = MSD[tokid]
            ann_tags_words = lexicon.lookup(theword)
            annotation_precisions = [(get_precision(msdtag, msdtags), annotation)
                                        for (annotation, msdtags, words) in ann_tags_words if not words]
            annotation_precisions = normalize_precision(annotation_precisions)
            annotation_precisions.sort(reverse=True)
                    
            if filter and annotation_precisions:
                if filter == "first":
                    annotation_precisions = annotation_precisions[:1]
                elif filter == "max":
                    maxprec = annotation_precisions[0][0]
                    ismax = lambda lemprec: lemprec[0] >= maxprec - PRECISION_DIFF
                    annotation_precisions = itertools.takewhile(ismax, annotation_precisions)
            
            if precision:
                annotation_info = [a + precision % prec
                                   for (prec, annotation) in annotation_precisions
                                    for a in annotation]
            else:
                annotation_info = [a for (prec, annotation) in annotation_precisions
                                   for a in annotation]
                    
            looking_for = [(annotation, words, REF[tokid]) for (annotation, _, wordslist) in ann_tags_words if wordslist for words in wordslist]
            
            for waiting in outstack.keys():
                todel = []
                i = 0
        
                for x in outstack[waiting]["looking_for"]:
                    seeking_word = x[1][0]
                    if seeking_word == theword or seeking_word.lower() == theword.lower() or seeking_word == "*":
                        del x[1][0]
                        
                        if not seeking_word == "*":
                            if len(x[1]) == 0:
                                # Current word is the last word we're looking for
                                todel.append(i)
                                if x[2]:
                                    annotation_info.extend(a + ":" + x[2] for a in x[0])
                                outstack[waiting]["annotation"].extend(x[0])
                            elif x[2]:
                                looking_for.append( ([a + ":" + x[2] for a in x[0]], x[1][:], "") )
                    else:
                        todel.append(i)
        
                    i += 1
                    
                for x in todel[::-1]:
                    del outstack[waiting]["looking_for"][x]
                
                if len(outstack[waiting]["looking_for"]) == 0:
                    OUT[waiting] = affix + delimiter.join(outstack[waiting]["annotation"]) + affix if outstack[waiting]["annotation"] else affix
                    del outstack[waiting]
            
            if len(looking_for) > 0:
                outstack.setdefault(tokid, {})["theword"] = theword
                outstack[tokid]["annotation"] = annotation_info
                outstack[tokid]["looking_for"] = looking_for
            else:
                OUT[tokid] = affix + delimiter.join(annotation_info) + affix if annotation_info else affix

        # Finish everything on the outstack, since we don't want to look for matches outside the current sentence.
        for leftover in outstack.keys():
            OUT[leftover] = affix + delimiter.join(outstack[leftover]["annotation"]) + affix if outstack[leftover]["annotation"] else affix
            del outstack[leftover]

    util.write_annotation(out, OUT)


# The minimun precision difference for two annotations to be considered equal
PRECISION_DIFF = 0.01


def get_precision(msd, msdtags):
    """
    A very simple way of calculating the precision of a Saldo annotation:
    if the the word's msdtag is among the annotation's possible msdtags,
    we return a high value (0.75), otherwise a low value (0.25).
    """
    return (0.5 if msd is None else
            0.75 if msd in msdtags else
            0.25)


def normalize_precision(annotations):
    """Normalize the rankings in the annotation list so that the sum is 1."""
    total_precision = sum(prec for (prec, _annotation) in annotations)
    return [(prec/total_precision, annotation) for (prec, annotation) in annotations]


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
        Returns a list of (annotation, list-of-pos-tags, list-of-tuples-with-words).
        """
        annotation_tag_pairs = self.lexicon.get(word) or self.lexicon.get(word.lower()) or []
        return map(_split_triple, annotation_tag_pairs)

    @staticmethod
    def save_to_picklefile(saldofile, lexicon, protocol=1, verbose=True):
        """Save a Saldo lexicon to a Pickled file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {(annotation): (set(possible tags), set(tuples with following words))}}
        """
        if verbose: util.log.info("Saving Saldo lexicon in Pickle format")
        
        picklex = {}
        for word in lexicon:
            annotations = []
            for annotation, extra in lexicon[word].items():
                annotationlist = PART_DELIM3.join(annotation)
                taglist =        PART_DELIM3.join(sorted(extra[0]))
                wordlist =       PART_DELIM2.join([PART_DELIM3.join(x) for x in sorted(extra[1])])
                annotations.append( PART_DELIM1.join([annotationlist, taglist, wordlist]) )
            
            picklex[word] = sorted(annotations)
        
        with open(saldofile, "wb") as F:
            pickle.dump(picklex, F, protocol=protocol)
        if verbose: util.log.info("OK, saved")

    @staticmethod
    def save_to_textfile(saldofile, lexicon, verbose=True):
        """Save a Saldo lexicon to a space-separated text file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {annotation: set(possible tags)}}
        NOT UP TO DATE
        """
        if verbose: util.log.info("Saving Saldo lexicon in text format")
        with open(saldofile, "w") as F:
            for word in sorted(lexicon):
                annotations = [PART_DELIM.join([annotation] + sorted(postags))
                          for annotation, postags in lexicon[word].items()]
                print >>F, " ".join([word] + annotations).encode(util.UTF8)
        if verbose: util.log.info("OK, saved")


# This delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"

def _split_triple(annotation_tag_words):
    annotation, tags, words = annotation_tag_words.split(PART_DELIM1)
    annotationlist = [x for x in annotation.split(PART_DELIM3) if x]
    taglist = [x for x in tags.split(PART_DELIM3) if x]
    wordlist = [x.split(PART_DELIM3) for x in words.split(PART_DELIM2) if x]
    
    return annotationlist, taglist, wordlist


######################################################################
# converting between different file formats

def read_xml(xml='saldom.xml', annotation_element='gf', tagset='SUC', verbose=True):
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).
    Return a lexicon dictionary, {wordform: {(annotation): ( set(possible tags), set(tuples with following words) )}}
     - annotation_element is the XML element for the annotation value (currently: 'gf' for baseform, 'lem' for lemgram or 'saldo' for SALDO id)
     - tagset is the tagset for the possible tags (currently: 'SUC', 'Parole', 'Saldo')
    """
    assert annotation_element in ("gf", "lem", "saldo"), "Invalid annotation element"
    import xml.etree.cElementTree as cet
    import re
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower())
    if verbose: util.log.info("Reading XML lexicon")
    lexicon = {}
    
    context = cet.iterparse(xml, events=("start", "end")) # "start" needed to save reference to root element
    context = iter(context)
    event, root = context.next()

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':
                annotation = tuple(x.text for x in elem.findall(annotation_element))
                if not annotation:
                    assert False, "Missing annotation"
                    annotation = "UNKNOWN"
                pos = elem.findtext("pos")
                inhs = elem.findtext("inhs")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()
                
                x_find = re.search(r"_x(\d+)_", elem.findtext("p"))
                x_insert = x_find.groups()[0] if x_find else None
                
                table = elem.find("table")
                multiwords = []
                
                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")
                    
                    if param[-1].isdigit() and param[-1] != "1":
                        # Handle multi-word expressions
                        multiwords.append(word)
                        multipart, multitotal = param.split(":")[-1].split("-")
                        
                        if x_insert and multipart == x_insert:
                            multiwords.append("*")
                        
                        if multipart == multitotal:
                            lexicon.setdefault(multiwords[0], {}).setdefault(annotation, (set(), set()))[1].add(tuple(multiwords[1:]))
                            multiwords = []
                    else:
                        # Single word expressions
                        if param[-1] == "1":
                            param = param.rsplit(" ", 1)[0]
                        saldotag = " ".join([pos] + inhs + [param])
                        tags = tagmap.get(saldotag)
                        if tags:
                            lexicon.setdefault(word, {}).setdefault(annotation, (set(), set()))[0].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()
    
    test_annotations(lexicon)
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
      - lexicon = {wordform: {annotation: set(possible tags)}}
    """
    tags = set()
    for annotations in lexicon.values():
        tags.update(*annotations.values())
    return tags


def test_annotations(lexicon):
    for key in testwords:
        util.log.output("%s = %s", key, lexicon.get(key))

testwords = [u"äggtoddyarna",
             u"Linköpingsbors",
             u"katabatiska",
             u"väg-",
             u"formar",
             u"in"]


def xml_to_pickle(xml, annotation_element, filename):
    """Read an XML dictionary and save as a pickle file."""
    
    xml_lexicon = read_xml(xml, annotation_element)
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(annotate, xml_to_pickle=xml_to_pickle)
