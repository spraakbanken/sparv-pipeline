# -*- coding: utf-8 -*-
import re
import os
import sparv.util as util

"""
Running malt processes are only kept if the input is small: otherwise
flush() on stdin blocks, and readline() on stdout is too slow to be
practical on long texts. We cannot use read() because it reads to EOF.

The value of this constant is a bit arbitrary, and could probably be longer.
"""
RESTART_THRESHOLD_LENGTH = 64000

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
HEAD_COLUMN = 6
DEPREL_COLUMN = 7
UNDEF = "_"


def maltparse(maltjar, model, out, word, pos, msd, sentence, encoding=util.UTF8, process_dict=None):
    """
    Runs the malt parser, in an already started process defined in
    process_dict, or starts a new process (default)

    The process_dict argument should never be set from the command line.
    """
    if process_dict is None:
        process = maltstart(maltjar, model, encoding)
    else:
        process = process_dict['process']
        # If process seems dead, spawn a new
        if process.stdin.closed or process.stdout.closed or process.poll():
            util.system.kill_process(process)
            process = maltstart(maltjar, model, encoding, send_empty_sentence=True)
            process_dict['process'] = process

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]

    WORD = util.read_annotation(word)
    POS = util.read_annotation(pos)
    MSD = util.read_annotation(msd)

    def conll_token(nr, tok):
        form = WORD[tok]
        lemma = UNDEF
        pos = cpos = POS[tok]
        feats = re.sub(r"[ ,.]", "|", MSD[tok]).replace("+", "/")
        return TAG_SEP.join((str(nr), form, lemma, cpos, pos, feats))

    stdin = SENT_SEP.join(TOK_SEP.join(conll_token(n + 1, tok) for n, tok in enumerate(sent))
                          for sent in sentences)

    if encoding:
        stdin = stdin.encode(encoding)

    keep_process = len(stdin) < RESTART_THRESHOLD_LENGTH and process_dict is not None
    util.log.info("Stdin length: %s, keep process: %s", len(stdin), keep_process)

    if process_dict is not None:
        process_dict['restart'] = not keep_process

    if keep_process:
        # Chatting with malt: send a SENT_SEP and read correct number of lines
        stdin_fd, stdout_fd = process.stdin, process.stdout
        stdin_fd.write(stdin + SENT_SEP.encode(util.UTF8))
        stdin_fd.flush()

        malt_sentences = []
        for sent in sentences:
            malt_sent = []
            for tok in sent:
                line = stdout_fd.readline()
                if encoding:
                    line = line.decode(encoding)
                malt_sent.append(line)
            line = stdout_fd.readline()
            assert line == b'\n'
            malt_sentences.append(malt_sent)
    else:
        # Otherwise use communicate which buffers properly
        stdout, _ = process.communicate(stdin)
        if encoding:
            stdout = stdout.decode(encoding)
        malt_sentences = (malt_sent.split(TOK_SEP)
                          for malt_sent in stdout.split(SENT_SEP))

    OUT = {}
    for (sent, malt_sent) in zip(sentences, malt_sentences):
        for (tok, malt_tok) in zip(sent, malt_sent):
            cols = [(None if col == UNDEF else col) for col in malt_tok.split(TAG_SEP)]
            deprel = cols[DEPREL_COLUMN]
            head = int(cols[HEAD_COLUMN])
            headid = sent[head - 1] if head else "-"
            OUT[tok] = (deprel, headid)

    util.write_annotation(out, OUT, transform=" ".join)


def maltstart(maltjar, model, encoding, send_empty_sentence=False):
    """
    Start a malt process and return it.
    """
    java_opts = ["-Xmx1024m"]
    malt_args = ["-ic", encoding, "-oc", encoding, "-m", "parse"]
    if model.startswith("http://"):
        malt_args += ["-u", model]
        util.log.info("Using MALT model from URL: %s", model)
    else:
        modeldir, model = os.path.split(model)
        if model.endswith(".mco"):
            model, _ = os.path.splitext(model)
        if modeldir:
            malt_args += ["-w", modeldir]
        malt_args += ["-c", model]
        util.log.info("Using local MALT model: %s (in directory %s)", model, modeldir or ".")

    process = util.system.call_java(maltjar, malt_args, options=java_opts,
                                    stdin="", encoding=encoding, verbose=True,
                                    return_command=True)

    if send_empty_sentence:
        # Send a simple sentence to malt, this greatly enhances performance
        # for subsequent requests.
        stdin_fd, stdout_fd = process.stdin, process.stdout
        util.log.info("Sending empty sentence to malt")
        stdin_fd.write("1\t.\t_\tMAD\tMAD\tMAD\n\n\n".encode(util.UTF8))
        stdin_fd.flush()
        stdout_fd.readline()
        stdout_fd.readline()

    return process


################################################################################

def read_conll_file(filename, encoding=util.UTF8):
    with open(filename, encoding=encoding) as F:
        sentence = []
        for line in F:
            line = line.strip()
            if line:
                cols = [(None if col == '_' else col) for col in line.split('\t')]
                nr, wordform, lemma, cpos, pos, feats, head, deprel, phead, pdeprel = cols + [None] * (10 - len(cols))
                sentence.append({'id': nr,
                                 'form': wordform,
                                 'lemma': lemma,
                                 'cpos': cpos,
                                 'pos': pos,
                                 'feats': feats,
                                 'head': head,
                                 'deprel': deprel,
                                 'phead': phead,
                                 'pdeprel': pdeprel,
                                 })
            elif sentence:
                yield sentence
                sentence = []
        if sentence:
            yield sentence


def write_conll_file(sentences, filename, encoding=util.UTF8):
    with open(filename, "w", encoding=encoding) as F:
        for sent in sentences:
            nr = 1
            for token in sent:
                if isinstance(token, str):
                    cols = (nr, token)
                elif isinstance(token, (tuple, list)):
                    cols = list(token)
                    if isinstance(cols[0], int):
                        assert cols[0] == nr, "Token mismatch: %s / %r" % (nr, token)
                    else:
                        cols.insert(0, nr)
                elif isinstance(token, dict):
                    form = token.get('form', token.get('word', '_'))
                    lemma = token.get('lemma', '_')
                    pos = token.get('pos', '_')
                    cpos = token.get('cpos', pos)
                    feats = token.get('feats', token.get('msd', '_'))
                    # feats = re.sub(r'[ ,.]', '|', feats)
                    cols = (nr, form, lemma, cpos, pos, feats)
                else:
                    raise ValueError("Unknown token: %r" % token)
                print("\t".join(str(col) for col in cols), file=F)
                nr += 1
            print(file=F)

################################################################################

if __name__ == '__main__':
    util.run.main(maltparse)
