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
import util.teidata as TEI

# TODO: lägg till metadata-annoteringar, ungefär som i obsolete/tei_parser.py

# A mapping with the TEI elements for each annotation type
# Each annotation type creates a directory below the corpus annotation directory
TEI_annotation_types = {util.TEXT: TEI.text_elements | TEI.toplevel_elements,
                        util.DIV: TEI.div_elements,
                        util.PARAGRAPH: TEI.paragraph_elements,
                        util.SENTENCE: TEI.sentence_elements,
                        util.LINK: TEI.link_elements,
                        util.TOKEN: TEI.token_elements,
                        util.MARKUP: TEI.markup_elements,
                        util.METADATA: TEI.header_elements,
                        }

# A reverse mapping of the above, from TEI elements to annotation types
TEI_get_annotation_type = dict((elem, typ) for typ in TEI_annotation_types
                               for elem in TEI_annotation_types[typ])


def parse(source, xml, out, anchorprefix, text, encoding=util.UTF8):
    """Parse one pseudo-xml source file, into the specified corpus.
    """
    if isinstance(xml, basestring): xml = xml.split()
    if isinstance(out, basestring): out = out.split()
    assert len(xml) == len(out), "xml and out must be the same length"
    with open(source) as SRC:
        content = SRC.read().decode(encoding)
    parser = TEIParser(xml, out, anchorprefix, text, len(content))
    parser.feed(content)
    parser.close()


def analyze(sources, encoding=util.UTF8, maxcount=0):
    """Analyze a list of source files, and print statistics.
    The maxcount is a cutoff; we only count information about
    things less frequent than maxcount.
    """
    maxcount = int(maxcount)
    if isinstance(sources, basestring):
        sources = sources.split()

    parser = TEIParser()
    parser.init_info()
    total_starttime = util.log.starttime
    for source in sources:
        util.log.init()
        util.log.header()
        util.log.info(source)
        with open(source) as F:
            corpusname, _ext = os.path.splitext(os.path.basename(source))
            parser.init_parser(corpusname)
            for line in F:
                parser.feed(line.decode(encoding))
            parser.close()
        util.log.statistics()
    print
    statistics(parser.info, maxcount)
    print
    # Some hacks for the final statistics:
    util.log.init()
    util.log.starttime = total_starttime
    util.log.line("_")


######################################################################

from HTMLParser import HTMLParser

