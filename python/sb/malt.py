# -*- coding: utf-8 -*-

import re, os, codecs #, tempfile
import util

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
HEAD_COLUMN = 6
DEPREL_COLUMN = 7
UNDEF = "_"

def maltparse(maltjar, model, out, word, pos, msd, sentence, encoding=util.UTF8, channels=None):
    """
    Starts the maltparser.

    The argument `channels` should never be set from the command line.
    If it is set, it is assumed that there is already a maltparser
    running. This can be enabled when using catapult, channels is then
    a tuple (stdin, stdout) for a running process. If this is the
    case, these will not be closed.
    """
    util.log.info("channels: %s", channels)
    stdin_fd, stdout_fd = channels or maltstart(maltjar, model, encoding)
    util.log.info("stdin: %s, stdout: %s", stdin_fd, stdout_fd)

    """
    Prepare stdin
    """
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

    stdin = SENT_SEP.join(TOK_SEP.join(conll_token(n+1, tok) for n, tok in enumerate(sent))
                          for sent in sentences) + "\n\n"
    if encoding:
        stdin = stdin.encode(encoding)
    util.log.info("malt stdin:\n%s", stdin)

    """
    Send stdin
    """

    stdin_fd.write(stdin)
    if channels:
        stdin_fd.flush()
    else:
        stdin_fd.close()

    """
    Read and process output
    """
    util.log.info("waiting for malt stdout")

    OUT = {}

    for sent in sentences:
        for tok in sent:
            malt_tok = stdout_fd.readline()
            util.log.info("token: %s", malt_tok)
            if encoding:
                malt_tok = malt_tok.decode(encoding)
            cols = [(None if col == UNDEF else col) for col in malt_tok.split(TAG_SEP)]
            deprel = cols[DEPREL_COLUMN]
            head = int(cols[HEAD_COLUMN])
            headid = sent[head - 1] if head else "-"
            OUT[tok] = (deprel, headid)

        malt_tok = stdout_fd.readline()
        assert malt_tok == '\n'

    channels or stdout_fd.close()

    util.write_annotation(out, OUT, encode=" ".join)

def maltstart(maltjar, model, encoding=util.UTF8):
    """
    Starts a malt process to communicate with, returning stdin and stdout
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

    return util.system.call_java(maltjar, malt_args, options=java_opts,
                                 stdin=None, encoding=encoding, verbose=True, mk_fds=True)

################################################################################

def read_conll_file(filename, encoding=util.UTF8):
    with codecs.open(filename, encoding=encoding) as F:
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
    with codecs.open(filename, "w", encoding=encoding) as F:
        for sent in sentences:
            nr = 1
            for token in sent:
                if isinstance(token, basestring):
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
                    #feats = re.sub(r'[ ,.]', '|', feats)
                    cols = (nr, form, lemma, cpos, pos, feats)
                else:
                    raise ValueError("Unknown token: %r" % token)
                print >>F, "\t".join(unicode(col) for col in cols)
                nr += 1
            print >>F

################################################################################

if __name__ == '__main__':
    util.run.main(maltparse)
