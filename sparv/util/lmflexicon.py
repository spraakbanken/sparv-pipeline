# -*- coding: utf-8 -*-

"""
Parses an lmf-lexicon into the standard Saldo format
Does not handle msd-information well
Does not mark particles
Does handle multiwords expressions with gaps
To pickle a file, run
lmflexicon.xml_to_pickle("swedberg.xml", "swedberg.pickle", skip_multiword=False)
lmlexicon place in subversion: https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm
"""
import sparv.saldo as saldo
import sparv.util as util
import re

######################################################################
# converting between different file formats


def read_xml(xml='dalinm.xml', annotation_elements='writtenForm lemgram', tagset='SUC', verbose=True, skip_multiword=False, translate_tags=True):
    """Read the XML version of a morphological lexicon in lmf format (dalinm.xml).
       Return a lexicon dictionary, {wordform: {{annotation-type: annotation}: ( set(possible tags), set(tuples with following words) )}}
        - annotation_element is the XML element for the annotation value, 'writtenForm' for baseform, 'lemgram' for lemgram
            writtenForm is translated to 'gf' and lemgram to 'lem' (for compatability with Saldo)
        - skip_multiword is a flag telling whether to make special entries for multiword expressions. Set this to False only if
          the tool used for text annotation cannot handle this at all
    """
    annotation_elements = annotation_elements.split()
    # assert annotation_element in ("writtenForm lemgram") "Invalid annotation element"
    import xml.etree.cElementTree as cet
    if verbose:
        util.log.info("Reading XML lexicon")
    lexicon = {}
    tagmap = getattr(util.tagsets, "saldo_to_" + tagset.lower())

    context = cet.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':
                annotations = saldo.HashableDict()

                lem = elem.find("Lemma").find("FormRepresentation")
                for a in annotation_elements:
                    if a == "writtenForm":
                        key = "gf"
                    elif a == "lemgram":
                        key = "lem"
                    annotations[key] = tuple([findval(lem, a)])

                pos = findval(lem, "partOfSpeech")
                inhs = findval(lem, "inherent")
                if inhs == "-":
                    inhs = ""
                inhs = inhs.split()

                # there may be several WordForms
                for forms in elem.findall("WordForm"):
                    word = findval(forms, "writtenForm")
                    param = findval(forms, "msd")

                    multiwords = []
                    wordparts = word.split()
                    for i, word in enumerate(wordparts):
                        if (not skip_multiword) and len(wordparts) > 1:

                            # Handle multi-word expressions
                            multiwords.append(word)

                            particle = False  # we don't use any particles or mwe:s with gaps
                                              # since that information is not formally expressed in the historical lexicons
                            mwe_gap = False   # but keep the fields so that the file format match the normal saldo-pickle format

                            # is it the last word in the multi word expression?
                            if i == len(wordparts) - 1:
                                lexicon.setdefault(multiwords[0], {}).setdefault(annotations, (set(), set(), mwe_gap, particle))[1].add(tuple(multiwords[1:]))
                                multiwords = []
                        else:
                            # Single word expressions
                            particle = False  # we don't use any particles or mwe:s with gaps
                            mwe_gap = False   # but keep the fields so that the file format match the normal saldo-pickle format

                            if translate_tags:
                                tags = convert_default(pos, inhs, param, tagmap)
                                if tags:
                                    lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), mwe_gap, particle))[0].update(tags)
                            else:
                                saldotag = " ".join([pos, param])  # this tag is rather useless, but at least gives some information
                                tags = tuple([saldotag])
                                lexicon.setdefault(word, {}).setdefault(annotations, (set(), set(), mwe_gap, particle))[0].update(tags)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()
    if verbose:
        testwords = ["äplebuske",
                     "stöpljus",
                     "katt"]
        util.test_annotations(lexicon, testwords)
        util.log.info("OK, read")
    return lexicon


def convert_default(pos, inh, param, tagmap):
    saldotag = ' '.join(([pos] + inh + [param]))
    tags = tagmap.get(saldotag)
    if tags:
        return tags
    tags = try_translate(saldotag)
    if tags:
        tagmap[saldotag] = tags
        return tags
    tags = tagmap.get(pos)
    if tags:
        return tags
    tags = []
    for t in list(tagmap.keys()):
        if t.split()[0] == pos:
            tags.extend(tagmap.get(t))
    return tags


def try_translate(params):
    """ Some basic translations """
    params_list = [params]
    if ' m ' in params:
        # masculine is translated into utrum
        params_list.append(re.sub(' m ', ' u ', params))
    if ' f ' in params:
        # feminine is translated into utrum
        params_list.append(re.sub(' f ', ' u ', params))
    for params in params_list:
        params = params.split()
        # copied from util.tagsets._make_saldo_to_suc(), try to convert the tag
        # but allow m (the match) to be None if the tag still can't be translated
        paramstr = " ".join(util.tagsets._translate_saldo_parameters.get(prm, prm.upper()) for prm in params)
        for (pre, post) in util.tagsets._suc_tag_replacements:
            m = re.match(pre, paramstr)
            if m:
                break
        if m is not None:
            sucfilter = m.expand(post).replace(" ", r"\.").replace("+", r"\+")
            return set(suctag for suctag in util.tagsets.suc_tags if re.match(sucfilter, suctag))
    return []


def findval(elems, key):
    """ help function for looking up values in the lmf """
    def iterfindval():
        for form in elems:
            att = form.get("att", "")
            if att == key:
                yield form.get("val")
        yield ""

    return next(iterfindval())


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


def xml_to_pickle(xml, filename, annotation_elements="writtenForm lemgram", skip_multiword=False):
    """Read an XML dictionary and save as a pickle file."""

    xml_lexicon = read_xml(xml, annotation_elements, skip_multiword=skip_multiword)
    saldo.SaldoLexicon.save_to_picklefile(filename, xml_lexicon)

######################################################################

if __name__ == '__main__':
    util.run.main(xml_to_pickle=xml_to_pickle)
