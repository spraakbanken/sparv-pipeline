"""Handle models for lexical classes."""

import csv
import subprocess
import xml.etree.ElementTree as etree  # noqa: N813
from collections import defaultdict
from pathlib import Path

from sparv.api import Model, ModelOutput, SparvErrorMessage, get_logger, modelbuilder, util

logger = get_logger(__name__)


@modelbuilder("Blingbring model", language=["swe"])
def blingbring_model(out: ModelOutput = ModelOutput("lexical_classes/blingbring.pickle")) -> None:
    """Download and build Blingbring model.

    Args:
        out: Output model.
    """
    # Download roget hierarchy
    classmap = Model("lexical_classes/roget_hierarchy.xml")
    classmap.download("https://github.com/spraakbanken/sparv-models/raw/master/lexical_classes/roget_hierarchy.xml")

    # Download blingbring.txt and build blingbring.pickle
    raw_file = Model("lexical_classes/blingbring.txt")
    raw_file.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/bring/blingbring.txt")
    lexicon = read_blingbring(raw_file.path, classmap.path)
    out.write_pickle(lexicon)

    # Clean up
    raw_file.remove()
    classmap.remove()


@modelbuilder("SweFN model", language=["swe"])
def swefn_model(out: ModelOutput = ModelOutput("lexical_classes/swefn.pickle")) -> None:
    """Download and build SweFN model.

    Args:
        out: Output model.
    """
    # Download swefn.xml and build swefn.pickle
    raw_file = Model("lexical_classes/swefn.xml")
    raw_file.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swefn/swefn.xml")
    lexicon = read_swefn(raw_file.path)
    out.write_pickle(lexicon)

    # Clean up
    raw_file.remove()


@modelbuilder("Blingbring frequency model", language=["swe"])
def blingbring_freq_model(
    out: ModelOutput = ModelOutput("lexical_classes/blingbring.freq.gp2008+suc3+romi.pickle"),
) -> None:
    """Download Blingbring frequency model.

    Args:
        out: Output model.
    """
    out.download(
        "https://github.com/spraakbanken/sparv-models/raw/master/lexical_classes/blingbring.freq.gp2008+suc3+romi.pickle"
    )


@modelbuilder("Blingbring frequency model", language=["swe"])
def swefn_freq_model(out: ModelOutput = ModelOutput("lexical_classes/swefn.freq.gp2008+suc3+romi.pickle")) -> None:
    """Download SweFN frequency model.

    Args:
        out: Output model.
    """
    out.download(
        "https://github.com/spraakbanken/sparv-models/raw/master/lexical_classes/swefn.freq.gp2008+suc3+romi.pickle"
    )


def read_blingbring(tsv: Path, classmap: Path, verbose: bool = True) -> dict:
    """Read the tsv version of the Blingbring lexicon (blingbring.xml).

    Args:
        tsv: Path to the tsv file.
        classmap: Path to the XML file with Roget hierarchy.
        verbose: If True, print progress messages.

    Returns:
        A dictionary with the following structure:
            {senseid: {roget_head: roget_head,
                roget_subsection: roget_subsection,
                roget_section: roget_section,
                roget_class: roget_class,
                bring: bring_ID}
    """
    rogetdict = read_rogetmap(xml=classmap, verbose=True)

    if verbose:
        logger.info("Reading tsv lexicon")
    lexicon = {}
    classmapping = {}

    with tsv.open(encoding="utf-8") as f:
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
        roget_head = {tup[0] for tup in rogetids}
        roget_subsection = {tup[1] for tup in rogetids if tup[1]}
        roget_section = {tup[2] for tup in rogetids if tup[2]}
        roget_class = {tup[3] for tup in rogetids if tup[3]}
        lexicon[senseid] = {
            "roget_head": roget_head,
            "roget_subsection": roget_subsection,
            "roget_section": roget_section,
            "roget_class": roget_class,
            "bring": {classmapping[r] for r in roget_head},
        }

    testwords = ["fågel..1", "behjälplig..1", "köra_ner..1"]
    util.misc.test_lexicon(lexicon, testwords)

    if verbose:
        logger.info("OK, read")
    return lexicon


def read_rogetmap(xml: Path, verbose: bool = True) -> dict:
    """Parse Roget map (Roget hierarchy) into a dictionary with Roget head words as keys.

    Args:
        xml: Path to the XML file.
        verbose: If True, print progress messages.

    Returns:
        A dictionary with the following structure:
            {roget_head: (roget_subsection, roget_section, roget_class)}
    """
    if verbose:
        logger.info("Reading XML lexicon")
    lexicon = {}
    context = etree.iterparse(xml, events=("start", "end"))
    context = iter(context)

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

    testwords = ["Existence", "Health", "Amusement", "Marriage"]
    util.misc.test_lexicon(lexicon, testwords)

    if verbose:
        logger.info("OK, read.")
    return lexicon


