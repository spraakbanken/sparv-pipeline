# -*- coding: utf-8 -*-

import sparv.util as util

SENTIMENT_LABLES = {
    -1: "negative",
    0: "neutral",
    1: "positive"
}


def sentiment(sense, out_scores, out_labels, model, max_decimals=6, lexicon=None):
    """Assign sentiment values to tokens based on their sense annotation.
    When more than one sense is possible, calulate a weighted mean.
    - sense: existing annotation with saldoIDs.
    - out_scores, out_labels: resulting annotation file.
    - model: pickled lexicon with saldoIDs as keys.
    - max_decimals: int stating the amount of decimals the result is rounded to.
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """

    if not lexicon:
        lexicon = util.PickledLexicon(model)
    # Otherwise use pre-loaded lexicon (from catapult)

    sense = util.read_annotation(sense)
    result_scores = {}
    result_labels = {}

    for token in sense:
        # Get set of senses for each token and sort them according to their probabilities
        token_senses = [tuple(s.rsplit(util.SCORESEP, 1)) if util.SCORESEP in s else (s, -1.0)
                        for s in sense[token].split(util.DELIM) if s]
        token_senses.sort(key=lambda x: x[1], reverse=True)

        # Lookup the sentiment score for the most probable sense and assign a sentiment label
        if token_senses:
            best_sense = token_senses[0][0]
            score = lexicon.lookup(best_sense, None)
        else:
            score = None

        if score:
            result_scores[token] = score
            result_labels[token] = SENTIMENT_LABLES.get(int(score))
        else:
            result_scores[token] = None
            result_labels[token] = None

    util.write_annotation(out_scores, result_scores)
    util.write_annotation(out_labels, result_labels)


def read_sensaldo(tsv="sensaldo-base-v02.txt", verbose=True):
    """
    Read the TSV version of the sensaldo lexicon (sensaldo-base.txt).
    Return a lexicon dictionary: {senseid: (class, ranking)}
    """

    if verbose:
        util.log.info("Reading TSV lexicon")
    lexicon = {}

    with open(tsv) as f:
        for line in f:
            if line.lstrip().startswith("#"):
                continue
            saldoid, label = line.split()
            lexicon[saldoid] = label

    testwords = ["förskräcklig..1",
                 "ödmjukhet..1",
                 "handla..1"
                 ]
    util.test_annotations(lexicon, testwords)

    if verbose:
        util.log.info("OK, read")
    return lexicon


def sensaldo_to_pickle(tsv, filename, protocol=-1, verbose=True):
    """Read sensaldo tsv dictionary and save as a pickle file."""
    lexicon = read_sensaldo(tsv)
    util.lexicon_to_pickle(lexicon, filename)


if __name__ == '__main__':
    util.run.main(sentiment,
                  sensaldo_to_pickle=sensaldo_to_pickle
                  )
