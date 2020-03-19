import re
import sparv.util as util

SENT_SEP = "\n\n"
TOK_SEP = "\n"
TAG_SEP = "\t"
TAG_COLUMN = 1


def msdtag(doc, model, out, word, sentence, tag_mapping=None, morphtable=None, patterns=None, encoding=util.UTF8):
    """POS/MSD tag using the Hunpos tagger."""
    if isinstance(tag_mapping, str) and tag_mapping:
        tag_mapping = util.tagsets.__dict__[tag_mapping]
    elif tag_mapping is None or tag_mapping == "":
        tag_mapping = {}

    pattern_list = []

    if patterns:
        with open(patterns, mode="r", encoding="utf-8") as pat:
            for line in pat:
                if line.strip() and not line.startswith("#"):
                    name, pattern, tags = line.strip().split("\t", 2)
                    pattern_list.append((name, re.compile("^%s$" % pattern), tags))

    def replace_word(w):
        """Replace word with alias if word matches a regex pattern."""
        for p in pattern_list:
            if re.match(p[1], w):
                return "[[%s]]" % p[0]
        return w

    sentences, orphans = util.parent.get_children(doc, sentence, word)
    token_word = list(util.read_annotation(doc, word))
    stdin = SENT_SEP.join(TOK_SEP.join(replace_word(token_word[token_index]) for token_index in sent)
                          for sent in sentences)
    args = [model]
    if morphtable:
        args.extend(["-m", morphtable])
    stdout, _ = util.system.call_binary("hunpos-tag", args, stdin, encoding=encoding, verbose=True)

    out_annotation = util.create_empty_attribute(doc, word)
    for sent, tagged_sent in zip(sentences, stdout.strip().split(SENT_SEP)):
        for token_index, tagged_token in zip(sent, tagged_sent.strip().split(TOK_SEP)):
            tag = tagged_token.strip().split(TAG_SEP)[TAG_COLUMN]
            tag = tag_mapping.get(tag, tag)
            out_annotation[token_index] = tag

    util.write_annotation(doc, out, out_annotation)


# TODO: använd sockets
# - spara socket-id i en fil i tmp/

def postag():
    pass


if __name__ == '__main__':
    util.run.main(msdtag)
