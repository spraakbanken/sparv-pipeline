# -*- coding: utf-8 -*-

import sb.util as util


def annotate_bb_words(out, model, saldoids, pos, pos_limit="NN VB JJ AB", class_set="bring",
                      delimiter=util.DELIM, affix=util.AFFIX, lexicon=None):
    """Blingbring specific wrapper for annotate_words. See annotate_words for more info."""
    # pos_limit="NN VB JJ AB" | None

    if class_set not in ["bring", "roget_head", "roget_subsection", "roget_section", "roget_class"]:
        util.log.warning("Class '%s' not available. Fallback to 'bring'.")
        class_set = "bring"

    # Blingbring annotation function
    def annotate_bring(saldo_ids, lexicon):
        rogetid = set()
        if saldo_ids:
            for sid in saldo_ids:
                rogetid = rogetid.union(lexicon.lookup(sid, default=dict()).get(class_set, set()))
        return sorted(rogetid)

    annotate_words(out, model, saldoids, pos, annotate_bring, pos_limit=pos_limit, class_set=class_set,
                   delimiter=delimiter, affix=affix, lexicon=lexicon)


def annotate_swefn_words(out, model, saldoids, pos, pos_limit="NN VB JJ AB", class_set=None, disambiguate=False,
                         delimiter=util.DELIM, affix=util.AFFIX, lexicon=None):
    """SweFN specific wrapper for annotate_words. See annotate_words for more info."""

    # SweFN annotation function
    def annotate_swefn(saldo_ids, lexicon):
        swefnid = set()
        if saldo_ids:
            for sid in saldo_ids:
                swefnid = swefnid.union(lexicon.lookup(sid, default=set()))
        return sorted(swefnid)

    annotate_words(out, model, saldoids, pos, annotate_swefn, pos_limit=pos_limit, class_set=class_set,
                   disambiguate=disambiguate, delimiter=delimiter, affix=affix, lexicon=lexicon)


def annotate_words(out, model, saldoids, pos, annotate, pos_limit, class_set=None, disambiguate=True,
                   delimiter=util.DELIM, affix=util.AFFIX, lexicon=None):
    """
    Annotate words with blingbring classes (rogetID).
    - out_sent: resulting annotation file.
    - model: pickled lexicon with saldoIDs as keys.
    - saldoids, pos: existing annotation with saldoIDs/parts of speech.
    - annotate: annotation function, returns an iterable containing annotations
        for one token ID. (annotate_bb() or annotate_swefn())
    - pos_limit: parts of speech that will be annotated.
        Set to None to annotate all pos.
    - class_set: output Bring classes or Roget IDs ("bring", "roget_head",
        "roget_subsection", "roget_section" or "roget_class").
        Set to None when not annotating blingbring.
    - delimiter: delimiter character to put between ambiguous results
    - affix: optional character to put before and after results to mark a set.
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """

    if not lexicon:
        lexicon = util.PickledLexicon(model)
    # Otherwise use pre-loaded lexicon (from catapult)

    if pos_limit.lower() == "none":
        pos_limit = None

    result_dict = {}
    sense = util.read_annotation(saldoids)
    token_pos = util.read_annotation(pos)
    for tokid in sense:

        # Check if part of speech of this token is allowed
        if not pos_ok(token_pos, tokid, pos_limit):
            saldo_ids = None
            result_dict[tokid] = affix
            continue

        if util.SCORESEP in sense[tokid]:  # WSD
            ranked_saldo = sense[tokid].strip(util.AFFIX).split(util.DELIM) \
                if sense[tokid] != util.AFFIX else None
            saldo_tuples = [(i.split(util.SCORESEP)[0], i.split(util.SCORESEP)[1]) for i in ranked_saldo]

            if not disambiguate:
                saldo_ids = [i[0] for i in saldo_tuples]
                print(saldo_ids)

            # Only take the most likely analysis into account.
            # Handle wsd with equal probability for several words
            else:
                saldo_ids = [saldo_tuples[0]]
                del saldo_tuples[0]
                while saldo_tuples and (saldo_tuples[0][1] == saldo_ids[0][1]):
                    saldo_ids = [saldo_tuples[0]]
                    del saldo_tuples[0]

                saldo_ids = [i[0] for i in saldo_ids]

        else:  # No WSD
            saldo_ids = sense[tokid].strip(util.AFFIX).split(util.DELIM) \
                if sense[tokid] != util.AFFIX else None

        result = annotate(saldo_ids, lexicon)

        result_dict[tokid] = util.cwbset(result, delimiter, affix) if result else affix
    util.write_annotation(out, result_dict)


def pos_ok(token_pos, tokid, pos_limit):
    """
    If there is a pos_limit, check if token has correct
    part of speech. Pass all tokens otherwise.
    """
    if pos_limit:
        return token_pos[tokid] in pos_limit.split()
    else:
        return True


