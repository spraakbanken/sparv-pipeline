"""POS tagging, lemmatisation and dependency parsing with Stanza."""

from contextlib import redirect_stderr
from os import devnull

import sparv.util as util
from sparv import Annotation, Config, Model, Output, annotator

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
             resources_file: Model = Model("[stanza.resources_file]"),
             use_gpu: bool = Config("stanza.use_gpu"),
             batch_size: int = Config("stanza.batch_size"),
             max_sentence_length: int = Config("stanza.max_sentence_length")):
    """Do dependency parsing using Stanza."""
    import stanza

    sentences_all, orphans = sentence.get_children(token)
    if orphans:
        logger.warning(f"Found {len(orphans)} tokens not belonging to any sentence. These will not be annotated with "
                       f"dependency relations.")

    sentences_dep = []
    sentences_pos = []
    skipped = 0

    for s in sentences_all:
        if len(s) <= max_sentence_length or not max_sentence_length:
            sentences_dep.append(s)
        elif len(s) <= batch_size:
            sentences_pos.append(s)
        else:
            skipped += 1

    if sentences_pos:
        n = len(sentences_pos)
        logger.warning(f"Found {n} sentence{'s' if n > 1 else ''} exceeding the max sentence length "
                       f"({max_sentence_length}). {'These' if n > 1 else 'This'} sentence{'s' if n > 1 else ''} will "
                       "not be annotated with dependency relations.")
    if skipped:
        logger.warning(f"Found {skipped} sentence{'s' if skipped > 1 else ''} exceeding the batch size "
                       f"({batch_size}) in number of tokens. {'These' if skipped > 1 else 'This'} "
                       f"sentence{'s' if skipped > 1 else ''} will not be annotated.")
    if orphans:
        sentences_pos.append(orphans)
    word_list = list(word.read())
    msd = word.create_empty_attribute()
    pos = word.create_empty_attribute()
    feats = word.create_empty_attribute()
    baseforms = word.create_empty_attribute()
    dephead = word.create_empty_attribute()
    dephead_ref = word.create_empty_attribute()
    deprel = word.create_empty_attribute()

    for sentences, dep in ((sentences_dep, True), (sentences_pos, False)):
        if not sentences:
            continue

        # Temporarily suppress stderr to silence warning about not having an NVIDIA GPU
        with open(devnull, "w") as fnull:
            with redirect_stderr(fnull):
                # Initialize the pipeline
                if dep:
                    logger.debug(f"Running dependency parsing and POS-taggning on {len(sentences)} sentences.")
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
                        tokenize_no_ssplit=True,  # Disable sentence segmentation
                        depparse_max_sentence_size=200,  # Create new batch when encountering sentences larger than this
                        depparse_batch_size=batch_size,
                        pos_batch_size=batch_size,
                        lemma_batch_size=batch_size,
                        use_gpu=use_gpu,
                        verbose=False
                    )
                else:
                    logger.debug(f"Running POS-taggning on {len(sentences)} sentences.")
                    nlp = stanza.Pipeline(
                        lang="sv",
                        processors="tokenize,pos,lemma",  # Comma-separated list of processors to use
                        dir=str(resources_file.path.parent),
                        lemma_model_path=str(lem_model.path),
                        pos_pretrain_path=str(pos_pretrain_model.path),
                        pos_model_path=str(pos_model.path),
                        tokenize_pretokenized=True,  # Assume the text is tokenized by white space and sentence split by
                                                     # newline. Do not run a model.
                        tokenize_no_ssplit=True,  # Disable sentence segmentation
                        pos_batch_size=batch_size,
                        lemma_batch_size=batch_size,
                        use_gpu=use_gpu,
                        verbose=False
                    )

        # Format document for stanza: separate tokens by whitespace and sentences by double new lines
        document = "\n\n".join([" ".join(word_list[i] for i in sent) for sent in sentences])

        doc = run_stanza(nlp, document, batch_size, max_sentence_length)
        word_count_real = sum(len(s) for s in sentences)
        word_count = 0
        for sent, tagged_sent in zip(sentences, doc.sentences):
            for w_index, w in zip(sent, tagged_sent.words):
                feats_str = util.cwbset(w.feats.split("|") if w.feats else "")
                # logger.debug(f"word: {w.text}"
                #              f"\tlemma: {w.lemma}"
                #              f"\tmsd: {w.xpos}"
                #              f"\tpos: {w.upos}"
                #              f"\tfeats: {feats_str}"
                #              f"\tdephead_ref: {dephead_ref_str}"
                #              f"\tdephead: {dephead_str}"
                #              f"\tdeprel: {w.deprel}"
                #              f"\thead word: {tagged_sent.words[w.head - 1].text if w.head > 0 else 'root'}")
                msd[w_index] = w.xpos
                pos[w_index] = w.upos
                feats[w_index] = feats_str
                baseforms[w_index] = w.lemma
                if dep:
                    dephead[w_index] = str(sent[w.head - 1]) if w.head > 0 else "-"
                    dephead_ref[w_index] = str(w.head) if w.head > 0 else ""
                    deprel[w_index] = w.deprel
            word_count += len(tagged_sent.words)

        if word_count != word_count_real:
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
           resources_file: Model = Model("[stanza.resources_file]"),
           use_gpu: bool = Config("stanza.use_gpu"),
           batch_size: int = Config("stanza.batch_size")):
    """Do dependency parsing using Stanza."""
    import stanza

    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)
    word_list = list(word.read())
    msd = word.create_empty_attribute()
    pos = word.create_empty_attribute()
    feats = word.create_empty_attribute()

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
                pos_batch_size=batch_size,
                use_gpu=use_gpu,
                verbose=False
            )

    doc = run_stanza(nlp, document, batch_size)
    word_count = 0
    for sent, tagged_sent in zip(sentences, doc.sentences):
        for w_index, w in zip(sent, tagged_sent.words):
            word_count += 1
            feats_str = util.cwbset(w.feats.split("|") if w.feats else "")
            logger.debug(f"word: {w.text}"
                         f"\tmsd: {w.xpos}"
                         f"\tpos: {w.upos}"
                         f"\tfeats: {feats_str}")
            msd[w_index] = w.xpos
            pos[w_index] = w.upos
            feats[w_index] = feats_str

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
              resources_file: Model = Model("[stanza.resources_file]"),
              use_gpu: bool = Config("stanza.use_gpu"),
              batch_size: int = Config("stanza.batch_size"),
              max_sentence_length: int = Config("stanza.max_sentence_length")):
    """Do dependency parsing using Stanza."""
    import stanza
    from stanza.models.common.doc import Document

    sentences_all, orphans = sentence.get_children(token)
    if orphans:
        logger.warning(f"Found {len(orphans)} tokens not belonging to any sentence. These will not be annotated with "
                       f"dependency relations.")
    sentences = []
    skipped_sent = 0
    skipped_batch = 0
    for s in sentences_all:
        if len(s) > max_sentence_length and max_sentence_length:
            skipped_sent += 1
        elif len(s) > batch_size:
            skipped_batch += 1
        else:
            sentences.append(s)
    if skipped_sent:
        logger.warning(f"Found {skipped_sent} sentence{'s' if skipped_sent > 1 else ''} exceeding the max sentence "
                       f"length ({max_sentence_length}). {'These' if skipped_sent > 1 else 'This'} "
                       f"sentence{'s' if skipped_sent > 1 else ''} will not be annotated with dependency relations.")
    if skipped_batch:
        logger.warning(f"Found {skipped_batch} sentence{'s' if skipped_batch > 1 else ''} exceeding the batch size "
                       f"({batch_size}) in number of tokens. {'These' if skipped_batch > 1 else 'This'} "
                       f"sentence{'s' if skipped_batch > 1 else ''} will not be annotated.")

    dephead = word.create_empty_attribute()
    dephead_ref = word.create_empty_attribute()
    deprel = word.create_empty_attribute()
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
                depparse_max_sentence_size=200,  # Create new batch when encountering sentences larger than this
                depparse_batch_size=batch_size,
                pos_batch_size=batch_size,
                lemma_batch_size=batch_size,
                use_gpu=use_gpu,
                verbose=False
            )

    doc = run_stanza(nlp, Document(document), batch_size, max_sentence_length)
    for sent, tagged_sent in zip(sentences, doc.sentences):
        for w_index, w in zip(sent, tagged_sent.words):
            dephead_str = str(sent[w.head - 1]) if w.head > 0 else "-"
            dephead_ref_str = str(w.head) if w.head > 0 else ""
            logger.debug(f"word: {w.text}"
                         f"\tdephead_ref: {dephead_ref_str}"
                         f"\tdephead: {dephead_str}"
                         f"\tdeprel: {w.deprel}"
                         f"\thead word: {tagged_sent.words[w.head - 1].text if w.head > 0 else 'root'}")
            dephead[w_index] = dephead_str
            dephead_ref[w_index] = dephead_ref_str
            deprel[w_index] = w.deprel

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


def run_stanza(nlp, document, batch_size, max_sentence_length: int = 0):
    """Run Stanza and handle possible errors."""
    try:
        doc = nlp(document)
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            msg = "Stanza ran out of GPU memory. You can try the following options to prevent this from happening:\n" \
                  " - Limit the number of parallel Stanza processes by using the 'threads' section in your Sparv " \
                  "configuration.\n" \
                  " - Limit the Stanza batch size by setting the 'stanza.batch_size' config variable to something " \
                  f"lower (current value: {batch_size}).\n" \
                  " - Exclude excessively long sentences from dependency parsing by setting the " \
                  "'stanza.max_sentence_length' config variable to something lower (current value: " \
                  f"{max_sentence_length}).\n" \
                  " - Switch to using CPU by setting the 'stanza.use_gpu' config variable to false."
        else:
            msg = str(e)
        raise util.SparvErrorMessage(msg)
    return doc
