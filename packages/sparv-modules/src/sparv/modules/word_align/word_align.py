"""NB: Not adapted to Sparv v4 yet!"""
# ruff: noqa

from sparv.api import util


def align_texts(
    word1,
    word2,
    linktok1,
    linktok2,
    link1,
    link2,
    linkref2,
    out_wordlink,
    out_sentences,
    outindex1,
    outindex2,
    delimiter="|",
    affix="|",
):
    """Make a word alignment between the current text (1) and a reference text (2). The texts need to be sentence aligned.
    word1 and word2 are existing annotations for the wordforms in the two texts
    linktok1 and linktok2 contain information about which words there are in each link
    link1 and link2 are existing annotations for the sentence link IDs in the two texts
    linkref2 is the existing annotation for the word linkref IDs in text 2
    out_wordlink is the resulting annotation for the word links (refers to linkrefs in text 2)
    out_sentences, outindex1 and outindex2 are internal files needed for fast_align and atools
    """

    LINKREF2 = util.read_annotation(linkref2)
    WORD1 = util.read_annotation(word1)
    WORD2 = util.read_annotation(word2)

    text1, text2 = make_sent_aligned_text(WORD1, WORD2, linktok1, linktok2, link1, link2, out_sentences)
    indices = word_align(out_sentences, outindex1, outindex2)

    # collect existing word links in a temporary dictionary
    TMP_WORDLINK = {}
    for indices, sent1, sent2 in zip(indices.split(b"\n"), text1, text2):
        for index_pair in indices.split():
            i, j = index_pair.split(b"-")
            tokid1 = sent1[int(i)]
            linklist = TMP_WORDLINK.get(tokid1, [])
            linklist.append(LINKREF2[sent2[int(j)]])
            TMP_WORDLINK[tokid1] = linklist

    # make final annotation including empty word links
    OUT_WORDLINK = {}
    for tokid in WORD1:
        OUT_WORDLINK[tokid] = (
            affix + delimiter.join(TMP_WORDLINK.get(tokid, -1)) + affix if TMP_WORDLINK.get(tokid, -1) != -1 else affix
        )

    util.write_annotation(out_wordlink, OUT_WORDLINK)
    # inspect_results("inspection.txt", WORD1, WORD2, linktok1, linktok2, link1, link2, OUT_WORDLINK, delimiter)


def make_sent_aligned_text(WORD1, WORD2, linktok1, linktok2, link1, link2, out_sentences):
    """Make a sentence aligned text file (serves as input for fast_align)."""
    out_sent_linked = open(out_sentences, "w", encoding="utf-8")
    LINKTOK1 = util.read_annotation(linktok1)
    LINKTOK2 = util.read_annotation(linktok2)
    REVERSED_LINK2 = {v: k for k, v in util.read_annotation(link2).items()}

    all_text1 = []
    all_text2 = []
    for linkkey1, linkid in util.read_annotation_iteritems(link1):
        # ignore links that don't exist in reference text
        if linkid in REVERSED_LINK2:
            linkkey2 = REVERSED_LINK2[linkid]
            # ignore empty links
            if linkkey1 in LINKTOK1 and linkkey2 in LINKTOK2:
                text1 = [(w, WORD1[w]) for w in LINKTOK1[linkkey1].split()]
                text2 = [(w, WORD2[w]) for w in LINKTOK2[linkkey2].split()]
                out_sent_linked.write(
                    " ".join(w for span, w in text1) + " ||| " + " ".join(w for span, w in text2) + "\n"
                )
                all_text1.append([span for span, w in text1])
                all_text2.append([span for span, w in text2])

    return (all_text1, all_text2)


def word_align(sentencefile, indexfile1, indexfile2):
    """Word link the sentences in sentencefile. Return a string of word link indices."""
    # align
    out1, _ = util.system.call_binary("word_alignment/fast_align", ["-i", sentencefile, "-d", "-o", "-v"])
    with open(indexfile1, "wb") as f:
        f.write(out1)
    # reverse align
    out2, _ = util.system.call_binary("word_alignment/fast_align", ["-i", sentencefile, "-d", "-o", "-v", "-r"])
    with open(indexfile2, "wb") as f:
        f.write(out2)
    # symmetrise
    indices, _ = util.system.call_binary(
        "word_alignment/atools", ["-i", indexfile1, "-j", indexfile2, "-c", "grow-diag-final-and"]
    )
    return indices


# def inspect_results(inspect, WORD1, WORD2, linktok1, linktok2, link1, link2, OUT_WORDLINK, delimiter):
#     """Create a word aligned text file ("inspection.txt") for
#     manual inspection of the word alignment result."""
#     LINKTOK1 = util.read_annotation(linktok1)
#     LINKTOK2 = util.read_annotation(linktok2)
#     REVERSED_LINK1 = {v:k for k, v in util.read_annotation(link1).items()}
#     REVERSED_LINK2 = {v:k for k, v in util.read_annotation(link2).items()}

#     inspection = open(inspect, 'wb')
#     for link in util.read_annotation(link1).values():
#         if link in REVERSED_LINK2:
#             if REVERSED_LINK1[link] in LINKTOK1 and REVERSED_LINK2[link] in LINKTOK2:
#                 sent1 = LINKTOK1[REVERSED_LINK1[link]].split()
#                 sent2 = LINKTOK2[REVERSED_LINK2[link]].split()
#                 for w1tokid in sent1:
#                     linkids = [int(l)-1 for l in OUT_WORDLINK[w1tokid].split(delimiter) if l]
#                     w2 = " | ".join(WORD2[sent2[linkid]] for linkid in linkids).encode("utf-8")
#                     w1 = WORD1[w1tokid].encode("utf-8")
#                     inspection.write("\n" + w1 + " "*(16-len(w1.decode("utf-8"))) + " " + w2)
#                 inspection.write("\n")

######################################################################

if __name__ == "__main__":
    util.run.main(align_texts)
