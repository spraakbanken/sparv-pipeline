# -*- coding: utf-8 -*-
from collections import defaultdict
import sparv.util as util
import sys
import pprint


def annotate(out_phrase_name, out_phrase_func, word, sentence, pos, msd, ref, dephead_ref, deprel):
    """ """

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    word_dict = util.read_annotation(word)
    ref_dict = util.read_annotation(ref)
    pos_dict = util.read_annotation(pos)
    msd_dict = util.read_annotation(msd)
    dephead_ref_dict = util.read_annotation(dephead_ref)
    deprel_dict = util.read_annotation(deprel)

    out_phrase_dict = {}
    out_func_dict = {}

    for n, s in enumerate(sentences):
        c = 0
        tokenlist = [Token(None)]
        for tokid in s:
            tokenlist.append(Token([ref_dict[tokid], word_dict[tokid], pos_dict[tokid], msd_dict[tokid],
                             dephead_ref_dict[tokid], deprel_dict[tokid]]))

        # Get PS tree
        sen = Sentence(tokenlist)
        if not sen.is_cyclic():
            print(pprint.pformat(convert_sentence(sen).top.to_tree_str()), file=sys.stderr)
            continue
            tree = convert_sentence(sen).top.to_tree_str()

            # # Make root
            # update_dictionary(out_phrase_dict, extract_id(s[0]), extract_id(s[-1], start=False), "Root", c)
            # update_dictionary(out_func_dict, extract_id(s[0]), extract_id(s[-1], start=False), "Root", c)
            c += 1

            # Make other nodes
            children = flatten_tree(tree[1], [])
            position = 0
            open_elem_stack = []
            # print
            for child in children:
                if not child[0].startswith('WORD:'):
                    open_elem_stack.append(child + (extract_id(s[position]),))
                    # print "<ph name=", child[0], "func=", child[1], ">", extract_id(s[position])
                else:
                    while open_elem_stack[-1][2] == child[2]:
                        start_id = open_elem_stack[-1][3]
                        end_id = extract_id(s[position - 1], start=False)
                        # update_dictionary(out_phrase_dict, start_id, end_id, open_elem_stack[-1][0], "name", c)
                        # update_dictionary(out_func_dict, start_id, end_id, open_elem_stack[-1][1], "func", c)
                        update_dictionary(out_phrase_dict, start_id, end_id, open_elem_stack[-1][0], open_elem_stack[-1][1], "name", c)
                        # print "</ph name=", open_elem_stack[-1][0], "func=", open_elem_stack[-1][1], ">", "-".join([start_id, end_id])
                        c += 1
                        open_elem_stack.pop()
                    position += 1
                    # print "   ", child[0]

            # Close remaining elements
            end_id = extract_id(s[-1], start=False)
            for elem in reversed(open_elem_stack):
                start_id = extract_id(elem[3])
                # update_dictionary(out_phrase_dict, start_id, end_id, elem[0], "name", c)
                # update_dictionary(out_func_dict, start_id, end_id, elem[1], "func", c)
                update_dictionary(out_phrase_dict, start_id, end_id, elem[0], elem[1], "name", c)
                # print "</ph name=", elem[0], "func=", elem[1], ">", "-".join([start_id, end_id])
                c += 1

    util.write_annotation(out_phrase_name, out_phrase_dict)
    util.write_annotation(out_phrase_func, out_func_dict)


def log(f):
    """
    Make a function write its input when called and output when finished.

    >>> @log
    ... def test(x, *ys, **kws):
    ...     return kws.get('c',0)+sum(x*y for y in ys)
    >>> test(2, 3, 4, c=1) == 1+2*3+2*4
    test(2, 3, 4, {'c': 1})
    test(2, 3, 4, {'c': 1}) = 15
    True
    """
    import sys
    import functools

    @functools.wraps(f)
    def g(*args, **kws):
        call = f.__name__ + pprint.pformat(args + (kws, ))
        print(call, file=sys.stderr)
        res = f(*args, **kws)
        print(call + ' = ' + pprint.pformat(res), file=sys.stderr)
        return res
    return g


def log(f):
    """
    Make a function write its input when called and output when finished.

    >>> @log
    ... def test(x, *ys, **kws):
    ...     return kws.get('c',0)+sum(x*y for y in ys)
    >>> test(2, 3, 4, c=1) == 1+2*3+2*4
    test(2, 3, 4, {'c': 1})
    test(2, 3, 4, {'c': 1}) = 15
    True
    """
    def g(*args, **kws):
        call = f.__name__ + pprint.pformat(args + (kws, ))
        print(call)
        res = f(*args, **kws)
        print(call + ' = ' + pprint.pformat(res))
        return res
    return g


@log
def flatten_tree(tree, children=[]):
    for child in tree:
        if has_children(child):
            flatten_tree(child, children)
        else:
            children.append(child)
    return children


