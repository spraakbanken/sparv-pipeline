"""Part of Speech annotation using Flair."""

from sparv import Annotation, Config, Model, ModelOutput, Output, annotator, modelbuilder
import sparv.util as util

logger = util.get_logger(__name__)


@annotator("Part-of-speech annotation with morphological descriptions from Flair", config=[
           Config("flair.model", default="flair/flair_full/final-model.pt", description="Flair model")])
def msdtag(out: Output = Output("<token>:flair.msd", cls="token:msd",
                                description="Part-of-speeches with morphological descriptions"),
           word: Annotation = Annotation("<token:word>"),
           sentence: Annotation = Annotation("<sentence>"),
           model: Model = Model("[flair.model]")):
    """POS tag using Flair."""
    sentences, _orphans = sentence.get_children(word)
    token_word = list(word.read())
    out_annotation = []

    # TODO: These imports cause annoying warnings due to PyTorch (https://github.com/pytorch/pytorch/issues/47038).
    # Move these to the top when this gets resolved.
    from flair.data import Sentence
    from flair.models import SequenceTagger

    # Load model
    tagger = SequenceTagger.load(model.path)

    # Tag one sentence at a time
    flair_sentences = []
    for sentence in sentences:
        s = " ".join(token_word[token_index] for token_index in sentence)
        flair_sent = Sentence(s, use_tokenizer=False)
        flair_sentences.append(flair_sent)
    tagger.predict(flair_sentences)
    for flair_sent, sparv_sent in zip(flair_sentences, sentences):
        # tagger.predict(sent)
        if len(flair_sent) != len(sparv_sent):
            raise util.SparvErrorMessage(
                "Flair POS tagger did not seem to respect the given tokenisation! Do your tokens contain whitespaces? "
                f"Failed at sentence:\n'{s}'")
        for token in flair_sent:
            tag = token.get_tag("pos")
            logger.debug(token.text, tag.value, tag.score)
            out_annotation.append(tag.value)

    out.write(out_annotation)


@annotator("Extract POS from MSD", language=["swe"])
def postag(out: Output = Output("<token>:flair.pos", cls="token:pos", description="Part-of-speech tags"),
           msd: Annotation = Annotation("<token>:flair.msd")):
    """Extract POS from MSD."""
    from sparv.modules.misc import misc
    misc.select(out, msd, index=0, separator=".")


@modelbuilder("Flair model", language=["swe"])
def flair_model(model: ModelOutput = ModelOutput("flair/flair_full/final-model.pt")):
    """Download and unzip the Flair model."""
    zip_model = Model("flair/flair_full.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/flair_full.zip")
    zip_model.unzip()
    zip_model.remove()
