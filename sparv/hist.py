# -*- coding: utf_8 -*-
import sparv.saldo as saldo
import sparv.util as util
import sparv.diapivot as diapivot
import re
import itertools
import os


def annotate_variants(word, out, spellmodel, delimiter="|", affix="|", model=None):
    """Use a lexicon model and a spelling model to annotate words with their spelling variants
      - word is existing annotations for wordforms
      - out is a string containing the resulting annotation file
      - spellmodel is the spelling model
      - model is the lexicon model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
    """
    # model -> {word : [(variant, dist)]}
    def parsevariant(modelfile):
        d = {}

        def addword(res, word, info):
            for part in info.strip().split('^^'):
                if part:
                    xs = part.split(',')
                    res.setdefault(word, []).append((xs[0], float(xs[1])))

        with open(modelfile, encoding='utf8') as f:
            for line in f:
                wd, info = line.split(':::')
                addword(d, wd, info)
        return d

    if model is None:
        lexicon = saldo.SaldoLexicon(model)

    variations = parsevariant(spellmodel)

    def findvariants(tokid, theword):
        variants = [x_d for x_d in variations.get(theword.lower(), []) if x_d[0] != theword]
        # return set(_concat([getsingleannotation(lexicon, v, 'lemgram') for v, d in variants]))
        return set([v for v, d in variants])

    annotate_standard(out, word, findvariants, split=False)


def extract_pos(out, lemgrams, extralemgrams='', delimiter="|", affix="|"):
    """ Annotates each lemgram with pos-tags, extracted from this
      - out is the resulting annotation file
      - lemgram is the existing annotations for lemgram
      - extralemgrams is an optional extra annotation from which more pos-tags can be extracted
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
    """

    def oktag(tag):
        return tag is not None and tag.group(1) not in ['e', 'sxc', 'mxc']

    def mkpos(tokid, thelems):
        pos = [re.search('\.\.(.*?)\.', lem) for lem in thelems]
        return set(sum([util.tagsets.lag18002pos(p.group(1)) for p in pos if oktag(p)], []))

    annotate_standard(out, lemgrams, mkpos, extralemgrams)


def annotate_fallback(out, word, msd, lemgram, models, key='lemgram', lexicons=None):
    """ Annotates the words that does not already have a lemgram, according to model
        - out is the resulting annotation file
        - word is the words to be annotated
        - lemgram is the existing annotations for lemgram
        - model is the crosslink model
    """

    # catalaunch stuff
    if lexicons is None:
        models = models.split()
        lexicons = [saldo.SaldoLexicon(lex) for lex in models]

    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)

    def annotate_empties(tokid, lemgrams):
        fallbacks = []
        if not lemgrams:
            word = WORD[tokid]
            msdtag = MSD[tokid]
            fallbacks.extend(getsingleannotation(lexicons, word, key, msdtag))

        return fallbacks

    annotate_standard(out, lemgram, annotate_empties)


def annotate_diachron(out, lemgram, model, extralemgrams='', delimiter="|", affix="|"):
    """ Annotates each lemgram with its corresponding saldo_id, according to model (diapivot.pickle)
     - out is the resulting annotation file
     - lemgram is the existing annotations for lemgram
     - model is the diapivot model
     - delimiter is the delimiter character to put between ambiguous results
     - affix is an optional character to put before and after results
    """

    lexicon = diapivot.PivotLexicon(model)

    def diachronlink(tokid, thelems):
        all_lemgrams = thelems
        for lemgram in thelems:
            s_i = lexicon.get_exactMatch(lemgram)
            if s_i:
                all_lemgrams += [s_i]
        return all_lemgrams

    annotate_standard(out, lemgram, diachronlink, extralemgrams)


