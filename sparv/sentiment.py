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
        # Get set of senses for each token
        token_senses = dict([s.rsplit(util.SCORESEP, 1) if util.SCORESEP in s else (s, -1.0)
                             for s in sense[token].split(util.DELIM) if s])

        # Check for sense annotations and if any of the senses occur in the sentiment lexicon
        if token_senses and any(lexicon.lookup(s, (None, None))[1] for s in token_senses):
            sent_sum = 0.0
            labels_set = set()
            for s in token_senses:
                p = float(token_senses[s])
                if p < 0:
                    p = 1.0 / len(token_senses)
                sent_label, sent_score = lexicon.lookup(s, (None, None))
                if sent_label is not None:
                    labels_set.add(sent_label)
                    # Calculate weighted mean value
                    sent_sum += float(sent_score) * p
            result_scores[token] = str(round(sent_sum, max_decimals))
            # If there are multiple labels, derive label from polarity_score
            if len(labels_set) > 1:
                result_labels[token] = SENTIMENT_LABLES.get(round(sent_sum))
            else:
                result_labels[token] = SENTIMENT_LABLES.get(int(list(labels_set)[0]))

        else:
            result_scores[token] = None
            result_labels[token] = None

    util.write_annotation(out_scores, result_scores)
    util.write_annotation(out_labels, result_labels)


def sentiment_class(out, sent, classes):
    """Translate numeric sentiment values into classes.
    - out: resulting annotation file.
    - sent: existing sentiment annotation.
    - classes: numeric spans and classes, on the format '0:0.33:negative|0.33:0.66:neutral|0.66:1:positive'."""

    classes = dict((tuple(float(n) for n in c.split(":")[:2]), c.split(":")[2]) for c in classes.split("|"))
    sent = util.read_annotation(sent)
    result = {}

    for token in sent:
        if not sent[token]:
            result[token] = None
            continue
        sent_value = float(sent[token])
        for c in classes:
            if c[0] <= sent_value <= c[1]:
                result[token] = classes[c]
                break

    util.write_annotation(out, result)


def read_sensaldo(tsv="sensaldo-base.txt", verbose=True):
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
            saldoid, manual_label, automatic_label, polarity_score, _freq = line.split()
            lexicon[saldoid] = (manual_label, polarity_score)

    testwords = ["förskräcklig..1",
                 "ödmjukhet..1",
                 "festlig..1"
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
                  sentiment_class=sentiment_class,
                  sensaldo_to_pickle=sensaldo_to_pickle
                  )
