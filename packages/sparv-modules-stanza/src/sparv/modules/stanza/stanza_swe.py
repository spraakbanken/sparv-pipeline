"""POS tagging, lemmatization and dependency parsing with Stanza."""

import warnings

from sparv.api import Annotation, Config, Model, Output, annotator, get_logger, util
from sparv.core.misc import SparvErrorMessage

from . import stanza_utils

logger = get_logger(__name__)


@annotator("POS, lemma and dependency relations from Stanza", language=["swe"], order=1)
def annotate_swe(
    out_msd: Output = Output(
        "<token>:stanza.msd", cls="token:msd", description="Part-of-speeches with morphological descriptions"
    ),
    out_pos: Output = Output("<token>:stanza.pos", cls="token:pos", description="Part-of-speech tags"),
    out_feats: Output = Output(
        "<token>:stanza.ufeats", cls="token:ufeats", description="Universal morphological features"
    ),
    out_baseform: Output = Output("<token>:stanza.baseform", cls="token:baseform", description="Baseform from Stanza"),
    out_dephead: Output = Output(
        "<token>:stanza.dephead", cls="token:dephead", description="Positions of the dependency heads"
    ),
    out_dephead_ref: Output = Output(
        "<token>:stanza.dephead_ref",
        cls="token:dephead_ref",
        description="Sentence-relative positions of the dependency heads",
    ),
    out_deprel: Output = Output(
        "<token>:stanza.deprel", cls="token:deprel", description="Dependency relations to the head"
    ),
    word: Annotation = Annotation("<token:word>"),
    token: Annotation = Annotation("<token>"),
    sentence: Annotation = Annotation("<sentence>"),
    pos_model: Model = Model("[stanza.swe_pos_model]"),
    pos_pretrain_model: Model = Model("[stanza.swe_pretrain_pos_model]"),
    lem_model: Model = Model("[stanza.swe_lem_model]"),
    dep_model: Model = Model("[stanza.swe_dep_model]"),
    dep_pretrain_model: Model = Model("[stanza.swe_pretrain_dep_model]"),
    resources_file: Model = Model("[stanza.resources_file]"),
    use_gpu: bool = Config("stanza.use_gpu"),
    batch_size: int = Config("stanza.batch_size"),
    max_sentence_length: int = Config("stanza.max_sentence_length"),
    cpu_fallback: bool = Config("stanza.cpu_fallback"),
    max_token_length: int = Config("stanza.max_token_length"),
) -> None:
    """Do dependency parsing using Stanza.

    Args:
        out_msd: Output attribute for part-of-speech with morphological descriptions.
        out_pos: Output attribute for part-of-speech tags.
        out_feats: Output attribute for universal morphological features.
        out_baseform: Output attribute for baseforms.
        out_dephead: Output attribute for dependency heads.
        out_dephead_ref: Output attribute for sentence-relative positions of the dependency heads.
        out_deprel: Output attribute for dependency relations to the head.
        word: Input attribute for words.
        token: Input annotation for tokens.
        sentence: Input annotation for sentences.
        pos_model: Model for part-of-speech tagging.
        pos_pretrain_model: Pretrain model for part-of-speech tagging.
        lem_model: Model for lemmatization.
        dep_model: Model for dependency parsing.
        dep_pretrain_model: Pretrain model for dependency parsing.
        resources_file: Stanza resources file.
        use_gpu: Whether to use GPU for processing.
        batch_size: Batch size for processing.
        max_sentence_length: Maximum sentence length for processing.
        cpu_fallback: Whether to use CPU fallback for processing.
        max_token_length: Maximum token length for processing.
    """
    import torch  # noqa: PLC0415

    import stanza  # noqa: PLC0415
    from stanza.pipeline.core import DownloadMethod  # noqa: PLC0415

    # cpu_fallback only makes sense if use_gpu is True
    cpu_fallback = cpu_fallback and use_gpu

    # Select the GPU with most free memory available
    try:
        if use_gpu:
            gpus = util.system.gpus()
            if gpus:
                torch.cuda.set_device(gpus[0])
    except Exception:
        pass

    sentences_all, orphans = sentence.get_children(token)
    if orphans:
        logger.warning(
            "Found %d tokens not belonging to any sentence. These will not be annotated with dependency relations.",
            len(orphans),
        )

    sentences_dep = []
    sentences_pos = []
    skipped = 0
    skipped_token = 0

    word_list = list(word.read())

    for s in sentences_all:
        if not s:
            continue
        if len(s) > batch_size:
            skipped += 1
        else:
            if max_token_length:
                skip = False
                for i in s:
                    if len(word_list[i]) > max_token_length:
                        skipped_token += 1
                        skip = True
                        break
                if skip:
                    continue
            if len(s) <= max_sentence_length or not max_sentence_length:
                sentences_dep.append(s)
            else:
                sentences_pos.append(s)

    if sentences_pos and not cpu_fallback:
        n = len(sentences_pos)
        logger.warning(
            f"Found {n} sentence{'s' if n > 1 else ''} exceeding the max sentence length "  # noqa: G004
            f"({max_sentence_length}). {'These' if n > 1 else 'This'} sentence{'s' if n > 1 else ''} will "
            "not be annotated with dependency relations."
        )
    if skipped:
        logger.warning(
            f"Found {skipped} sentence{'s' if skipped > 1 else ''} exceeding the batch size "  # noqa: G004
            f"({batch_size}) in number of tokens. {'These' if skipped > 1 else 'This'} "
            f"sentence{'s' if skipped > 1 else ''} will not be annotated."
        )
    if skipped_token:
        logger.warning(
            f"Found {skipped_token} sentence{'s' if skipped_token > 1 else ''} with tokens exceeding the "  # noqa: G004
            f"max token length ({max_token_length}). {'These' if skipped_token > 1 else 'This'} "
            f"sentence{'s' if skipped_token > 1 else ''} will not be annotated."
        )
    if orphans:
        sentences_pos.append(orphans)
    msd = word.create_empty_attribute()
    pos = word.create_empty_attribute()
    feats = word.create_empty_attribute()
    baseforms = word.create_empty_attribute()
    dephead = word.create_empty_attribute()
    dephead_ref = word.create_empty_attribute()
    deprel = word.create_empty_attribute()

    nlp_args = {
        "lang": "sv",
        "dir": str(resources_file.path.parent),
        "tokenize_pretokenized": True,  # Assume the text is tokenized by whitespace and sentence split by newline.
        "lemma_model_path": str(lem_model.path),
        "pos_pretrain_path": str(pos_pretrain_model.path),
        "pos_model_path": str(pos_model.path),
        "depparse_pretrain_path": str(dep_pretrain_model.path),
        "depparse_model_path": str(dep_model.path),
        "depparse_max_sentence_size": 200,  # Create new batch when encountering sentences larger than this
        "depparse_batch_size": batch_size,
        "pos_batch_size": batch_size,
        "lemma_batch_size": batch_size,
        "verbose": False,
        "download_method": DownloadMethod.NONE,
    }

    for sentences, dep, fallback in ((sentences_dep, True, False), (sentences_pos, False, cpu_fallback)):
        if not sentences:
            continue

        # Init Stanza pipeline
        if dep or fallback:
            logger.debug(
                "Running dependency parsing and POS-taggning on %d sentences (using %s).",
                len(sentences),
                "GPU" if use_gpu and not fallback else "CPU",
            )
            nlp_args["processors"] = "tokenize,pos,lemma,depparse"  # Comma-separated list of processors to use
            nlp_args["use_gpu"] = use_gpu and not fallback
            nlp = _create_pipeline(stanza, nlp_args, resources_file)

        else:
            logger.debug("Running POS-taggning on %d sentences.", len(sentences))
            nlp_args["processors"] = "tokenize,pos"  # Comma-separated list of processors to use
            nlp_args["use_gpu"] = use_gpu
            nlp = _create_pipeline(stanza, nlp_args, resources_file)

        # Format document for stanza: list of lists of string
        document = [[word_list[i] for i in s] for s in sentences]

        doc = stanza_utils.run_stanza(nlp, document, batch_size, max_sentence_length)
        stanza_utils.check_sentence_respect(len([s for s in sentences if s]), len(doc.sentences))
        word_count_real = sum(len(s) for s in sentences)
        word_count = 0
        for sent, tagged_sent in zip(sentences, doc.sentences, strict=True):
            for w_index, w in zip(sent, tagged_sent.words, strict=True):
                feats_str = util.misc.cwbset(w.feats.split("|") if w.feats else "")
                msd[w_index] = w.xpos
                pos[w_index] = w.upos
                feats[w_index] = feats_str
                baseforms[w_index] = w.lemma
                if dep or fallback:
                    dephead[w_index] = str(sent[w.head - 1]) if w.head > 0 else "-"
                    dephead_ref[w_index] = str(w.head) if w.head > 0 else ""
                    deprel[w_index] = w.deprel
            word_count += len(tagged_sent.words)
        stanza_utils.check_token_respect(word_count_real, word_count)

    out_msd.write(msd)
    out_pos.write(pos)
    out_feats.write(feats)
    out_baseform.write(baseforms)
    out_dephead_ref.write(dephead_ref)
    out_dephead.write(dephead)
    out_deprel.write(deprel)


