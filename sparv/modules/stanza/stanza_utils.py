"""Util functions used in stanza."""

import sparv.util as util


def run_stanza(nlp, document, batch_size, max_sentence_length: int = 0):
    """Run Stanza and handle possible errors."""
    try:
        doc = nlp(document)
    except RuntimeError as e:
        gpu_error = "CUDA out of memory" in str(e)
        cpu_error = "DefaultCPUAllocator: can't allocate memory" in str(e)
        if gpu_error or cpu_error:
            msg = "Stanza ran out of memory. You can try the following options to prevent this from happening:\n" \
                  " - Limit the number of parallel Stanza processes by using the 'threads' section in your Sparv " \
                  "configuration.\n" \
                  " - Limit the Stanza batch size by setting the 'stanza.batch_size' config variable to something " \
                  f"lower (current value: {batch_size}).\n" \
                  " - Exclude excessively long sentences from dependency parsing by setting the " \
                  "'stanza.max_sentence_length' config variable to something lower (current value: " \
                  f"{max_sentence_length})."
            if gpu_error:
                msg += "\n - Switch to using CPU by setting the 'stanza.use_gpu' config variable to false."
        else:
            msg = str(e)
        raise util.SparvErrorMessage(msg)
    return doc
