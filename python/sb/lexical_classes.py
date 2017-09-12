# -*- coding: utf-8 -*-

import sb.util as util


def annotate_bb_words(out, model, saldoids, delimiter=util.DELIM, affix=util.AFFIX, lexicon=None):
    """
    Annotate words with blingbring classes (rogetID).
    - out_sent: resulting annotation file.
    - model: pickled lexicon with saldoIDs as keys.
    - saldoids: existing annotation with saldoIDs.
    - delimiter: delimiter character to put between ambiguous results
    - affix: optional character to put before and after results to mark a set.
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """
    if not lexicon:
        lexicon = util.PickledLexicon(model)
    # Otherwise use pre-loaded lexicon (from catapult)

    OUT = {}

    SALDO_ID = util.read_annotation(saldoids)
    for tokid in SALDO_ID:
        if util.SCORESEP in SALDO_ID[tokid]:  # WSD
            ranked_saldo = SALDO_ID[tokid].strip(util.AFFIX).split(util.DELIM) \
                if SALDO_ID[tokid] != util.AFFIX else None
            saldo_tuples = [(i.split(util.SCORESEP)[0], i.split(util.SCORESEP)[1]) for i in ranked_saldo]

            # Handle wsd with equal probability for several words
            saldo_ids = [saldo_tuples[0]]
            del saldo_tuples[0]
            while saldo_tuples and (saldo_tuples[0][1] == saldo_ids[0][1]):
                saldo_ids = [saldo_tuples[0]]
                del saldo_tuples[0]

            saldo_ids = [i[0] for i in saldo_ids]

        else:  # No WSD
            saldo_ids = SALDO_ID[tokid].strip(util.AFFIX).split(util.DELIM) \
                if SALDO_ID[tokid] != util.AFFIX else None

        rogetid = set()
        if saldo_ids:
            for sid in saldo_ids:
                rogetid = rogetid.union(lexicon.lookup(sid, default=set()))
        result = sorted(rogetid)

        OUT[tokid] = util.cwbset(result, delimiter, affix) if result else affix
    util.write_annotation(out, OUT)


def annotate_bb_doc(out, in_token_bb, text_children, cutoff=10, delimiter=util.DELIM, affix=util.AFFIX):
    """
    Annotate documents with blingbring classes (rogetID).
    - out: resulting annotation file
    - in_token_bb: existing annotation with blingbring tokens.
    - text_children: existing annotation for text-IDs and their word children.
    - cutoff: value for limiting the resulting bring classes.
              The result will contain all words with the top x frequencies.
              Words with frequency = 1 will be removed from the result.
    - delimiter: delimiter character to put between ambiguous results.
    - affix: optional character to put before and after results to mark a set.
    """
    cutoff = int(cutoff)
    text_children = util.read_annotation(text_children)
    roget_words = util.read_annotation(in_token_bb)

    out_bb_doc = {}

    for textid, words in text_children.items():
        roget_freqs = {}
        for tokid in words.split():
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


def read_blingbring(xml='blingbring.xml', verbose=True):
    """
    Read the XML version of the Blingbring lexicon (blingbring.xml).
    Return a lexicon dictionary: {senseid: set([rogetID, rogetID ...])}
    """
    import xml.etree.cElementTree as etree

    if verbose:
        util.log.info("Reading XML lexicon")
    lexicon = {}

    context = etree.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == 'LexicalEntry':
                senseids = [sid.attrib.get("id") for sid in elem.findall("Sense")]
                rogetid = elem.find("Lemma/FormRepresentation/feat[@att='roget_head_id']").attrib.get("val")
                rogetid = rogetid.split("/")[-1]
                for senseid in senseids:
                    lexicon.setdefault(senseid, set()).add(rogetid)

            # Done parsing section. Clear tree to save memory
            if elem.tag == 'LexicalEntry':
                root.clear()

    testwords = ["fågel..1",
                 "behjälplig..1",
                 "kamp..2",
                 "köra_ner..1"
                 ]
    util.test_annotations(lexicon, testwords)

    if verbose:
        util.log.info("OK, read")
    return lexicon


def blingbring_to_pickle(xml, filename, protocol=-1, verbose=True):
    """Read blingbring xml dictionary and save as a pickle file."""
    lexicon = read_blingbring(xml)
    util.lexicon_to_pickle(lexicon, filename)


if __name__ == '__main__':
    util.run.main(annotate_bb_words=annotate_bb_words,
                  annotate_bb_doc=annotate_bb_doc,
                  blingbring_to_pickle=blingbring_to_pickle
                  )
