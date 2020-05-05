"""Handle models for lexical classes."""

import logging
import os
import subprocess
import sys
from collections import defaultdict

import sparv.util as util
from sparv import ModelOutput, modelbuilder
from sparv.core import paths

log = logging.getLogger(__name__)

# Path to the cwb binaries
CWB_SCAN_EXECUTABLE = "cwb-scan-corpus"
CWB_DESCRIBE_EXECUTABLE = "cwb-describe-corpus"
CORPUS_REGISTRY = os.environ.get("CORPUS_REGISTRY")


@modelbuilder("Blingbring model")
def blingbring_model(out: str = ModelOutput("lexical_classes/blingbring.pickle")):
    """Download and build Blingbring model."""
    modeldir = paths.get_model_path(util.dirname(out))

    # Download blingbring.txt and build blingbring.pickle
    raw_path = os.path.join(modeldir, "blingbring.txt")
    util.download_file("https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/bring/blingbring.txt", raw_path)
    classmap_path = os.path.join(modeldir, "roget_hierarchy.xml")
    blingbring_to_pickle(raw_path, classmap_path, paths.get_model_path(out))

    # Clean up
    util.remove_files([raw_path])


@modelbuilder("SweFN model")
def swefn_model(out: str = ModelOutput("lexical_classes/swefn.pickle")):
    """Download and build SweFN model."""
    modeldir = paths.get_model_path(util.dirname(out))

    # Download swefn.xml and build swefn.pickle
    raw_path = os.path.join(modeldir, "swefn.xml")
    util.download_file("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swefn/swefn.xml", raw_path)
    swefn_to_pickle(raw_path, paths.get_model_path(out))

    # Clean up
    util.remove_files([raw_path])


def read_blingbring(tsv="blingbring.txt", classmap="rogetMap.xml", verbose=True):
    """Read the tsv version of the Blingbring lexicon (blingbring.xml).

    Return a lexicon dictionary: {senseid: {roget_head: roget_head,
                                            roget_subsection: roget_subsection,
                                            roget_section: roget_section,
                                            roget_class: roget_class,
                                            bring: bring_ID}
    """
    rogetdict = read_rogetmap(xml=classmap, verbose=True)

    import csv

    if verbose:
        log.info("Reading tsv lexicon")
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
        log.info("OK, read")
    return lexicon


def read_rogetmap(xml="roget_hierarchy.xml", verbose=True):
    """Parse Roget map (Roget hierarchy) into a dictionary with Roget head words as keys."""
    import xml.etree.ElementTree as cet
    if verbose:
        log.info("Reading XML lexicon")
    lexicon = {}
    context = cet.iterparse(xml, events=("start", "end"))
    context = iter(context)
    _event, _root = next(context)

    for _event, elem in context:
        if elem.tag == "class":
            l1 = elem.get("name")
        elif elem.tag == "section":
            l2 = elem.get("name")
        elif elem.tag == "subsection":
            l3 = elem.get("name")
        elif elem.tag == "headword":
            head = elem.get("name")
            lexicon[head] = (l3, l2, l1)

    testwords = ["Existence",
                 "Health",
                 "Amusement",
                 "Marriage"]
    util.test_annotations(lexicon, testwords)

    if verbose:
        log.info("OK, read.")
    return lexicon


def read_swefn(xml='swefn.xml', verbose=True):
    """Read the XML version of the swedish Framenet resource.

    Return a lexicon dictionary, {saldoID: {swefnID}}.
    """
    import xml.etree.ElementTree as cet
    if verbose:
        log.info("Reading XML lexicon")
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
        log.info("OK, read.")
    return lexicon


def blingbring_to_pickle(tsv, classmap, filename, protocol=-1, verbose=True):
    """Read blingbring tsv dictionary and save as a pickle file."""
    lexicon = read_blingbring(tsv, classmap)
    util.lexicon_to_pickle(lexicon, filename)


def swefn_to_pickle(xml, filename, protocol=-1, verbose=True):
    """Read sweFN xml dictionary and save as a pickle file."""
    lexicon = read_swefn(xml)
    util.lexicon_to_pickle(lexicon, filename)


def create_freq_pickle(corpus, annotation, filename, model, class_set=None, score_separator=util.SCORESEP):
    """Build pickle with relative frequency for a given annotation in one or more reference corpora."""
    lexicon = util.PickledLexicon(model)
    # Create a set of all possible classes
    if class_set:
        all_classes = set(cc for c in lexicon.lexicon.values() for cc in c[class_set])
    else:
        all_classes = set(cc for c in lexicon.lexicon.values() for cc in c)
    lexicon_size = len(all_classes)
    smoothing = 0.1

    corpus_stats = defaultdict(int)
    corpus_size = 0

    if isinstance(corpus, str):
        corpus = corpus.split()

    for c in corpus:
        # Get corpus size
        process = subprocess.Popen([CWB_DESCRIBE_EXECUTABLE, "-r", CORPUS_REGISTRY, c],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        reply, error = process.communicate()
        reply = reply.decode()

        if error:
            error = error.decode()
            log.error(error)
            sys.exit(1)

        for line in reply.splitlines():
            if line.startswith("size (tokens)"):
                _, size = line.split(":")
                corpus_size += int(size.strip())

        # Get frequency of annotation
        log.info("Getting frequencies from %s", c)
        process = subprocess.Popen([CWB_SCAN_EXECUTABLE, "-r", CORPUS_REGISTRY, c] + [annotation],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        reply, error = process.communicate()
        reply = reply.decode()
        if error:
            error = error.decode()
            if "Error:" in error:  # We always get something back on stderror from cwb-scan-corpus, so we must check if it really is an error
                if "Error: can't open attribute" in error:
                    log.error("Annotation '%s' not found", annotation)
                    sys.exit(1)

        for line in reply.splitlines():
            if not line.strip():
                continue
            freq, classes = line.split("\t")
            for cl in classes.split("|"):
                if cl:
                    freq = int(freq)
                    if score_separator:
                        cl, score = cl.rsplit(score_separator, 1)
                        score = float(score)
                        if score <= 0:
                            continue
                        freq = freq * score
                    corpus_stats[cl.replace("_", " ")] += freq

    rel_freq = defaultdict(float)

    for cl in all_classes:
        cl = cl.replace("_", " ")
        rel_freq[cl] = (corpus_stats[cl] + smoothing) / (corpus_size + smoothing * lexicon_size)

    util.lexicon_to_pickle(rel_freq, filename)
