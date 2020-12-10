"""POS tagging, lemmatisation and dependency parsing with Stanza."""

from contextlib import redirect_stderr
from os import devnull

import stanza
from stanza.models.common.doc import Document

import sparv.util as util
from sparv import Annotation, Model, Output, annotator

logger = util.get_logger(__name__)


@annotator("POS, lemma and dependency relations from Stanza", order=1)
def annotate(out_msd: Output = Output("<token>:stanza.msd", cls="token:msd",
                                      description="Part-of-speeches with morphological descriptions"),
             out_pos: Output = Output("<token>:stanza.pos", cls="token:pos", description="Part-of-speech tags"),
             out_feats: Output = Output("<token>:stanza.ufeats", cls="token:ufeats",
                                        description="Universal morphological features"),
             out_baseform: Output = Output("<token>:stanza.baseform", cls="token:baseform",
                                           description="Baseform from Stanza"),
             out_dephead: Output = Output("<token>:stanza.dephead", cls="token:dephead",
                                          description="Positions of the dependency heads"),
             out_dephead_ref: Output = Output("<token>:stanza.dephead_ref", cls="token:dephead_ref",
                                              description="Sentence-relative positions of the dependency heads"),
             out_deprel: Output = Output("<token>:stanza.deprel", cls="token:deprel",
                                         description="Dependency relations to the head"),
             word: Annotation = Annotation("<token:word>"),
             token: Annotation = Annotation("<token>"),
             sentence: Annotation = Annotation("<sentence>"),
             pos_model: Model = Model("[stanza.pos_model]"),
             pos_pretrain_model: Model = Model("[stanza.pretrain_pos_model]"),
             lem_model: Model = Model("[stanza.lem_model]"),
             dep_model: Model = Model("[stanza.dep_model]"),
             dep_pretrain_model: Model = Model("[stanza.pretrain_dep_model]"),
             resources_file: Model = Model("[stanza.resources_file]")):
    """Do dependency parsing using Stanza."""
    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)
    word_list = list(word.read())
    msd = []
    pos = []
    feats = []
    baseforms = []
    dephead = []
    dephead_ref = []
    deprel = []

    # Format document for stanza: separate tokens by whitespace and sentences by double new lines
    document = "\n\n".join([" ".join(word_list[i] for i in sent) for sent in sentences])
    logger.debug(document)

    # Temporarily suppress stderr to silence warning about not having an NVIDIA GPU
    with open(devnull, "w") as fnull:
        with redirect_stderr(fnull):
            # Initialize the pipeline
            nlp = stanza.Pipeline(
                lang="sv",
                processors="tokenize,pos,lemma,depparse",  # Comma-separated list of processors to use
                dir=str(resources_file.path.parent),
                lemma_model_path=str(lem_model.path),
                pos_pretrain_path=str(pos_pretrain_model.path),
                pos_model_path=str(pos_model.path),
                depparse_pretrain_path=str(dep_pretrain_model.path),
                depparse_model_path=str(dep_model.path),
                tokenize_pretokenized=True,  # Assume the text is tokenized by white space and sentence split by
                                             # newline. Do not run a model.
                tokenize_no_ssplit=True,     # Disable sentence segmentation
                verbose=False
                # depparse_pretagged=True,  # Only run dependency parsing on the document
            )

    doc = nlp(document)
    word_count = 0  # Keep track of total word count for 'dephead' attribute
    for sent in doc.sentences:
        for w in sent.words:
            feats_str = util.cwbset(w.feats.split("|") if w.feats else "")
            # Calculate dephead as position in document
            dephead_str = str(w.head - 1 + word_count) if w.head > 0 else "-"
            dephead_ref_str = str(w.head) if w.head > 0 else ""
            logger.debug(f"word: {w.text}"
                         f"\tlemma: {w.lemma}"
                         f"\tmsd: {w.xpos}"
                         f"\tpos: {w.upos}"
                         f"\tfeats: {feats_str}"
                         f"\tdephead_ref: {dephead_ref_str}"
                         f"\tdephead: {dephead_str}"
                         f"\tdeprel: {w.deprel}"
                         f"\thead word: {sent.words[w.head - 1].text if w.head > 0 else 'root'}")
            msd.append(w.xpos)
            pos.append(w.upos)
            feats.append(feats_str)
            baseforms.append(w.lemma)
            dephead.append(dephead_str)
            dephead_ref.append(dephead_ref_str)
            deprel.append(w.deprel)
        word_count += len(sent.words)

    if len(word_list) != word_count:
        raise util.SparvErrorMessage(
            "Stanza POS tagger did not seem to respect the given tokenisation! Do your tokens contain whitespaces?")

    out_msd.write(msd)
    out_pos.write(pos)
    out_feats.write(feats)
    out_baseform.write(baseforms)
    out_dephead_ref.write(dephead_ref)
    out_dephead.write(dephead)
    out_deprel.write(deprel)


