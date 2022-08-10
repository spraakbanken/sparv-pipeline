"""Train a probability model on a Korp statistics file."""

import os
import pickle
import urllib.request

from nltk import FreqDist, LidstoneProbDist

from sparv.api import Model, ModelOutput, get_logger, modelbuilder

logger = get_logger(__name__)

MIN_FREQ = 4


@modelbuilder("Korp statistic model", language=["swe"], order=1)
def download_korp_stats(out: ModelOutput = ModelOutput("saldo/stats.pickle")):
    """Download stats.pickle model."""
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/saldo/stats.pickle")


@modelbuilder("Korp statistic model", language=["swe"], order=2)
def build_korp_stats(out: ModelOutput = ModelOutput("saldo/stats.pickle"),
                     _saldom: Model = Model("saldo/saldom.xml")):
    """Download Korp's word frequency file and convert it to a model."""
    txt_file = Model("saldo/stats_all.txt")
    try:
        logger.info("Downloading Korp stats file...")
        download_stats_file("https://svn.spraakdata.gu.se/sb-arkiv/pub/frekvens/stats_all.txt", txt_file.path)

        logger.info("Building frequency model...")
        make_model(txt_file.path, out.path)
    finally:
        # Clean up
        txt_file.remove()


def download_stats_file(url, destination):
    """Download statistics file in chunks, aborting when we've got what we need."""
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    response = urllib.request.urlopen(url)
    chunk_size = 512 * 1024
    with open(destination, "wb") as out_file:
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


def make_model(stats_infile, picklefile, smoothingparam=0.001, min_freq=MIN_FREQ, protocol=-1):
    """Train a probability model on a Korp statistics file and save it as a pickle file.

    The model is a LidstoneProbDist (NLTK) which has tuples (wordform, MSD-tag) as keys
    and smoothed probabilities as values.
    """
    fdist = FreqDist()
    with open(stats_infile, encoding="UTF-8") as f:
        for line in f:
            fields = line[:-1].split("\t")
            word = fields[0]
            freq = int(fields[4])
            # Skip word forms that occur fewer times than min_freq
            if freq < min_freq:
                break
            # Get rid of all URLs
            if word.startswith("http://") or word.startswith("https://") or word.startswith("www."):
                continue
            # # Words that only occur once may only contain letters and hyphens
            # if fields[4] == "1" and any(not (c.isalpha() or c == "-") for c in word):
            #     continue
            # if len(word) > 100:
            #     continue
            simple_msd = fields[1][:fields[1].find(".")] if "." in fields[1] else fields[1]
            fdist[(word, simple_msd)] += freq
    pd = LidstoneProbDist(fdist, smoothingparam, fdist.B())

    # Save probability model as pickle
    with open(picklefile, "wb") as p:
        pickle.dump(pd, p, protocol=protocol)