def has_children(elem):
    if type(elem) == list:
        return True
    try:
        for child in elem:
            if type(child) == list:
                return True
    except TypeError:
        return False
    return False


def extract_id(token, start=True):
    if start:
        return token.strip('w:').split('-')[0]
    else:
        return token.strip('w:').split('-')[1]


def update_dictionary(phrase_dict, start_id, end_id, name, func, d_name, c):
    phrase_dict[str(c) + ":" + "-".join([start_id, end_id])] = ":".join([name, func])

##############################################################################
# from file "trees.py":


class Token(object):
    """Token containing a list of attributes."""
    def __init__(self, t):
        if t:
            self.word = t[1]
            self.pos = t[2]
            self.msd = t[3]
            self.ref = t[0]
            self.position = int(self.ref)
            self.deprel = t[5]
            self.depheadid = t[4]
            self.dephead = None
        else:
            self.ref = '0'
            self.position = 0
            self.deprel = None
            self.word = None
            self.pos = None
            self.msd = None
            self.dephead = None
        self.deps = []

    def get_deps_by_rel(self, r):
        out = []
        for n in self.deps:
            if n.deprel == r:
                out.append(n)
        return out

    def __str__(self):
        if self.position == 0:
            return "(ROOT)"
        else:
            return "WORD:" + self.ustr(self.word)

    def is_cyclic(self):
        seen = {}
        n = self
        while n:
            if n.position in seen:
                return True
            seen[n.position] = 1
            n = n.dephead
        return False

    @staticmethod
    def ustr(us):
        if not us:
            return "NONE"
        return us.encode("utf-8")


class Sentence(object):
    """Sentence containing a list of token objects."""
    def __init__(self, l):
        self.tokens = l
        table = {}
        for t in l:
            table[t.ref] = t
        for n in l:
            if n.deprel:
                if n.depheadid:
                    n.dephead = table[n.depheadid]
                else:
                    n.dephead = self.tokens[0]
                n.dephead.deps.append(n)

    def length(self):
        return len(self.tokens)

    # def __str__(self):
    #     return "(Sen: " + str(self.tokens) + ")"

    def to_tree_str(self):
        return "\n".join([str(t) for t in self.tokens])

    def words(self):
        out = ""
        for n in self.tokens:
            if n.word:
                out = out + n.word + u" "
        return out.strip()

    def is_cyclic(self):
        return any(n.is_cyclic() for n in self.tokens)

##############################################################################
# from file "to_const.py":


class Terminal(object):
    """Class representing a terminal node of a phrase structure tree."""
    def __init__(self, fun, t):
        self.fun = fun
        self.t = t
        self.start = self.t.position
        self.end = self.start + 1
        self.label = self.t.pos
        self.parent = None

    def head_position(self):
        return self.t.position

    def to_tree_str(self, n=0):
        return (str(self.t), str(self.fun), n)

    def to_word_str(self):
        if self.t.pos == 'PM':
            return self.t.word
        else:
            return self.t.word.lower()

    def length(self):
        return 1

    def is_punctuation(self):
        return self.t.pos in ['MAD', 'MID', 'PAD']

    def is_name(self):
        return self.t.pos == 'PM'

    def add_starts(self, starts):
        starts[self.start].append(self)

    def set_parents(self):
        pass


class Nonterminal(object):
    """Class representing a non-terminal node of a phrase structure tree."""
    def __init__(self, label, fun, headchild, children):
        self.label = label
        self.fun = fun
        self.headchild = headchild
        self.children = children
        self.start = min(c.start for c in self.children)
        self.end = max(c.end for c in self.children)
        self.parent = None

    def head_position(self):
        return self.headchild.head_position()

    def to_tree_str(self, n=0):
        parent = (str(self.label), str(self.fun), n)
        children = [parent]
        for c in self.children:
            children.append((c.to_tree_str(n + 2)))
        return children

    def to_word_str(self):
        l = []
        for c in self.children:
            l.append(c.to_word_str())
        return " ".join(l)

    def length(self):
        out = 0
        for c in self.children:
            out += c.length()
        return out

    def is_punctuation(self):
        if len(self.children) > 1:
            return False
        return self.children[0].is_punctuation()

    def is_name(self):
        return False

    def add_starts(self, starts):
        starts[self.start].append(self)
        for c in self.children:
            c.add_starts(starts)

    def set_parents(self):
        for c in self.children:
            c.parent = self
            c.set_parents()


class PSTree(object):
    """Class representing a phrase structure tree."""
    def __init__(self, top):
        self.top = top
        self.starts = defaultdict(list)
        self.top.add_starts(self.starts)
        self.top.set_parents()

    def length(self):
        return self.top.length()

    def to_tree_str(self):
        return self.top.to_tree_str()


