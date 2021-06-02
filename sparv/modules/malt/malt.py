"""Dependency parsing using MaltParser."""

import re

from sparv.api import Annotation, Binary, Config, Model, ModelOutput, Output, annotator, get_logger, modelbuilder, util

logger = get_logger(__name__)


# Running Malt processes are only kept if the input is small: otherwise
# flush() on stdin blocks, and readline() on stdout is too slow to be
# practical on long texts. We cannot use read() because it reads to EOF.
# The value of this constant is a bit arbitrary, and could probably be longer.
RESTART_THRESHOLD_LENGTH = 64000

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
HEAD_COLUMN = 6
DEPREL_COLUMN = 7
UNDEF = "_"


def preloader(maltjar, model, encoding):
    """Preload MaltParser executable."""
    process = maltstart(maltjar, model, encoding, send_empty_sentence=True)
    process_dict = {
        "process": process,
        "restart": False
    }
    return process_dict


def cleanup(maltjar, model, encoding, process_dict):
    """Cleanup function used by preloader to restart Malt."""
    if process_dict["restart"]:
        util.system.kill_process(process_dict["process"])
        logger.info("Restarting MaltParser process")
        process_dict = preloader(maltjar, model, encoding)
    return process_dict


@annotator("Dependency parsing using MaltParser", language=["swe"], config=[
    Config("malt.jar", default="maltparser-1.7.2/maltparser-1.7.2.jar",
           description="Path name of the executable .jar file"),
    Config("malt.model", default="malt/swemalt-1.7.2.mco", description="Path to Malt model")],
    preloader=preloader, preloader_params=["maltjar", "model", "encoding"], preloader_target="process_dict",
    preloader_cleanup=cleanup, preloader_shared=False)
def annotate(maltjar: Binary = Binary("[malt.jar]"),
             model: Model = Model("[malt.model]"),
             out_dephead: Output = Output("<token>:malt.dephead", cls="token:dephead",
                                          description="Positions of the dependency heads"),
             out_dephead_ref: Output = Output("<token>:malt.dephead_ref", cls="token:dephead_ref",
                                              description="Sentence-relative positions of the dependency heads"),
             out_deprel: Output = Output("<token>:malt.deprel", cls="token:deprel",
                                         description="Dependency relations to the head"),
             word: Annotation = Annotation("<token:word>"),
             pos: Annotation = Annotation("<token:pos>"),
             msd: Annotation = Annotation("<token:msd>"),
             ref: Annotation = Annotation("<token>:malt.ref"),
             sentence: Annotation = Annotation("<sentence>"),
             token: Annotation = Annotation("<token>"),
             encoding: str = util.constants.UTF8,
             process_dict=None):
    """
    Run the malt parser, in an already started process defined in process_dict, or start a new process (default).

    The process_dict argument should never be set from the command line.
    """
    if process_dict is None:
        process = maltstart(maltjar, model, encoding)
    else:
        process = process_dict["process"]
        # If process seems dead, spawn a new
        if process.stdin.closed or process.stdout.closed or process.poll():
            util.system.kill_process(process)
            process = maltstart(maltjar, model, encoding, send_empty_sentence=True)
            process_dict["process"] = process

    sentences, orphans = sentence.get_children(token)
    if orphans:
        logger.warning(f"Found {len(orphans)} tokens not belonging to any sentence. These will not be annotated with "
                       f"dependency relations.")

    word_annotation = list(word.read())
    pos_annotation = list(pos.read())
    msd_annotation = list(msd.read())
    ref_annotation = list(ref.read())

    def conll_token(nr, token_index):
        form = word_annotation[token_index]
        lemma = UNDEF
        pos = cpos = pos_annotation[token_index]
        feats = re.sub(r"[ ,.]", "|", msd_annotation[token_index]).replace("+", "/")
        return TAG_SEP.join((str(nr), form, lemma, cpos, pos, feats))

    stdin = SENT_SEP.join(TOK_SEP.join(conll_token(n + 1, token_index) for n, token_index in enumerate(sent))
                          for sent in sentences)

    if encoding:
        stdin = stdin.encode(encoding)

    keep_process = len(stdin) < RESTART_THRESHOLD_LENGTH and process_dict is not None
    logger.info("Stdin length: %s, keep process: %s", len(stdin), keep_process)

    if process_dict is not None:
        process_dict["restart"] = not keep_process

    if keep_process:
        # Chatting with malt: send a SENT_SEP and read correct number of lines
        stdin_fd, stdout_fd = process.stdin, process.stdout
        stdin_fd.write(stdin + SENT_SEP.encode(util.constants.UTF8))
        stdin_fd.flush()

        malt_sentences = []
        for sent in sentences:
            malt_sent = []
            for _ in sent:
                line = stdout_fd.readline()
                if encoding:
                    line = line.decode(encoding)
                malt_sent.append(line)
            line = stdout_fd.readline()
            assert line == b"\n"
            malt_sentences.append(malt_sent)
    else:
        # Otherwise use communicate which buffers properly
        stdout, _ = process.communicate(stdin)
        if encoding:
            stdout = stdout.decode(encoding)
        malt_sentences = (malt_sent.split(TOK_SEP)
                          for malt_sent in stdout.split(SENT_SEP))

    out_dephead_annotation = word.create_empty_attribute()
    out_dephead_ref_annotation = out_dephead_annotation.copy()
    out_deprel_annotation = out_dephead_annotation.copy()
    for (sent, malt_sent) in zip(sentences, malt_sentences):
        for (token_index, malt_tok) in zip(sent, malt_sent):
            cols = [(None if col == UNDEF else col) for col in malt_tok.split(TAG_SEP)]
            out_deprel_annotation[token_index] = cols[DEPREL_COLUMN]
            head = int(cols[HEAD_COLUMN])
            out_dephead_annotation[token_index] = str(sent[head - 1]) if head else "-"
            out_dephead_ref_annotation[token_index] = str(ref_annotation[sent[head - 1]]) if head else ""

    out_dephead.write(out_dephead_annotation)
    out_dephead_ref.write(out_dephead_ref_annotation)
    out_deprel.write(out_deprel_annotation)