class TEIParser(HTMLParser):
    # this regexp specifies possible tokens, between each token
    # an anchor point is inserted:
    regexp_token = re.compile(r"([^\W_\d]+|\d+| +|\s|.)", re.UNICODE)
    # note about regexp_token: the first group matches sequences of letters,
    # but we cannot use \w directly, since it matches [_\d], so we have to
    # exclude these in the first group above, hence [^\W_\d];
    # idea taken from http://stackoverflow.com/questions/1673749

    def __init__(self, xml=None, out=None, anchorprefix=None, text=None, corpus_size=None):
        HTMLParser.__init__(self)
        self.info = None
        self.init_parser(xml, out, anchorprefix, text, corpus_size)

    def init_parser(self, xml, out, anchorprefix, text, corpus_size):
        """This should be called once for every new corpus.
        """
        self.reset()
        self.tagstack = []
        self.inside_header = False
        self.xml = xml
        self.out = out
        self.anchorprefix = anchorprefix
        self.textfile = text
        self.position = 0
        self.pos2anchor = {}
        self.anchor2pos = {}
        self.textbuffer = []
        self.dbs = defaultdict(lambda: defaultdict(dict))
        util.resetIdent(self.anchorprefix, maxidents=corpus_size)

    def init_info(self):
        """This should be called if we want to use the parser as an analyzer.
        """
        self.info = {'tag': {'files': defaultdict(dict),
                             'freq': defaultdict(int),
                             'non-tei': defaultdict(int),
                             'attrs': defaultdict(set),
                             },
                     'char': {'files': defaultdict(dict),
                              'freq': defaultdict(int),
                              },
                     'entity': {'files': defaultdict(dict),
                                'freq': defaultdict(int),
                                },
                     'error': defaultdict(int),
                     'warning': defaultdict(int),
                     }

    def err(self, msg, *args):
        """Print an error message, including the current position.
        """
        util.log.error("{%d:%d} " + msg, * self.getpos() + args)
        if self.info:
            self.info['error'][self.base] += 1

    def warn(self, msg, *args):
        """Print a warning message, including the current position.
        """
        util.log.warning("{%d:%d} " + msg, * self.getpos() + args)
        if self.info:
            self.info['warning'][self.base] += 1

    def close(self):
        """This should be called at the end of the file. If in parser mode,
        it saves the corpus text and the annotations to files.
        """
        while self.tagstack:
            t, _, a = self.tagstack[0]
            self.err("(at EOF) Autoclosing tag </%s>, starting at %s", t, a)
            self.handle_endtag(t)
        self.anchor()

        if not self.info:
            text = u"".join(self.textbuffer)
            util.write_corpus_text(self.corpustext, text, self.pos2anchor)
            for name, annot in self.dbs.iteritems():
                for key, db in annot.iteritems():
                    filename = name
                    if key: filename += "." + key
                    util.write_annotation(os.path.join(self.dir, self.base, filename), db)
        
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
            anchor = self.pos2anchor[position] = util.mkIdent(self.base + ".", identifiers=self.anchor2pos)
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

    def handle_starttag(self, tagname, attrs):
        """When we come to a start tag <name attrs=...>, we save
        the name, attrs and anchor on a stack, which we read from
        when the matching closing tag comes along.
        """
        if self.info:
            self.info['tag']['freq'][tagname] += 1
            self.info['tag']['files'][tagname].setdefault(self.base, self.getpos())
            for attr, _value in attrs:
                self.info['tag']['attrs'][tagname].add(attr)

        name = TEI.mixed_case_elements.get(tagname)
        if not name:
            self.warn("Not a TEI element: <%s>", tagname)
            if self.info:
                self.info['tag']['non-tei'][tagname] += 1
            return
        
        if name == TEI.header or self.inside_header:
            self.inside_header = True
            return

        annotation = TEI_get_annotation_type.get(name)
        if annotation in (None, util.METADATA):
            self.warn("TEI element not allowed in body: <%s>", name)
            return

        # we use a reversed stack (push from the left), which
        # simplifies searching for elements below the top of the stack
        self.tagstack.insert(0, (name, self.anchor(), attrs))

    def handle_endtag(self, tagname):
        """When there is a closing tag, we look for the matching open tag
        in the stack. Since we allow overlapping elements, the open tag
        need not be first in the stack.

        We create an edge from the name, start and end anchor, and add it
        to the corresponding annotation. Each xml attr also gets added to
        an annotation. The annotation group depends on the tag name.
        """
        name = TEI.mixed_case_elements.get(tagname)
        if not name:
            self.warn("Not a TEI element: <%s>", tagname)
            if self.info:
                self.info['tag']['non-tei'][tagname] += 1
            return

        if self.inside_header:
            self.inside_header = (name != TEI.header)
            return

        # Retrieve the annotation group:
        annotation = TEI_get_annotation_type.get(name)
        if annotation in (None, util.METADATA):
            self.warn("TEI element not allowed in body: <%s>", name)
            return

        # Retrieve the open tag in the tagstack:
        try:
            ix = [t[0] for t in self.tagstack].index(name)
        except ValueError:
            self.err("Closing element </%s>, but it is not open", name)
            return
        
        name, start, attrs = self.tagstack.pop(ix)
        end = self.anchor()
        if ix > 0:
            overlaps = self.tagstack[:ix]
            if not TEI.can_overlap(name, [t[0] for t in overlaps]):
                self.warn("Tag <%s> [%s:%s], overlapping with %s", name, start, end,
                          ", ".join("<%s> [%s:]" % (t[0], t[1]) for t in overlaps)) 

        span = (start, end)
        edge = util.mkEdge(name, span)
        if not self.info:
            for key, value in attrs + [(None, None)]:
                self.dbs[annotation][key][edge] = value

    def handle_data(self, content):
        """Plain text data are tokenized and each 'token' is added to the text.
        """
        if "&" in content: self.err("XML special character: &")
        if "<" in content: self.err("XML special character: <")
        if ">" in content: self.err("XML special character: >")
        if self.position == 0 and isinstance(content, unicode):
            content = content.replace(u"\ufeff", u"")
        if self.info:
            for char in content:
                self.info['char']['freq'][char] += 1
                self.info['char']['files'][char].setdefault(self.base, self.getpos())
        if self.inside_header:
            return
        for token in self.regexp_token.split(content):
            self.add_token(token)

    def handle_charref(self, name):
        """Character references &#nnn; are translated to unicode and
        added as single tokens.
        """
        entity = '#' + name
        if self.info:
            self.info['entity']['freq'][entity] += 1
            self.info['entity']['files'][entity].setdefault(self.base, self.getpos())
        if problematic_entity(entity):
            self.err("Control character reference: &%s;", entity)
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
        if self.info:
            self.info['entity']['freq'][name] += 1
            self.info['entity']['files'][name].setdefault(self.base, self.getpos())
        if problematic_entity(name):
            self.err("Unknown HTML entity: &%s;", name)
            return
        if self.inside_header:
            return
        code = html_entities[name]
        self.add_token(unichr(code))

    def handle_comment(self, comment):
        """XML comments are added as annotations themselves.
        """
        if "--" in comment or comment.endswith('-'):
            self.err("Comment contains '--' or ends with '-'")
        if self.inside_header:
            self.warn("[SKIPPING] Comment in TEI header")
            return
        self.warn("Comment: %d characters wide", len(comment))

        self.handle_starttag('comment', [('value', comment)])
        self.handle_endtag('comment')

    def handle_pi(self, data):
        """XML processing instructions are not allowed,
        except for the single <?XML...> on the first line.
        """
        if data.startswith(u'xml ') and data.endswith(u'?'):
            if self.getpos() != (1,0):
                self.err("XML declaration not first in file")
        else:
            self.err("Unknown processing instruction: <?%s>", data)

    def handle_decl(self, decl):
        """SGML declarations <!...> are not allowed.
        """
        self.err("SGML declaration: <!%s>", decl)


