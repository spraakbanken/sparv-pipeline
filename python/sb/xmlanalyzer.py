# -*- coding: utf-8 -*-

"""
An analyzer for pseuo-XML documents.
Pseudo-XML is almost like XML, but admits overlapping elements.
"""

import os
import re
from collections import defaultdict

import util

def analyze(sources, header="teiheader", encoding=util.UTF8, maxcount=0):
    """Analyze a list of source files, and print statistics.
    The maxcount is a cutoff; we only count information about
    things less frequent than maxcount.
    """
    maxcount = int(maxcount)
    if isinstance(sources, basestring):
        sources = sources.split()

    parser = XMLAnalyzer()
    total_starttime = util.log.starttime
    for source in sources:
        util.log.init()
        util.log.header()
        util.log.info(source)
        with open(source) as F:
            corpus, _ext = os.path.splitext(os.path.basename(source))
            parser.init_parser(corpus, header)
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

class XMLAnalyzer(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.info = {'tag': {'files': defaultdict(dict),
                             'freq': defaultdict(int),
                             'attrs': defaultdict(set),
                             },
                     'header': {'files': defaultdict(dict),
                                'freq': defaultdict(int),
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

    def init_parser(self, corpus, header_elem):
        """This should be called once for every new corpus.
        """
        self.reset()
        self.tagstack = []
        self.inside_header = False
        self.corpus = corpus
        self.header_elem = header_elem

    def pos(self):
        return "{%d:%d}" % self.getpos()

    def err(self, msg, *args):
        """Print an error message, including the current position.
        """
        util.log.error(self.pos() + " " + msg, *args)
        self.info['error'][self.corpus] += 1

    def warn(self, msg, *args):
        """Print a warning message, including the current position.
        """
        util.log.warning(self.pos() + " " + msg, *args)
        self.info['warning'][self.corpus] += 1

    def close(self):
        """This should be called at the end of the file. If in parser mode,
        it saves the corpus text and the annotations to files.
        """
        while self.tagstack:
            t, a = self.tagstack[0]
            self.err("(at EOF) Autoclosing tag </%s>, starting at %s", t, a)
            self.handle_endtag(t)
        HTMLParser.close(self)

    def handle_starttag(self, name, attrs):
        """When we come to a start tag <name attrs=...>, we save
        the name, attrs and anchor on a stack, which we read from
        when the matching closing tag comes along.
        """
        if name == self.header_elem:
            self.inside_header = True

        tag_or_header = 'header' if self.inside_header else 'tag'
        self.info[tag_or_header]['freq'][name] += 1
        self.info[tag_or_header]['files'][name].setdefault(self.corpus, self.getpos())
        for attr, _value in attrs:
            self.info[tag_or_header]['attrs'][name].add(attr)

        # we use a reversed stack (push from the left), which
        # simplifies searching for elements below the top of the stack
        self.tagstack.insert(0, (name, self.pos()))

    def handle_endtag(self, name):
        """When there is a closing tag, we look for the matching open tag
        in the stack. Since we allow overlapping elements, the open tag
        need not be first in the stack.

        We create an edge from the name, start and end anchor, and add it
        to the corresponding annotation. Each xml attr also gets added to
        an annotation. The annotation group depends on the tag name.
        """
        if self.inside_header:
            self.inside_header = (name != self.header_elem)

        # Retrieve the open tag in the tagstack:
        try:
            ix = [t[0] for t in self.tagstack].index(name)
        except ValueError:
            self.err("Closing element </%s>, but it is not open", name)
            return
        
        name, start = self.tagstack.pop(ix)
        if ix > 0:
            overlaps = self.tagstack[:ix]
            end = self.pos()
            self.warn("Tag <%s> at %s - %s, overlapping with %s", name, start, end,
                      ", ".join("<%s> at %s" % (n,s) for (n,s) in overlaps)) 

    def handle_data(self, content):
        """Plain text data are tokenized and each 'token' is added to the text.
        """
        if "&" in content: self.err("XML special character: &")
        if "<" in content: self.err("XML special character: <")
        if ">" in content: self.err("XML special character: >")
        for char in content:
            self.info['char']['freq'][char] += 1
            self.info['char']['files'][char].setdefault(self.corpus, self.getpos())

    def handle_charref(self, name):
        """Character references &#nnn; are translated to unicode and
        added as single tokens.
        """
        entity = '#' + name
        self.info['entity']['freq'][entity] += 1
        self.info['entity']['files'][entity].setdefault(self.corpus, self.getpos())
        if problematic_entity(entity):
            self.err("Control character reference: &%s;", entity)

    def handle_entityref(self, name):
        """Entity refs &bullet; are lookep up in a database and
        added as single tokens.
        """
        if self.info:
            self.info['entity']['freq'][name] += 1
            self.info['entity']['files'][name].setdefault(self.corpus, self.getpos())
        if problematic_entity(name):
            self.err("Unknown HTML entity: &%s;", name)

    def handle_comment(self, comment):
        """XML comments are added as annotations themselves.
        """
        if "--" in comment or comment.endswith('-'):
            self.err("Comment contains '--' or ends with '-'")
        if self.inside_header:
            self.warn("Comment in TEI header: %d characters wide", len(comment))
        else:
            self.warn("Comment: %d characters wide", len(comment))

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
    stat_tags(result['tag'], maxcount, "Body tags")
    stat_tags(result['header'], maxcount, "Header tags")
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

def stat_chars(charinfo, maxcount, title="Characters"):
    """Statistics about the characters in the corpus.
    """
    chars = charinfo['freq']
    if not chars: return
    print
    print "%-60sFiles" % title
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

def stat_entities(entinfo, maxcount, title="Entities"):
    """Statistics about the entities in the corpus.
    """
    entities = entinfo['freq']
    if not entities: return
    print
    print "%-60sFiles" % title
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

def stat_tags(taginfo, maxcount, title="Tags"):
    """Statistics about the xml tags in the corpus.
    """
    tags = taginfo['freq']
    if not tags: return
    print
    print "%-30s%-30sFiles" % (title, "Attributes")
    print "-" * 100
    for tag, count in items_by_frequency(tags):
        if 0 < maxcount < count: continue
        attrs = " ".join(sorted(taginfo['attrs'][tag]))
        files = strfiles(taginfo['files'][tag])
        print "%8d    %-18s%-30s%s" % (count, "<"+tag+">", attrs, files)
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
    util.run.main(analyze)