def convert_sentence(sen):
    """Do a recursive analysis of sen.
    Return a PSTree object (phrase structure tree)
    if the analysis was successful."""
    return PSTree(convert(sen.tokens[0]))


def convert(token):
    """Recursively analyse the phrase structure of token."""
    children = [convert(c) for c in token.deps]

    def nonterminal(label):
        head = Terminal("HEAD", token)
        add_head(children, head)
        return Nonterminal(label, token.deprel, head, children)
    if token.position == 0:
        return Nonterminal("ROOT", "ROOT", token, children)
    elif token.deprel == "HD":
        return Terminal(token.deprel, token)
    elif token.pos == "KN" or token.pos == "MID":
        if children:
            lbl = get_coord_label(children)
            return nonterminal(lbl)
        else:
            return Terminal(token.deprel, token)
    elif token.pos == "NN" or token.pos == "PN" or token.pos == "PM":
        if starts_with_wh(token):
            # "vars mamma" etc
            return nonterminal("NP-wh")
        else:
            return nonterminal("NP")
    elif token.pos == "PP":
        if len(children) == 0:
            return Terminal(token.deprel, token)
        if any(c.fun == "UA" for c in children):
            return nonterminal("SBAR")
        elif wh_after_prep(token):
            # "i vilken" etc
            return nonterminal("PrP-wh")
        else:
            return nonterminal("PrP")
    elif token.pos == "SN":
        if children > 0:
            return nonterminal("SBAR")
        else:
            return Terminal(token.deprel, token)
    elif token.pos == "VB":
        if has_subject(token):
            if starts_with_wh(token):
                if is_attributive_subclause(token):
                    label = "S-wh"
                else:
                    # too unreliable...
                    label = "S-wh"
            else:
                label = "S"
        elif "IMP" in token.msd:
            label = "S-imp"
        elif "SUP" in token.msd:
            label = "VP-sup"
        else:
            ie = find_first_by_pos(token.deps, "IE")
            if ie and ie.dephead == token and ie.position < token.position:
                label = "VP-att"
            elif "INF" in token.msd:
                label = "VP-inf"
            else:
                label = "VP-fin"
        return nonterminal(label)
    elif token.pos == "IE":
        vbc = find_first_by_pos(token.deps, "VB")
        if vbc:
            ds2 = token.deps + vbc.deps
            ds2.remove(vbc)
            c_ie = Terminal("IM-att", token)
            children = [convert(c) for c in ds2] + [c_ie]
            sort_by_head_pos(children)
            head = Terminal("HEAD", vbc)
            add_head(children, head)
            return Nonterminal("VP-att", token.deprel, head, children)
        elif children:
            return nonterminal("XX")
        else:
            return Terminal(token.deprel, token)
    elif token.pos == "JJ" or token.pos == "PC":
        return nonterminal("ADJP")
    elif token.pos == "AB":
        return nonterminal("ADVP")
    elif token.pos == "HP":
        return nonterminal("NP-wh")
    elif token.pos == "HA":
        return nonterminal("ADVP-wh")
    elif token.pos == "RG":
        return nonterminal("QP")
    elif children:
        return nonterminal("XX")
    else:
        return Terminal(token.deprel, token)


### The following functions belong to convert()

def add_head(l, h):
    hp = h.head_position()
    for ix in range(len(l)):
        if hp < l[ix].head_position():
            l.insert(ix, h)
            return
    l.append(h)


def get_coord_label(l):
    for c in l:
        if isinstance(c, Nonterminal) and c.fun == "CJ":
            return c.label
    for c in l:
        if c.fun == "MS" and isinstance(c, Nonterminal):
            return c.label
    return "XX"


def has_subject(token):
    for c in token.deps:
        if c.deprel in ["SS", "ES", "FS"] and c.pos != "IE":
            return True
    return False


def is_finite(token):
    return ("PRS" in token.msd) or ("PRT" in token.msd)


def find_first_by_pos(deps, pos):
    for d in deps:
        if d.pos == pos:
            return d
    return None


def starts_with_wh(token):
    for c in token.deps:
        if (c.position < token.position) and (c.pos[0] == 'H'):
            return True
        if c.pos not in ['MAD', 'MID', 'PAD']:
            return False
    return False


def is_attributive_subclause(token):
    # we try to detect attributive subordinate clauses even though
    # they are often inconsistently handled by MaltParser...
    if token.deprel == "ET":
        return True
    for c in token.deps:
        if c.pos[0] == 'H' and c.word.lower() == "som":
            return True
    return False


def wh_after_prep(token):
    for c in token.deps:
        if c.pos == 'HP' and c.position > token.position and len(c.deps) == 0:
            return True
    return False


def sort_by_head_pos(l):
    l.sort(key=lambda x: x.head_position())


##############################################################################

if __name__ == '__main__':
    util.run.main(annotate)