def mergemany(out, annotations, separator="|"):
    """Concatenate values from two or more annotations, with an optional separator.
       Removes superfluous separators"""
    # annotations = [util.read_annotation(a) for a in annotations]
    d = {}
    OUT = {}

    if isinstance(annotations, str):
        annotations = annotations.split()
    for annotation in [util.read_annotation(a) for a in annotations]:
        for key_a, val_a in list(annotation.items()):
            if val_a:
                d.setdefault(key_a, []).append(val_a)

    for key, lst in list(d.items()):
        OUT[key] = separator + separator.join(lst) + separator if lst else separator

    util.write_annotation(out, OUT)


def merge(out, left, right, separator=""):
    """Concatenate values from two annotations, with an optional separator.
       Removes superfluous separators"""
    b = util.read_annotation(right)
    OUT = {}

    for key_a, val_a in util.read_annotation_iteritems(left):
        val = [x for x in [val_a, b[key_a]] if x != separator]
        OUT[key_a] = separator.join(list(val)) if val else separator

    util.write_annotation(out, OUT)


def posset(out, pos, separator="|"):
    """Concatenate values from two annotations, with an optional separator.
       Removes superfluous separators"""
    oldpos = util.read_annotation(pos)
    OUT = {}

    # dummy function to annotated thepos with separators
    def makeset(tokid, thepos):
        return [thepos]

    annotate_standard(out, pos, makeset, split=False)


def annotate_standard(out, input_annotation, annotator, extra_input='', delimiter="|", affix="|", split=True):
    """
      Applies the 'annotator' function to the annotations in 'input_annotation' and writes the new output
      to 'out'. The annotator function should have type :: token_id -> oldannotations -> newannotations
      No support for multiword expressions
    - out is the output file
    - input_annotation is the given input annotation
    - f is the function which is to be applied to the input annotation
    - extra_input is an extra input annotation
    - delimiter is the delimiter character to put between ambiguous results
    - affix is an optional character to put before and after results
    - split defines if the input annatoation is a set, with elements separated by delimiter
      if so, return a list. Else, return one single element
    """
    def merge(d1, d2):
        result = dict(d1)
        for k, v in list(d2.items()):
            if k in result:
                result[k] = result[k] + delimiter + v
            else:
                result[k] = v
        return result

    LEMS = util.read_annotation(input_annotation)
    if extra_input:
        LEMS = merge(LEMS, util.read_annotation(extra_input))

    util.clear_annotation(out)
    OUT = {}

    for tokid in LEMS:
        thelems = LEMS[tokid]
        if split:
            thelems = [x for x in thelems.split(delimiter) if x != '']

        output_annotation = set(annotator(tokid, thelems))
        OUT[tokid] = affix + delimiter.join(list(output_annotation)) + affix if output_annotation else affix

    util.write_annotation(out, OUT)


