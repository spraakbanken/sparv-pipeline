# -*- coding: utf-8 -*-

"""
A parser for TEI pseuo-XML documents.
Pseudo-XML is almost like XML, but admits overlapping elements.
There are two modes: parsing and analyzing:
- default: parses the document and creates DBM annotations from the XML markup
- analyze: parses the document(s) and prints statistics 
"""

import os
import re
from collections import defaultdict

import util

TEIHEADER = "teiheader"

# this regexp specifies possible tokens, between each token an anchor point is inserted:
REGEXP_TOKEN = re.compile(r"([^\W_\d]+|\d+| +|\s|.)", re.UNICODE)
# note about REGEXP_TOKEN: the first group matches sequences of letters,
# but we cannot use \w directly, since it matches [_\d], so we have to
# exclude these in the first group above, hence [^\W_\d];
# idea taken from http://stackoverflow.com/questions/1673749

# TODO: lägg till metadata-annoteringar, ungefär som i obsolete/tei_parser.py

def parse(source, prefix, text, elements, annotations, skip=(), overlap=(), encoding=util.UTF8):
    """Parse one pseudo-xml source file, into the specified corpus."""
    if isinstance(elements, basestring): elements = elements.split()
    if isinstance(annotations, basestring): annotations = annotations.split()
    if isinstance(skip, basestring): skip = skip.split()
    if isinstance(overlap, basestring): overlap = overlap.split()
    assert len(elements) == len(annotations), "elements and annotations must be the same length"

    def elsplit(elem):
        tag, _, attr = elem.partition(":")
        return tag, attr

    elem_annotations = dict((elsplit(elem), annotation)
                            for elemgroup, annotation in zip(elements, annotations)
                            for elem in elemgroup.split("+"))

    skipped_elems = set(elsplit(elem) for elem in skip)
    assert skipped_elems.isdisjoint(elem_annotations), "skip and elements must be disjoint"

    can_overlap = set((t1, t2) for tags in overlap
                      for t1 in tags.split("+") for t2 in tags.split("+") if t1 != t2)

    with open(source) as SRC:
        content = SRC.read().decode(encoding)
    parser = XMLParser(elem_annotations, skipped_elems, can_overlap, prefix, text, len(content))
    parser.feed(content)
    parser.close()


######################################################################

from HTMLParser import HTMLParser

