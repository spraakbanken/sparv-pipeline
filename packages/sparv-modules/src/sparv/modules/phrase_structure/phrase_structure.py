"""Module for converting Mamba-Dep dependencies to phrase structure trees."""

from __future__ import annotations

from collections import defaultdict

from sparv.api import Annotation, Output, annotator, get_logger

logger = get_logger(__name__)


@annotator("Convert Mamba-Dep dependencies into phrase structure", language=["swe"])
def annotate(
    out_phrase: Output = Output("phrase_structure.phrase", description="Phrase segments"),
    out_phrase_name: Output = Output("phrase_structure.phrase:phrase_structure.name", description="Phrase names"),
    out_phrase_func: Output = Output("phrase_structure.phrase:phrase_structure.func", description="Phrase functions"),
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
    pos: Annotation = Annotation("<token:pos>"),
    msd: Annotation = Annotation("<token:msd>"),
    ref: Annotation = Annotation("<token:ref>"),
    dephead_ref: Annotation = Annotation("<token:dephead_ref>"),
    deprel: Annotation = Annotation("<token:deprel>"),
) -> None:
    """Annotate sentence with phrase structures.

    Args:
        out_phrase: Output annotation for phrase segments.
        out_phrase_name: Output annotation for phrase names.
        out_phrase_func: Output annotation for phrase functions.
        token: Token annotation.
        word: Word annotation.
        sentence: Sentence annotation.
        pos: POS annotation.
        msd: MSD annotation.
        ref: Token reference annotation.
        dephead_ref: Dependency head reference annotation.
        deprel: Dependency relation annotation.
    """
    sentences, _orphans = sentence.get_children(word)
    token_annotations = list(ref.read_attributes([ref, word, pos, msd, dephead_ref, deprel]))
    token_spans = list(token.read_spans())

    nodes = []

    for s in sentences:
        if len(s) == 1:
            # Skip single token sentences
            continue
        tokenlist = [Token(None)]
        for token_index in s:
            token = token_annotations[token_index]
            tokenlist.append(Token(token))

        # Get PS tree
        sen = Sentence(tokenlist)
        if not sen.is_cyclic():
            tree = convert_sentence(sen).top.to_tree_str()

            # Make nodes
            children = flatten_tree(tree[1])
            logger.debug("\n\nSENTENCE:")
            position = 0
            open_elem_stack = []
            for child in children:
                if not child[0].startswith("WORD:"):
                    start_pos = token_spans[s[position]][0]
                    open_elem_stack.append((*child, start_pos))
                    logger.debug("<phrase name=%s func=%s> %s", child[0], child[1], s[position])
                else:
                    # Close nodes
                    while open_elem_stack[-1][2] == child[2]:
                        start_pos = open_elem_stack[-1][3]
                        end_pos = token_spans[s[position - 1]][1]
                        nodes.append(((start_pos, end_pos), open_elem_stack[-1][0], open_elem_stack[-1][1]))
                        logger.debug(
                            "</phrase name=%s func=%s> %d-%d",
                            open_elem_stack[-1][0],
                            open_elem_stack[-1][1],
                            start_pos,
                            end_pos,
                        )
                        open_elem_stack.pop()
                    position += 1
                    logger.debug("   %s", child[0][5:])

            # Close remaining open nodes
            end_pos = token_spans[s[-1]][1]
            for elem in reversed(open_elem_stack):
                start_pos = elem[3]
                nodes.append(((start_pos, end_pos), elem[0], elem[1]))
                logger.debug("</phrase name=%s func=%s> %d-%d", elem[0], elem[1], start_pos, end_pos)

    # Sort nodes
    sorted_nodes = sorted(nodes)

    # Write annotations
    out_phrase.write([i[0] for i in sorted_nodes])
    out_phrase_name.write([i[1] for i in sorted_nodes])
    out_phrase_func.write([i[2] for i in sorted_nodes])


def flatten_tree(tree: list) -> list:
    """Flatten a nested tree structure into a list of children.

    Args:
        tree: A nested list structure representing a tree.

    Returns:
        A flat list of children.
    """
    children = []
    for child in tree:
        if has_children(child):
            children.extend(flatten_tree(child))
        else:
            children.append(child)
    return children


def has_children(elem: list | tuple) -> bool:
    """Return True if elem has any child elements."""
    if isinstance(elem, list):
        return True
    try:
        for child in elem:
            if isinstance(child, list):
                return True
    except TypeError:
        return False
    return False


##############################################################################
# from file "trees.py" (Richard Johansson):