@annotator("Part-of-speech annotation with morphological descriptions from Stanza", language=["swe"], order=2)
def msdtag(
    out_msd: Output = Output(
        "<token>:stanza.msd", cls="token:msd", description="Part-of-speeches with morphological descriptions"
    ),
    out_pos: Output = Output("<token>:stanza.pos", cls="token:pos", description="Part-of-speech tags"),
    out_feats: Output = Output(
        "<token>:stanza.ufeats", cls="token:ufeats", description="Universal morphological features"
    ),
    word: Annotation = Annotation("<token:word>"),
    token: Annotation = Annotation("<token>"),
    sentence: Annotation = Annotation("<sentence>"),
    model: Model = Model("[stanza.swe_pos_model]"),
    pretrain_model: Model = Model("[stanza.swe_pretrain_pos_model]"),
    resources_file: Model = Model("[stanza.resources_file]"),
    use_gpu: bool = Config("stanza.use_gpu"),
    batch_size: int = Config("stanza.batch_size"),
) -> None:
    """Do dependency parsing using Stanza.

    Args:
        out_msd: Output attribute for part-of-speeches with morphological descriptions.
        out_pos: Output attribute for part-of-speech tags.
        out_feats: Output attribute for universal morphological features.
        word: Input attribute for words.
        token: Input annotation for tokens.
        sentence: Input annotation for sentences.
        model: Model for part-of-speech tagging.
        pretrain_model: Pretrain model for part-of-speech tagging.
        resources_file: Stanza resources file.
        use_gpu: Whether to use GPU for processing.
        batch_size: Batch size for processing.
    """
    import stanza  # noqa: PLC0415

    sentences, orphans = sentence.get_children(token)
    if orphans:
        sentences.append(orphans)
    word_list = list(word.read())
    msd = word.create_empty_attribute()
    pos = word.create_empty_attribute()
    feats = word.create_empty_attribute()

    # Format document for stanza: list of lists of string
    document = [[word_list[i] for i in s] for s in sentences]

    # Init Stanza Pipeline
    nlp = _create_pipeline(
        stanza,
        {
            "lang": "sv",
            "processors": "tokenize,pos",
            "dir": str(resources_file.path.parent),
            "tokenize_pretokenized": True,  # Assume the text is tokenized by whitespace and sentence split by newline.
            "pos_pretrain_path": str(pretrain_model.path),
            "pos_model_path": str(model.path),
            "pos_batch_size": batch_size,
            "use_gpu": use_gpu,
            "verbose": False,
        },
        resources_file,
    )

    doc = stanza_utils.run_stanza(nlp, document, batch_size)
    stanza_utils.check_sentence_respect(len([s for s in sentences if s]), len(doc.sentences))
    word_count = 0
    for sent, tagged_sent in zip(sentences, doc.sentences, strict=True):
        for w_index, w in zip(sent, tagged_sent.words, strict=True):
            word_count += 1
            feats_str = util.misc.cwbset(w.feats.split("|") if w.feats else "")
            msd[w_index] = w.xpos
            pos[w_index] = w.upos
            feats[w_index] = feats_str
    stanza_utils.check_token_respect(len(word_list), word_count)

    out_msd.write(msd)
    out_pos.write(pos)
    out_feats.write(feats)