class XMLParser(HTMLParser):
    def __init__(self, elem_annotations, skipped_elems, can_overlap, prefix, textfile, corpus_size):
        HTMLParser.__init__(self)
        self.reset()
        self.tagstack = []
        self.inside_header = False
        self.elem_annotations = elem_annotations
        self.skipped_elems = skipped_elems
        self.can_overlap = can_overlap
        self.prefix = prefix
        self.textfile = textfile
        self.position = 0
        self.pos2anchor = {}
        self.anchor2pos = {}
        self.textbuffer = []
        self.dbs = dict((annot, {}) for annot in elem_annotations.values())
        util.resetIdent(self.prefix, maxidents=corpus_size)

    def pos(self):
        return "{%d:%d} " % self.getpos()

    def close(self):
        """This should be called at the end of the file. If in parser mode,
        it saves the corpus text and the annotations to files.
        """
        while self.tagstack:
            t, _, a = self.tagstack[0]
            util.log.error(self.pos() + "(at EOF) Autoclosing tag </%s>, starting at %s", t, a)
            self.handle_endtag(t)
        self.anchor()

        text = u"".join(self.textbuffer)
        util.write_corpus_text(self.textfile, text, self.pos2anchor)
        for annot, db in self.dbs.iteritems():
            util.write_annotation(annot, db)
        
        HTMLParser.close(self)

    def anchor(self):
        """Return the anchor for the currect position. If there is no
        anchor yet, create one and return it. The anchors are pseudo-random,
        so that we can shuffle the text if we want.
        """
        position = self.position
        try:
            anchor = self.pos2anchor[position]
        except KeyError:
            anchor = self.pos2anchor[position] = util.mkIdent(self.prefix, identifiers=self.anchor2pos)
            self.anchor2pos[anchor] = position
        return anchor
    
    def add_token(self, token):
        """Add a token to the text, creating anchors before and after.
        """
        if token:
            self.anchor()
            self.textbuffer.append(token)
            self.position += len(token)
            self.anchor()

    def handle_starttag(self, name, attrs):
        """When we come to a start tag <name attrs=...>, we save
        the name, attrs and anchor on a stack, which we read from
        when the matching closing tag comes along.
        """
        if name == TEIHEADER or self.inside_header:
            self.inside_header = True
            return

        elem_attrs = attrs + [("", "")]
        for attr, value in elem_attrs:
            elem = (name, attr)
            if not (elem in self.elem_annotations or elem in self.skipped_elems):
                self.skipped_elems.add(elem)
                if attr:
                    util.log.warning(self.pos() + "Skipping XML element <%s %s=%s>", name, attr, value)
                elif not attrs:
                    util.log.warning(self.pos() + "Skipping XML element <%s>", name)

        # we use a reversed stack (push from the left), to simplify
        # searching for elements below the top of the stack:
        self.tagstack.insert(0, (name, self.anchor(), elem_attrs))

    def handle_endtag(self, name):
        """When there is a closing tag, we look for the matching open tag
        in the stack. Since we allow overlapping elements, the open tag
        need not be first in the stack.

        We create an edge from the name, start and end anchor, and add it
        to the corresponding annotation. Each xml attr also gets added to
        an annotation. The annotation group depends on the tag name.
        """
        if self.inside_header:
            self.inside_header = (name != TEIHEADER)
            return
        # Retrieve the open tag in the tagstack:
        try:
            ix = [t[0] for t in self.tagstack].index(name)
        except ValueError:
            util.log.error(self.pos() + "Closing element </%s>, but it is not open", name)
            return

        name, start, attrs = self.tagstack.pop(ix)
        end = self.anchor()
        overlaps = [t[:2] for t in self.tagstack[:ix]
                    if (name, t[0]) not in self.can_overlap]
        if overlaps:
            overlapping_elems = ["<%s> [%s:]" % t for t in overlaps]
            util.log.warning(self.pos() + "Tag <%s> [%s:%s], overlapping with %s",
                             name, start, end, ", ".join(overlapping_elems)) 

        edge = util.mkEdge(name, (start, end))
        for attr, value in attrs:
            try:
                annotation = self.elem_annotations[name, attr]
                self.dbs[annotation][edge] = value
            except KeyError:
                pass

    def handle_data(self, content):
        """Plain text data are tokenized and each 'token' is added to the text."""
        if "&" in content: self.log(util.log.error, "XML special character: &")
        if "<" in content: self.log(util.log.error, "XML special character: <")
        if ">" in content: self.log(util.log.error, "XML special character: >")
        if self.position == 0 and isinstance(content, unicode):
            content = content.lstrip(u"\ufeff")
        if self.inside_header:
            return
        for token in REGEXP_TOKEN.split(content):
            self.add_token(token)

    def handle_charref(self, name):
        """Character references &#nnn; are translated to unicode."""
        entity = '#' + name
        if problematic_entity(entity):
            self.log(util.log.error, "Control character reference: &%s;", entity)
            return
        if self.inside_header:
            return
        if name.startswith('x'):
            code = int(name[1:], 16)
        else:
            code = int(name)
        self.add_token(unichr(code))

    def handle_entityref(self, name):
        """Entity refs &bullet; are lookep up in a database and
        added as single tokens.
        """
        if problematic_entity(name):
            self.log(util.log.error, "Unknown HTML entity: &%s;", name)
            return
        if self.inside_header:
            return
        code = html_entities[name]
        self.add_token(unichr(code))

    def handle_comment(self, comment):
        """XML comments are added as annotations themselves."""
        if "--" in comment or comment.endswith('-'):
            self.log(util.log.error, "Comment contains '--' or ends with '-'")
        if self.inside_header:
            self.log(util.log.warning, "[SKIPPING] Comment in TEI header")
            return
        self.log(util.log.warning, "Comment: %d characters wide", len(comment))
        self.handle_starttag('comment', [('value', comment)])
        self.handle_endtag('comment')

    def handle_pi(self, data):
        """XML processing instructions are not allowed,
        except for the single <?XML...> on the first line.
        """
        if data.startswith(u'xml ') and data.endswith(u'?'):
            if self.getpos() != (1,0):
                self.log(util.log.error, "XML declaration not first in file")
        else:
            self.log(util.log.error, "Unknown processing instruction: <?%s>", data)

    def handle_decl(self, decl):
        """SGML declarations <!...> are not allowed."""
        self.log(util.log.error, "SGML declaration: <!%s>", decl)


