# -*- coding: utf-8 -*-

#from StringIO import StringIO
#import dbm
#import util
import util.tagsets

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1


def msdtag(model, out, word, sentence, tag_mapping=None, morphtable=None, encoding=util.UTF8):
    """POS/MSD tag using the Hunpos tagger.
    """
    if isinstance(tag_mapping, basestring) and tag_mapping:
        tag_mapping = util.tagsets.__dict__[tag_mapping]
    elif tag_mapping is None or tag_mapping == "":
        tag_mapping = {}

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    stdin = SENT_SEP.join(TOK_SEP.join(WORD[tokid] for tokid in sent)
                          for sent in sentences)
    args = [model]
    if morphtable: args.extend(["-m", morphtable])
    stdout, _ = util.system.call_binary("hunpos-tag", args, stdin, encoding=encoding, verbose=True)

    OUT = {}
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_id, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            tag = tag_mapping.get(tag, tag)
            OUT[token_id] = tag
    util.write_annotation(out, OUT)


# TODO: använd sockets
# - spara socket-id i en fil i tmp/

if __name__ == '__main__':
    util.run.main(msdtag)