def annotate_full(word, sentence, reference, out, annotations, models,  msd="",
                  delimiter="|", affix="|", precision=":%.3f", precision_filter=None, min_precision=0.0,
                  skip_multiword=False, lexicons=None):
    # TODO almost the same as normal saldo.annotate, but doesn't use msd or saldo-specific stuff
    """Use a lmf-lexicon model to annotate (pos-tagged) words.
      - word, msd are existing annotations for wordforms and part-of-speech
      - sentence is an existing annotation for sentences and their children (words)
      - reference is an existing annotation for word references, to be used when
        annotating multi-word units
      - out is a string containing a whitespace separated list of the resulting annotation files
      - annotations is a string containing a whitespace separate list of annotations to be written.
        Currently: gf (= baseform), lem (=lemgram)
        Number of annotations and their order must correspond to the list in the 'out' argument.
      - model is the Saldo model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
      - precision is a format string for how to print the precision for each annotation
        (use empty string for no precision)
      - precision_filter is an optional filter, currently there are the following values:
        max: only use the annotations that are most probable
        first: only use the most probable annotation (or one of the most probable if more than one)
      - min_precision: only use annotations with a probability score higher than this
      - skip_multiword can be set to True to disable multi word annotations
      - lexicon: this argument cannot be set from the command line,
        but is used in the catapult. This argument must be last.
    """

    # allow use of multiple lexicons
    if not lexicons:
        models = [(os.path.basename(m).rstrip(".pickle"), m) for m in models.split()]
        lexicons = [(name, saldo.SaldoLexicon(lex)) for name, lex in models]

    MAX_GAPS = 0  # Maximum number of gaps in multi-word units.
                  # Set to 0 since many (most?) multi-word in the old lexicons are unseparable (half öre etc)

    annotations = annotations.split()
    out = out.split()
    assert len(out) == len(annotations), "Number of target files and annotations must be the same"

    if isinstance(skip_multiword, str):
        skip_multiword = (skip_multiword.lower() == "true")
    if skip_multiword:
        util.log.info("Skipping multi word annotations")

    min_precision = float(min_precision)

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
            thewords = [w for w in WORD[tokid].split('|') if w]
            ref = REF[tokid]
            if msd:
                msdtag = MSD[tokid]
            else:
                msdtag = ''

            annotation_info = {}
            sentence_tokens[ref] = {"tokid": tokid, "word": thewords, "msd": msdtag, "annotations": annotation_info}

            for theword in thewords:

                # First use MSD tags to find the most probable single word annotations
                ann_tags_words = findsingleword(theword, lexicons, msdtag, precision, min_precision, precision_filter, annotation_info)

                # Find multi-word expressions
                if not skip_multiword:
                    findmultiwordexpressions(incomplete_multis, complete_multis, theword, ref, MAX_GAPS, ann_tags_words)

                # Loop to next token

        # Check that we don't have any unwanted overlaps
        removeunwantedoverlaps(complete_multis)

        # Then save the rest of the multi word expressions in sentence_tokens
        savemultiwords(complete_multis, sentence_tokens)

        for token in list(sentence_tokens.values()):
            OUT[token["tokid"]] = saldo._join_annotation(token["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_file, annotation in zip(out, annotations):
        util.write_annotation(out_file, [(tok, OUT[tok].get(annotation, affix)) for tok in OUT], append=True)


def findsingleword(theword, lexicons, msdtag, precision, min_precision, precision_filter, annotation_info):
    ann_tags_words = []

    for name, lexicon in lexicons:
        if name == "saldo":
            prefix = ""
        else:
            prefix = name + "m--"
        annotation = []
        for a in lexicon.lookup(theword):
            annotation.append(a + (prefix,))
        ann_tags_words += annotation
        # set break if each word only gets annotations from first lexicon that has entry for word
        # break

    annotation_precisions = [(get_precision(msdtag, msdtags), annotation, prefix)
                             for (annotation, msdtags, wordslist, _, _, prefix) in ann_tags_words if not wordslist]

    if min_precision > 0:
        annotation_precisions = [x for x in annotation_precisions if x[0] >= min_precision]
    annotation_precisions = normalize_precision(annotation_precisions)
    annotation_precisions.sort(reverse=True)

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


def findmultiwordexpressions(incomplete_multis, complete_multis, theword, ref, MAX_GAPS, ann_tags_words):
    todelfromincomplete = []  # list to keep track of which expressions that have been completed

    for i, x in enumerate(incomplete_multis):
        seeking_word = x['words'][0]  # The next word we are looking for in this multi-word expression

        # TODO '*' only in saldo
        if seeking_word == "*":
            if x['words'][1].lower() == theword.lower():
                seeking_word = x['words'][1]
                del x['words'][0]

        if x['numberofgaps'] > MAX_GAPS:
            todelfromincomplete.append(i)

        elif seeking_word.lower() == theword.lower():
            x['lastwordwasgap'] = False
            del x['words'][0]
            x['ref'].append(ref)

            # Is current word the last word we are looking for?
            if len(x['words']) == 0:
                todelfromincomplete.append(i)
                complete_multis.append((x['ref'], x['annotation']))
        else:
            # Increment gap counter if previous word was not part of a gap
            if not x['lastwordwasgap']:
                x['numberofgaps'] += 1
            x['lastwordwasgap'] = True  # Marking that previous word was part of a gap

    # Remove found word from incompletes-list
    for x in todelfromincomplete[::-1]:
        del incomplete_multis[x]

    # Is this word a possible start for multi-word units?
    looking_for = [{'annotation': annotation, 'words': words, 'ref': [ref],
                    'is_particle': is_particle, 'lastwordwasgap': False, 'numberofgaps': 0}
                   for (annotation, _, wordslist, _, is_particle, _) in ann_tags_words if wordslist for words in wordslist]
    if len(looking_for) > 0:
        incomplete_multis.extend(looking_for)


def getsingleannotation(lexicons, word, key, msdtag):
    annotation = []
    # TODO the translation of tags is not fully working yet.
    # the precision must be set to 0.25 in order for the
    # lemgrams to be kept.

    for lexicon in lexicons:
        #for (ann,msdtags,wordlist,_,_,) in lexicon.lookup(word):
        #   print 'word',word
        #   print 'msd',msdtag
        #   print 'msdtags',msdtags
        #   print msdtag in (re.sub('av','jj',m.split()[0]).upper() for m in msdtags)
        res = [(saldo.get_precision(msdtag, msdtags), ann) for (ann, msdtags, wordslist, _, _) in lexicon.lookup(word) if not wordslist]
        #print word.encode('utf8'),msdtag
        #print lexicon.lookup(word)
        res = [a for x, a in sorted(res, reverse=True) if x >= 0.25]  # TODO use saldo.py for this!!!
        if res:
            annotation = res
            break
    return _concat(a.get(key) for a in annotation)


def removeunwantedoverlaps(complete_multis):
    remove = set()
    for ci, c in enumerate(complete_multis):
        for d in complete_multis:
            if re.search(r"(.*)--.*", c[1]["lemgram"][0]).groups()[0] != re.search(r"(.*)--.*", d[1]["lemgram"][0]).groups()[0]:
                # Both are from the same lexicon
                remove.add(ci)
            elif len(set(c[0])) != len(c[0]):
                # Since we allow many words for one token (when using spelling variation)
                # we must make sure that two words of a mwe are not made up by two variants of one token
                # that is, that the same reference-id is not used twice in a mwe
                remove.add(ci)
            elif re.search(r"\.\.(\w+)\.", c[1]["lemgram"][0]).groups()[0] == re.search(r"\.\.(\w+)\.", d[1]["lemgram"][0]).groups()[0]:
                # Both are of same POS
                if d[0][0] < c[0][0] and d[0][-1] > c[0][0] and d[0][-1] < c[0][-1]:
                    # A case of x1 y1 x2 y2. Remove y.
                    remove.add(ci)
                elif c[0][0] < d[0][0] and d[0][-1] == c[0][-1]:
                    # A case of x1 y1 xy2. Remove x.
                    remove.add(ci)

    for c in sorted(remove, reverse=True):
        del complete_multis[c]


def savemultiwords(complete_multis, sentence_tokens):
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


def annotate_mwe(variants, word, reference, sentence, out, annotations, models, delimiter="|", affix="|", precision_filter=":%.3f", filter=None, lexicons=None):
    """print multi words only
    """
    MAX_GAPS = 0  # Maximum number of gaps in multi-word units.
                  # Set to 0 since many (most?) multi-word in the old lexicons are unseparable (half öre etc)

    annotations = annotations.split()
    out = out.split()
    assert len(out) == len(annotations), "Number of target files and annotations must be the same"

    # we allow multiple lexicons, each word will get annotations from only one of the lexicons, starting the lookup in the first lexicon in the list
    if lexicons is None:
        models = models.split()
        lexicons = [saldo.SaldoLexicon(lex) for lex in models]
    WORD = util.read_annotation(variants)
    REALWORD = util.read_annotation(word)
    REF = util.read_annotation(reference)

    for out_file in out:
        util.clear_annotation(out_file)

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    OUT = {}
    # output_info = {}

    for sent in sentences:
        incomplete_multis = []  # :: [{annotation, words, [ref], is_particle, lastwordWasGap, numberofgaps}]
        complete_multis = []  # :: ([ref], annotation, [text])
        sentence_tokens = {}

        for tokid in sent:
            thewords = [w for w in WORD[tokid].split('|') if w]
            ref = REF[tokid]
            word = REALWORD[tokid]

            annotation_info = {}
            sentence_tokens[ref] = {"tokid": tokid, "word": word, "variant": thewords, "annotations": annotation_info}

            endword = len(thewords) - 1
            for i, theword in enumerate(thewords):

                ann_tags_words = findsingleword(theword, lexicons, '', annotation_info)  # emtpy msd tag
                # For multi-word expressions
                findvariantmultiwordexpressions(incomplete_multis, complete_multis, theword, word, ref, MAX_GAPS, ann_tags_words, i == endword)

                # Loop to next token

        # Check that we don't have any unwanted overlaps
        removeunwantedoverlaps(complete_multis)

        # Then save the rest of the multi word expressions in sentence_tokens
        savemultiwords(complete_multis, sentence_tokens)

        for token in list(sentence_tokens.values()):
            OUT[token["tokid"]] = saldo._join_annotation(token["annotations"], delimiter, affix)

        # Loop to next sentence

    for out_file, annotation in zip(out, annotations):
        print('adding', [(tok, OUT[tok].get(annotation, affix)) for tok in OUT])
        util.write_annotation(out_file, [(tok, OUT[tok].get(annotation, affix)) for tok in OUT], append=True)


def findvariantmultiwordexpressions(incomplete_multis, complete_multis, theword, textword, ref, MAX_GAPS, ann_tags_words, increase):
    # use normal findvariant instead, only textword is different, but not used anyway
    todelfromincomplete = []  # list to keep track of which expressions that have been completed

    for i, x in enumerate(incomplete_multis):
        seeking_word = x['words'][0]  # The next word we are looking for in this multi-word expression

        if x['numberofgaps'] > MAX_GAPS:
            todelfromincomplete.append(i)

        elif seeking_word.lower() == theword.lower():
            x['lastwordwasgap'] = False
            del x['words'][0]
            x['ref'].append(ref)
            x['text'].append(textword)

            # Is current word the last word we are looking for?
            if len(x['words']) == 0:
                todelfromincomplete.append(i)
                complete_multis.append((x['ref'], x['annotation'], x['text']))
        elif increase and ref != x['ref'][-1]:
            # Increment gap counter if previous word was not part of a gap
            if not x['lastwordwasgap']:
                x['numberofgaps'] += 1
            x['lastwordwasgap'] = True  # Marking that previous word was part of a gap

    # Remove found word from incompletes-list
    for x in todelfromincomplete[::-1]:
        del incomplete_multis[x]

    # Is this word a possible start for multi-word units?
    looking_for = [{'annotation': annotation, 'words': words, 'ref': [ref], 'text': [textword],
                    'is_particle': is_particle, 'lastwordwasgap': False, 'numberofgaps': 0}
                   for (annotation, _, wordslist, _, is_particle) in ann_tags_words if wordslist for words in wordslist]
    if len(looking_for) > 0:
        incomplete_multis.extend(looking_for)


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

# The minimun precision difference for two annotations to be considered equal
PRECISION_DIFF = 0.01


def normalize_precision(annotations):
    """Normalize the rankings in the annotation list so that the sum is 1."""
    total_precision = sum(prec for (prec, _annotation, prefix) in annotations)
    return [(prec / total_precision, annotation, prefix) for (prec, annotation, prefix) in annotations]


def _concat(xs):
    return sum(xs, [])


if __name__ == '__main__':
    util.run.main(annotate_variants=annotate_variants,
                  extract_pos=extract_pos,
                  merge=merge,
                  mergemany=mergemany,
                  posset=posset,
                  annotate_full=annotate_full,
                  annotate_fallback=annotate_fallback,
                  annotate_mwe=annotate_mwe,
                  annotate_diachron=annotate_diachron
                  )
