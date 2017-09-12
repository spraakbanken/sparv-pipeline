# -*- coding: utf-8 -*-

import sb.util as util


def sentiment(sense, out, model, max_decimals=6):
    """Assign sentiment values to tokens based on their sense annotation.
    When more than one sense is possible, calulate a weighted mean."""

    senses = {}
    with open(model, encoding="UTF-8") as infile:
        for line in infile:
            s, _, v = line.split()
            senses[s] = float(v)

    sense = util.read_annotation(sense)
    result = {}

    for token in sense:
        token_senses = dict([s.rsplit(util.SCORESEP, 1) if util.SCORESEP in s else (s, -1.0)
                             for s in sense[token].split(util.DELIM) if s])

        sum = 0.0
        for s in token_senses:
            p = float(token_senses[s])
            if p < 0:
                p = 1.0 / len(token_senses)
            sum += senses.get(s, 0.0) * p

        result[token] = str(round(sum, max_decimals))

    util.write_annotation(out, result)

if __name__ == '__main__':
    util.run.main(sentiment
                  )
