
import sb.util as util
import pickle


def annotate_bb_words(out_blingbring, model, saldoids, delimiter="|", affix="|", lexicon=None):
    """
    Annotate words with blingbring classes (rogetID).
    - out_blingbring: resulting annotation file
    - model: pickled blingbring lexicon.
    - saldoids: existing annotation with saldoIDs.
    - delimiter: delimiter character to put between ambiguous results
    - affix: optional character to put before and after results to mark a set.
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """
    if not lexicon:
        lexicon = Blingbring(model)
    # Otherwise use pre-loaded lexicon (from catapult)

    OUT_blingbring = {}

    SALDO_ID = util.read_annotation(saldoids)
    for tokid in SALDO_ID:
        rogetid = set()
        if ":" in SALDO_ID[tokid]:  # WSD
            ranked_saldo = SALDO_ID[tokid].strip("|").split("|") if SALDO_ID[tokid] != "|" else None
            saldo_tuples = [(i.split(":")[0], i.split(":")[1]) for i in ranked_saldo]

            # Handle wsd with equal probability for several words
            saldo_ids = [saldo_tuples[0]]
            del saldo_tuples[0]
            while saldo_tuples and (saldo_tuples[0][1] == saldo_ids[0][1]):
                saldo_ids = [saldo_tuples[0]]
                del saldo_tuples[0]

            saldo_ids = [i[0] for i in saldo_ids]

        else:  # No WSD
            saldo_ids = SALDO_ID[tokid].strip("|").split("|") if SALDO_ID[tokid] != "|" else None

        if saldo_ids:
            for sid in saldo_ids:
                rogetid = rogetid.union(lexicon.lookup(sid))

        OUT_blingbring[tokid] = util.cwbset(sorted(rogetid), delimiter, affix) if rogetid else affix
    util.write_annotation(out_blingbring, OUT_blingbring)


def annotate_bb_document(out, in_bb_word, text, cutoff=10, delimiter="|", affix="|"):
    """
    Annotate documents with blingbring classes (rogetID).
    - out: resulting annotation file
    - in_bb_word: pickled blingbring lexicon.
    - text: existing annotation file for text parent.
    - cutoff: value for limiting the resulting bring classes.
              The result will contain all words with the top x frequencies.
              Words with frequency = 1 will be removed from the result.
    - delimiter: delimiter character to put between ambiguous results.
    - affix: optional character to put before and after results to mark a set.
    """
    cutoff = int(cutoff)
    OUT_bb_doc = {}

    roget_words = util.read_annotation(in_bb_word)
    text = util.read_annotation(text)

    roget_freqs = {}

    for tokid in roget_words:
        words = roget_words[tokid].strip("|").split("|") if roget_words[tokid] != "|" else []
        for w in words:
            roget_freqs[w] = roget_freqs.setdefault(w, 0) + 1

    # Sort words according to frequency and remove words with frequency = 1
    ordered_words = sorted(roget_freqs.items(), key=lambda x: x[1], reverse=True)
    ordered_words = [w for w in ordered_words if w[1] > 1]

    if len(ordered_words) > cutoff:
        cutoff_freq = ordered_words[cutoff - 1][1]
        ordered_words = [w for w in ordered_words if w[1] >= cutoff_freq]

    # Join tuples with words and frequencies
    ordered_words = [":".join([word, str(freq)]) for word, freq in ordered_words]
    # util.log.info("%s", ordered_words)

    for tokid in text:
        OUT_bb_doc[tokid] = util.cwbset(ordered_words, delimiter, affix) if ordered_words else affix

    util.write_annotation(out, OUT_bb_doc)


class Blingbring(object):
    """Lexicon for Blingbring lookups, initialized from a Pickled file."""
    def __init__(self, picklefile, verbose=True):
        if verbose:
            util.log.info("Reading Blingbring lexicon: %s", picklefile)
        with open(picklefile, "rb") as F:
            self.lexicon = pickle.load(F)
        if verbose:
            util.log.info("OK, read %d words", len(self.lexicon))

    def lookup(self, saldo_id):
        """Lookup a word in the lexicon."""
        return self.lexicon.get(saldo_id, set())


def read_xml(xml='blingbring.xml', verbose=True):
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


def xml_to_pickle(xml, filename, protocol=-1, verbose=True):
    """Read an XML dictionary and save as a pickle file."""
    lexicon = read_xml(xml)
    if verbose:
        util.log.info("Saving lexicon in pickle format")
    with open(filename, "wb") as F:
        pickle.dump(lexicon, F, protocol=protocol)
    if verbose:
        util.log.info("OK, saved")


if __name__ == '__main__':
    util.run.main(annotate_bb_words=annotate_bb_words,
                  annotate_bb_document=annotate_bb_document,
                  xml_to_pickle=xml_to_pickle)
