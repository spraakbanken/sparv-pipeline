# -*- coding: utf-8 -*-

import codecs
import util


def align_texts(word1, word2, linktok1, linktok2, link1, link2, linkref2, out_wordlink, out_sentences, outindex1, outindex2, delimiter="|", affix="|"):
    """Makes a word alignment between the current text (1) and a reference text (2). The texts need to be sentence aligned.
    word1 and word2 are existing annotations for the wordforms in the two texts
    linktok1 and linktok2 contain information about which words there are in each link
    link1 and link2 are existing annotations for the link IDs in the two texts
    linkref2 is the existing annotation for the linkref IDs in text 2
    out_wordlink is the resulting annotation for the word links (refers to linkrefs in text 2)
    out_sentences, outindex1 and outindex2 are internal files needed for fast_align and atools
    """

    LINKREF2 = util.read_annotation(linkref2)
    WORD1 = util.read_annotation(word1)
    WORD2 = util.read_annotation(word2)
    
    text1, text2 = make_sent_aligned_text(WORD1, WORD2, linktok1, linktok2, link1, link2, out_sentences)
    indices = word_align(out_sentences, outindex1, outindex2)

    TMP_WORDLINK = {}
    for indices, sent1, sent2 in zip(indices.split("\n"), text1, text2):
        for index_pair in indices.split():
            i, j = index_pair.split("-")
            tokid1 = sent1[int(i)]
            linklist = TMP_WORDLINK.get(tokid1, [])
            linklist.append(LINKREF2[sent2[int(j)]])
            TMP_WORDLINK[tokid1] = linklist

    OUT_WORDLINK = {}
    for tokid in WORD1:
        OUT_WORDLINK[tokid] = affix + delimiter.join(TMP_WORDLINK.get(tokid, -1)) + affix \
            if TMP_WORDLINK.get(tokid, -1) != -1 else affix

    util.write_annotation(out_wordlink, OUT_WORDLINK)


def make_sent_aligned_text(WORD1, WORD2, linktok1, linktok2, link1, link2, out_sentences):
    """ Make a sentence aligned text file (serves as input for fast_align)."""
    out_sent_linked = codecs.open(out_sentences, 'wb', encoding='utf-8')
    LINKTOK1 = util.read_annotation(linktok1)
    LINKTOK2 = util.read_annotation(linktok2)
    REVERSED_LINK2 = {v:k for k, v in util.read_annotation(link2).items()}

    all_text1 = []
    all_text2 = []
    for linkkey1, linkid in util.read_annotation_iteritems(link1):
        linkkey2 = REVERSED_LINK2[linkid]
        text1 = [(w, WORD1[w]) for w in LINKTOK1[linkkey1].split()]
        text2 = [(w, WORD2[w]) for w in LINKTOK2[linkkey2].split()]
        out_sent_linked.write(" ".join(w for span, w in text1) + " ||| " + " ".join(w for span, w in text2) + "\n")
        all_text1.append([span for span, w in text1])
        all_text2.append([span for span, w in text2])

    return (all_text1, all_text2)


def word_align(sentencefile, indexfile1, indexfile2):
    """ Word link the sentences in sentencefile. Return a string of word link indices."""
    # align
    out1, _ = util.system.call_binary("fast_align", ["-i", sentencefile, "-d", "-o", "-v"])
    with open(indexfile1, 'wb') as f:
        f.write(out1)
    # reverse align
    out2, _ = util.system.call_binary("fast_align", ["-i", sentencefile, "-d", "-o", "-v", "-r"])
    with open(indexfile2, 'wb') as f:
        f.write(out2)
    # symmetrise
    indices, _ = util.system.call_binary("atools", ["-i", indexfile1, "-j", indexfile2, "-c", "grow-diag-final-and"])
    return indices

######################################################################

if __name__ == '__main__':
    util.run.main(align_texts)