class Token:
    """Token containing a list of attributes."""

    def __init__(self, t: tuple | None) -> None:
        """Initialize a token with attributes."""
        if t:
            self.word = t[1]
            self.pos = t[2]
            self.msd = t[3]
            self.ref = t[0]
            self.position = int(self.ref)
            self.deprel = t[5]
            self.depheadid = t[4]
            self.dephead: Token | None = None
        else:
            self.ref = "0"
            self.position = 0
            self.deprel = ""
            self.word = ""
            self.pos = ""
            self.msd = ""
            self.dephead: Token | None = None
        self.deps: list[Token] = []

    def get_deps_by_rel(self, r: str) -> list:
        """Get dependencies with a specific relation.

        Args:
            r: The relation to filter by.

        Returns:
            A list of dependencies with the specified relation.
        """
        return [n for n in self.deps if n.deprel == r]

    def __str__(self) -> str:
        """Return a string representation of the token."""
        if self.position == 0:
            return "(ROOT)"
        return f"WORD:{self.word}"

    def is_cyclic(self) -> bool:
        """Return True if the token has a cyclic dependency."""
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

    def __init__(self, token_list: list[Token]) -> None:
        """Initialize a sentence with a list of tokens."""
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

    def length(self) -> int:
        """Return the number of tokens in the sentence."""
        return len(self.tokens)

    def __str__(self) -> str:
        """Return a string representation of the sentence."""
        return "(Sen: " + str(self.tokens) + ")"

    def to_tree_str(self) -> str:
        """Return a string representation of the sentence in tree format."""
        return "\n".join([str(t) for t in self.tokens])

    def words(self) -> str:
        """Return a string of words in the sentence."""
        words = [n.word for n in self.tokens if n.word]
        return " ".join(words)

    def is_cyclic(self) -> bool:
        """Return True if the sentence has a cyclic dependency."""
        return any(n.is_cyclic() for n in self.tokens)


##############################################################################
# from file "to_const.py" (Richard Johansson):


class Terminal:
    """Class representing a terminal node of a phrase structure tree."""

    def __init__(self, fun: str, token: Token) -> None:
        """Initialize a terminal node with a function and token."""
        self.fun = fun
        self.t = token
        self.start = self.t.position
        self.end = self.start + 1
        self.label = self.t.pos
        self.parent: Nonterminal | Terminal | None = None

    def head_position(self) -> int:
        """Return the position of the token."""
        return self.t.position

    def to_tree_str(self, n: int = 0) -> tuple:
        """Return a tuple representation of the terminal node in tree format."""
        return str(self.t), str(self.fun), n

    def to_word_str(self) -> str:
        """Return the word representation of the terminal node."""
        if self.t.pos == "PM":
            return self.t.word
        return self.t.word.lower()

    @staticmethod
    def length() -> int:
        """Return the length of the terminal node (always 1)."""
        return 1

    def is_punctuation(self) -> bool:
        """Check if the token is a punctuation.

        Returns:
            True if the token is a punctuation, False otherwise.
        """
        return self.t.pos in {"MAD", "MID", "PAD"}

    def is_name(self) -> bool:
        """Check if the token is a name.

        Returns:
            True if the token is a name, False otherwise.
        """
        return self.t.pos == "PM"

    def add_starts(self, starts: dict) -> None:
        """Add the terminal node to the starts dictionary."""
        starts[self.start].append(self)

    def set_parents(self) -> None:
        """Set the parent of the terminal node (does nothing)."""


class Nonterminal:
    """Class representing a non-terminal node of a phrase structure tree."""

    def __init__(
        self,
        label: str,
        fun: str,
        headchild: Nonterminal | Terminal,
        children: list[Nonterminal | Terminal],
    ) -> None:
        """Initialize a non-terminal node."""
        self.label = label
        self.fun = fun
        self.headchild = headchild
        self.children = children
        self.start = min(c.start for c in self.children)
        self.end = max(c.end for c in self.children)
        self.parent: Nonterminal | Terminal | None = None

    def head_position(self) -> int:
        """Return the position of the head child."""
        return self.headchild.head_position()

    def to_tree_str(self, n: int = 0) -> list:
        """Return a representation of the non-terminal node and its children."""
        parent = (str(self.label), str(self.fun), n)
        return [parent] + [c.to_tree_str(n + 2) for c in self.children]

    def to_word_str(self) -> str:
        """Return a string representation of the non-terminal node and its children."""
        wordlist = [c.to_word_str() for c in self.children]
        return " ".join(wordlist)

    def length(self) -> int:
        """Return the length of the non-terminal node (sum of lengths of children)."""
        out = 0
        for c in self.children:
            out += c.length()
        return out

    def is_punctuation(self) -> bool:
        """Return True if the non-terminal node has only one child and that child is a punctuation."""
        if len(self.children) > 1:
            return False
        return self.children[0].is_punctuation()

    @staticmethod
    def is_name() -> bool:
        """Return False as non-terminal nodes are not names."""
        return False

    def add_starts(self, starts: dict) -> None:
        """Add the non-terminal node to the starts dictionary."""
        starts[self.start].append(self)
        for c in self.children:
            c.add_starts(starts)

    def set_parents(self) -> None:
        """Set the parent of the non-terminal node for all children recursively."""
        for c in self.children:
            c.parent = self
            c.set_parents()


class PSTree:
    """Class representing a phrase structure tree."""

    def __init__(self, top: Nonterminal) -> None:
        """Initialize a phrase structure tree with a top node."""
        self.top = top
        self.starts = defaultdict(list)
        self.top.add_starts(self.starts)
        self.top.set_parents()

    def length(self) -> int:
        """Return the length of the phrase structure tree."""
        return self.top.length()

    def to_tree_str(self) -> list:
        """Return a representation of the phrase structure tree."""
        return self.top.to_tree_str()


