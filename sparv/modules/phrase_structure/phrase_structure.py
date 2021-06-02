"""Module for converting Mamba-Dep dependencies to phrase structure trees."""

import pprint
from collections import defaultdict

from sparv.api import Annotation, Output, annotator, get_logger

logger = get_logger(__name__)



@annotator("Convert Mamba-Dep dependencies into phrase structure", language=["swe"])
def annotate(out_phrase: Output = Output("phrase_structure.phrase", description="Phrase segments"),
             out_phrase_name: Output = Output("phrase_structure.phrase:phrase_structure.name",
                                              description="Phrase names"),
             out_phrase_func: Output = Output("phrase_structure.phrase:phrase_structure.func",
                                              description="Phrase functions"),
             token: Annotation = Annotation("<token>"),
             word: Annotation = Annotation("<token:word>"),
             sentence: Annotation = Annotation("<sentence>"),
             pos: Annotation = Annotation("<token:pos>"),
             msd: Annotation = Annotation("<token:msd>"),
             ref: Annotation = Annotation("<token:ref>"),
             dephead_ref: Annotation = Annotation("<token:dephead_ref>"),
             deprel: Annotation = Annotation("<token:deprel>")):
    """Annotate sentence with phrase structures."""
    sentences, _orphans = sentence.get_children(word)
    token_annotations = list(ref.read_attributes([ref, word, pos, msd, dephead_ref, deprel]))
    token_spans = list(token.read_spans())

    def get_token_span(index):
        return token_spans[index]

    nodes = []

    for s in sentences:
        tokenlist = [Token(None)]
        for token_index in s:
            token = token_annotations[token_index]
            tokenlist.append(Token(token))

        # Get PS tree
        sen = Sentence(tokenlist)
        if not sen.is_cyclic():
            tree = convert_sentence(sen).top.to_tree_str()
            # print(pprint.pformat(tree), file=sys.stderr)

            # Make nodes
            children = flatten_tree(tree[1], [])
            logger.debug("\n\nSENTENCE:")
            position = 0
            open_elem_stack = []
            for child in children:
                if not child[0].startswith("WORD:"):
                    start_pos = get_token_span(s[position])[0]
                    open_elem_stack.append(child + (start_pos,))
                    logger.debug(f"<phrase name={child[0]} func={child[1]}> {s[position]}")
                else:
                    # Close nodes
                    while open_elem_stack[-1][2] == child[2]:
                        start_pos = open_elem_stack[-1][3]
                        end_pos = get_token_span(s[position - 1])[1]
                        nodes.append(((start_pos, end_pos), open_elem_stack[-1][0], open_elem_stack[-1][1]))
                        logger.debug(f"</phrase name={open_elem_stack[-1][0]} func={open_elem_stack[-1][1]}> {start_pos}-{end_pos}")
                        open_elem_stack.pop()
                    position += 1
                    logger.debug(f"   {child[0][5:]}")

            # Close remaining open nodes
            end_pos = get_token_span(s[-1])[1]
            for elem in reversed(open_elem_stack):
                start_pos = elem[3]
                nodes.append(((start_pos, end_pos), elem[0], elem[1]))
                logger.debug(f"</phrase name={elem[0]} func={elem[1]}> {start_pos}-{end_pos}")

    # Sort nodes
    sorted_nodes = sorted(nodes)

    # Write annotations
    out_phrase.write([i[0] for i in sorted_nodes])
    out_phrase_name.write([i[1] for i in sorted_nodes])
    out_phrase_func.write([i[2] for i in sorted_nodes])


def log_output(f):
    """
    Make a function write its input when called and output when finished.

    >>> @log_output
    ... def test(x, *ys, **kws):
    ...     return kws.get("c",0)+sum(x*y for y in ys)
    >>> test(2, 3, 4, c=1) == 1+2*3+2*4
    test(2, 3, 4, {"c": 1})
    test(2, 3, 4, {"c": 1}) = 15
    True
    """
    def g(*args, **kws):
        call = f.__name__ + pprint.pformat(args + (kws, ))
        print(call)
        res = f(*args, **kws)
        print(call + " = " + pprint.pformat(res))
        return res
    return g


# @log_output
def flatten_tree(tree, children=[]):
    """Flatten a nested tree structure into a list of children."""
    for child in tree:
        if has_children(child):
            flatten_tree(child, children)
        else:
            children.append(child)
    return children


def has_children(elem):
    """Check if elem has any child elements."""
    if type(elem) == list:
        return True
    try:
        for child in elem:
            if type(child) == list:
                return True
    except TypeError:
        return False
    return False


##############################################################################
# from file "trees.py" (Richard Johansson):


class Token:
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
            self.ref = "0"
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
            return "WORD:" + self.word

    def is_cyclic(self):
        seen = {}
        n = self
        while n:
            if n.position in seen:
                return True
            seen[n.position] = 1
            n = n.dephead
        return False