def annotate_bb_doc(out, in_token_bb, text_children, saldoids, cutoff=10, types=False,
                    delimiter=util.DELIM, affix=util.AFFIX):
    """
    Annotate documents with blingbring classes (rogetID).
    - out: resulting annotation file
    - in_token_bb: existing annotation with blingbring tokens.
    - text_children: existing annotation for text-IDs and their word children.
    - saldoids: existing annotation with saldoIDs, needed when types=True.
    - cutoff: value for limiting the resulting bring classes.
              The result will contain all words with the top x frequencies.
              Words with frequency = 1 will be removed from the result.
    - types: if True, count every blingbring class only once per saldo ID occurrence.
    - delimiter: delimiter character to put between ambiguous results.
    - affix: optional character to put before and after results to mark a set.
    """
    cutoff = int(cutoff)
    types = util.strtobool(types)
    text_children = util.read_annotation(text_children)
    roget_words = util.read_annotation(in_token_bb)
    sense = util.read_annotation(saldoids)

    out_bb_doc = {}

    for textid, words in text_children.items():
        seen_types = set()
        roget_freqs = {}

        for tokid in words.split():
            # Count only sense types
            if types:
                senses = str(sorted([s.split(util.SCORESEP)[0] for s in sense[tokid].strip(util.AFFIX).split(util.DELIM)]))
                if senses in seen_types:
                    continue
                else:
                    seen_types.add(senses)

            rogwords = roget_words[tokid].strip(util.AFFIX).split(util.DELIM) \
                if roget_words[tokid] != util.AFFIX else []
            for w in rogwords:
                roget_freqs[w] = roget_freqs.setdefault(w, 0) + 1

        # Sort words according to frequency and remove words with frequency = 1
        ordered_words = sorted(roget_freqs.items(), key=lambda x: x[1], reverse=True)
        ordered_words = [w for w in ordered_words if w[1] > 1]

        if len(ordered_words) > cutoff:
            cutoff_freq = ordered_words[cutoff - 1][1]
            ordered_words = [w for w in ordered_words if w[1] >= cutoff_freq]

        # Join tuples with words and frequencies
        ordered_words = [util.SCORESEP.join([word, str(freq)]) for word, freq in ordered_words]
        out_bb_doc[textid] = util.cwbset(ordered_words, delimiter, affix) if ordered_words else affix

    util.write_annotation(out, out_bb_doc)


def annotate_swefn_doc(out, in_token_swefn, text_children, saldoids, cutoff=10, types=False,
                       delimiter=util.DELIM, affix=util.AFFIX):
    """
    Annotate documents with sweFN classes.
    - out: resulting annotation file
    - in_token_bb: existing annotation with blingbring tokens.
    - text_children: existing annotation for text-IDs and their word children.
    - saldoids: existing annotation with saldoIDs, needed when types=True.
    - cutoff: value for limiting the resulting bring classes.
              The result will contain all words with the top x frequencies.
              Words with frequency = 1 will be removed from the result.
    - types: if True, count every sweFN class only once per saldo ID occurrence.
    - delimiter: delimiter character to put between ambiguous results.
    - affix: optional character to put before and after results to mark a set.
    """
    cutoff = int(cutoff)
    types = util.strtobool(types)
    text_children = util.read_annotation(text_children)
    fn_words = util.read_annotation(in_token_swefn)
    sense = util.read_annotation(saldoids)

    out_bb_doc = {}

    for textid, words in text_children.items():
        seen_types = set()
        fn_freqs = {}

        for tokid in words.split():
            # Count only sense types
            if types:
                senses = str(sorted([s.split(util.SCORESEP)[0] for s in sense[tokid].strip(util.AFFIX).split(util.DELIM)]))
                if senses in seen_types:
                    continue
                else:
                    seen_types.add(senses)

            fnwords = fn_words[tokid].strip(util.AFFIX).split(util.DELIM) \
                if fn_words[tokid] != util.AFFIX else []
            for w in fnwords:
                fn_freqs[w] = fn_freqs.setdefault(w, 0) + 1

        # Sort words according to frequency and remove words with frequency = 1
        ordered_words = sorted(fn_freqs.items(), key=lambda x: x[1], reverse=True)
        ordered_words = [w for w in ordered_words if w[1] > 1]

        if len(ordered_words) > cutoff:
            cutoff_freq = ordered_words[cutoff - 1][1]
            ordered_words = [w for w in ordered_words if w[1] >= cutoff_freq]

        # Join tuples with words and frequencies
        ordered_words = [util.SCORESEP.join([word, str(freq)]) for word, freq in ordered_words]
        out_bb_doc[textid] = util.cwbset(ordered_words, delimiter, affix) if ordered_words else affix

    util.write_annotation(out, out_bb_doc)


