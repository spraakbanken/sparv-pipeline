"""Train a probability model on a Korp statistics file."""

import pickle
import urllib.request
from pathlib import Path

from sparv.api import Model, ModelOutput, get_logger, modelbuilder

logger = get_logger(__name__)

MIN_FREQ = 4


@modelbuilder("Korp statistic model", order=1)
def download_korp_stats(out: ModelOutput = ModelOutput("saldo/stats.pickle")) -> None:
    """Download prebuilt stats.pickle model.

    Args:
        out: The model output file path.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/saldo/stats.pickle")


@modelbuilder("Korp statistic model", order=2)
def build_korp_stats(
    out: ModelOutput = ModelOutput("saldo/stats.pickle"), _saldom: Model = Model("saldo/saldom.xml")
) -> None:
    """Download Korp's word frequency file and convert it to a model.

    Args:
        out: The model output file path.
        _saldom: The saldom.xml model path.
    """
    txt_file = Model("saldo/stats_all.txt")
    try:
        logger.info("Downloading Korp stats file...")
        download_stats_file(
            "https://svn.spraakbanken.gu.se/sb-arkiv/!svn/bc/246648/pub/frekvens/stats_all.txt", txt_file.path
        )

        logger.info("Building frequency model...")
        make_model(txt_file.path, out.path)
    finally:
        # Clean up
        txt_file.remove()


def download_stats_file(url: str, destination: Path) -> None:
    """Download statistics file in chunks, aborting when we've got what we need.

    Args:
        url: The URL to download the file from.
        destination: The path where the file will be saved.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    response = urllib.request.urlopen(url)
    chunk_size = 512 * 1024
    with destination.open("wb") as out_file:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            try:
                # Pick out second line in chunk (first is likely incomplete)
                first_line = chunk.decode("UTF-8").split("\n", 2)[1]
                if int(first_line.split("\t")[4]) < MIN_FREQ:
                    break
            except UnicodeDecodeError:
                # Some chunks won't be decodable but that's okay
                pass

            out_file.write(chunk)


def make_model(
    stats_infile: Path, picklefile: Path, smoothingparam: float = 0.001, min_freq: int = MIN_FREQ, protocol: int = -1
) -> None:
    """Train a probability model on a Korp statistics file and save it as a pickle file.

    The model is a LidstoneProbDist (NLTK) which has tuples (wordform, MSD-tag) as keys
    and smoothed probabilities as values.

    Args:
        stats_infile: The input Korp statistics file.
        picklefile: The output pickle file.
        smoothingparam: The smoothing parameter for the Lidstone probability distribution.
        min_freq: The minimum frequency for a word to be included in the model.
        protocol: The pickle protocol to use. -1 means the highest protocol available.
    """
    from nltk import FreqDist, LidstoneProbDist  # noqa: PLC0415

    fdist = FreqDist()
    with stats_infile.open(encoding="UTF-8") as f:
        for line in f:
            fields = line[:-1].split("\t")
            word = fields[0]
            freq = int(fields[4])
            # Skip word forms that occur fewer times than min_freq
            if freq < min_freq:
                break
            # Get rid of all URLs
            if word.startswith(("http://", "https://", "www.")):
                continue
            # # Words that only occur once may only contain letters and hyphens
            # if fields[4] == "1" and any(not (c.isalpha() or c == "-") for c in word):
            #     continue
            # if len(word) > 100:
            #     continue
            simple_msd = fields[1][: fields[1].find(".")] if "." in fields[1] else fields[1]
            fdist[word, simple_msd] += freq
    pd = LidstoneProbDist(fdist, smoothingparam, fdist.B())

    # Save probability model as pickle
    with picklefile.open("wb") as p:
        pickle.dump(pd, p, protocol=protocol)
