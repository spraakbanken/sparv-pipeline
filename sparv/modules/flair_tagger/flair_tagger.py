"""Part of Speech annotation using Flair."""

from flair.data import Sentence
from flair.models import SequenceTagger

from sparv import Annotation, Config, Model, ModelOutput, Output, annotator, modelbuilder


@annotator("Convert every word to uppercase.", config=[
           Config("flair_tagger.model", default="flair_tagger/flair_full/final-model.pt", description="Flair model")])
def annotate(out: Output = Output("<token>:flair_tagger.pos", cls="token:pos", description="Part-of-speech tags"),
             word: Annotation = Annotation("<token:word>"),
             sentence: Annotation = Annotation("<sentence>"),
             model: Model = Model("[flair_tagger.model]")):
    """POS tag using Flair."""
    sentences, _orphans = sentence.get_children(word)
    token_word = list(word.read())
    out_annotation = []

    # Load model
    tagger = SequenceTagger.load(model.path)

    # Tag one sentence at a time
    for sentence in sentences:
        s = " ".join(token_word[token_index] for token_index in sentence)
        sent = Sentence(s, use_tokenizer=False)
        tagger.predict(sent)
        assert len(sent) == len(sentence), "Flair did not seem to respect the given tokenisation! Do your tokens contain whitespaces?"
        for token in sent:
            tag = token.get_tag("pos")
            # print(token.text, tag.value, tag.score)
            out_annotation.append(tag.value)

    out.write(out_annotation)


@modelbuilder("Flair model", language=["swe"])
def flair_model(model: ModelOutput = ModelOutput("flair_tagger/flair_full/final-model.pt")):
    """Download and unzip the Flair model."""
    zip_model = Model("flair_tagger/flair_full.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/flair_full.zip")
    zip_model.unzip()
    zip_model.remove()