class Sentence:
    """Sentence containing a list of token objects."""

    def __init__(self, token_list):
        self.tokens = token_list
        table = {}
        for t in token_list:
            table[t.ref] = t
        for n in token_list:
            if n.deprel:
                if n.depheadid:
                    n.dephead = table[n.depheadid]
                else:
                    n.dephead = self.tokens[0]
                n.dephead.deps.append(n)

    def length(self):
        return len(self.tokens)

    def __str__(self):
        return "(Sen: " + str(self.tokens) + ")"

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
# from file "to_const.py" (Richard Johansson):


class Terminal:
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
        return str(self.t), str(self.fun), n

    def to_word_str(self):
        if self.t.pos == "PM":
            return self.t.word
        else:
            return self.t.word.lower()

    def length(self):
        return 1

    def is_punctuation(self):
        return self.t.pos in ["MAD", "MID", "PAD"]

    def is_name(self):
        return self.t.pos == "PM"

    def add_starts(self, starts):
        starts[self.start].append(self)

    def set_parents(self):
        pass


class Nonterminal:
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
        wordlist = []
        for c in self.children:
            wordlist.append(c.to_word_str())
        return " ".join(wordlist)

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


class PSTree:
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
    """
    Do a recursive analysis of sen.

    Return a PSTree object (phrase structure tree) if the analysis was successful.
    """
    return PSTree(convert(sen.tokens[0]))


def convert(token):
    """Recursively analyse the phrase structure of token."""
    children = [convert(c) for c in token.deps]

    def nonterminal(label):
        head = Terminal("HEAD", token)
        _add_head(children, head)
        return Nonterminal(label, token.deprel, head, children)
    if token.position == 0:
        return Nonterminal("ROOT", "ROOT", token, children)
    elif token.deprel == "HD":
        return Terminal(token.deprel, token)
    elif token.pos == "KN" or token.pos == "MID":
        if children:
            lbl = _get_coord_label(children)
            return nonterminal(lbl)
        else:
            return Terminal(token.deprel, token)
    elif token.pos == "NN" or token.pos == "PN" or token.pos == "PM":
        if _starts_with_wh(token):
            # "vars mamma" etc
            return nonterminal("NP-wh")
        else:
            return nonterminal("NP")
    elif token.pos == "PP":
        if len(children) == 0:
            return Terminal(token.deprel, token)
        if any(c.fun == "UA" for c in children):
            return nonterminal("SBAR")
        elif _wh_after_prep(token):
            # "i vilken" etc
            return nonterminal("PrP-wh")
        else:
            return nonterminal("PrP")
    elif token.pos == "SN":
        if len(children) > 0:
            return nonterminal("SBAR")
        else:
            return Terminal(token.deprel, token)
    elif token.pos == "VB":
        if _has_subject(token):
            if _starts_with_wh(token):
                if _is_attributive_subclause(token):
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
            ie = _find_first_by_pos(token.deps, "IE")
            if ie and ie.dephead == token and ie.position < token.position:
                label = "VP-att"
            elif "INF" in token.msd:
                label = "VP-inf"
            else:
                label = "VP-fin"
        return nonterminal(label)
    elif token.pos == "IE":
        vbc = _find_first_by_pos(token.deps, "VB")
        if vbc:
            ds2 = token.deps + vbc.deps
            ds2.remove(vbc)
            c_ie = Terminal("IM-att", token)
            children = [convert(c) for c in ds2] + [c_ie]
            _sort_by_head_pos(children)
            head = Terminal("HEAD", vbc)
            _add_head(children, head)
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


################################################################################
# Auxiliaries used by convert
################################################################################

def _add_head(in_list, h):
    hp = h.head_position()
    for ix in range(len(in_list)):
        if hp < in_list[ix].head_position():
            in_list.insert(ix, h)
            return
    in_list.append(h)


def _get_coord_label(in_list):
    for c in in_list:
        if isinstance(c, Nonterminal) and c.fun == "CJ":
            return c.label
    for c in in_list:
        if c.fun == "MS" and isinstance(c, Nonterminal):
            return c.label
    return "XX"


def _has_subject(token):
    for c in token.deps:
        if c.deprel in ["SS", "ES", "FS"] and c.pos != "IE":
            return True
    return False


# def _is_finite(token):
#     return ("PRS" in token.msd) or ("PRT" in token.msd)


def _find_first_by_pos(deps, pos):
    for d in deps:
        if d.pos == pos:
            return d
    return None


def _starts_with_wh(token):
    for c in token.deps:
        if (c.position < token.position) and (c.pos[0] == "H"):
            return True
        if c.pos not in ["MAD", "MID", "PAD"]:
            return False
    return False


def _is_attributive_subclause(token):
    # we try to detect attributive subordinate clauses even though
    # they are often inconsistently handled by MaltParser...
    if token.deprel == "ET":
        return True
    for c in token.deps:
        if c.pos[0] == "H" and c.word.lower() == "som":
            return True
    return False


def _wh_after_prep(token):
    for c in token.deps:
        if c.pos == "HP" and c.position > token.position and len(c.deps) == 0:
            return True
    return False


def _sort_by_head_pos(in_list):
    in_list.sort(key=lambda x: x.head_position())
