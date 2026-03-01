"""Util functions used in stanza."""

from sparv.api import Annotation, Output, SparvErrorMessage, annotator


@annotator("Annotate tokens with IDs relative to their sentences")
def make_ref(
    out: Output = Output("<token>:stanza.ref", cls="token:ref", description="Token IDs relative to their sentences"),
    sentence: Annotation = Annotation("<sentence>"),
    token: Annotation = Annotation("<token>"),
) -> None:
    """Annotate tokens with IDs relative to their sentences.

    Args:
        out: Output annotation.
        sentence: Sentence annotation.
        token: Token annotation.
    """
    from sparv.modules.misc import number  # noqa: PLC0415

    number.number_relative(out, sentence, token)


def run_stanza(nlp, document: list, batch_size: int, max_sentence_length: int = 0, max_token_length: int = 0):  # noqa: ANN001, ANN201
    """Run Stanza and handle possible errors.

    Args:
        nlp: Stanza pipeline.
        document: Document to process.
        batch_size: Stanza batch size.
        max_sentence_length: Maximum sentence length to parse.
        max_token_length: Maximum token length to parse.

    Returns:
        Parsed Stanza document.

    Raises:
        SparvErrorMessage: If Stanza encounters a recursion error or runs out of memory.
    """
    try:
        doc = nlp(document)
    except RecursionError:
        msg = (
            "Stanza encountered a recursion error. To prevent this from happening you can try to limit "
            "the Stanza batch size by setting the 'stanza.batch_size' config variable to something lower "
            f"(current value: {batch_size}).\n"
        )
        raise SparvErrorMessage(msg) from None
    except RuntimeError as e:
        gpu_error = "CUDA out of memory" in str(e)
        cpu_error = "DefaultCPUAllocator: can't allocate memory" in str(e)
        if gpu_error or cpu_error:
            msg = (
                "Stanza ran out of memory. You can try the following options to prevent this from happening:\n"
                " - Limit the number of parallel Stanza processes by using the 'threads' section in your Sparv "
                "configuration.\n"
                " - Limit the Stanza batch size by setting the 'stanza.batch_size' config variable to something "
                f"lower (current value: {batch_size}).\n"
                " - Exclude excessively long sentences from dependency parsing by setting the "
                "'stanza.max_sentence_length' config variable to something lower (current value: "
                f"{max_sentence_length or 'disabled'}).\n"
                " - Exclude sentences with unreasonably long tokens by setting the "
                "'stanza.max_token_length' config variable to something lower (current value: "
                f"{max_token_length or 'disabled'})."
            )
            if gpu_error:
                msg += "\n - Switch to using CPU by setting the 'stanza.use_gpu' config variable to false."
        else:
            msg = str(e)
        raise SparvErrorMessage(msg) from None
    return doc


def check_sentence_respect(sparv_sent_len: int, stanza_sent_len: int) -> None:
    """Check whether Stanza respected the given sentence segmentation.

    Args:
        sparv_sent_len: Number of sentences in Sparv.
        stanza_sent_len: Number of sentences in Stanza.

    Raises:
        SparvErrorMessage: If Stanza did not respect the given sentence segmentation.
    """
    if sparv_sent_len != stanza_sent_len:
        raise SparvErrorMessage("The Stanza pipeline did not seem to respect the given sentence segmentation!")


def check_token_respect(sparv_token_len: int, stanza_token_len: int) -> None:
    """Check whether Stanza respected the given tokenization.

    Args:
        sparv_token_len: Number of tokens in Sparv.
        stanza_token_len: Number of tokens in Stanza.

    Raises:
        SparvErrorMessage: If Stanza did not respect the given tokenization.
    """
    if sparv_token_len != stanza_token_len:
        raise SparvErrorMessage("Stanza pipeline did not seem to respect the given tokenization!")
