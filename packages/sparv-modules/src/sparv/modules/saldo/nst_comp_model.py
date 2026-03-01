"""Train a POS probability model on the NST lexicon."""

import pickle
import re
from pathlib import Path

from sparv.api import Model, ModelOutput, get_logger, modelbuilder

logger = get_logger(__name__)


@modelbuilder("Compound POS model", order=1)
def download_nst_comp(out: ModelOutput = ModelOutput("saldo/nst_comp_pos.pickle")) -> None:
    """Download compound POS model from sparv-models repo.

    Args:
        out: The output file path.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/saldo/nst_comp_pos.pickle")


@modelbuilder("Compound POS model", order=2)
def build_nst_comp(
    out: ModelOutput = ModelOutput("saldo/nst_comp_pos.pickle"), nst_lexicon: Model = Model("saldo/nst_utf8.txt")
) -> None:
    """Download NST lexicon and convert it to a compound POS model.

    The NST lexicon can be retrieved from SVN with credentials:
        svn export https://svn.spraakdata.gu.se/sb-arkiv/lexikon/NST_svensk_leksikon/nst_utf8.txt saldo/nst_utf8.txt

    Args:
        out: The output file path.
        nst_lexicon: The NST lexicon file path.
    """
    logger.info("Building compound POS probability model...")
    make_model(nst_lexicon.path, out.path)


def make_model(nst_infile: Path, picklefile: Path, protocol: int = -1) -> None:
    """Train a POS probability model on the NST lexicon and save it as a pickle file.

    The model is a LidstoneProbDist (NLTK) which has compounded POS tags (SUC set) as keys (e.g. "NN+NN")
    and smoothed probabilities as values.

    Args:
        nst_infile: The NST lexicon file path.
        picklefile: The output file path for the model.
        protocol: The pickle protocol to use (default is -1, which uses the highest protocol available).
    """
    from nltk import FreqDist, LidstoneProbDist  # noqa: PLC0415

    # Collect all compounds from nst data
    nst_full_compounds = set()
    with nst_infile.open(encoding="UTF-8") as f:
        for line in f:
            fields = line[:-1].split("\t")
            word = fields[0]
            comp = fields[3].replace("!", "")
            pos = fields[4]
            if "+" in comp and "_" not in word and not (comp.startswith(("+", "-"))):
                nst_full_compounds.add((word, comp, pos))

    # Build POS probability model
    pos_fdist = FreqDist()
    for _w, _c, pos in nst_full_compounds:
        if "+" in pos:
            pos = re.sub(r"\+LN", "", pos)  # noqa: PLW2901
            pos_fdist[pos] += 1

    pd = LidstoneProbDist(pos_fdist, 0.001, pos_fdist.B())

    # Save probability model as pickle
    with picklefile.open("wb") as f:
        pickle.dump(pd, f, protocol=protocol)
