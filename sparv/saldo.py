# -*- coding: utf-8 -*-

"""
Adds annotations from Saldo.
"""

import sparv.util as util
import itertools
import pickle
import re
import os

######################################################################
# Annotate.


def annotate(word, sentence, reference, out, annotations, models, msd="",
             delimiter="|", affix="|", precision=":%.3f", precision_filter=None, min_precision=0.0,
             skip_multiword=False, allow_multiword_overlap=False, word_separator="", lexicons=None):
    """Use the Saldo lexicon model (and optionally other older lexicons) to annotate pos-tagged words.
      - word, msd are existing annotations for wordforms and part-of-speech
      - sentence is an existing annotation for sentences and their children (words)
      - reference is an existing annotation for word references, to be used when
        annotating multi-word units
      - out is a string containing a whitespace separated list of the resulting annotation files
      - annotations is a string containing a whitespace separated list of annotations to be written.
        Currently: gf (=baseform), lem (=lemgram), saldo
        Number of annotations and their order must correspond to the list in the 'out' argument.
      - models is a list of pickled lexica, typically the Saldo model (saldo.pickle) and optional old lexicons
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
      - precision is a format string for how to print the precision for each annotation
        (use empty string for no precision)
      - precision_filter is an optional filter, currently there are the following values:
        max: only use the annotations that are most probable
        first: only use the most probable annotation (or one of the most probable if more than one)
        none: use all annotations
      - min_precision: only use annotations with a probability score higher than this
      - skip_multiword can be set to True to disable multi word annotations
      - allow_multiword_overlap: by default we do some cleanup among overlapping multi word annotations.
        By setting this to True, all overlaps will be allowed.
      - word_separator is an optional character used to split the values of "word" into several word variations.
      - lexicons: this argument cannot be set from the command line,
        but is used in the catapult. This argument must be last.
    """

    # Allow use of multiple lexicons
    models = [(os.path.basename(m).rstrip(".pickle"), m) for m in models.split()]
    if not lexicons:
        lexicon_list = [(name, SaldoLexicon(lex)) for name, lex in models]
    # Use pre-loaded lexicons (from catapult)
    else:
        lexicon_list = []
        for name, _lex in models:
            assert lexicons.get(name, None) is not None, "Lexicon %s not found!" % name
            lexicon_list.append((name, lexicons[name]))

    MAX_GAPS = 1  # Maximum number of gaps in multi-word units.
                  # Set to 0 for hist-mode? since many (most?) multi-word in the old lexicons are unseparable (half öre etc)

    annotations = annotations.split()
    out = out.split()
    assert len(out) == len(annotations), "Number of target files and annotations must be the same"

    if isinstance(skip_multiword, str):
        skip_multiword = (skip_multiword.lower() == "true")
    if skip_multiword:
        util.log.info("Skipping multi word annotations")

    if isinstance(allow_multiword_overlap, str):
        allow_multiword_overlap = (allow_multiword_overlap.lower() == "true")

    min_precision = float(min_precision)

    # If min_precision is 0, skip almost all part-of-speech checking (verb multi-word expressions still won't be allowed to span over other verbs)
    skip_pos_check = (min_precision == 0.0)

    WORD = util.read_annotation(word)
    REF = util.read_annotation(reference)
    if msd:
        MSD = util.read_annotation(msd)
    for out_file in out:
        util.clear_annotation(out_file)

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    OUT = {}

    for sent in sentences:
        incomplete_multis = []  # [{annotation, words, [ref], is_particle, lastwordWasGap, numberofgaps}]
        complete_multis = []    # ([ref], annotation)
        sentence_tokens = {}

        for tokid in sent:
            theword = WORD[tokid]
            ref = REF[tokid]
            msdtag = MSD[tokid] if msd else ""

            annotation_info = {}
            sentence_tokens[ref] = {"tokid": tokid, "annotations": annotation_info}

            # Support for multiple values of word
            if word_separator:
                thewords = (w for w in theword.split(word_separator) if w)
            else:
                thewords = [theword]

            # First use MSD tags to find the most probable single word annotations
            ann_tags_words = find_single_word(thewords, lexicon_list, msdtag, precision, min_precision, precision_filter, annotation_info)

            # Find multi-word expressions
            if not skip_multiword:
                find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, MAX_GAPS, ann_tags_words, MSD, sent, skip_pos_check)

            # Loop to next token

        if not allow_multiword_overlap:
            # Check that we don't have any unwanted overlaps
            remove_unwanted_overlaps(complete_multis)

        # Then save the rest of the multi word expressions in sentence_tokens
        save_multiwords(complete_multis, sentence_tokens)

        for token in list(sentence_tokens.values()):
            OUT[token["tokid"]] = _join_annotation(token["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_file, annotation in zip(out, annotations):
        util.write_annotation(out_file, [(tok, OUT[tok].get(annotation, affix)) for tok in OUT], append=True)


def find_single_word(thewords, lexicon_list, msdtag, precision, min_precision, precision_filter, annotation_info):
    ann_tags_words = []

    for w in thewords:
        for name, lexicon in lexicon_list:
            if name == "saldo" or len(lexicon_list) == 1:
                prefix = ""
            else:
                prefix = name + "m--"
            annotation = []
            for a in lexicon.lookup(w):
                annotation.append(a + (prefix,))
            ann_tags_words += annotation
            # Set break if each word only gets annotations from first lexicon that has entry for word
            # break

    annotation_precisions = [(get_precision(msdtag, msdtags), annotation, prefix)
                             for (annotation, msdtags, wordslist, _, _, prefix) in ann_tags_words if not wordslist]

    if min_precision > 0:
        annotation_precisions = [x for x in annotation_precisions if x[0] >= min_precision]
    annotation_precisions = normalize_precision(annotation_precisions)
    annotation_precisions.sort(reverse=True, key=lambda x: x[0])

    if precision_filter and annotation_precisions:
        if precision_filter == "first":
            annotation_precisions = annotation_precisions[:1]
        elif precision_filter == "max":
            maxprec = annotation_precisions[0][0]
            ismax = lambda lemprec: lemprec[0] >= maxprec - PRECISION_DIFF
            annotation_precisions = itertools.takewhile(ismax, annotation_precisions)

    if precision:
        for (prec, annotation, prefix) in annotation_precisions:
            for key in annotation:
                annotation_entry = []
                for item in annotation[key]:
                    if not item.startswith(prefix):
                        annotation_entry.append(prefix + item)
                    else:
                        annotation_entry.append(item)
                annotation_info.setdefault(key, []).extend([a + precision % prec for a in annotation_entry])
    else:
        for (prec, annotation, prefix) in annotation_precisions:
            for key in annotation:
                annotation_entry = []
                for item in annotation[key]:
                    if not item.startswith(prefix):
                        annotation_entry.append(prefix + item)
                    else:
                        annotation_entry.append(item)
                annotation_info.setdefault(key, []).extend(annotation_entry)

    return ann_tags_words


def find_multiword_expressions(incomplete_multis, complete_multis, thewords, ref, msdtag, max_gaps, ann_tags_words, MSD, sent, skip_pos_check):
    todelfromincomplete = []  # list to keep track of which expressions that have been completed

    for i, x in enumerate(incomplete_multis):
        # x = (annotations, following_words, [ref], gap_allowed, is_particle, [part-of-gap-boolean, gap_count])
        seeking_word = x[1][0]  # The next word we are looking for in this multi-word expression

        # Is a gap necessary in this position for this expression?
        if seeking_word == "*":
            if x[1][1].lower() in (w.lower() for w in thewords):
                seeking_word = x[1][1]
                del x[1][0]

        # If current gap is greater than MAX_GAPS, stop searching
        if x[5][1] > max_gaps:
            todelfromincomplete.append(i)
        #                                                         |  Last word may not be PP if this is a particle-multi-word                      |
        elif seeking_word.lower() in (w.lower() for w in thewords) and (skip_pos_check or not (len(x[1]) == 1 and x[4] and msdtag.startswith("PP"))):
            x[5][0] = False     # last word was not a gap
            del x[1][0]
            x[2].append(ref)

            # Is current word the last word we are looking for?
            if len(x[1]) == 0:
                todelfromincomplete.append(i)

                # Create a list of msdtags of words belonging to the completed multi-word expr.
                msdtag_list = [MSD[sent[int(ref) - 1]] for ref in x[2]]

                # For completed verb multis, check that at least one of the words is a verb:
                if not skip_pos_check and "..vbm." in x[0]['lem'][0]:
                    for tag in msdtag_list:
                        if tag.startswith('VB'):
                            complete_multis.append((x[2], x[0]))
                            break

                # For completed noun multis, check that at least one of the words is a noun:
                elif not skip_pos_check and "..nnm." in x[0]['lem'][0]:
                    for tag in msdtag_list:
                        if tag[:2] in ('NN', 'PM', 'UO'):
                            complete_multis.append((x[2], x[0]))
                            break

                else:
                    complete_multis.append((x[2], x[0]))

        else:
            # We've reached a gap
            # Are gaps allowed?
            if x[3]:
                # If previous word was NOT part of a gap, this is a new gap, so increment gap counter
                if not x[5][0]:
                    x[5][1] += 1
                x[5][0] = True  # Mark that this word was part of a gap

                # Avoid having another verb within a verb multi-word expression:
                # delete current incomplete multi-word expr. if it starts with a verb and if current word has POS tag VB
                if "..vbm." in x[0]['lem'][0] and msdtag.startswith("VB"):
                    todelfromincomplete.append(i)

            else:
                # Gaps are not allowed for this multi-word expression
                todelfromincomplete.append(i)

    # Delete seeking words from incomplete_multis
    for x in todelfromincomplete[::-1]:
        del incomplete_multis[x]

    # Collect possible multiword expressions:
    # Is this word a possible beginning of a multi-word expression?
    looking_for = [(annotation, words, [ref], gap_allowed, is_particle, [False, 0])
                   for (annotation, _, wordslist, gap_allowed, is_particle, _) in ann_tags_words if wordslist for words in wordslist]
    if len(looking_for) > 0:
        incomplete_multis.extend(looking_for)


def remove_unwanted_overlaps(complete_multis):
    remove = set()
    for ai, a in enumerate(complete_multis):
        for b in complete_multis:
            # Check if both are of same POS
            if not a == b and re.search(r"\.(\w\w?)m?\.", a[1]["lem"][0]).groups()[0] == re.search(r"\.(\w\w?)m?\.", b[1]["lem"][0]).groups()[0]:
                if b[0][0] < a[0][0] < b[0][-1] < a[0][-1]:
                    # A case of b1 a1 b2 a2. Remove a.
                    remove.add(ai)
                elif a[0][0] < b[0][0] and a[0][-1] == b[0][-1] and not all((x in a[0]) for x in b[0]):
                    # A case of a1 b1 ab2. Remove a.
                    remove.add(ai)

    for a in sorted(remove, reverse=True):
        del complete_multis[a]


def save_multiwords(complete_multis, sentence_tokens):
    for c in complete_multis:
        first = True
        first_ref = ""
        for tok_ref in c[0]:
            if first:
                first_ref = tok_ref
            for ann, val in list(c[1].items()):
                if not first:
                    val = [x + ":" + first_ref for x in val]
                sentence_tokens[tok_ref]["annotations"].setdefault(ann, []).extend(val)
            first = False


######################################################################
# Different kinds of lexica

class SaldoLexicon(object):
    """A lexicon for Saldo lookups.
    It is initialized from a Pickled file, or a space-separated text file.
    """
    def __init__(self, saldofile, verbose=True):
        if verbose:
            util.log.info("Reading Saldo lexicon: %s", saldofile)
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
        if verbose:
            util.log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, word):
        """Lookup a word in the lexicon.
        Returns a list of (annotation-dictionary, list-of-pos-tags, list-of-lists-with-words).
        """
        if word.lower() == word:
            annotation_tag_pairs = self.lexicon.get(word, [])
        else:
            annotation_tag_pairs = self.lexicon.get(word, []) + self.lexicon.get(word.lower(), [])
        return list(map(_split_triple, annotation_tag_pairs))

    @staticmethod
    def save_to_picklefile(saldofile, lexicon, protocol=-1, verbose=True):
        """Save a Saldo lexicon to a Pickled file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {{annotation-type: annotation}: (set(possible tags), set(tuples with following words), gap-allowed-boolean, is-particle-verb-boolean)}}
        """
        if verbose:
            util.log.info("Saving Saldo lexicon in Pickle format")

        picklex = {}
        for word in lexicon:
            annotations = []
            for annotation, extra in list(lexicon[word].items()):
                #annotationlist = PART_DELIM3.join(annotation)
                annotationlist = PART_DELIM2.join(k + PART_DELIM3 + PART_DELIM3.join(annotation[k]) for k in annotation)
                taglist =        PART_DELIM3.join(sorted(extra[0]))
                wordlist =       PART_DELIM2.join([PART_DELIM3.join(x) for x in sorted(extra[1])])
                gap_allowed =    "1" if extra[2] else "0"
                particle =       "1" if extra[3] else "0"
                annotations.append(PART_DELIM1.join([annotationlist, taglist, wordlist, gap_allowed, particle]))

            picklex[word] = sorted(annotations)

        with open(saldofile, "wb") as F:
            pickle.dump(picklex, F, protocol=protocol)
        if verbose:
            util.log.info("OK, saved")

    @staticmethod
    def save_to_textfile(saldofile, lexicon, verbose=True):
        """Save a Saldo lexicon to a space-separated text file.
        The input lexicon should be a dict:
          - lexicon = {wordform: {annotation: set(possible tags)}}
        NOT UP TO DATE
        """
        if verbose:
            util.log.info("Saving Saldo lexicon in text format")
        with open(saldofile, "w") as F:
            for word in sorted(lexicon):
                annotations = [PART_DELIM.join([annotation] + sorted(postags))
                               for annotation, postags in list(lexicon[word].items())]
                print(" ".join([word] + annotations).encode(util.UTF8), file=F)
        if verbose:
            util.log.info("OK, saved")


def _join_annotation(annotation, delimiter, affix):
    seen = set()
    return dict([(a, affix + delimiter.join(b for b in annotation[a] if b not in seen and not seen.add(b)) + affix) for a in annotation])

# The minimun precision difference for two annotations to be considered equal
PRECISION_DIFF = 0.01


def get_precision(msd, msdtags):
    """
    A very simple way of calculating the precision of a Saldo annotation:
    if the the word's msdtag is among the annotation's possible msdtags,
    we return a high value (0.75), a partial match returns 0.66, missing MSD returns 0.5,
    and otherwise a low value (0.25).
    """
    return (0.5 if msd is None else
            0.75 if msd in msdtags else
            0.66 if "." in msd and [partial for partial in msdtags if partial.startswith(msd[:msd.find(".")])] else
            0.25)


def normalize_precision(annotations):
    """Normalize the rankings in the annotation list so that the sum is 1."""
    total_precision = sum(prec for (prec, _annotation, prefix) in annotations)
    return [(prec / total_precision, annotation, prefix) for (prec, annotation, prefix) in annotations]


# Delimiters that hopefully are never found in an annotation or in a POS tag:
PART_DELIM = "^"
PART_DELIM1 = "^1"
PART_DELIM2 = "^2"
PART_DELIM3 = "^3"


def _split_triple(annotation_tag_words):
    annotation, tags, words, gap_allowed, particle = annotation_tag_words.split(PART_DELIM1)
    # annotationlist = [x for x in annotation.split(PART_DELIM3) if x]
    annotationdict = {}
    for a in annotation.split(PART_DELIM2):
        key, values = a.split(PART_DELIM3, 1)
        annotationdict[key] = values.split(PART_DELIM3)

    taglist = [x for x in tags.split(PART_DELIM3) if x]
    wordlist = [x.split(PART_DELIM3) for x in words.split(PART_DELIM2) if x]

    return annotationdict, taglist, wordlist, gap_allowed == "1", particle == "1"


######################################################################
# converting between different file formats

class HashableDict(dict):
    def __key(self):
        return tuple((k, self[k]) for k in sorted(self))

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
    # assert annotation_element in ("gf", "lem", "saldo"), "Invalid annotation element"
    import xml.etree.cElementTree as cet
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower())
    if verbose:
        util.log.info("Reading XML lexicon")
    lexicon = {}

    context = cet.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':
                annotations = HashableDict()

                for a in annotation_elements:
                    annotations[a] = tuple(x.text for x in elem.findall(a))

                pos = elem.findtext("pos")
                inhs = elem.findtext("inhs")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()

                # Check the paradigm for an "x", meaning a multi-word expression with a required gap
                p = elem.findtext("p")
                x_find = re.search(r"_x(\d*)_", p)
                x_insert = x_find.groups()[0] if x_find else None
                if x_insert == "":
                    x_insert = "1"

                # Only vbm and certain paradigms allow gaps
                gap_allowed = (pos == "vbm" or p in (u"abm_x1_var_än", u"knm_x_ju_ju", u"pnm_x1_inte_ett_dugg", u"pnm_x1_vad_än", u"ppm_x1_för_skull"))

                table = elem.find("table")
                multiwords = []

                for form in list(table):
                    word = form.findtext("wf")
                    param = form.findtext("param")

                    if param in ("frag", "c", "ci", "cm"):
                        # We don't use these wordforms, so skip
                        continue
                    elif param[-1].isdigit() and param[-2:] != "-1":
                        # Handle multi-word expressions
                        multiwords.append(word)
                        multipart, multitotal = param.split(":")[-1].split("-")
                        particle = bool(re.search(r"vbm_.+?p.*?\d+_", p))  # Multi-word with particle

                        # Add a "*" where the gap should be
                        if x_insert and multipart == x_insert:
                            multiwords.append("*")

                        if multipart == multitotal:
                            lexicon.setdefault(multiwords[0], {}).setdefault(annotations, (set(), set(), gap_allowed, particle))[1].add(tuple(multiwords[1:]))
                            multiwords = []
                    else:
                        # Single word expressions
                        if param[-2:] == "-1":
                            param = param.rsplit(" ", 1)[0]
                            if pos == "vbm":
                                pos = "vb"
                        saldotag = " ".join([pos] + inhs + [param])
                        tags = tagmap.get(saldotag)
                        if tags:
                            lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), False, False))[0].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ["LexicalEntry", "frame", "resFrame"]:
                root.clear()

    testwords = ["äggtoddyarna",
                 "Linköpingsbors",
                 "katabatiska",
                 "väg-",
                 "formar",
                 "in",
                 "datorrelaterade"]
    util.test_annotations(lexicon, testwords)

    if verbose:
        util.log.info("OK, read")
    return lexicon