######################################################################
# problematic html entities

def problematic_entity(name):
    if name.startswith('#x'):
        return is_control_code(int(name[2:], 16))
    elif name.startswith('#'):
        return is_control_code(int(name[1:]))
    else:
        return name not in html_entities

def is_control_code(code):
    return code < 0x20 or 0x80 <= code < 0xA0


######################################################################
# html entities

import htmlentitydefs

# Entities defined in HTML Latin-1 (ISO 8859-1)
html_entities = htmlentitydefs.name2codepoint

# Entity defined in XML
html_entities['apos'] = ord("'")

# Additional entities defined in HTML Latin-2 (ISO 8859-2)
html_entities.update(
    Aogon   = 260,  # capital letter A with ogonek
    breve   = 728,  # breve (spacing accent)
    Lstrok  = 321,  # capital letter L with stroke
    Lcaron  = 317,  # capital letter L with caron
    Sacute  = 346,  # capital letter S with acute accent
    Scaron  = 352,  # capital letter S with caron
    Scedil  = 350,  # capital letter S with cedil
    Tcaron  = 356,  # capital letter T with caron
    Zacute  = 377,  # capital letter Z with acute accent
    Zcaron  = 381,  # capital letter Z with caron
    Zdot    = 379,  # capital letter Z with dot above
    aogon   = 261,  # small letter a with ogonek
    ogon    = 731,  # small letter o with ogonek
    lstrok  = 322,  # small letter l with stroke
    lcaron  = 318,  # small letter l with caron
    sacute  = 347,  # small letter s with acute accent
    caron   = 711,  # caron (spacing accent)
    scaron  = 353,  # small letter s with caron
    scedil  = 351,  # small letter s with cedil
    tcaron  = 357,  # small letter t with caron
    zacute  = 378,  # small letter z with acute accent
    dblac   = 733,  # double accute (spacing accent)
    zcaron  = 382,  # small letter z with caron
    zdot    = 380,  # small letter z with dot above
    Racute  = 340,  # capital letter R with acute accent
    Abreve  = 258,  # capital letter A with breve
    Lacute  = 313,  # capital letter L with acute accent
    Cacute  = 262,  # capital letter C with acute accent
    Ccaron  = 268,  # capital letter C with caron
    Eogon   = 280,  # capital letter E with ogonek
    Ecaron  = 282,  # capital letter E with caron
    Dcaron  = 270,  # capital letter D with caron
    Dstrok  = 272,  # capital letter D with stroke
    Nacute  = 323,  # capital letter N with acute accent
    Ncaron  = 327,  # capital letter N with caron
    Odblac  = 336,  # capital letter O with double accute accent
    Rcaron  = 344,  # capital letter R with caron
    Uring   = 366,  # capital letter U with ring
    Udblac  = 368,  # capital letter U with double accute accent
    Tcedil  = 354,  # capital letter T with cedil
    racute  = 341,  # small letter r with acute accent
    abreve  = 259,  # small letter a with breve
    lacute  = 314,  # small letter l with acute accent
    cacute  = 263,  # small letter c with acute accent
    ccaron  = 269,  # small letter c with caron
    eogon   = 281,  # small letter e with ogonek
    ecaron  = 283,  # small letter e with caron
    dcaron  = 271,  # small letter d with caron
    dstrok  = 273,  # small letter d with stroke
    nacute  = 324,  # small letter n with acute accent
    ncaron  = 328,  # small letter n with caron
    odblac  = 337,  # small letter o with double acute accent
    rcaron  = 345,  # small letter r with caron
    uring   = 367,  # small letter u with ring
    udblac  = 369,  # small letter u with double acute accent
    tcedil  = 355,  # small letter t with cedil
    dot     = 729,  # dot (spacing accent)
    cir     = 9675, # white circle
    )


######################################################################

if __name__ == '__main__':
    util.run.main(parse)
