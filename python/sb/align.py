# -*- coding: utf-8 -*-

from collections import defaultdict
import util


def align(link_column, sent_column, files, out):
    if isinstance(files, basestring):
        files = files.split()
    link_column = int(link_column)
    sent_column = int(sent_column)

    linkdict = defaultdict(dict)
    sentdict = defaultdict(dict)
    for fil in files:
        with open(fil) as F:
            for nr, line in enumerate(F):
                if not line.strip() or line.startswith("<"):
                    continue
                cols = line.split("\t")
                try:
                    sent = cols[sent_column].strip()
                    link = cols[link_column].strip()
                    link = int(link)
                except IndexError:
                    continue
                except ValueError:
                    util.log.warning("%s (line %d), link not integer: %s", fil, nr+1, link)
                linkdict[link].setdefault(fil, set()).add(sent)
                sentdict[sent].setdefault(fil, set()).add(link)

    for sent in sentdict:
        if sent:
            for fil in sentdict[sent]:
                links = tuple(sorted(sentdict[sent][fil]))
                if len(links) > 1:
                    util.log.warning("MERGING overlap in %s: sentence %s -> links %s", fil, sent, links)
                    for link in links:
                        for fil in linkdict[link]:
                            sents = linkdict[link][fil]
                            linkdict[links].setdefault(fil, set()).update(sents)
                        del linkdict[link]

    with open(out, "w") as OUT:
        for link in linkdict:
            beads = []
            for fil in files:
                sents = linkdict[link].get(fil, ())
                beads.append(" ".join(sents))
            if all(beads):
                print >>OUT, "\t".join(beads)
            else:
                util.log.warning("Missing sentences in link nr %s: %s", link, " / ".join(beads))
    util.log.info("Wrote alignment %d beads: %s", len(linkdict), out)


if __name__ == '__main__':
    util.run.main(align)