def read_swefn(xml: Path, verbose: bool = True) -> dict:
    """Read the XML version of the swedish Framenet resource.

    Args:
        xml: Path to the XML file.
        verbose: If True, print progress messages.

    Returns:
        A dictionary with the following structure:
            {saldoID: {swefnID}}
    """
    if verbose:
        logger.info("Reading XML lexicon")
    lexicon = {}

    context = etree.iterparse(xml, events=("start", "end"))  # "start" needed to save reference to root element
    context = iter(context)
    _event, root = next(context)

    for event, elem in context:
        if event == "end":
            if elem.tag == "LexicalEntry":
                sense = elem.find("Sense")
                sid = sense.get("id").removeprefix("swefn--")
                for lu in sense.findall("feat[@att='LU']"):
                    saldosense = lu.get("val")
                    lexicon.setdefault(saldosense, set()).add(sid)

            # Done parsing section. Clear tree to save memory
            if elem.tag in {"LexicalEntry", "frame", "resFrame"}:
                root.clear()

    testwords = ["slant..1", "befrielse..1", "granne..1", "sisådär..1", "mjölkcentral..1"]
    util.misc.test_lexicon(lexicon, testwords)

    if verbose:
        logger.info("OK, read.")
    return lexicon


def create_freq_pickle(
    corpus: str | list,
    annotation: str,
    model: str,
    cwb_bin_dir: str,
    cwb_registry: str,
    class_set: set | None = None,
    score_separator: str = util.constants.SCORESEP,
) -> None:
    """Build pickle with relative frequency for a given annotation in one or more reference corpora.

    This function is not used in the pipeline, but can be used to create a frequency model for a given annotation.

    Args:
        corpus: Corpus or list of corpora to use.
        annotation: Annotation to use.
        model: Path to the output model.
        cwb_bin_dir: Path to the CWB bin directory.
        cwb_registry: Path to the CWB registry.
        class_set: Class set to use. If None, all classes are used.
        score_separator: Separator for scores in the annotation. Default is util.constants.SCORESEP.

    Raises:
        SparvErrorMessage: If the annotation is not found in the corpus.
    """
    lexicon = util.misc.PickledLexicon(model)
    # Create a set of all possible classes
    if class_set:
        all_classes = {cc for c in lexicon.lexicon.values() for cc in c[class_set]}
    else:
        all_classes = {cc for c in lexicon.lexicon.values() for cc in c}
    lexicon_size = len(all_classes)
    smoothing = 0.1

    corpus_stats = defaultdict(int)
    corpus_size = 0

    if isinstance(corpus, str):
        corpus = corpus.split()

    cwb_path = Path(cwb_bin_dir)

    for c in corpus:
        # Get corpus size
        process = subprocess.Popen(
            [cwb_path / "cwb-describe-corpus", "-r", cwb_registry, c], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        reply, error = process.communicate()
        reply = reply.decode()

        if error:
            error = error.decode()
            raise SparvErrorMessage(error)

        for line in reply.splitlines():
            if line.startswith("size (tokens)"):
                _, size = line.split(":")
                corpus_size += int(size.strip())

        # Get frequency of annotation
        logger.info("Getting frequencies from %s", c)
        process = subprocess.Popen(
            [cwb_path / "cwb-scan-corpus", "-q", "-r", cwb_registry, c, annotation],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        reply, error = process.communicate()
        reply = reply.decode()
        if error and "Error: can't open attribute" in error.decode():
            logger.error("Annotation '%s' not found", annotation)
            raise SparvErrorMessage(f"Annotation '{annotation}' not found")

        for line in reply.splitlines():
            if not line.strip():
                continue
            freq, classes = line.split("\t")
            for cl in classes.split("|"):
                if cl:
                    freq = int(freq)
                    if score_separator:
                        cl, score = cl.rsplit(score_separator, 1)  # noqa: PLW2901
                        score = float(score)
                        if score <= 0:
                            continue
                        freq *= score
                    corpus_stats[cl.replace("_", " ")] += freq

    rel_freq = defaultdict(float)

    for cl in all_classes:
        cl = cl.replace("_", " ")  # noqa: PLW2901
        rel_freq[cl] = (corpus_stats[cl] + smoothing) / (corpus_size + smoothing * lexicon_size)

    model.write_pickle(rel_freq)
