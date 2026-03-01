"""NB: Not adapted to Sparv v4 yet!"""
# ruff: noqa

import math

from sparv.api import util


def align_texts(sentence1, sentence2, link1, link2, sent_parents1, sent_parents2, out_sentlink1, out_sentlink2):
    """Make a more fine-grained sentence alignment between the current text (1) and a parallel reference text (2).
    - sentence1 and sentence2 contain information about which word-IDs there are in each sentence
    - link1 and link2 are existing annotations for the link IDs in the two texts
    - linkref2 is the existing annotation for the linkref IDs in text 2
    - sent_parents1 and sent_parents2 contain information about which sentences there are in each of the old sentence links
    - out_sentlink1 and out_sentlink2, are the resulting annotations for the new sentence links
    """

    REVERSED_LINK2 = {v: k for k, v in util.read_annotation(link2).items()}
    SENTPARENTS1 = util.read_annotation(sent_parents1)
    SENTPARENTS2 = util.read_annotation(sent_parents2)
    SENT1 = util.read_annotation(sentence1)
    SENT2 = util.read_annotation(sentence2)

    OUT_SENTLINK1 = {}
    OUT_SENTLINK2 = {}

    linkcounter = 0

    # Loop through existing links and split them into smaller units if possible (only if both links have text)
    for linkkey1, linkid in util.read_annotation_iteritems(link1):
        linkkey2 = REVERSED_LINK2[linkid]
        if linkkey1 in SENTPARENTS1 and linkkey2 in SENTPARENTS2:
            linkedsents1 = []
            linkedsents2 = []
            for sentid in SENTPARENTS1[linkkey1].split():
                linkedsents1.append((sentid, list(SENT1[sentid].split())))
            for sentid in SENTPARENTS2[linkkey2].split():
                linkedsents2.append((sentid, list(SENT2[sentid].split())))

            for s1, s2 in gachalign(linkedsents1, linkedsents2, mean="gacha"):
                linkcounter += 1
                if s1:
                    newlink1 = util.mkEdge("link", [util.edgeStart(s1[0]), util.edgeEnd(s1[-1])])
                    OUT_SENTLINK1[newlink1] = str(linkcounter)

                if s2:
                    newlink2 = util.mkEdge("link", [util.edgeStart(s2[0]), util.edgeEnd(s2[-1])])
                    OUT_SENTLINK2[newlink2] = str(linkcounter)

        # annotation if a link has text in one language but is empty in the other one
        elif linkkey1 in SENTPARENTS1 or linkkey2 in SENTPARENTS2:
            linkcounter += 1
            newlink1 = util.mkEdge("link", [util.edgeStart(linkkey1), util.edgeEnd(linkkey1)])
            OUT_SENTLINK1[newlink1] = str(linkcounter)
            newlink2 = util.mkEdge("link", [util.edgeStart(linkkey2), util.edgeEnd(linkkey2)])
            OUT_SENTLINK2[newlink2] = str(linkcounter)

    util.write_annotation(out_sentlink1, OUT_SENTLINK1)
    util.write_annotation(out_sentlink2, OUT_SENTLINK2)


##############################################################################
# The remaining code is adapted from the python module "gachalign",
# available at https://code.google.com/p/gachalign/
# code license: GNU GPL v3

BEAD_COSTS = {(1, 1): 0, (2, 1): 230, (1, 2): 230, (0, 1): 450, (1, 0): 450, (2, 2): 440}


def gachalign(text1, text2, mean=1.0, variance=6.8, bc=BEAD_COSTS):
    """Alignment wrapper function"""
    lt1 = list(map(len, [s[1] for s in text1]))
    lt2 = list(map(len, [s[1] for s in text2]))

    if mean == "gacha":
        mean = len([s[1] for s in text1]) / float(len([s[1] for s in text2]))

    for (i1, i2), (j1, j2) in reversed(list(align(lt1, lt2, mean, variance, bc))):
        yield [t[0] for t in text1[i1:i2]], [t[0] for t in text2[j1:j2]]


def align(t1, t2, mean_xy, variance_xy, bead_costs):
    """The minimization function to choose the sentence pair with the cheapest alignment cost."""
    m = {}
    for i in range(len(t1) + 1):
        for j in range(len(t2) + 1):
            if i == j == 0:
                m[0, 0] = (0, 0, 0)
            else:
                m[i, j] = min(
                    (
                        m[i - di, j - dj][0]
                        + length_cost(t1[i - di : i], t2[j - dj : j], mean_xy, variance_xy)
                        + bead_cost,
                        di,
                        dj,
                    )
                    for (di, dj), bead_cost in BEAD_COSTS.items()
                    if i - di >= 0 and j - dj >= 0
                )
    i, j = len(t1), len(t2)
    while True:
        (_c, di, dj) = m[i, j]
        if di == dj == 0:
            break
        yield (i - di, i), (j - dj, j)
        i -= di
        j -= dj


def length_cost(sx, sy, mean_xy, variance_xy):
    """Calculate length cost given 2 sentence. Lower cost = higher prob.
    The original Gale-Church (1993:pp. 81) paper considers l2/l1 = 1 hence:
    delta = (l2-l1*c)/math.sqrt(l1*s2)
    If l2/l1 != 1 then the following should be considered:
    delta = (l2-l1*c)/math.sqrt((l1+l2*c)/2 * s2)
    substituting c = 1 and c = l2/l1, gives the original cost function.
    """
    lx, ly = sum(sx), sum(sy)
    m = (lx + ly * mean_xy) / 2
    try:
        delta = (lx - ly * mean_xy) / math.sqrt(m * variance_xy)
    except ZeroDivisionError:
        return float("-inf")
    return -100 * (math.log(2) + norm_logsf(abs(delta)))


def norm_cdf(z):
    """Scipy's norm distribution function as of Gale-Church'srcfile (1993)."""
    # Equation 26.2.17 from Abramowitz and Stegun (1964:p.932)
    t = 1 / float(1 + 0.2316419 * z)  # t = 1/(1+pz) , z=0.2316419
    probdist = 1 - 0.3989423 * math.exp(-z * z / 2) * (
        (0.319381530 * t)
        + (-0.356563782 * math.pow(t, 2))
        + (1.781477937 * math.pow(t, 3))
        + (-1.821255978 * math.pow(t, 4))
        + (1.330274429 * math.pow(t, 5))
    )
    return probdist


def norm_logsf(z):
    """Take log of the survival function for normal distribution."""
    try:
        return math.log(1 - norm_cdf(z))
    except ValueError:
        return float("-inf")


######################################################################

if __name__ == "__main__":
    util.run.main(align_texts)