@annotator("Dependency parsing using Stanza", language=["swe"], order=2)
def dep_parse(
    out_dephead: Output = Output(
        "<token>:stanza.dephead", cls="token:dephead", description="Positions of the dependency heads"
    ),
    out_dephead_ref: Output = Output(
        "<token>:stanza.dephead_ref",
        cls="token:dephead_ref",
        description="Sentence-relative positions of the dependency heads",
    ),
    out_deprel: Output = Output(
        "<token>:stanza.deprel", cls="token:deprel", description="Dependency relations to the head"
    ),
    word: Annotation = Annotation("<token:word>"),
    token: Annotation = Annotation("<token>"),
    baseform: Annotation = Annotation("<token:baseform>"),
    msd: Annotation = Annotation("<token:msd>"),
    feats: Annotation = Annotation("<token:ufeats>"),
    ref: Annotation = Annotation("<token>:stanza.ref"),
    sentence: Annotation = Annotation("<sentence>"),
    model: Model = Model("[stanza.swe_dep_model]"),
    pretrain_model: Model = Model("[stanza.swe_pretrain_dep_model]"),
    resources_file: Model = Model("[stanza.resources_file]"),
    use_gpu: bool = Config("stanza.use_gpu"),
    batch_size: int = Config("stanza.batch_size"),
    max_sentence_length: int = Config("stanza.max_sentence_length"),
    cpu_fallback: bool = Config("stanza.cpu_fallback"),
) -> None:
    """Do dependency parsing using Stanza.

    Args:
        out_dephead: Output attribute for dependency heads.
        out_dephead_ref: Output attribute for sentence-relative positions of the dependency heads.
        out_deprel: Output attribute for dependency relations to the head.
        word: Input attribute for words.
        token: Input annotation for tokens.
        baseform: Input attribute for baseforms.
        msd: Input attribute for part-of-speech with morphological descriptions.
        feats: Input attribute for universal morphological features.
        ref: Input attribute for reference IDs.
        sentence: Input annotation for sentences.
        model: Model for dependency parsing.
        pretrain_model: Pretrain model for dependency parsing.
        resources_file: Stanza resources file.
        use_gpu: Whether to use GPU for processing.
        batch_size: Batch size for processing.
        max_sentence_length: Maximum sentence length for processing.
        cpu_fallback: Whether to use CPU fallback for processing.
    """
    import stanza  # noqa: PLC0415
    from stanza.models.common.doc import Document  # noqa: PLC0415

    # cpu_fallback only makes sense if use_gpu is True
    cpu_fallback = cpu_fallback and use_gpu

    sentences_all, orphans = sentence.get_children(token)
    if orphans:
        logger.warning(
            "Found %d tokens not belonging to any sentence. These will not be annotated with dependency relations.",
            len(orphans),
        )
    sentences_dep = []
    sentences_fallback = []
    skipped_sent = 0
    skipped_batch = 0

    for s in sentences_all:
        if len(s) > batch_size:
            skipped_batch += 1
        elif max_sentence_length and len(s) > max_sentence_length:
            if cpu_fallback:
                sentences_fallback.append(s)
            else:
                skipped_sent += 1
        else:
            sentences_dep.append(s)

    if skipped_sent:
        logger.warning(
            f"Found {skipped_sent} sentence{'s' if skipped_sent > 1 else ''} exceeding the max sentence "  # noqa: G004
            f"length ({max_sentence_length}). {'These' if skipped_sent > 1 else 'This'} "
            f"sentence{'s' if skipped_sent > 1 else ''} will not be annotated."
        )
    if skipped_batch:
        logger.warning(
            f"Found {skipped_batch} sentence{'s' if skipped_batch > 1 else ''} exceeding the batch size "  # noqa: G004
            f"({batch_size}) in number of tokens. {'These' if skipped_batch > 1 else 'This'} "
            f"sentence{'s' if skipped_batch > 1 else ''} will not be annotated."
        )

    word_vals = list(word.read())
    baseform_vals = list(baseform.read())
    msd_vals = list(msd.read())
    feats_vals = list(feats.read())
    ref_vals = list(ref.read())

    dephead = word.create_empty_attribute()
    dephead_ref = word.create_empty_attribute()
    deprel = word.create_empty_attribute()

    for sentences, fallback in ((sentences_dep, False), (sentences_fallback, cpu_fallback)):
        if not sentences:
            continue

        document = _build_doc(sentences, word_vals, baseform_vals, msd_vals, feats_vals, ref_vals)

        # Init Stanza Pipeline
        nlp = _create_pipeline(
            stanza,
            {
                "lang": "sv",
                "dir": str(resources_file.path.parent),
                "processors": "tokenize,pos,lemma,depparse",
                "tokenize_pretokenized": True,
                "depparse_pretrain_path": str(pretrain_model.path),
                "depparse_model_path": str(model.path),
                "depparse_max_sentence_size": 200,  # Create new batch when encountering sentences larger than this
                "depparse_batch_size": batch_size,
                "use_gpu": use_gpu and not fallback,
                "verbose": False,
            },
            resources_file,
        )

        doc = stanza_utils.run_stanza(nlp, Document(document), batch_size, max_sentence_length)
        for sent, tagged_sent in zip(sentences, doc.sentences, strict=True):
            for w_index, w in zip(sent, tagged_sent.words, strict=True):
                dephead_str = str(sent[w.head - 1]) if w.head > 0 else "-"
                dephead_ref_str = str(w.head) if w.head > 0 else ""
                dephead[w_index] = dephead_str
                dephead_ref[w_index] = dephead_ref_str
                deprel[w_index] = w.deprel

    out_dephead_ref.write(dephead_ref)
    out_dephead.write(dephead)
    out_deprel.write(deprel)


