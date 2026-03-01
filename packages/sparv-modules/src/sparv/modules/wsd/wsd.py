"""Word sense disambiguation based on SALDO annotation."""

import re
import subprocess
from pathlib import Path

from sparv.api import (
    Annotation,
    Binary,
    Config,
    Model,
    ModelOutput,
    Output,
    SourceFilename,
    annotator,
    get_logger,
    modelbuilder,
    util,
)

logger = get_logger(__name__)

SENT_SEP = "$SENT$"


@annotator(
    "Word sense disambiguation",
    language=["swe"],
    config=[
        Config(
            "wsd.sense_model",
            default="wsd/ALL_512_128_w10_A2_140403_ctx1.bin",
            description="Path to sense model",
            datatype=str,
        ),
        Config(
            "wsd.context_model",
            default="wsd/lem_cbow0_s512_w10_NEW2_ctx.bin",
            description="Path to context model",
            datatype=str,
        ),
        Config("wsd.default_prob", -1.0, description="Default value for unanalyzed senses", datatype=float),
        Config(
            "wsd.jar", default="wsd/saldowsd.jar", description="Path name of the executable .jar file", datatype=str
        ),
        Config(
            "wsd.prob_format",
            util.constants.SCORESEP + "%.3f",
            description="Format string for how to print the sense probability",
            datatype=str,
        ),
    ],
)
def annotate(
    wsdjar: Binary = Binary("[wsd.jar]"),
    sense_model: Model = Model("[wsd.sense_model]"),
    context_model: Model = Model("[wsd.context_model]"),
    out: Output = Output("<token>:wsd.sense", cls="token:sense", description="Sense disambiguated SALDO identifiers"),
    sentence: Annotation = Annotation("<sentence>"),
    word: Annotation = Annotation("<token:word>"),
    ref: Annotation = Annotation("<token:ref>"),
    lemgram: Annotation = Annotation("<token:lemgram>"),
    saldo: Annotation = Annotation("<token>:saldo.sense"),
    pos: Annotation = Annotation("<token:pos>"),
    token: Annotation = Annotation("<token>"),
    prob_format: str = Config("wsd.prob_format"),
    default_prob: float = Config("wsd.default_prob"),
    source_file: SourceFilename = SourceFilename(),
    encoding: str = util.constants.UTF8,
) -> None:
    """Run the word sense disambiguation tool (saldowsd.jar) to add probabilities to the saldo annotation.

    Unanalyzed senses (e.g. multiword expressions) receive the probability value given by default_prob.
      - wsdjar is the name of the java programme to be used for the wsd
      - sense_model and context_model are the models to be used with wsdjar
      - out is the resulting annotation file
      - sentence is an existing annotation for sentences and their children (words)
      - word is an existing annotations for wordforms
      - ref is an existing annotation for word references
      - lemgram and saldo are existing annotations for inflection tables and meanings
      - pos is an existing annotations for part-of-speech
      - prob_format is a format string for how to print the sense probability
      - default_prob is the default value for unanalyzed senses
    """
    word_annotation = list(word.read())
    ref_annotation = list(ref.read())
    lemgram_annotation = list(lemgram.read())
    saldo_annotation = list(saldo.read())
    pos_annotation = list(pos.read())

    sentences, orphans = sentence.get_children(token)
    sentences.append(orphans)
    # Remove empty sentences
    sentences = [s for s in sentences if s]

    # Start WSD process
    process = wsd_start(wsdjar, sense_model.path, context_model.path, encoding)

    # Construct input and send to WSD
    stdin = build_input(
        sentences, word_annotation, ref_annotation, lemgram_annotation, saldo_annotation, pos_annotation, source_file
    )

    if encoding:
        stdin = stdin.encode(encoding)

    stdout, stderr = process.communicate(stdin)
    # TODO: Solve hack line below!
    # Problem is that regular messages "Reading sense vectors..." are also piped to stderr.
    if len(stderr) > 52:  # noqa: PLR2004
        util.system.kill_process(process)
        logger.error(str(stderr))
        return

    if encoding:
        stdout = stdout.decode(encoding)

    process_output(word, out, stdout, sentences, saldo_annotation, prob_format, default_prob)

    # Kill running subprocess
    util.system.kill_process(process)
    return


@modelbuilder("WSD models", language=["swe"])
def build_model(
    sense_model: ModelOutput = ModelOutput("wsd/ALL_512_128_w10_A2_140403_ctx1.bin"),
    context_model: ModelOutput = ModelOutput("wsd/lem_cbow0_s512_w10_NEW2_ctx.bin"),
) -> None:
    """Download models for SALDO-based word sense disambiguation."""
    # Download sense model
    sense_model.download(
        "https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/ALL_512_128_w10_A2_140403_ctx1.bin"
    )

    # Download context model
    context_model.download(
        "https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/lem_cbow0_s512_w10_NEW2_ctx.bin"
    )


