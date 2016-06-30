import util

SENT_SEP = "$SENT$"


def run_wsd(wsdjar, sense_model, context_model, out, sentence, word, ref, lemgram, saldo, pos, sensefmt=":%.3f", default_prob="-1", encoding=util.UTF8):
    """
    Runs the word sense disambiguation tool (saldowsd.jar) to add probabilities to the saldo annotation.
    Unanalyzed senses (e.g. multiword expressions) receive the probability value given by default_prob.
      - wsdjar is the name of the java programme to be used for the wsd
      - sense_model and context_model are the models to be used with wsdjar
      - out is the resulting annotation file
      - sentence is an existing annotation for sentences and their children (words)
      - word is an existing annotations for wordforms
      - ref is an existing annotation for word references
      - lemgram and saldo are existing annotations for inflection tables and meanings
      - pos is an existing annotations for part-of-speech
      - sensefmt is a format string for how to print the sense and its probability
      - default_prob is the default value for unanalyzed senses
    """

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    REF = util.read_annotation(ref)
    LEMGRAM = util.read_annotation(lemgram)
    SALDO = util.read_annotation(saldo)
    POS = util.read_annotation(pos)

    # Start WSD process
    process = wsd_start(wsdjar, sense_model, context_model, encoding)

    # Construct input and send to WSD
    stdin = build_input(sentences, WORD, REF, LEMGRAM, SALDO, POS)
    if encoding:
        stdin = stdin.encode(encoding)

    stdout, stderr = process.communicate(stdin)
    # TODO: Solve hack line below!
    # Problem is that regular messages "Reading sense vectors.." are also piped to stderr.
    if len(stderr) > 52:
        util.system.kill_process(process)
        util.log.error(stderr)
        return

    if encoding:
        stdout = stdout.decode(encoding)

    process_output(out, stdout, sentences, SALDO, sensefmt, default_prob)

    # Kill running subprocess
    util.system.kill_process(process)
    return


def wsd_start(wsdjar, sense_model, context_model, encoding):
    """Start a wsd process and return it."""
    java_opts = ["-Xmx6G"]
    wsd_args = [("-appName", "se.gu.spraakbanken.wsd.VectorWSD"),
                ("-format", "tab"),
                ("-svFile", sense_model),
                ("-cvFile", context_model),
                ("-s1Prior", "1"),
                ("-decay", "true"),
                ("-contextWidth", "10"),
                ("-verbose", "false")]

    process = util.system.call_java(wsdjar, wsd_args, options=java_opts,
                                    stdin="", encoding=encoding,
                                    return_command=True)
    return process


def build_input(sentences, WORD, REF, LEMGRAM, SALDO, POS):
    """Construct tab-separated input for WSD."""
    rows = []
    for sentence in sentences:
        for tokid in sentence:
            mwe = False
            word = WORD[tokid]
            ref = REF[tokid]
            pos = POS[tokid].lower()
            saldo = SALDO[tokid].strip("|") if SALDO[tokid] != "|" else "_"
            if "_" in saldo and len(saldo) > 1:
                mwe = True

            lemgram, simple_lemgram = make_lemgram(LEMGRAM[tokid], word, pos)

            if mwe:
                lemgram = remove_mwe(lemgram)
                simple_lemgram = remove_mwe(simple_lemgram)
                saldo = remove_mwe(saldo)
            row = "\t".join([ref, word, "_", lemgram, simple_lemgram, saldo])
            rows.append(row)
        # Append empty row as sentence seperator
        rows.append("\t".join(["_", "_", "_", "_", SENT_SEP, "_"]))

    return "\n".join(rows)


def process_output(out, stdout, in_sentences, SALDO, sensefmt, default_prob):
    """Parse WSD output and write annotation."""
    OUT = {}

    # Split output into sentences
    out_sentences = stdout.strip()
    out_sentences = out_sentences.split("\t".join(["_", "_", "_", "_", SENT_SEP, "_", "_"]))
    out_sentences = [i for i in out_sentences if i]

    # Split output into tokens
    for out_sent, in_sent in zip(out_sentences, in_sentences):
        out_tokens = [t for t in out_sent.split("\n") if t]
        for (out_tok, in_tok) in zip(out_tokens, in_sent):
            out_prob = out_tok.split("\t")[6]
            out_prob = [i for i in out_prob.split("|") if i != "_"]
            out_meanings = [i for i in out_tok.split("\t")[5].split("|") if i != "_"]
            saldo = [i for i in SALDO[in_tok].split("|") if i]

            new_saldo = []
            if out_prob:
                for meaning in saldo:
                    if meaning in out_meanings:
                        i = out_meanings.index(meaning)
                        new_saldo.append(meaning + sensefmt % float(out_prob[i]))
                    else:
                        new_saldo.append(meaning + sensefmt % float(default_prob))
            else:
                new_saldo = [meaning + sensefmt % float(default_prob) for meaning in saldo]

            # Sort by probability
            new_saldo = sorted(new_saldo, key=lambda x: float(x.split(":")[-1]), reverse=True)
            OUT[in_tok] = util.cwbset(new_saldo)

    util.write_annotation(out, OUT)


def make_lemgram(lemgram, word, pos):
    """Construct lemgram and simple_lemgram format."""
    lemgram = lemgram.strip("|") if lemgram != "|" else "_"
    simple_lemgram = "|".join(set((l[:l.rfind(".")] for l in lemgram.split("|"))))

    # Fix simple lemgram for tokens without lemgram (word + pos)
    if not simple_lemgram:
        simple_lemgram = word + ".." + pos
    return lemgram, simple_lemgram


def remove_mwe(annotation):
    """For MWEs: strip unnecessary information."""
    annotation = annotation.split("|")
    annotation = [i for i in annotation if "_" not in i]
    if annotation:
        return "|".join(annotation)
    else:
        return "_"


if __name__ == "__main__":
    util.run.main(run_wsd)