@annotator("Part-of-speech annotation with morphological descriptions from Stanza", order=2)
def msdtag(out_msd: Output = Output("<token>:stanza.msd", cls="token:msd",
                                    description="Part-of-speeches with morphological descriptions"),
           out_pos: Output = Output("<token>:stanza.pos", cls="token:pos", description="Part-of-speech tags"),
           out_feats: Output = Output("<token>:stanza.ufeats", cls="token:ufeats",
                                      description="Universal morphological features"),
           word: Annotation = Annotation("<token:word>"),
           token: Annotation = Annotation("<token>"),
           sentence: Annotation = Annotation("<sentence>"),
           model: Model = Model("[stanza.pos_model]"),
           pretrain_model: Model = Model("[stanza.pretrain_pos_model]"),
           resources_file: Model = Model("[stanza.resources_file]")):
    """Do dependency parsing using Stanza."""
    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)
    word_list = list(word.read())
    msd = []
    pos = []
    feats = []

    # Format document for stanza: separate tokens by whitespace and sentences by double new lines
    document = "\n\n".join([" ".join(word_list[i] for i in sent) for sent in sentences])
    logger.debug(document)

    # Temporarily suppress stderr to silence warning about not having an NVIDIA GPU
    with open(devnull, "w") as fnull:
        with redirect_stderr(fnull):
            # Initialize the pipeline
            nlp = stanza.Pipeline(
                lang="sv",                   # Language code for the language to build the Pipeline in
                processors="tokenize,pos",   # Comma-separated list of processors to use
                dir=str(resources_file.path.parent),
                pos_pretrain_path=str(pretrain_model.path),
                pos_model_path=str(model.path),
                tokenize_pretokenized=True,  # Assume the text is tokenized by white space and sentence split by
                                             # newline. Do not run a model.
                tokenize_no_ssplit=True,     # Disable sentence segmentation
                verbose=False
            )

    doc = nlp(document)
    word_count = 0
    for sent in doc.sentences:
        for w in sent.words:
            word_count += 1
            feats_str = util.cwbset(w.feats.split("|") if w.feats else "")
            logger.debug(f"word: {w.text}"
                         f"\tmsd: {w.xpos}"
                         f"\tpos: {w.upos}"
                         f"\tfeats: {feats_str}")
            msd.append(w.xpos)
            pos.append(w.upos)
            feats.append(feats_str)

    if len(word_list) != word_count:
        raise util.SparvErrorMessage(
            "Stanza POS tagger did not seem to respect the given tokenisation! Do your tokens contain whitespaces?")

    out_msd.write(msd)
    out_pos.write(pos)
    out_feats.write(feats)


@annotator("Dependency parsing using Stanza", order=2)
def dep_parse(out_dephead: Output = Output("<token>:stanza.dephead", cls="token:dephead",
                                           description="Positions of the dependency heads"),
              out_dephead_ref: Output = Output("<token>:stanza.dephead_ref", cls="token:dephead_ref",
                                               description="Sentence-relative positions of the dependency heads"),
              out_deprel: Output = Output("<token>:stanza.deprel", cls="token:deprel",
                                          description="Dependency relations to the head"),
              word: Annotation = Annotation("<token:word>"),
              token: Annotation = Annotation("<token>"),
              baseform: Annotation = Annotation("<token:baseform>"),
              msd: Annotation = Annotation("<token:msd>"),
              feats: Annotation = Annotation("<token:ufeats>"),
              ref: Annotation = Annotation("<token>:misc.number_rel_<sentence>"),
              sentence: Annotation = Annotation("<sentence>"),
              model: Model = Model("[stanza.dep_model]"),
              pretrain_model: Model = Model("[stanza.pretrain_dep_model]"),
              resources_file: Model = Model("[stanza.resources_file]")):
    """Do dependency parsing using Stanza."""
    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)
    dephead = []
    dephead_ref = []
    deprel = []
    document = _build_doc(sentences,
                          list(word.read()),
                          list(baseform.read()),
                          list(msd.read()),
                          list(feats.read()),
                          list(ref.read()))

    # Temporarily suppress stderr to silence warning about not having an NVIDIA GPU
    with open(devnull, "w") as fnull:
        with redirect_stderr(fnull):
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
        for w in sent.words:
            # Calculate dephead as position in document
            dephead_str = str(w.head - 1 + word_count) if w.head > 0 else "-"
            dephead_ref_str = str(w.head) if w.head > 0 else ""
            logger.debug(f"word: {w.text}"
                         f"\tdephead_ref: {dephead_ref_str}"
                         f"\tdephead: {dephead_str}"
                         f"\tdeprel: {w.deprel}"
                         f"\thead word: {sent.words[w.head - 1].text if w.head > 0 else 'root'}")
            dephead.append(dephead_str)
            dephead_ref.append(dephead_ref_str)
            deprel.append(w.deprel)
        word_count += len(sent.words)

    out_dephead_ref.write(dephead_ref)
    out_dephead.write(dephead)
    out_deprel.write(deprel)


def _build_doc(sentences, word, baseform, msd, feats, ref):
    """Build stanza input for dependency parsing."""
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