def convert_sentence(sentence: Sentence) -> PSTree:
    """Do a recursive analysis of a sentence.

    Args:
        sentence: A Sentence object containing a list of tokens.

    Returns:
        A phrase structure tree object representing the sentence.
    """
    return PSTree(convert(sentence.tokens[0]))


def convert(token: Token) -> Nonterminal | Terminal:
    """Recursively analyse the phrase structure of token.

    Args:
        token: A Token object to analyse (including its dependencies).

    Returns:
        A Nonterminal or Terminal object representing the phrase structure.
    """
    children = [convert(c) for c in token.deps]

    def nonterminal(label: str) -> Nonterminal:
        """Return a non-terminal node with the given label."""
        head = Terminal("HEAD", token)
        _add_head(children, head)
        return Nonterminal(label, token.deprel, head, children)

    if token.position == 0:
        return Nonterminal("ROOT", "ROOT", None, children)
    if token.deprel == "HD":
        return Terminal(token.deprel, token)
    if token.pos in {"KN", "MID"}:
        if children:
            lbl = _get_coord_label(children)
            return nonterminal(lbl)
        else:  # noqa: RET505
            return Terminal(token.deprel, token)
    if token.pos in {"NN", "PN", "PM"}:
        if _starts_with_wh(token):
            # "vars mamma" etc
            return nonterminal("NP-wh")
        else:  # noqa: RET505
            return nonterminal("NP")
    if token.pos == "PP":
        if len(children) == 0:
            return Terminal(token.deprel, token)
        if any(c.fun == "UA" for c in children):
            return nonterminal("SBAR")
        if _wh_after_prep(token):
            # "i vilken" etc
            return nonterminal("PrP-wh")
        else:  # noqa: RET505
            return nonterminal("PrP")
    if token.pos == "SN":
        if len(children) > 0:
            return nonterminal("SBAR")
        else:  # noqa: RET505
            return Terminal(token.deprel, token)
    if token.pos == "VB":
        if _has_subject(token):
            if _starts_with_wh(token):
                if _is_attributive_subclause(token):  # noqa: SIM108
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
    if token.pos == "IE":
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
        elif children:  # noqa: RET505
            return nonterminal("XX")
        else:
            return Terminal(token.deprel, token)
    elif token.pos in {"JJ", "PC"}:
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


def _add_head(in_list: list[Terminal | Nonterminal], h: Terminal) -> None:
    """Add a head to the list of children based on its head position.

    Args:
        in_list: A list of children (Terminal or Nonterminal).
        h: The head to be added.
    """
    hp = h.head_position()
    for ix in range(len(in_list)):
        if hp < in_list[ix].head_position():
            in_list.insert(ix, h)
            return
    in_list.append(h)


def _get_coord_label(in_list: list[Terminal | Nonterminal]) -> str:
    """Get the label for a coordinate structure.

    Args:
        in_list: A list of children (Terminal or Nonterminal).

    Returns:
        The label for the coordinate structure.
    """
    for c in in_list:
        if isinstance(c, Nonterminal) and c.fun == "CJ":
            return c.label
    for c in in_list:
        if c.fun == "MS" and isinstance(c, Nonterminal):
            return c.label
    return "XX"


def _has_subject(token: Token) -> bool:
    """Return True if the token has a subject."""
    return any(c.deprel in {"SS", "ES", "FS"} and c.pos != "IE" for c in token.deps)


# def _is_finite(token):
#     return ("PRS" in token.msd) or ("PRT" in token.msd)


def _find_first_by_pos(deps: list[Token], pos: str) -> Token | None:
    """Find the first Token in a list of dependencies with a specific POS tag.

    Args:
        deps: A list of Token objects.
        pos: The POS tag to search for.

    Returns:
        The first dependency with the specified POS tag, or None if not found.
    """
    for d in deps:
        if d.pos == pos:
            return d
    return None


def _starts_with_wh(token: Token) -> bool:
    """Return True if the token has a dependent which is interrogative and comes before it."""
    for c in token.deps:
        if (c.position < token.position) and (c.pos[0] == "H"):
            return True
        if c.pos not in {"MAD", "MID", "PAD"}:
            return False
    return False


def _is_attributive_subclause(token: Token) -> bool:
    """Check if the token is part of an attributive subordinate clause.

    We try to detect attributive subordinate clauses even though they are often inconsistently handled by MaltParser.

    Args:
        token: A Token object to check.

    Returns:
        True if the token is part of an attributive subordinate clause, False otherwise.
    """
    if token.deprel == "ET":
        return True
    return any(c.pos[0] == "H" and c.word.lower() == "som" for c in token.deps)


def _wh_after_prep(token: Token) -> bool:
    return any(c.pos == "HP" and c.position > token.position and len(c.deps) == 0 for c in token.deps)


def _sort_by_head_pos(in_list: list) -> None:
    in_list.sort(key=lambda x: x.head_position())
