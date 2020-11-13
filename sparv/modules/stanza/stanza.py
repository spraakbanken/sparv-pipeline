"""Dependency parsing using Stanza."""

import json

import stanza
from stanza.models.common.doc import Document

import sparv.util as util
from sparv import Annotation, Config, Model, ModelOutput, Output, annotator, modelbuilder

logger = util.get_logger(__name__)


@annotator("Dependency parsing using Stanza", config=[
           Config("stanza.model", default="stanza/sv_talbanken_parser.pt", description="Stanza dependency model"),
           Config("stanza.pretrain_model", default="stanza/sv_talbanken.pretrain.pt", description="Stanza pretrain dep model"),
           Config("stanza.resources_file", default="stanza/resources.json", description="Stanza resources file")])
def annotate(out_dephead: Output = Output("<token>:stanza.dephead", description="Positions of the dependency heads"),
             out_dephead_ref: Output = Output("<token>:stanza.dephead_ref",
                                              description="Sentence-relative positions of the dependency heads"),
             out_deprel: Output = Output("<token>:stanza.deprel", description="Dependency relations to the head"),
             word: Annotation = Annotation("<token:word>"),
             token: Annotation = Annotation("<token>"),
             baseform: Annotation = Annotation("<token:baseform>"),
             msd: Annotation = Annotation("<token:msd>"),
             feats: Annotation = Annotation("<token:ufeats>"),
             ref: Annotation = Annotation("<token>:misc.number_rel_<sentence>"),
             sentence: Annotation = Annotation("<sentence>"),
             model: Model = Model("[stanza.model]"),
             pretrain_model: Model = Model("[stanza.pretrain_model]"),
             resources_file: Model = Model("[stanza.resources_file]")):
    """Do dependency parsing using Stanza."""
    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)
    dephead = []
    dephead_ref = []
    deprel = []
    document = build_doc(sentences,
                         list(word.read()),
                         list(baseform.read()),
                         list(msd.read()),
                         list(feats.read()),
                         list(ref.read()))

    # Initialize the pipeline
    nlp = stanza.Pipeline(
        lang="sv",                # Language code for the language to build the Pipeline in
        processors="depparse",    # Comma-separated list of processors to use
        dir=str(resources_file.path.parent),
        depparse_pretrain_path=str(pretrain_model.path),
        depparse_model_path=str(model.path),
        depparse_pretagged=True,  # Only run dependency parsing on the document
        verbose=False
    )

    doc = nlp(Document(document))
    word_count = 0  # Keep track of total word count for 'dephead' attribute
    for sent in doc.sentences:
        for word in sent.words:
            # Calculate dephead as position in document
            dephead_str = str(word.head - 1 + word_count) if word.head > 0 else "-"
            dephead_ref_str = str(word.head) if word.head > 0 else ""
            # logger.debug(f"word: {word.text}"
            #              f"\tdephead_ref: {dephead_ref_str}"
            #              f"\tdephead {dephead_str}"
            #              f"\tdeprel: {word.deprel}"
            #              f"\thead word: {sent.words[word.head - 1].text if word.head > 0 else 'root'}")
            dephead.append(dephead_str)
            dephead_ref.append(dephead_ref_str)
            deprel.append(word.deprel)
        word_count += len(sent._words)

    out_dephead_ref.write(dephead_ref)
    out_dephead.write(dephead)
    out_deprel.write(deprel)


@modelbuilder("Stanza dependency model", language=["swe"])
def stanza_model(model: ModelOutput = ModelOutput("stanza/sv_talbanken_parser.pt"),
                 pretrain: ModelOutput = ModelOutput("stanza/sv_talbanken.pretrain.pt"),
                 resources_file: ModelOutput = ModelOutput("stanza/resources.json")):
    """Download and unzip the Stanza dependency model."""
    zip_model = Model("stanza/synt_stanza_full.zip")
    zip_model.download("https://svn.spraakdata.gu.se/sb-arkiv/pub/stanza/synt_stanza_full.zip")
    zip_model.unzip()
    zip_model.remove()

    # Write resources.json file to keep Stanza from complaining
    res = json.dumps({
        "sv": {
            "lang_name": "Swedish",
            "tokenize": {
                "orchid": {},
                "best": {}
            },
            "default_processors": {
                "tokenize": "orchid"
            },
            "default_dependencies": {},
        }})
    resources_file.write(res)


def build_doc(sentences, word, baseform, msd, feats, ref):
    """Build stanza input."""
    document = []
    for sent in sentences:
        in_sent = []
        for i in sent:
            # Format feats
            feats_list = util.set_to_list(feats[i])
            if not feats_list:
                feats_str = "_"
            else:
                feats_str = "|".join(feats_list)
            # Format baseform
            baseform_list = util.set_to_list(baseform[i])
            if not baseform_list:
                baseform_str = word[i]
            else:
                baseform_str = baseform_list[0]

            token_dict = {"id": int(ref[i]), "text": word[i], "lemma": baseform_str,
                          "xpos": msd[i], "feats": feats_str}
            in_sent.append(token_dict)
            logger.debug("\t".join(str(v) for v in token_dict.values()))
        if in_sent:
            document.append(in_sent)
    return document
