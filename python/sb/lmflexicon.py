# -*- coding: utf-8 -*-

"""
Parses an lmf-lexicon into the standard Saldo format
Does not handle or use msd-information
Does not make any useable tags (as the SUC/Saldo-tags in saldo.py)
Does not mark particles
Does handle multiwords expressions with gaps
"""

import sb.saldo as s
import util

######################################################################
# converting between different file formats

def read_xml(xml='dalinm.xml', annotation_elements='writtenForm lemgram', verbose=True, skip_multiword=True):
    """Read the XML version of a morphological lexicon in lmf format (dalinm.xml).
    Return a lexicon dictionary, {wordform: {{annotation-type: annotation}: ( set(possible tags), set(tuples with following words) )}}
     - annotation_element is the XML element for the annotation value, 'writtenForm' for baseform, 'lemgram' for lemgram
     - skip_multiword is a flag telling whether to make special entries for multiword expressions. Set this to False only if
       the tool used for text annotation cannot handle this at all
    """
    annotation_elements = annotation_elements.split()
    #assert annotation_element in ("writtenForm lemgram") "Invalid annotation element"
    import xml.etree.cElementTree as cet
    import re
    if verbose: util.log.info("Reading XML lexicon")
    lexicon = {}

    context = cet.iterparse(xml, events=("start", "end")) # "start" needed to save reference to root element
    context = iter(context)
    event, root = context.next()

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':
                annotations = s.hashabledict()

                lem = elem.find("Lemma").find("FormRepresentation")
                for a in annotation_elements:
                    annotations[a] = tuple([findval(lem, a)])

                pos = findval(lem, "partOfSpeech")

                # there may be several WordForms
                for forms in elem.findall("WordForm"):
                    word  = findval(forms, "writtenForm")
                    param = findval(forms, "msd")

                    multiwords = []
                    wordparts = word.split()
                    for i, word in enumerate(wordparts):
                        if (not skip_multiword) and len(wordparts) > 1:

                            # Handle multi-word expressions
                            multiwords.append(word)

                            particle = False # we don't use any particles or mwe:s with gaps
                            mwe_gap  = False # but keep the fields so that the file format match the normal saldo-pickle format

                            # is it the last word in the multi word expression?
                            if i == len(wordparts) - 1:
                                lexicon.setdefault(multiwords[0], {}).setdefault(annotations, (set(), set(), mwe_gap, particle))[1].add(tuple(multiwords[1:]))
                                multiwords = []
                        else:
                            # Single word expressions
                            saldotag = " ".join([pos, param]) # this tag is rather useless, but at least gives some information
                            tags = tuple([saldotag])
                            lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), mwe_gap, particle))[0].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()
    if verbose:
        s.test_annotations(lexicon)
        util.log.info("OK, read")
    return lexicon

def findval(elems, key):
    def iterfindval():
        for form in elems:
            att = form.get("att", "")
            if att == key:
                yield form.get("val")
        yield ""

    return iterfindval().next()


######################################################################
# additional utilities

testwords = [u"äggtoddyarna",
             u"Linköpingsbors",
             u"vike",
             u"katabatiska",
             u"väg-",
             u"formar",
             u"ackommodera",
             u"pittoresk",
             u"in"]

def xml_to_pickle(xml, filename, annotation_elements="writtenForm lemgram", skip_multiword=True):
    """Read an XML dictionary and save as a pickle file."""

    xml_lexicon = read_xml(xml, annotation_elements, skip_multiword=skip_multiword)
    s.SaldoLexicon.save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(xml_to_pickle=xml_to_pickle)