def wsd_start(wsdjar: Binary, sense_model: Path, context_model: Path, encoding: str) -> subprocess.Popen:
    """Start a wsd process and return it.

    Args:
        wsdjar: Path to the JAR file.
        sense_model: Path to the sense model.
        context_model: Path to the context model.
        encoding: Encoding for the process.

    Returns:
        The started process.
    """
    java_opts = ["-Xmx6G"]
    wsd_args = [
        ("-appName", "se.gu.spraakbanken.wsd.VectorWSD"),
        ("-format", "tab"),
        ("-svFile", sense_model),
        ("-cvFile", context_model),
        ("-s1Prior", "1"),
        ("-decay", "true"),
        ("-contextWidth", "10"),
        ("-verbose", "false"),
    ]

    return util.system.call_java(wsdjar, wsd_args, options=java_opts, encoding=encoding, return_command=True)


def build_input(
    sentences: list,
    word_annotation: list[str],
    ref_annotation: list[str],
    lemgram_annotation: list[str],
    saldo_annotation: list[str],
    pos_annotation: list[str],
    source_file: SourceFilename,
) -> str:
    """Construct tab-separated input for WSD.

    Args:
        sentences: List of sentences.
        word_annotation: Word annotation.
        ref_annotation: Reference annotation.
        lemgram_annotation: Lemgram annotation.
        saldo_annotation: SALDO annotation.
        pos_annotation: Part-of-speech annotation.
        source_file: Source filename.

    Returns:
        Tab-separated input for WSD.
    """
    rows = []
    for sentence in sentences:
        for token_index in sentence:
            mwe = False
            word = word_annotation[token_index]
            if re.search(r"\s", word):
                logger.warning(
                    "Found whitespace in token %r in source file %r; replacing with underscore.", word, source_file
                )
                word = re.sub(r"\s", "_", word)
            ref = ref_annotation[token_index]
            pos = pos_annotation[token_index].lower()
            saldo = (
                saldo_annotation[token_index].strip(util.constants.AFFIX)
                if saldo_annotation[token_index] != util.constants.AFFIX
                else "_"
            )
            if "_" in saldo and len(saldo) > 1:
                mwe = True

            lemgram, simple_lemgram = make_lemgram(lemgram_annotation[token_index], word, pos)

            if mwe:
                lemgram = remove_mwe(lemgram)
                simple_lemgram = remove_mwe(simple_lemgram)
                saldo = remove_mwe(saldo)
            row = f"{ref}\t{word}\t_\t{lemgram}\t{simple_lemgram}\t{saldo}"
            rows.append(row)
        # Append empty row as sentence separator
        rows.append(f"_\t_\t_\t_\t{SENT_SEP}\t_")
    return "\n".join(rows)


def process_output(
    word: Annotation,
    out: Output,
    stdout: str,
    in_sentences: list,
    saldo_annotation: list[str],
    prob_format: str,
    default_prob: float,
) -> None:
    """Parse WSD output and write annotation."""
    out_annotation = word.create_empty_attribute()

    # Split output into sentences
    out_sentences = stdout.strip()
    out_sentences = out_sentences.split(f"_\t_\t_\t_\t{SENT_SEP}\t_\t_")
    out_sentences = [i for i in out_sentences if i]

    # Split output into tokens
    for out_sent, in_sent in zip(out_sentences, in_sentences, strict=True):
        out_tokens = [t for t in out_sent.split("\n") if t]
        for out_tok, in_tok in zip(out_tokens, in_sent, strict=True):
            out_prob = out_tok.split("\t")[6]
            out_prob = [i for i in out_prob.split("|") if i != "_"]
            out_meanings = [i for i in out_tok.split("\t")[5].split("|") if i != "_"]
            saldo = [i for i in saldo_annotation[in_tok].strip(util.constants.AFFIX).split(util.constants.DELIM) if i]

            new_saldo = []
            if out_prob:
                for meaning in saldo:
                    if meaning in out_meanings:
                        i = out_meanings.index(meaning)
                        new_saldo.append((meaning, float(out_prob[i])))
                    else:
                        new_saldo.append((meaning, default_prob))
            else:
                new_saldo = [(meaning, default_prob) for meaning in saldo]

            # Sort by probability
            new_saldo.sort(key=lambda x: (-x[1], x[0]))
            # Format probability according to prob_format
            new_saldo = [saldo + prob_format % prob if prob_format else saldo for saldo, prob in new_saldo]
            out_annotation[in_tok] = util.misc.cwbset(new_saldo)

    out.write(out_annotation)


def make_lemgram(lemgram: str, word: str, pos: str) -> tuple[str, str]:
    """Construct lemgram and simple_lemgram format.

    Args:
        lemgram: Lemgram annotation.
        word: Word annotation.
        pos: Part-of-speech annotation.

    Returns:
        A tuple containing the lemgram and simple_lemgram.
    """
    lemgram = lemgram.strip(util.constants.AFFIX) if lemgram != util.constants.AFFIX else "_"
    simple_lemgram = util.constants.DELIM.join({lem[: lem.rfind(".")] for lem in lemgram.split(util.constants.DELIM)})

    # Fix simple lemgram for tokens without lemgram (word + pos)
    if not simple_lemgram:
        simple_lemgram = word + ".." + pos
    return lemgram, simple_lemgram


def remove_mwe(annotation: str) -> str:
    """Strip unnecessary information from multi word expressions.

    Args:
        annotation: Annotation string.

    Returns:
        A cleaned annotation string.
    """
    annotation = annotation.split(util.constants.DELIM)
    annotation = [i for i in annotation if "_" not in i]
    return util.constants.DELIM.join(annotation) if annotation else "_"
