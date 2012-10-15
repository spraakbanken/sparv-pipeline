# -*- coding: utf-8 -*-

"""
Adds annotations from Saldo.
"""

import util
import itertools
import cPickle as pickle
import re

######################################################################
# Annotate.

def annotate(word, msd, sentence, reference, out, annotations, model,
             delimiter="|", affix="|", precision=":%.3f", filter=None, skip_multiword=False, lexicon=None):
    """Use the Saldo lexicon model to annotate pos-tagged words.
      - word, msd are existing annotations for wordforms and part-of-speech
      - sentence is an existing annotation for sentences and their children (words)
      - reference is an existing annotation for word references, to be used when
        annotating multi-word units
      - out is a string containing a whitespace separated list of the resulting annotation files
      - annotations is a string containing a whitespace separate list of annotations to be written.
        Number of annotations and their order must correspond to the list in the 'out' argument.
      - model is the Saldo model
      - membrane_address could be specified if you have a server running with this model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
      - precision is a format string for how to print the precision for each annotation
        (use empty string for no precision)
      - filter is an optional filter, currently there are the following values:
        max: only use the annotations that are most probable
        first: only use one annotation; one of the most probable
      - skip_multiword can be set to True to disable multi word annotations
      - lexicon: this argument cannot be set from the command line,
        but is used in the catapult. this argument must be last
    """

    if not lexicon:
        lexicon = SaldoLexicon(model)

    MAX_GAPS = 1 # Maximum number of gaps in multi-word units.

    annotations = annotations.split()
    out = out.split()
    assert len(out) == len(annotations), "Number of target files and annotations must be the same"

    skip_multiword = (skip_multiword or (isinstance(skip_multiword, basestring) and skip_multiword.lower() == "true"))

    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)
    REF = util.read_annotation(reference)
    for out_file in out:
        util.clear_annotation(out_file)

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    OUT = {}

    for sent in sentences:
        incomplete_multis = []
        complete_multis = []
        sentence_tokens = {}

        for tokid in sent:
            theword = WORD[tokid]
            msdtag = MSD[tokid]
            ref = REF[tokid]

            annotation_info = {}
            sentence_tokens[ref] = {"tokid": tokid, "word": theword, "msd": msdtag, "annotations": annotation_info}

            ######################################################################
            # First use MSD tags to find the most probable single word annotations

            ann_tags_words = lexicon.lookup(theword)
            annotation_precisions = [(get_precision(msdtag, msdtags), annotation)
                                        for (annotation, msdtags, wordslist, _) in ann_tags_words if not wordslist]
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
                for (prec, annotation) in annotation_precisions:
                    for key in annotation:
                        annotation_info.setdefault(key, []).extend([a + precision % prec for a in annotation[key]])
            else:
                for (prec, annotation) in annotation_precisions:
                    for key in annotation:
                        annotation_info.setdefault(key, []).extend(annotation[key])


            #######################################################
            # The rest is for multi-word expressions

            todelfromincomplete = []

            for i, x in enumerate(incomplete_multis):
                seeking_word = x[1][0] # The next word we are looking for in this multi-word expression

                if seeking_word == "*":
                    if x[1][1].lower() == theword.lower():
                        seeking_word = x[1][1]
                        del x[1][0]

                if x[4][1] > MAX_GAPS:
                    todelfromincomplete.append(i)
                #                                           |  Last word may not be PP if this is a particle-multi-word |
                elif seeking_word.lower() == theword.lower() and not (len(x[1]) == 1 and x[3] and msdtag.startswith("PP")):
                    x[4][0] = False
                    del x[1][0]
                    x[2].append(ref)

                    # Is current word the last word we are looking for?
                    if len(x[1]) == 0:
                        todelfromincomplete.append(i)
                        complete_multis.append((x[2], x[0]))
                else:
                    # Increment gap counter if previous word was not part of a gap
                    if not x[4][0]:
                        x[4][1] += 1
                    x[4][0] = True # Marking that previous word was part of a gap

            for x in todelfromincomplete[::-1]:
                del incomplete_multis[x]

            if not skip_multiword:
                # Is this word a possible start for multi-word units?
                looking_for = [(annotation, words, [ref], is_particle, [False, 0]) for (annotation, _, wordslist, is_particle) in ann_tags_words if wordslist for words in wordslist]
                if len(looking_for) > 0:
                    incomplete_multis.extend(looking_for)

            # Loop to next token

        # Check that we don't have any unwanted overlaps
        remove = set()
        for ci, c in enumerate(complete_multis):
            for d in complete_multis:
                if re.search(r"\.(\w\wm)\.", c[1]["lem"][0]).groups()[0] == re.search(r"\.(\w\wm)\.", d[1]["lem"][0]).groups()[0]:
                    # Both are of same POS
                    if d[0][0] < c[0][0] and d[0][-1] > c[0][0] and d[0][-1] < c[0][-1]:
                        # A case of x1 y1 x2 y2. Remove y.
                        remove.add(ci)
                    elif c[0][0] < d[0][0] and d[0][-1] == c[0][-1]:
                        #A case of x1 y1 xy2. Remove x.
                        remove.add(ci)

        for c in sorted(remove, reverse=True):
            del complete_multis[c]

        for c in complete_multis:
            first = True
            first_ref = ""
            for tok_ref in c[0]:
                if first:
                    first_ref = tok_ref
                for ann, val in c[1].items():
                    if not first:
                        val = [x + ":" + first_ref for x in val]
                    sentence_tokens[tok_ref]["annotations"].setdefault(ann, []).extend(val)
                first = False

        for token in sentence_tokens.values():
            OUT[token["tokid"]] = _join_annotation(token["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_file, annotation in zip(out, annotations):
        util.write_annotation(out_file, [(tok, OUT[tok].get(annotation, affix)) for tok in OUT], append=True)

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
        Returns a list of (annotation-dictionary, list-of-pos-tags, list-of-lists-with-words).
        """
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return map(_split_triple, annotation_tag_pairs)

    @staticmethod
    def save_to_picklefile(saldofile, lexicon, protocol=1, verbose=True):
        """Save a Saldo lexicon to a Pickled file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {{annotation-type: annotation}: (set(possible tags), set(tuples with following words), is-particle-verb-boolean)}}
        """
        if verbose: util.log.info("Saving Saldo lexicon in Pickle format")

        picklex = {}
        for word in lexicon:
            annotations = []
            for annotation, extra in lexicon[word].items():
                #annotationlist = PART_DELIM3.join(annotation)
                annotationlist = PART_DELIM2.join( k + PART_DELIM3 + PART_DELIM3.join(annotation[k]) for k in annotation)
                taglist =        PART_DELIM3.join(sorted(extra[0]))
                wordlist =       PART_DELIM2.join([PART_DELIM3.join(x) for x in sorted(extra[1])])
                particle =       "1" if extra[2] else "0"
                annotations.append( PART_DELIM1.join([annotationlist, taglist, wordlist, particle]) )

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


def _join_annotation(annotation, delimiter, affix):
    seen = set()
    return dict([(a, affix + delimiter.join(b for b in annotation[a] if not b in seen and not seen.add(b)) + affix) for a in annotation])

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
            0.66 if "." in msd and [partial for partial in msdtags if partial.startswith(msd[:msd.find(".")])] else
            0.25)


def normalize_precision(annotations):
    """Normalize the rankings in the annotation list so that the sum is 1."""
    total_precision = sum(prec for (prec, _annotation) in annotations)
    return [(prec/total_precision, annotation) for (prec, annotation) in annotations]



# This delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"

def _split_triple(annotation_tag_words):
    annotation, tags, words, particle = annotation_tag_words.split(PART_DELIM1)
    #annotationlist = [x for x in annotation.split(PART_DELIM3) if x]
    annotationdict = {}
    for a in annotation.split(PART_DELIM2):
        key, values = a.split(PART_DELIM3, 1)
        annotationdict[key] = values.split(PART_DELIM3)

    taglist = [x for x in tags.split(PART_DELIM3) if x]
    wordlist = [x.split(PART_DELIM3) for x in words.split(PART_DELIM2) if x]

    return annotationdict, taglist, wordlist, particle == "1"


######################################################################
# converting between different file formats

class hashabledict(dict):
    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))
    def __hash__(self):
        return hash(self.__key())
    def __eq__(self, other):
        return self.__key() == other.__key()

def read_xml(xml='saldom.xml', annotation_elements='gf lem saldo', tagset='SUC', verbose=True):
    """Read the XML version of SALDO's morphological lexicon (saldom.xml).
    Return a lexicon dictionary, {wordform: {{annotation-type: annotation}: ( set(possible tags), set(tuples with following words) )}}
     - annotation_element is the XML element for the annotation value (currently: 'gf' for baseform, 'lem' for lemgram or 'saldo' for SALDO id)
     - tagset is the tagset for the possible tags (currently: 'SUC', 'Parole', 'Saldo')
    """
    annotation_elements = annotation_elements.split()
    #assert annotation_element in ("gf", "lem", "saldo"), "Invalid annotation element"
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
                annotations = hashabledict()

                for a in annotation_elements:
                    annotations[a] = tuple(x.text for x in elem.findall(a))

                pos = elem.findtext("pos")
                inhs = elem.findtext("inhs")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()

                p = elem.findtext("p")
                x_find = re.search(r"_x(\d*)_", p)
                x_insert = x_find.groups()[0] if x_find else None
                if x_insert == "": x_insert = "1"

                table = elem.find("table")
                multiwords = []

                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")

                    if param in ("frag", "c", "ci", "cm"):
                        continue
                    elif param[-1].isdigit() and param[-1] != "1":
                        # Handle multi-word expressions
                        multiwords.append(word)
                        multipart, multitotal = param.split(":")[-1].split("-")
                        particle = bool(re.search(r"vbm_.+?p.*?\d+_", p)) # Multi-word with particle

                        if x_insert and multipart == x_insert:
                            multiwords.append("*")

                        if multipart == multitotal:
                            lexicon.setdefault(multiwords[0], {}).setdefault(annotations, (set(), set(), particle))[1].add(tuple(multiwords[1:]))
                            multiwords = []
                    else:
                        # Single word expressions
                        if param[-1] == "1":
                            param = param.rsplit(" ", 1)[0]
                            if pos == "vbm": pos = "vb"
                        saldotag = " ".join([pos] + inhs + [param])
                        tags = tagmap.get(saldotag)
                        if tags:
                            lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False))[0].update(tags)

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


def xml_to_pickle(xml, filename, annotation_elements="gf lem saldo"):
    """Read an XML dictionary and save as a pickle file."""

    xml_lexicon = read_xml(xml, annotation_elements)
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(annotate, xml_to_pickle=xml_to_pickle)