def read_blingbring(tsv="blingbring.txt", classmap="rogetMap.xml", verbose=True):
    """
    Read the tsv version of the Blingbring lexicon (blingbring.xml).
    Return a lexicon dictionary: {senseid: {roget_head: roget_head,
                                            roget_subsection: roget_subsection,
                                            roget_section: roget_section,
                                            roget_class: roget_class,
                                            bring: bring_ID}
    """
    rogetdict = read_rogetmap(xml=classmap, verbose=True)

    import csv

    if verbose:
        util.log.info("Reading tsv lexicon")
    lexicon = {}
    classmapping = {}

    with open(tsv) as f:
        for line in csv.reader(f, delimiter="\t"):
            if line[0].startswith("#"):
                continue
            rogetid = line[1].split("/")[-1]
            if rogetid in rogetdict:
                roget_l3 = rogetdict[rogetid][0]  # subsection
                roget_l2 = rogetdict[rogetid][1]  # section
                roget_l1 = rogetdict[rogetid][2]  # class
            else:
                roget_l3 = roget_l2 = roget_l1 = ""
            senseids = set(line[3].split(":"))
            for senseid in senseids:
                lexicon.setdefault(senseid, set()).add((rogetid, roget_l3, roget_l2, roget_l1))

            # Make mapping between Roget and Bring classes
            if line[0].split("/")[1] == "B":
                classmapping[rogetid] = line[2]

    for senseid, rogetids in lexicon.items():
        roget_head = set([tup[0] for tup in rogetids])
        roget_subsection = set([tup[1] for tup in rogetids if tup[1]])
        roget_section = set([tup[2] for tup in rogetids if tup[2]])
        roget_class = set([tup[3] for tup in rogetids if tup[3]])
        lexicon[senseid] = {"roget_head": roget_head,
                            "roget_subsection": roget_subsection,
                            "roget_section": roget_section,
                            "roget_class": roget_class,
                            "bring": set([classmapping[r] for r in roget_head])}

    testwords = ["fågel..1",
                 "behjälplig..1",
                 "köra_ner..1"
                 ]
    util.test_annotations(lexicon, testwords)

    if verbose:
        util.log.info("OK, read")
    return lexicon


def read_rogetmap(xml="rogetMap.xml", verbose=True):
    """
    Parse Roget map (Roget hierarchy) into a dictionary with
    Roget head words as keys.
    Roget map was taken from Open Roget's Thesaurus
    (http://www.cs.utoronto.ca/~akennedy/resources.html).
    """
    import xml.etree.cElementTree as cet
    if verbose:
        util.log.info("Reading XML lexicon")
    lexicon = {}
    context = cet.iterparse(xml, events=("start", "end"))
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if elem.tag == "class":
            l1 = elem.get("name")
        elif elem.tag == "section":
            l2 = elem.get("name")
        elif elem.tag == "subsection":
            l3 = elem.get("name")
        elif elem.tag == "head":
            head = elem.get("name")
            lexicon[head] = (l3, l2, l1)

    testwords = ["Existence",
                 "Health",
                 "Amusement",
                 "Marriage"]
    util.test_annotations(lexicon, testwords)

    if verbose:
        util.log.info("OK, read.")
    return lexicon


def read_swefn(xml='swefn.xml', verbose=True):
    """
    Read the XML version of the swedish Framenet resource.
    Return a lexicon dictionary, {saldoID: {swefnID}}.
    """
    import xml.etree.cElementTree as cet
    if verbose:
        util.log.info("Reading XML lexicon")
    lexicon = {}

    context = cet.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':
                sense = elem.find("Sense")
                sid = sense.get("id").lstrip("swefn--")
                for lu in sense.findall("feat[@att='LU']"):
                    saldosense = lu.get("val")
                    lexicon.setdefault(saldosense, set()).add(sid)

            # Done parsing section. Clear tree to save memory
            if elem.tag in ['LexicalEntry', 'frame', 'resFrame']:
                root.clear()

    testwords = ["slant..1",
                 "befrielse..1",
                 "granne..1",
                 "sisådär..1",
                 "mjölkcentral..1"]
    util.test_annotations(lexicon, testwords)

    if verbose:
        util.log.info("OK, read.")
    return lexicon


def blingbring_to_pickle(tsv, classmap, filename, protocol=-1, verbose=True):
    """Read blingbring tsv dictionary and save as a pickle file."""
    lexicon = read_blingbring(tsv, classmap)
    util.lexicon_to_pickle(lexicon, filename)


def swefn_to_pickle(xml, filename, protocol=-1, verbose=True):
    """Read sweFN xml dictionary and save as a pickle file."""
    lexicon = read_swefn(xml)
    util.lexicon_to_pickle(lexicon, filename)


if __name__ == '__main__':
    util.run.main(annotate_bb_words=annotate_bb_words,
                  annotate_bb_doc=annotate_bb_doc,
                  blingbring_to_pickle=blingbring_to_pickle,
                  annotate_swefn_words=annotate_swefn_words,
                  annotate_swefn_doc=annotate_swefn_doc,
                  swefn_to_pickle=swefn_to_pickle
                  )
