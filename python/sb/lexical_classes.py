
import sb.util as util
import pickle


def annotate_blingbring(out_blingbring, saldoids, model, wsd=None, lexicon=None, delimiter="|", affix="|"):
    if not lexicon:
        lexicon = Blingbring(model)
    # Otherwise use pre-loaded lexicons (from catapult)

    OUT_blingbring = {}

    if wsd:
        SALDO_ID = util.read_annotation(wsd)
        for tokid in SALDO_ID:
            saldo_id = SALDO_ID[tokid].strip("|").split("|")[0].split(":")[0] if SALDO_ID[tokid] != "|" else None
            rogetid = set()
            if saldo_id:
                rogetid = rogetid.union(lexicon.lookup(saldo_id))
            OUT_blingbring[tokid] = util.cwbset(sorted(rogetid), delimiter, affix) if rogetid else affix

    else:
        SALDO_ID = util.read_annotation(saldoids)
        for tokid in SALDO_ID:
            saldo_ids = SALDO_ID[tokid].strip("|").split("|") if SALDO_ID[tokid] != "|" else None
            rogetid = set()
            if saldo_ids:
                for sid in saldo_ids:
                    rogetid = rogetid.union(lexicon.lookup(sid))
            OUT_blingbring[tokid] = util.cwbset(sorted(rogetid), delimiter, affix) if rogetid else affix

    util.write_annotation(out_blingbring, OUT_blingbring)


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
                # print(senseids, rogetid)
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
    util.run.main(annotate_blingbring, xml_to_pickle=xml_to_pickle)