@annotator("Annotate tokens with IDs relative to their sentences", language=["swe"])
def make_ref(out: Output = Output("<token>:malt.ref", cls="token:ref",
                                  description="Token IDs relative to their sentences"),
             sentence: Annotation = Annotation("<sentence>"),
             token: Annotation = Annotation("<token>")):
    """Annotate tokens with IDs relative to their sentences."""
    from sparv.modules.misc import number
    number.number_relative(out, sentence, token)


def maltstart(maltjar, model, encoding, send_empty_sentence=False):
    """Start a malt process and return it."""
    java_opts = ["-Xmx1024m"]
    malt_args = ["-ic", encoding, "-oc", encoding, "-m", "parse"]
    if str(model).startswith("http://") or str(model).startswith("https://"):
        malt_args += ["-u", str(model)]
        logger.info("Using Malt model from URL: %s", model)
    else:
        model_dir = model.path.parent
        model_file = model.path.name
        if model.path.suffix == ".mco":
            model_file = model.path.stem
        if model_dir:
            malt_args += ["-w", model_dir]
        malt_args += ["-c", model_file]
        logger.info("Using local Malt model: %s (in directory %s)", model_file, model_dir or ".")

    process = util.system.call_java(maltjar, malt_args, options=java_opts, encoding=encoding, return_command=True)

    if send_empty_sentence:
        # Send a simple sentence to malt, this greatly enhances performance
        # for subsequent requests.
        stdin_fd, stdout_fd = process.stdin, process.stdout
        logger.info("Sending empty sentence to malt")
        stdin_fd.write("1\t.\t_\tMAD\tMAD\tMAD\n\n\n".encode(util.constants.UTF8))
        stdin_fd.flush()
        stdout_fd.readline()
        stdout_fd.readline()

    return process


@modelbuilder("Model for MaltParser", language=["swe"])
def build_model(out: ModelOutput = ModelOutput("malt/swemalt-1.7.2.mco"),
                _maltjar: Binary = Binary("[malt.jar]")):
    """Download model for MaltParser.

    Won't download model unless maltjar has been installed.
    """
    out.download("http://maltparser.org/mco/swedish_parser/swemalt-1.7.2.mco")
