# -*- coding: utf-8 -*-
"""
Creates training material from SUC2 for use with the HUNPOS-tagger.
"""
import sparv.util as util
import os.path


def suc2hunpos(out, msd, sentences, word):
    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)
    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentences)]

    OUT = []

    for sentence in sentences:
        for tokid in sentence:
            OUT.append((WORD[tokid], MSD[tokid]))
        OUT.append(("", ""))

    write_hunsource(out, OUT)


def write_hunsource(file, annotation):
    util.system.make_directory(os.path.dirname(file))
    with open(file, "w") as DB:
        ctr = 0
        for key, value in annotation:
            if value is None:
                value = ""
            value = value.replace("\\", r"\\").replace("\n", r"\n")
            if key:
                print((key + "\t" + value).encode(util.UTF8), file=DB)
            else:
                print("".encode(util.UTF8), file=DB)
            ctr += 1
    util.log.info("Wrote %d items: %s", ctr, file)

if __name__ == '__main__':
    util.run.main(suc2hunpos)