@annotator("Extract POS from MSD", language=["swe", "swe-1800"])
def msd_backoff_hunpos(
    stanza_msd: Annotation = Annotation("<token>:stanza.msd"),
    hunpos_msd: Annotation = Annotation("<token>:hunpos.msd"),
    out: Output = Output(
        "<token>:stanza.msd_hunpos_backoff",
        cls="token:msd",
        description="Part-of-speech tags with morphological descriptions from Stanza or Hunpos.",
    ),
    info: Output = Output(
        "<token>:stanza.msd_hunpos_backoff_info",
        description="Info about which annotator each msd annotation was produced with.",
    ),
) -> None:
    """Replace empty values in 'stanza_msd' with values from 'hunpos_msd'.

    Args:
        stanza_msd: Input attribute for part-of-speeches with morphological descriptions from Stanza.
        hunpos_msd: Input attribute for part-of-speeches with morphological descriptions from Hunpos.
        out: Output attribute for part-of-speeches with morphological descriptions from Stanza or Hunpos.
        info: Output attribute for info about which annotator each msd annotation was produced with.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.backoff_with_info(
        chunk=stanza_msd, backoff=hunpos_msd, out=out, out_info=info, chunk_name="stanza", backoff_name="hunpos"
    )


@annotator("Extract POS from MSD", language=["swe", "swe-1800"])
def pos_backoff_hunpos(
    stanza_pos: Annotation = Annotation("<token>:stanza.pos"),
    hunpos_pos: Annotation = Annotation("<token>:hunpos.pos"),
    out: Output = Output(
        "<token>:stanza.pos_hunpos_backoff", cls="token:pos", description="Part-of-speech tags from Stanza or Hunpos."
    ),
    info: Output = Output(
        "<token>:stanza.pos_hunpos_backoff_info",
        description="Info about which annotator each pos annotation was produced with.",
    ),
) -> None:
    """Replace empty values in 'stanza_pos' with values from 'hunpos_pos'.

    Args:
        stanza_pos: Input attribute for part-of-speech tags from Stanza.
        hunpos_pos: Input attribute for part-of-speech tags from Hunpos.
        out: Output attribute for part-of-speech tags from Stanza or Hunpos.
        info: Output attribute for info about which annotator each pos annotation was produced with.
    """
    from sparv.modules.misc import misc  # noqa: PLC0415

    misc.backoff_with_info(
        chunk=stanza_pos, backoff=hunpos_pos, out=out, out_info=info, chunk_name="stanza", backoff_name="hunpos"
    )


def _build_doc(
    sentences: list, word: list[str], baseform: list[str], msd: list[str], feats: list[str], ref: list[str]
) -> list:
    """Build stanza input for dependency parsing.

    Args:
        sentences: List of sentences.
        word: List of words.
        baseform: List of baseforms.
        msd: List of part-of-speech tags.
        feats: List of features.
        ref: List of sentence-relative positions of the tokens.

    Returns:
        List of lists of dictionaries representing the document.
    """
    document = []
    for sent in sentences:
        in_sent = []
        for i in sent:
            # Format feats
            feats_list = util.misc.set_to_list(feats[i])
            feats_str = "_" if not feats_list else "|".join(feats_list)
            # Format baseform
            baseform_list = util.misc.set_to_list(baseform[i])
            baseform_str = word[i] if not baseform_list else baseform_list[0]

            token_dict = {"id": int(ref[i]), "text": word[i], "lemma": baseform_str, "xpos": msd[i], "feats": feats_str}
            in_sent.append(token_dict)
            # logger.debug("\t".join(str(v) for v in token_dict.values()))
        if in_sent:
            document.append(in_sent)
    return document


def _create_pipeline(stanza, nlp_args: dict, resources_file: str):  # noqa: ANN001, ANN202
    """Create and return Stanza pipeline.

    Args:
        stanza: Stanza module.
        nlp_args: Arguments for the pipeline.
        resources_file: Path to the resources file.

    Returns:
        Stanza pipeline.

    Raises:
        SparvErrorMessage: If the resources file is missing or invalid.
    """
    # Silence warning about Stanza using torch.load with weights_only=False
    # https://github.com/stanfordnlp/stanza/issues/1429
    warnings.simplefilter(action="ignore", category=FutureWarning)

    try:
        nlp = stanza.Pipeline(**nlp_args)
    except KeyError as e:
        if e.args[0] == "packages":
            raise SparvErrorMessage(
                "Stanza has been updated and the resources file for the Swedish model needs to be recreated. "
                f"Delete the file {resources_file.name!r} and rerun Sparv."
            ) from None
        raise e

    return nlp