######################################################################
# statistics

def statistics(result, maxcount):
    print
    print "#" * 100
    print "## Statistics"
    stat_chars(result['char'], maxcount)
    stat_entities(result['entity'], maxcount)
    stat_tags(result['tag'], maxcount)
    stat_errors(result['warning'], result['error'])

def strfiles(files):
    """Return a string of filenames, truncated to at most 3.
    """
    if len(files) > 3:
        (filename, (line, col)) = files.items()[0]
        return "%s:%d, (...and %d more files...)" % (filename, line, len(files)-1)
    else:
        return ", ".join(filename + ":" + str(line)
                         for (filename, (line, col)) in files.items())

def items_by_frequency(freqdist):
    """Sort a dictionary by frequency. Return as a list of pairs.
    """
    frequency = lambda x: x[1]
    return sorted(freqdist.iteritems(), key=frequency, reverse=True)

def stat_chars(charinfo, maxcount):
    """Statistics about the characters in the corpus.
    """
    chars = charinfo['freq']
    if not chars: return
    print
    print "   Count    Code point        Char                          Files"
    print "-" * 100
    for char, count in items_by_frequency(chars):
        if 0 < maxcount < count: continue
        code = ord(char)
        files = strfiles(charinfo['files'][char])
        char = "    CTRL" if is_control_code(code) else "("+char+")"
        encoded = char.encode(util.UTF8)
        extra = len(encoded) - len(char)
        print ("%8d    U+%04X %5d       %-10s%s                   %s" %
               (count, code, code, encoded, " "*extra, files))
    print
    if "&" in chars or "<" in chars or ">" in chars:
        print "NOTE: There are occurrences of & < > in the text"
        print "      Replace with &amp; &lt; &gt;"
        print

def stat_entities(entinfo, maxcount):
    """Statistics about the entities in the corpus.
    """
    entities = entinfo['freq']
    if not entities: return
    print
    print "   Count    Entity name                                     Files"
    print "-" * 100
    problematic = set()
    for name, count in items_by_frequency(entities):
        if problematic_entity(name):
            problematic.add(name)
        if 0 < maxcount < count: continue
        files = strfiles(entinfo['files'][name])
        print u"%8d    %-10s                                      %s" % (count, "&"+name+";", files)
    print
    if problematic:
        print "NOTE: Control characters and unknown entities:", ", ".join(problematic)
        print "      Replace them with better entities"
        print

def stat_tags(taginfo, maxcount):
    """Statistics about the xml tags in the corpus.
    """
    tags = taginfo['freq']
    if not tags: return
    print
    print "   Count    Tag               Attributes                    Files"
    print "-" * 100
    for tag, count in items_by_frequency(tags):
        if 0 < maxcount < count: continue
        attrs = " ".join(sorted(taginfo['attrs'][tag]))
        files = strfiles(taginfo['files'][tag])
        print "%8d    %-18s%-30s%s" % (count, "<"+tag+">", attrs, files)
    print
    if taginfo['non-tei']:
        print "NOTE: The following non-TEI elements were encountered:"
        for tag, count in taginfo['non-tei'].items():
            print "  %10s %d times" % ("<"+tag+">", count)
        print

def stat_errors(warnings, errors):
    """Statistics about the errors and warnings.
    """
    if not errors and not warnings: return
    print
    print "   File                Warnings  Errors"
    print "-" * 100
    for f in sorted(set(warnings) | set(errors)):
        print "   %-20s%6s  %6s" % (f, warnings[f] or "", errors[f] or "")
    print



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
    util.run.main(parse, analyze=analyze)
