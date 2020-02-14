#!/usr/bin/env python3

"""Build word frequency list from Sparv's XML output."""

import argparse
import csv
from collections import defaultdict
import glob
import xml.etree.ElementTree as etree


WORD_NODE = "w"

parser = argparse.ArgumentParser(description="Build word frequency list from Sparv's XML output.")
parser.add_argument("-i", "--inpattern", help="pattern for XML files to process, relative to working dir (default: 'export*/**/*.xml')",
                    dest="inpattern", default="export*/**/*.xml")
parser.add_argument("-o", "--outfile", help="path to the output file (frequency list), e.g. stats_attasidor.tsv", required=True, dest="outfile")


def loop_exports(glob_exp, out_file):
    """Loop through XML files matching glob_exp and write frequencies to out_file."""
    freq_dict = defaultdict(int)
    pathlist = glob.glob(glob_exp, recursive=True)
    print("\nCollecting frequencies from %s files:\n" % len(pathlist))
    for path in sorted(pathlist):
        parse_export(path, freq_dict)

    with open(out_file, "w") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter="\t")
        csv_writer.writerow(["token", "POS", "lemma", "SALDO sense", "lemgram", "compound", "count"])
        for (wordform, msd, lemma, sense, lemgram, complemgram), freq in sorted(freq_dict.items(), key=lambda x: -x[1]):
            csv_writer.writerow([wordform, msd, lemma, sense, lemgram, complemgram, freq])


def parse_export(in_file, freq_dict):
    """Parse in_file and add frequencies in freq_dict."""
    print("Parsing %s" % in_file)
    tree = etree.parse(in_file)
    root = tree.getroot()
    for word in root.findall(".//" + WORD_NODE):
        wordform = word.text
        msd = word.get("msd")
        lemma = word.get("lemma").split("|")[1]
        sense = word.get("sense").split("|")[1].split(":")[0]
        lemgram = word.get("lex").split("|")[1].split(":")[0]
        if not sense:
            complemgram = word.get("complemgram").split("|")[1].split(":")[0]
        else:
            complemgram = ""
        freq_dict[(wordform, msd, lemma, sense, lemgram, complemgram)] += 1


if __name__ == "__main__":
    args = parser.parse_args()
    loop_exports(args.inpattern, args.outfile)
