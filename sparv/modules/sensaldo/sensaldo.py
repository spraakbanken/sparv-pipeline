"""Sentiment annotation per token using SenSALDO."""


from sparv.api import Annotation, Config, Model, ModelOutput, Output, annotator, get_logger, modelbuilder, util

logger = get_logger(__name__)

SENTIMENT_LABLES = {
    -1: "negative",
    0: "neutral",
    1: "positive"
}


@annotator("Sentiment annotation per token using SenSALDO", language=["swe"], config=[
    Config("sensaldo.model", default="sensaldo/sensaldo.pickle", description="Path to SenSALDO model")
])
def annotate(sense: Annotation = Annotation("<token:sense>"),
             out_scores: Output = Output("<token>:sensaldo.sentiment_score", description="SenSALDO sentiment score"),
             out_labels: Output = Output("<token>:sensaldo.sentiment_label", description="SenSALDO sentiment label"),
             model: Model = Model("[sensaldo.model]"),
             lexicon=None):
    """Assign sentiment values to tokens based on their sense annotation.

    When more than one sense is possible, calulate a weighted mean.
    - sense: existing annotation with saldoIDs.
    - out_scores, out_labels: resulting annotation file.
    - model: pickled lexicon with saldoIDs as keys.
    - lexicon: this argument cannot be set from the command line,
      but is used in the catapult. This argument must be last.
    """
    if not lexicon:
        lexicon = util.misc.PickledLexicon(model.path)
    # Otherwise use pre-loaded lexicon (from catapult)

    result_scores = []
    result_labels = []

    for token in sense.read():
        # Get set of senses for each token and sort them according to their probabilities
        token_senses = [tuple(s.rsplit(util.constants.SCORESEP, 1)) if util.constants.SCORESEP in s else (s, -1.0)
                        for s in token.split(util.constants.DELIM) if s]
        token_senses.sort(key=lambda x: float(x[1]), reverse=True)

        # Lookup the sentiment score for the most probable sense and assign a sentiment label
        if token_senses:
            best_sense = token_senses[0][0]
            score = lexicon.lookup(best_sense, None)
        else:
            score = None

        if score:
            result_scores.append(score)
            result_labels.append(SENTIMENT_LABLES.get(int(score)))
        else:
            result_scores.append(None)
            result_labels.append(None)

    out_scores.write(result_scores)
    out_labels.write(result_labels)


@modelbuilder("Sentiment model (SenSALDO)", language=["swe"])
def build_model(out: ModelOutput = ModelOutput("sensaldo/sensaldo.pickle")):
    """Download and build SenSALDO model."""
    # Download and extract sensaldo-base-v02.txt
    zip_model = Model("sensaldo/sensaldo-v02.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/sensaldo/sensaldo-v02.zip")
    zip_model.unzip()
    tsv_model = Model("sensaldo/sensaldo-base-v02.txt")

    # Read sensaldo tsv dictionary and save as a pickle file
    lexicon = read_sensaldo(tsv_model)
    out.write_pickle(lexicon)

    # Clean up
    zip_model.remove()
    tsv_model.remove()
    Model("sensaldo/sensaldo-fullform-v02.txt").remove()


def read_sensaldo(tsv, verbose=True):
    """Read the TSV version of the sensaldo lexicon (sensaldo-base.txt).

    Return a lexicon dictionary: {senseid: (class, ranking)}
    """
    if verbose:
        logger.info("Reading TSV lexicon")
    lexicon = {}

    f = tsv.read()
    # with open(tsv) as f:
    for line in f.split("\n"):
        if line.lstrip():
            if line.startswith("#"):
                continue
            saldoid, label = line.split()
            lexicon[saldoid] = label

    testwords = ["förskräcklig..1",
                 "ödmjukhet..1",
                 "handla..1"
                 ]
    util.misc.test_lexicon(lexicon, testwords)

    if verbose:
        logger.info("OK, read")
    return lexicon