def save_to_cstlemmatizer(cstfile, lexicon, encoding="latin-1", verbose=True):
    """Save a JSON lexicon as an external file that can be used for
    training the CST lemmatizer. The default encoding of the resulting
    file is ISO-8859-1 (Latin-1).
    """
    if verbose:
        util.log.info("Saving CST lexicon")
    with open(cstfile, "w") as F:
        for word in sorted(lexicon):
            for lemma in sorted(lexicon[word]):
                for postag in sorted(lexicon[word][lemma]):
                    # the order between word, lemma, postag depends on
                    # the argument -c to cstlemma, this order is -cBFT:
                    line = "%s\t%s\t%s" % (word, lemma, postag)
                    print(line.encode(encoding), file=F)
    if verbose:
        util.log.info("OK, saved")


######################################################################
# additional utilities

def extract_tags(lexicon):
    """Extract the set of all tags that are used in a lexicon.
    The input lexicon should be a dict:
      - lexicon = {wordform: {annotation: set(possible tags)}}
    """
    tags = set()
    for annotations in list(lexicon.values()):
        tags.update(*list(annotations.values()))
    return tags


def xml_to_pickle(xml, filename, annotation_elements="gf lem saldo"):
    """Read an XML dictionary and save as a pickle file."""

    xml_lexicon = read_xml(xml, annotation_elements)
    SaldoLexicon.save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(annotate, xml_to_pickle=xml_to_pickle)
