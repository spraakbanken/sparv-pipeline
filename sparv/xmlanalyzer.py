# -*- coding: utf-8 -*-

"""
An analyzer for pseudo-XML documents.
Pseudo-XML is almost like XML, but admits overlapping elements.
"""
import os
from collections import defaultdict
import sparv.util as util


def analyze(sources, header="teiheader", encoding=util.UTF8, maxcount=0):
    """Analyze a list of source files, and print statistics.
    The maxcount is a cutoff; we only count information about
    things less frequent than maxcount.
    """
    maxcount = int(maxcount)
    if isinstance(sources, str):
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
                parser.feed(line)
            parser.close()
        util.log.statistics()
    print()
    statistics(parser.info, maxcount)
    print()
    # Some hacks for the final statistics:
    util.log.init()
    util.log.starttime = total_starttime
    util.log.line("_")


######################################################################

from html.parser import HTMLParser


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
                      ", ".join("<%s> at %s" % (n, s) for (n, s) in overlaps))

    def handle_data(self, content):
        """Plain text data are tokenized and each 'token' is added to the text.
        """
        if "&" in content:
            self.err("XML special character: &")
        if "<" in content:
            self.err("XML special character: <")
        if ">" in content:
            self.err("XML special character: >")
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
            if self.getpos() != (1, 0):
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
    print()
    print("#" * 100)
    print("## Statistics")
    stat_chars(result['char'], maxcount)
    stat_entities(result['entity'], maxcount)
    stat_tags(result['tag'], maxcount, "Body tags")
    stat_tags(result['header'], maxcount, "Header tags")
    stat_errors(result['warning'], result['error'])


def strfiles(files):
    """Return a string of filenames, truncated to at most 3.
    """
    if len(files) > 3:
        (filename, (line, col)) = list(files.items())[0]
        return "%s:%d, (...and %d more files...)" % (filename, line, len(files) - 1)
    else:
        return ", ".join(filename + ":" + str(line)
                         for (filename, (line, col)) in list(files.items()))


def items_by_frequency(freqdist):
    """Sort a dictionary by frequency. Return as a list of pairs.
    """
    frequency = lambda x: x[1]
    return sorted(iter(list(freqdist.items())), key=frequency, reverse=True)


def stat_chars(charinfo, maxcount, title="Characters"):
    """Statistics about the characters in the corpus.
    """
    chars = charinfo['freq']
    if not chars:
        return
    print()
    print("%-60sFiles" % title)
    print("-" * 100)
    for char, count in items_by_frequency(chars):
        if 0 < maxcount < count:
            continue
        code = ord(char)
        files = strfiles(charinfo['files'][char])
        char = "    CTRL" if is_control_code(code) else "(" + char + ")"
        encoded = char.encode(util.UTF8)
        extra = len(encoded) - len(char)
        print ("%8d    U+%04X %5d       %-10s%s                   %s" %
               (count, code, code, encoded, " " * extra, files))
    print()
    if "&" in chars or "<" in chars or ">" in chars:
        print("NOTE: There are occurrences of & < > in the text")
        print("      Replace with &amp; &lt; &gt;")
        print()


def stat_entities(entinfo, maxcount, title="Entities"):
    """Statistics about the entities in the corpus.
    """
    entities = entinfo['freq']
    if not entities:
        return
    print()
    print("%-60sFiles" % title)
    print("-" * 100)
    problematic = set()
    for name, count in items_by_frequency(entities):
        if problematic_entity(name):
            problematic.add(name)
        if 0 < maxcount < count:
            continue
        files = strfiles(entinfo['files'][name])
        print(u"%8d    %-10s                                      %s" % (count, "&" + name + ";", files))
    print()
    if problematic:
        print("NOTE: Control characters and unknown entities:", ", ".join(problematic))
        print("      Replace them with better entities")
        print()


def stat_tags(taginfo, maxcount, title="Tags"):
    """Statistics about the xml tags in the corpus.
    """
    tags = taginfo['freq']
    if not tags:
        return
    print()
    print("%-30s%-30sFiles" % (title, "Attributes"))
    print("-" * 100)
    for tag, count in items_by_frequency(tags):
        if 0 < maxcount < count:
            continue
        attrs = " ".join(sorted(taginfo['attrs'][tag]))
        files = strfiles(taginfo['files'][tag])
        print("%8d    %-18s%-30s%s" % (count, "<" + tag + ">", attrs, files))
    print()


def stat_errors(warnings, errors):
    """Statistics about the errors and warnings.
    """
    if not errors and not warnings:
        return
    print()
    print("   File                Warnings  Errors")
    print("-" * 100)
    for f in sorted(set(warnings) | set(errors)):
        print("   %-20s%6s  %6s" % (f, warnings[f] or "", errors[f] or ""))
    print()


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

# import htmlentitydefs

# Entities defined in HTML Latin-1 (ISO 8859-1)
# html_entities = htmlentitydefs.name2codepoint

# Entity defined in XML
# html_entities['apos'] = ord("'")

# Additional entities defined in HTML Latin-2 (ISO 8859-2)
"""
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
horbar  = 8213, # horizontal bar
percnt  = 0x00025, # percent sign
cir     = 9675, # white circle
frac14  = 0x000BC, # 1/4
frac12  = 0x000BD, # 1/2
half    = 0x000BD, # 1/2
frac34  = 0x000BE, # 3/4
frac13  = 0x02153,
frac23  = 0x02154,
frac15  = 0x02155,
frac25  = 0x02156,
frac35  = 0x02157,
frac45  = 0x02158,
frac16  = 0x02159,
frac56  = 0x0215A,
frac18  = 0x0215B,
frac38  = 0x0215C,
frac58  = 0x0215D,
frac78  = 0x0215E,
Ccirc   = 0x00108,
Omacr   = 0x0014C,
omacr   = 0x0014D,
thetav  = 0x003D1,
ogr     = 0x003BF,
emacr   = 0x00113,
ubreve  = 0x0016D,
amacr   = 0x00101,
imacr   = 0x0012B,
ebreve  = 0x0115,
obreve  = 0x014F,
ibreve  = 0x012D,
umacr   = 0x016B,
plus    = 0x0002B,
rcub    = 0x0007D,
female  = 0x02640,
male    = 0x02642,
utilde  = 0x00169,
itilde  = 0x00129,
epsi    = 0x003B5,
sigmav  = 0x003C2,
"""

# HTML entities (from http://www.derose.net/steve/utilities/XMLUTILS/entityNameList)
html_entities = {

    "ebreve": 0x0115,
    "obreve": 0x014F,
    "ibreve": 0x012D,

    ############################### 0x00000 (ASCII/ISO 646)
    "excl": 0x00021,
    "quot": 0x00022,
    "num": 0x00023,
    "dollar": 0x00024,
    "percnt": 0x00025,
    "amp": 0x00026,
    "apos": 0x00027,
    "lpar": 0x00028,
    "rpar": 0x00029,
    "ast": 0x0002A,
    "midast": 0x0002A,
    "plus": 0x0002B,
    "comma": 0x0002C,
    "period": 0x0002E,
    "sol": 0x0002F,
    "colon": 0x0003A,
    "semi": 0x0003B,
    "lt": 0x0003C,
    "equals": 0x0003D,
    "gt": 0x0003E,
    "quest": 0x0003F,
    "commat": 0x00040,
    "lsqb": 0x0005B,
    "bsol": 0x0005C,
    "rsqb": 0x0005D,
    "circ": 0x0005E,
    "lowbar": 0x0005F,
    "grave": 0x00060,
    "lcub": 0x0007B,
    "verbar": 0x0007C,
    "rcub": 0x0007D,
    ############################### 0x00080 (Latin-1) (C1)

    ############################### 0x000A0 (Latin-1) (G1)
    "nbsp": 0x000A0,
    "iexcl": 0x000A1,
    "cent": 0x000A2,
    "pound": 0x000A3,
    "curren": 0x000A4,
    "yen": 0x000A5,
    "brvbar": 0x000A6,
    "sect": 0x000A7,
    "uml": 0x000A8,
    "copy": 0x000A9,
    "ordf": 0x000AA,
    "laquo": 0x000AB,
    "not": 0x000AC,
    "shy": 0x000AD,
    "reg": 0x000AE,
    "macr": 0x000AF,

    "deg": 0x000B0,
    "plusmn": 0x000B1,
    "sup2": 0x000B2,
    "sup3": 0x000B3,
    "acute": 0x000B4,
    "micro": 0x000B5,
    "para": 0x000B6,
    "middot": 0x000B7,
    "cedil": 0x000B8,
    "sup1": 0x000B9,
    "ordm": 0x000BA,
    "raquo": 0x000BB,
    "frac14": 0x000BC,
    "frac12": 0x000BD,
    "half": 0x000BD,
    "frac34": 0x000BE,
    "iquest": 0x000BF,

    "Agrave": 0x000C0,
    "Aacute": 0x000C1,
    "Acirc": 0x000C2,
    "Atilde": 0x000C3,
    "Auml": 0x000C4,
    "Aring": 0x000C5,
    "AElig": 0x000C6,
    "Ccedil": 0x000C7,
    "Egrave": 0x000C8,
    "Eacute": 0x000C9,
    "Ecirc": 0x000CA,
    "Euml": 0x000CB,
    "Igrave": 0x000CC,
    "Iacute": 0x000CD,
    "Icirc": 0x000CE,
    "Iuml": 0x000CF,

    "ETH": 0x000D0,
    "Ntilde": 0x000D1,
    "Ograve": 0x000D2,
    "Oacute": 0x000D3,
    "Ocirc": 0x000D4,
    "Otilde": 0x000D5,
    "Ouml": 0x000D6,
    "times": 0x000D7,
    "Oslash": 0x000D8,
    "Ugrave": 0x000D9,
    "Uacute": 0x000DA,
    "Ucirc": 0x000DB,
    "Uuml": 0x000DC,
    "Yacute": 0x000DD,
    "THORN": 0x000DE,
    "szlig": 0x000DF,

    "agrave": 0x000E0,
    "aacute": 0x000E1,
    "acirc": 0x000E2,
    "atilde": 0x000E3,
    "auml": 0x000E4,
    "aring": 0x000E5,
    "aelig": 0x000E6,
    "ccedil": 0x000E7,
    "egrave": 0x000E8,
    "eacute": 0x000E9,
    "ecirc": 0x000EA,
    "euml": 0x000EB,
    "igrave": 0x000EC,
    "iacute": 0x000ED,
    "icirc": 0x000EE,
    "iuml": 0x000EF,

    "eth": 0x000F0,
    "ntilde": 0x000F1,
    "ograve": 0x000F2,
    "oacute": 0x000F3,
    "ocirc": 0x000F4,
    "otilde": 0x000F5,
    "ouml": 0x000F6,
    "divide": 0x000F7,
    "oslash": 0x000F8,
    "ugrave": 0x000F9,
    "uacute": 0x000FA,
    "ucirc": 0x000FB,
    "uuml": 0x000FC,
    "yacute": 0x000FD,
    "thorn": 0x000FE,
    "yuml": 0x000FF,

    ############################### 0x00100 Latin Extended-A (0x00100-0x0017F)
    "Amacr": 0x00100,
    "amacr": 0x00101,
    "Abreve": 0x00102,
    "abreve": 0x00103,
    "Aogon": 0x00104,
    "aogon": 0x00105,
    "Cacute": 0x00106,
    "cacute": 0x00107,
    "Ccirc": 0x00108,
    "ccirc": 0x00109,
    "Cdot": 0x0010A,
    "cdot": 0x0010B,
    "Ccaron": 0x0010C,
    "ccaron": 0x0010D,
    "Dcaron": 0x0010E,
    "dcaron": 0x0010F,

    "Dstrok": 0x00110,
    "dstrok": 0x00111,
    "Emacr": 0x00112,
    "emacr": 0x00113,
    # ??
    "Edot": 0x00116,
    "edot": 0x00117,
    "Eogon": 0x00118,
    "eogon": 0x00119,
    "Ecaron": 0x0011A,
    "ecaron": 0x0011B,
    "Gcirc": 0x0011C,
    "gcirc": 0x0011D,
    "Gbreve": 0x0011E,
    "gbreve": 0x0011F,

    "Gdot": 0x00120,
    "gdot": 0x00121,
    "Gcedil": 0x00122,
    "Hcirc": 0x00124,
    "hcirc": 0x00125,
    "Hstrok": 0x00126,
    "hstrok": 0x00127,
    "Itilde": 0x00128,
    "itilde": 0x00129,
    "Imacr": 0x0012A,
    "imacr": 0x0012B,
    "Iogon": 0x0012E,
    "iogon": 0x0012F,
    "Idot": 0x00130,
    "imath": 0x00131,
    "inodot": 0x00131,
    "IJlig": 0x00132,
    "ijlig": 0x00133,
    "Jcirc": 0x00134,
    "jcirc": 0x00135,
    "Kcedil": 0x00136,
    "kcedil": 0x00137,
    "kgreen": 0x00138,
    "Lacute": 0x00139,
    "lacute": 0x0013A,
    "Lcedil": 0x0013B,
    "lcedil": 0x0013C,
    "Lcaron": 0x0013D,
    "lcaron": 0x0013E,
    "Lmidot": 0x0013F,
    "lmidot": 0x00140,
    "Lstrok": 0x00141,
    "lstrok": 0x00142,
    "Nacute": 0x00143,
    "nacute": 0x00144,
    "Ncedil": 0x00145,
    "ncedil": 0x00146,
    "Ncaron": 0x00147,
    "ncaron": 0x00148,
    "napos": 0x00149,
    "ENG": 0x0014A,
    "eng": 0x0014B,
    "Omacr": 0x0014C,
    "omacr": 0x0014D,
    "Odblac": 0x00150,
    "odblac": 0x00151,
    "OElig": 0x00152,
    "oelig": 0x00153,
    "Racute": 0x00154,
    "racute": 0x00155,
    "Rcedil": 0x00156,
    "rcedil": 0x00157,
    "Rcaron": 0x00158,
    "rcaron": 0x00159,
    "Sacute": 0x0015A,
    "sacute": 0x0015B,
    "Scirc": 0x0015C,
    "scirc": 0x0015D,
    "Scedil": 0x0015E,
    "scedil": 0x0015F,
    "Scaron": 0x00160,
    "scaron": 0x00161,
    "Tcedil": 0x00162,
    "tcedil": 0x00163,
    "Tcaron": 0x00164,
    "tcaron": 0x00165,
    "Tstrok": 0x00166,
    "tstrok": 0x00167,
    "Utilde": 0x00168,
    "utilde": 0x00169,
    "Umacr": 0x0016A,
    "umacr": 0x0016B,
    "Ubreve": 0x0016C,
    "ubreve": 0x0016D,
    "Uring": 0x0016E,
    "uring": 0x0016F,
    "Udblac": 0x00170,
    "udblac": 0x00171,
    "Uogon": 0x00172,
    "uogon": 0x00173,
    "Wcirc": 0x00174,
    "wcirc": 0x00175,
    "Ycirc": 0x00176,
    "ycirc": 0x00177,
    "Yuml": 0x00178,
    "Zacute": 0x00179,
    "zacute": 0x0017A,
    "Zdot": 0x0017B,
    "zdot": 0x0017C,
    "Zcaron": 0x0017D,
    "zcaron": 0x0017E,
    "fnof": 0x00192,
    "gacute": 0x001F5,

    ############################### 0x00180 Latin Extended-B (0x00180-0x0024F)


    ############################### 0x00200 Latin Extended-B (0x00180-0x0024F)


    ############################### 0x00250 IPA Extensions (0x00250-0x002AF)
    "epsiv": 0x0025B,

    ############################### 0x002B0 Spacing Modifier Letters (0x002B0-0x002FF)
    "circ": 0x002C6,
    "caron": 0x002C7,
    "breve": 0x002D8,
    "dot": 0x002D9,
    "ring": 0x002DA,
    "ogon": 0x002DB,
    "tilde": 0x002DC,
    "dblac": 0x002DD,

    ############################### 0x00300 Combining Diacritical Marks (0x00300-0x0036F)

    ############################### 0x00370 Greek and Coptic (0x00370-0x003FF)
    "Aacgr": 0x00386,
    "Eacgr": 0x00388,
    "EEacgr": 0x00389,
    "Iacgr": 0x0038A,
    "Oacgr": 0x0038C,
    "Uacgr": 0x0038E,
    "OHacgr": 0x0038F,
    "idiagr": 0x00390,
    "Agr": 0x00391,
    "Alpha": 0x00391,
    "Beta": 0x00392,
    "Bgr": 0x00392,
    "Gamma": 0x00393,
    "Ggr": 0x00393,
    "Delta": 0x00394,
    "Dgr": 0x00394,
    "Egr": 0x00395,
    "Epsilon": 0x00395,
    "Zeta": 0x00396,
    "Zgr": 0x00396,
    "EEgr": 0x00397,
    "Eta": 0x00397,
    "THgr": 0x00398,
    "Theta": 0x00398,
    "Igr": 0x00399,
    "Iota": 0x00399,
    "Kappa": 0x0039A,
    "Kgr": 0x0039A,
    "Lambda": 0x0039B,
    "Lgr": 0x0039B,
    "Mgr": 0x0039C,
    "Mu": 0x0039C,
    "Ngr": 0x0039D,
    "Nu": 0x0039D,
    "Xgr": 0x0039E,
    "Xi": 0x0039E,
    "Ogr": 0x0039F,
    "Omicron": 0x0039F,
    "Pgr": 0x003A0,
    "Pi": 0x003A0,
    "Rgr": 0x003A1,
    "Rho": 0x003A1,
    "Sgr": 0x003A3,
    "Sigma": 0x003A3,
    "Tau": 0x003A4,
    "Tgr": 0x003A4,
    "Ugr": 0x003A5,
    "Upsilon": 0x003A5,
    "PHgr": 0x003A6,
    "Phi": 0x003A6,
    "Chi": 0x003A7,
    "KHgr": 0x003A7,
    "PSgr": 0x003A8,
    "Psi": 0x003A8,
    "OHgr": 0x003A9,
    "Omega": 0x003A9,
    "Idigr": 0x003AA,
    "Udigr": 0x003AB,
    "aacgr": 0x003AC,
    "eacgr": 0x003AD,
    "eeacgr": 0x003AE,
    "iacgr": 0x003AF,
    "udiagr": 0x003B0,
    "agr": 0x003B1,
    "alpha": 0x003B1,
    "beta": 0x003B2,
    "bgr": 0x003B2,
    "gamma": 0x003B3,
    "ggr": 0x003B3,
    "delta": 0x003B4,
    "dgr": 0x003B4,
    "egr": 0x003B5,
    "epsi": 0x003B5,
    "epsilon": 0x003B5,
    "zeta": 0x003B6,
    "zgr": 0x003B6,
    "eegr": 0x003B7,
    "eta": 0x003B7,
    "theta": 0x003B8,
    # "thetas": 0x003B8,
    # "thgr": 0x003B8,
    "igr": 0x003B9,
    "iota": 0x003B9,
    "kappa": 0x003BA,
    "kgr": 0x003BA,
    "lambda": 0x003BB,
    "lgr": 0x003BB,
    "mgr": 0x003BC,
    "mu": 0x003BC,
    "ngr": 0x003BD,
    "nu": 0x003BD,
    "xgr": 0x003BE,
    "xi": 0x003BE,
    "ogr": 0x003BF,
    "omicron": 0x003BF,
    "pgr": 0x003C0,
    "pi": 0x003C0,
    "rgr": 0x003C1,
    "rho": 0x003C1,
    "sfgr": 0x003C2,
    "sigmaf": 0x003C2,
    "sigmav": 0x003C2,
    "sgr": 0x003C3,
    "sigma": 0x003C3,
    "tau": 0x003C4,
    "tgr": 0x003C4,
    "ugr": 0x003C5,
    "upsi": 0x003C5,
    "upsilon": 0x003C5,
    "phgr": 0x003C6,
    "phi": 0x003C6,
    "phis": 0x003C6,
    "chi": 0x003C7,
    "khgr": 0x003C7,
    "psgr": 0x003C8,
    "psi": 0x003C8,
    "ohgr": 0x003C9,
    "omega": 0x003C9,
    "idigr": 0x003CA,
    "udigr": 0x003CB,
    "oacgr": 0x003CC,
    "uacgr": 0x003CD,
    "ohacgr": 0x003CE,
    "thetasym": 0x003D1,
    "thetav": 0x003D1,
    "Upsi": 0x003D2,
    "upsih": 0x003D2,
    "phiv": 0x003D5,
    "piv": 0x003D6,
    "Gammad": 0x003DC,
    "gammad": 0x003DC,
    "kappav": 0x003F0,
    "rhov": 0x003F1,
    "bepsi": 0x003F6,

    ############################### 0x00400 Cyrillic
    "IOcy": 0x00401,
    "DJcy": 0x00402,
    "GJcy": 0x00403,
    "Jukcy": 0x00404,
    "DScy": 0x00405,
    "Iukcy": 0x00406,
    "YIcy": 0x00407,
    "Jsercy": 0x00408,
    "LJcy": 0x00409,
    "NJcy": 0x0040A,
    "TSHcy": 0x0040B,
    "KJcy": 0x0040C,
    "Ubrcy": 0x0040E,
    "DZcy": 0x0040F,
    "Acy": 0x00410,
    "Bcy": 0x00411,
    "Vcy": 0x00412,
    "Gcy": 0x00413,
    "Dcy": 0x00414,
    "IEcy": 0x00415,
    "ZHcy": 0x00416,
    "Zcy": 0x00417,
    "Icy": 0x00418,
    "Jcy": 0x00419,
    "Kcy": 0x0041A,
    "Lcy": 0x0041B,
    "Mcy": 0x0041C,
    "Ncy": 0x0041D,
    "Ocy": 0x0041E,
    "Pcy": 0x0041F,
    "Rcy": 0x00420,
    "Scy": 0x00421,
    "Tcy": 0x00422,
    "Ucy": 0x00423,
    "Fcy": 0x00424,
    "KHcy": 0x00425,
    "TScy": 0x00426,
    "CHcy": 0x00427,
    "SHcy": 0x00428,
    "SHCHcy": 0x00429,
    "HARDcy": 0x0042A,
    "Ycy": 0x0042B,
    "SOFTcy": 0x0042C,
    "Ecy": 0x0042D,
    "YUcy": 0x0042E,
    "YAcy": 0x0042F,
    "acy": 0x00430,
    "bcy": 0x00431,
    "vcy": 0x00432,
    "gcy": 0x00433,
    "dcy": 0x00434,
    "iecy": 0x00435,
    "zhcy": 0x00436,
    "zcy": 0x00437,
    "icy": 0x00438,
    "jcy": 0x00439,
    "kcy": 0x0043A,
    "lcy": 0x0043B,
    "mcy": 0x0043C,
    "ncy": 0x0043D,
    "ocy": 0x0043E,
    "pcy": 0x0043F,
    "rcy": 0x00440,
    "scy": 0x00441,
    "tcy": 0x00442,
    "ucy": 0x00443,
    "fcy": 0x00444,
    "khcy": 0x00445,
    "tscy": 0x00446,
    "chcy": 0x00447,
    "shcy": 0x00448,
    "shchcy": 0x00449,
    "hardcy": 0x0044A,
    "ycy": 0x0044B,
    "softcy": 0x0044C,
    "ecy": 0x0044D,
    "yucy": 0x0044E,
    "yacy": 0x0044F,
    "iocy": 0x00451,
    "djcy": 0x00452,
    "gjcy": 0x00453,
    "jukcy": 0x00454,
    "dscy": 0x00455,
    "iukcy": 0x00456,
    "yicy": 0x00457,
    "jsercy": 0x00458,
    "ljcy": 0x00459,
    "njcy": 0x0045A,
    "tshcy": 0x0045B,
    "kjcy": 0x0045C,
    "ubrcy": 0x0045E,
    "dzcy": 0x0045F,

    ############################### 0x02000 General Punctuation (0x02000-0x0206F)
    "ensp": 0x02002,
    "emsp": 0x02003,
    "emsp13": 0x02004,
    "emsp14": 0x02005,
    "numsp": 0x02007,
    "puncsp": 0x02008,
    "thinsp": 0x02009,
    "hairsp": 0x0200A,
    "zwnj": 0x0200C,
    "zwj": 0x0200D,
    "lrm": 0x0200E,
    "rlm": 0x0200F,
    "dash": 0x02010,
    "hyphen": 0x02010,
    "ndash": 0x02013,
    "mdash": 0x02014,
    "horbar": 0x02015,
    "Verbar": 0x02016,
    "lsquo": 0x02018,
    "rsquo": 0x02019,
    "rsquor": 0x02019,
    "lsquor": 0x0201A,
    "sbquo": 0x0201A,
    "ldquo": 0x0201C,
    "rdquo": 0x0201D,
    "rdquor": 0x0201D,
    "bdquo": 0x0201E,
    "ldquor": 0x0201E,
    "dagger": 0x02020,
    "Dagger": 0x02021,
    "bull": 0x02022,
    "nldr": 0x02025,
    "hellip": 0x02026,
    "mldr": 0x02026,
    "permil": 0x02030,
    "pertenk": 0x02031,
    "prime": 0x02032,
    "Prime": 0x02033,
    "tprime": 0x02034,
    "bprime": 0x02035,
    "lsaquo": 0x02039,
    "rsaquo": 0x0203A,
    "oline": 0x0203E,
    "caret": 0x02041,
    "hybull": 0x02043,
    "frasl": 0x02044,
    "bsemi": 0x0204F,
    "qprime": 0x02057,

    ############################### 0x02070 Superscripts and Subscripts (0x02070-0x0209F)
    ############################### 0x020A0 Currency Symbols (0x020A0-0x020CF)
    "euro": 0x020AC,
    "tdot": 0x020DB,

    ############################### 0x020D0 Combining Diacritical Marks for Symbols (0x020D0-0x020FF)
    "DotDot": 0x020DC,

    ############################### 0x02100 Letterlike Symbols (0x02100-0x0214F)
    "Copf": 0x02102,
    "incare": 0x02105,
    "gscr": 0x0210A,
    "Hscr": 0x0210B,
    "hamilt": 0x0210B,
    "Hfr": 0x0210C,
    "Hopf": 0x0210D,
    "plankv": 0x0210F,
    "Iscr": 0x02110,
    "Ifr": 0x02111,
    "image": 0x02111,
    "Lscr": 0x02112,
    "lagran": 0x02112,
    "ell": 0x02113,
    "lscr": 0x02113,
    "Nopf": 0x02115,
    "numero": 0x02116,
    "copysr": 0x02117,
    "weierp": 0x02118,
    "Popf": 0x02119,
    "Qopf": 0x0211A,
    "Rscr": 0x0211B,
    "Rfr": 0x0211C,
    "real": 0x0211C,
    "Ropf": 0x0211D,
    "rx": 0x0211E,
    "trade": 0x02122,
    "Zopf": 0x02124,
    "ohm": 0x02126,
    "mho": 0x02127,
    "Zfr": 0x02128,
    "iiota": 0x02129,
    "angst": 0x0212B,
    "Bscr": 0x0212C,
    "bernou": 0x0212C,
    "Cfr": 0x0212D,
    "escr": 0x0212F,
    "Escr": 0x02130,
    "Fscr": 0x02131,
    "Mscr": 0x02133,
    "phmmat": 0x02133,
    "order": 0x02134,
    "oscr": 0x02134,
    "alefsym": 0x02135,
    "aleph": 0x02135,
    "beth": 0x02136,
    "gimel": 0x02137,
    "daleth": 0x02138,

    ############################### 0x02150 Number Forms (0x02150-0x0218F)
    "frac13": 0x02153,
    "frac23": 0x02154,
    "frac15": 0x02155,
    "frac25": 0x02156,
    "frac35": 0x02157,
    "frac45": 0x02158,
    "frac16": 0x02159,
    "frac56": 0x0215A,
    "frac18": 0x0215B,
    "frac38": 0x0215C,
    "frac58": 0x0215D,
    "frac78": 0x0215E,

    ############################### 0x02190 Arrows (0x02190-0x021FF)
    "larr": 0x02190,
    "uarr": 0x02191,
    "rarr": 0x02192,
    "darr": 0x02193,
    "harr": 0x02194,
    "varr": 0x02195,
    "nwarr": 0x02196,
    "nearr": 0x02197,
    "drarr": 0x02198,
    "searr": 0x02198,
    "swarr": 0x02199,
    "nlarr": 0x0219A,
    "nrarr": 0x0219B,
    "rarrw": 0x0219D,
    "Larr": 0x0219E,
    "Uarr": 0x0219F,
    "Rarr": 0x021A0,
    "Darr": 0x021A1,
    "larrtl": 0x021A2,
    "rarrtl": 0x021A3,
    "ratail": 0x021A3,
    "map": 0x021A6,
    "larrhk": 0x021A9,
    "rarrhk": 0x021AA,
    "larrlp": 0x021AB,
    "rarrlp": 0x021AC,
    "harrw": 0x021AD,
    "nharr": 0x021AE,
    "lsh": 0x021B0,
    "rsh": 0x021B1,
    "ldsh": 0x021B2,
    "rdsh": 0x021B3,
    "crarr": 0x021B5,
    "cularr": 0x021B6,
    "curarr": 0x021B7,
    "olarr": 0x021BA,
    "orarr": 0x021BB,
    "lharu": 0x021BC,
    "lhard": 0x021BD,
    "uharr": 0x021BE,
    "uharl": 0x021BF,
    "rharu": 0x021C0,
    "rhard": 0x021C1,
    "dharr": 0x021C2,
    "dharl": 0x021C3,
    "rlarr": 0x021C4,
    "udarr": 0x021C5,
    "lrarr": 0x021C6,
    "llarr": 0x021C7,
    "uuarr": 0x021C8,
    "rrarr": 0x021C9,
    "ddarr": 0x021CA,
    "lrhar": 0x021CB,
    "rlhar": 0x021CC,
    "rlhar2": 0x021CC,
    "nlArr": 0x021CD,
    "nvlArr": 0x021CD,
    "nhArr": 0x021CE,
    "nvHarr": 0x021CE,
    "nrArr": 0x021CF,
    "nvrArr": 0x021CF,
    "lArr": 0x021D0,
    "uArr": 0x021D1,
    "rArr": 0x021D2,
    "dArr": 0x021D3,
    "hArr": 0x021D4,
    "iff": 0x021D4,
    "vArr": 0x021D5,
    "nwArr": 0x021D6,
    "neArr": 0x021D7,
    "seArr": 0x021D8,
    "swArr": 0x021D9,
    "lAarr": 0x021DA,
    "rAarr": 0x021DB,
    "zigrarr": 0x021DD,
    "duarr": 0x021F5,
    "loarr": 0x021FD,
    "roarr": 0x021FE,
    "hoarr": 0x021FF,

    ############################### 0x02200 Mathematical Operators
    "forall": 0x02200,
    "comp": 0x02201,
    "part": 0x02202,
    "exist": 0x02203,
    "nexist": 0x02204,
    "empty": 0x02205,
    "emptyv": 0x02205,
    "nabla": 0x02207,
    "isin": 0x02208,
    "isinv": 0x02208,
    "notin": 0x02209,
    "ni": 0x0220B,
    "niv": 0x0220B,
    "notni": 0x0220C,
    "notniva": 0x0220C,
    "prod": 0x0220F,
    "coprod": 0x02210,
    "sum": 0x02211,
    "minus": 0x02212,
    "mnplus": 0x02213,
    "plusdo": 0x02214,
    "setmn": 0x02216,
    "lowast": 0x02217,
    "compfn": 0x02218,
    "radic": 0x0221A,
    "prop": 0x0221D,
    "vprop": 0x0221D,
    "infin": 0x0221E,
    "angrt": 0x0221F,
    "ang": 0x02220,
    "angmsd": 0x02221,
    "angsph": 0x02222,
    "mid": 0x02223,
    "nmid": 0x02224,
    "par": 0x02225,
    "npar": 0x02226,
    "and": 0x02227,
    "or": 0x02228,
    "cap": 0x02229,
    "cup": 0x0222A,
    "int": 0x0222B,
    "Int": 0x0222C,
    "tint": 0x0222D,
    "conint": 0x0222E,
    "Conint": 0x0222F,
    "Cconint": 0x02230,
    "cwint": 0x02231,
    "cwconint": 0x02232,
    "awconint": 0x02233,
    "there4": 0x02234,
    "becaus": 0x02235,
    "ratio": 0x02236,
    "Colon": 0x02237,
    "minusd": 0x02238,
    "mDDot": 0x0223A,
    "homtht": 0x0223B,
    "sim": 0x0223C,
    "bsim": 0x0223D,
    "mstpos": 0x0223E,
    "acd": 0x0223F,
    "wreath": 0x02240,
    "nsim": 0x02241,
    "esim": 0x02242,
    "sime": 0x02243,
    "nsime": 0x02244,
    "cong": 0x02245,
    "simne": 0x02246,
    "ncong": 0x02247,
    "ap": 0x02248,
    "asymp": 0x02248,
    "nap": 0x02249,
    "apE": 0x0224A,
    "ape": 0x0224A,
    "apid": 0x0224B,
    "bcong": 0x0224C,
    "asymp": 0x0224D,
    "bump": 0x0224E,
    "bumpe": 0x0224F,
    "esdot": 0x02250,
    "eDot": 0x02251,
    "efDot": 0x02252,
    "erDot": 0x02253,
    "colone": 0x02254,
    "ecolon": 0x02255,
    "ecir": 0x02256,
    "cire": 0x02257,
    "wedgeq": 0x02259,
    "veeeq": 0x0225A,
    "easter": 0x0225B,
    "trie": 0x0225C,
    "equest": 0x0225F,
    "ne": 0x02260,
    "equiv": 0x02261,
    "nequiv": 0x02262,
    "le": 0x02264,
    "ge": 0x02265,
    "lE": 0x02266,
    "gE": 0x02267,
    "lnE": 0x02268,
    "lne": 0x02268,
    "gnE": 0x02269,
    "gne": 0x02269,
    "Lt": 0x0226A,
    "Gt": 0x0226B,
    "twixt": 0x0226C,
    "nlt": 0x0226E,
    "nvlt": 0x0226E,
    "ngt": 0x0226F,
    "nvgt": 0x0226F,
    "nlE": 0x02270,
    "nles": 0x02270,
    "nvle": 0x02270,
    "ngE": 0x02271,
    "nges": 0x02271,
    "nvge": 0x02271,
    "lap": 0x02272,
    "lsim": 0x02272,
    "gap": 0x02273,
    "gsim": 0x02273,
    "nlsim": 0x02274,
    "ngsim": 0x02275,
    "lg": 0x02276,
    "gl": 0x02277,
    "ntlg": 0x02278,
    "ntgl": 0x02279,
    "pr": 0x0227A,
    "sc": 0x0227B,
    "prcue": 0x0227C,
    "sccue": 0x0227D,
    "sce": 0x0227D,
    "prap": 0x0227E,
    "prsim": 0x0227E,
    "scE": 0x0227E,
    "scap": 0x0227F,
    "scsim": 0x0227F,

    "npr": 0x02280,
    "nsc": 0x02281,
    "sub": 0x02282,
    "sup": 0x02283,
    "nsub": 0x02284,
    "vnsub": 0x02284,
    "nsup": 0x02285,
    "vnsup": 0x02285,
    "subE": 0x02286,
    "sube": 0x02286,
    "supE": 0x02287,
    "supe": 0x02287,
    "nsubE": 0x02288,
    "nsube": 0x02288,
    "nsupE": 0x02289,
    "nsupe": 0x02289,
    "subnE": 0x0228A,
    "subne": 0x0228A,
    "supnE": 0x0228B,
    "supne": 0x0228B,
    "cupdot": 0x0228D,
    "uplus": 0x0228E,
    "xuplus": 0x0228E,
    "sqsub": 0x0228F,
    "sqsup": 0x02290,
    "sqsube": 0x02291,
    "sqsupe": 0x02292,
    "sqcap": 0x02293,
    "sqcup": 0x02294,
    "xsqcup": 0x02294,
    "oplus": 0x02295,
    "xoplus": 0x02295,
    "ominus": 0x02296,
    "otimes": 0x02297,
    "xotime": 0x02297,
    "osol": 0x02298,
    "odot": 0x02299,
    "xodot": 0x02299,
    "ocir": 0x0229A,
    "oast": 0x0229B,
    "odash": 0x0229D,
    "plusb": 0x0229E,
    "minusb": 0x0229F,
    "timesb": 0x022A0,
    "sdotb": 0x022A1,
    "vdash": 0x022A2,
    "dashv": 0x022A3,
    "top": 0x022A4,
    "bottom": 0x022A5,
    "perp": 0x022A5,
    "models": 0x022A7,
    "vDash": 0x022A8,
    "Vdash": 0x022A9,
    "Vvdash": 0x022AA,
    "VDash": 0x022AB,
    "nvdash": 0x022AC,
    "nvDash": 0x022AD,
    "nVdash": 0x022AE,
    "nVDash": 0x022AF,
    "prurel": 0x022B0,
    "vltri": 0x022B2,
    "vrtri": 0x022B3,
    "ltrie": 0x022B4,
    "rtrie": 0x022B5,
    "origof": 0x022B6,
    "imof": 0x022B7,
    "mumap": 0x022B8,
    "hercon": 0x022B9,
    "intcal": 0x022BA,
    "veebar": 0x022BB,
    "barwed": 0x022BC,
    "barvee": 0x022BD,
    "vangrt": 0x022BE,
    "lrtri": 0x022BF,
    "xwedge": 0x022C0,
    "xvee": 0x022C1,
    "xcap": 0x022C2,
    "xcup": 0x022C3,
    "diam": 0x022C4,
    "sdot": 0x022C5,
    "sstarf": 0x022C6,
    "star": 0x022C6,
    "divonx": 0x022C7,
    "bowtie": 0x022C8,
    "ltimes": 0x022C9,
    "rtimes": 0x022CA,
    "lthree": 0x022CB,
    "rthree": 0x022CC,
    "bsime": 0x022CD,
    "cuvee": 0x022CE,
    "cuwed": 0x022CF,
    "Sub": 0x022D0,
    "Sup": 0x022D1,
    "Cap": 0x022D2,
    "Cup": 0x022D3,
    "fork": 0x022D4,
    "epar": 0x022D5,
    "ltdot": 0x022D6,
    "gtdot": 0x022D7,
    "Ll": 0x022D8,
    "Gg": 0x022D9,
    "lEg": 0x022DA,
    "leg": 0x022DA,
    "gEl": 0x022DB,
    "gel": 0x022DB,
    "els": 0x022DC,
    "egs": 0x022DD,
    "cuepr": 0x022DE,
    "cuesc": 0x022DF,
    "nprcue": 0x022E0,
    "nsccue": 0x022E1,
    "nsqsube": 0x022E2,
    "nsqsupe": 0x022E3,
    "lnsim": 0x022E6,
    "gnsim": 0x022E7,
    "prnap": 0x022E8,
    "prnsim": 0x022E8,
    "scnap": 0x022E9,
    "scnsim": 0x022E9,
    "nltri": 0x022EA,
    "nrtri": 0x022EB,
    "nltrie": 0x022EC,
    "nrtrie": 0x022ED,
    "vellip": 0x022EE,
    "ctdot": 0x022EF,
    "utdot": 0x022F0,
    "dtdot": 0x022F1,
    "disin": 0x022F2,
    "isinsv": 0x022F3,
    "isins": 0x022F4,
    "isindot": 0x022F5,
    "notinvc": 0x022F6,
    "notinvb": 0x022F7,
    "isinE": 0x022F9,
    "nisd": 0x022FA,
    "xnis": 0x022FB,
    "nis": 0x022FC,
    "notnivc": 0x022FD,
    "notnivb": 0x022FE,

    ############################### 0x02300 Miscellaneous Technical
    "Barwed": 0x02306,
    "lceil": 0x02308,
    "rceil": 0x02309,
    "lfloor": 0x0230A,
    "rfloor": 0x0230B,
    "drcrop": 0x0230C,
    "dlcrop": 0x0230D,
    "urcrop": 0x0230E,
    "ulcrop": 0x0230F,
    "bnot": 0x02310,
    "profline": 0x02312,
    "profsurf": 0x02313,
    "telrec": 0x02315,
    "target": 0x02316,
    "ulcorn": 0x0231C,
    "urcorn": 0x0231D,
    "dlcorn": 0x0231E,
    "drcorn": 0x0231F,
    "frown": 0x02322,
    "smile": 0x02323,
    "lang": 0x02329,
    "rang": 0x0232A,
    "cylcty": 0x0232D,
    "profalar": 0x0232E,
    "topbot": 0x02336,
    "ovbar": 0x0233D,
    "solbar": 0x0233F,
    "angzarr": 0x0237C,
    "lmoust": 0x023B0,
    "rmoust": 0x023B1,
    "tbrk": 0x023B4,
    "bbrk": 0x023B5,

    ############################### 0x02400 Control Pictures (0x02400-0x0243F)
    "blank": 0x02423,

    ############################### 0x02440 Optical Character Recognition (0x02440-0x0245F)

    ############################### 0x02460 Enclosed Alphanumerics (0x02460-0x024FF)
    "oS": 0x024C8,

    ############################### 0x02500 Box Drawing (0x02500-0x0257F)
    "boxh": 0x02500,
    "boxv": 0x02502,
    "boxdr": 0x0250C,
    "boxdl": 0x02510,
    "boxur": 0x02514,
    "boxul": 0x02518,
    "boxvr": 0x0251C,
    "boxvl": 0x02524,
    "boxhd": 0x0252C,
    "boxhu": 0x02534,
    "boxvh": 0x0253C,
    "boxH": 0x02550,
    "boxV": 0x02551,
    "boxdR": 0x02552,
    "boxDr": 0x02553,
    "boxDR": 0x02554,
    "boxdL": 0x02555,
    "boxDl": 0x02556,
    "boxDL": 0x02557,
    "boxuR": 0x02558,
    "boxUr": 0x02559,
    "boxUR": 0x0255A,
    "boxuL": 0x0255B,
    "boxUl": 0x0255C,
    "boxUL": 0x0255D,
    "boxvR": 0x0255E,
    "boxVr": 0x0255F,
    "boxVR": 0x02560,
    "boxvL": 0x02561,
    "boxVl": 0x02562,
    "boxVL": 0x02563,
    "boxHd": 0x02564,
    "boxhD": 0x02565,
    "boxHD": 0x02566,
    "boxHu": 0x02567,
    "boxhU": 0x02568,
    "boxHU": 0x02569,
    "boxvH": 0x0256A,
    "boxVh": 0x0256B,
    "boxVH": 0x0256C,

    ############################### 0x02580 Block Elements (0x02580-0x0259F)
    "uhblk": 0x02580,
    "lhblk": 0x02584,
    "block": 0x02588,
    "blk14": 0x02591,
    "blk12": 0x02592,
    "blk34": 0x02593,

    ############################### 0x025A0 Geometric Shapes (0x025A0-0x025FF)7
    "squ": 0x025A1,
    "square": 0x025A1,
    "squarf": 0x025AA,
    "squf": 0x025AA,
    "rect": 0x025AD,
    "marker": 0x025AE,
    "xutri": 0x025B3,
    "utrif": 0x025B4,
    "utri": 0x025B5,
    "rtrif": 0x025B8,
    "rtri": 0x025B9,
    "xdtri": 0x025BD,
    "dtrif": 0x025BE,
    "dtri": 0x025BF,
    "ltrif": 0x025C2,
    "ltri": 0x025C3,
    "loz": 0x025CA,
    "cir": 0x025CB,
    "tridot": 0x025EC,
    "xcirc": 0x025EF,
    "ultri": 0x025F8,
    "urtri": 0x025F9,
    "lltri": 0x025FA,

    ############################### 0x02600 Miscellaneous Symbols
    "starf": 0x02605,
    "phone": 0x0260E,
    "female": 0x02640,
    "male": 0x02642,
    "spades": 0x02660,
    "clubs": 0x02663,
    "hearts": 0x02665,
    "diams": 0x02666,
    "sung": 0x0266A,
    "flat": 0x0266D,
    "natur": 0x0266E,
    "sharp": 0x0266F,

    ############################### 0x02700 Dingbats (0x02700-0x027BF)
    "check": 0x02713,
    "cross": 0x02717,
    "malt": 0x02720,
    "sext": 0x02736,

    ############################### 0x027C0 Miscellaneous Mathematical Symbols-A (0x027C0-0x027EF)

    ############################### 0x027F0 Supplemental Arrows-A (0x027F0-0x027FF)

    ############################### 0x02800 Braille Patterns

    ############################### 0x02900 Supplemental Arrows-B
    "Map": 0x02905,
    "lbarr": 0x0290C,
    "rbarr": 0x0290D,
    "lBarr": 0x0290E,
    "ac": 0x0290F,
    "rBarr": 0x0290F,
    "RBarr": 0x02910,
    "DDotrahd": 0x02911,
    "Rarrtl": 0x02916,
    "latail": 0x02919,
    "lAtail": 0x0291B,
    "rAtail": 0x0291C,
    "larrfs": 0x0291D,
    "rarrfs": 0x0291E,
    "larrbfs": 0x0291F,
    "rarrbfs": 0x02920,
    "nwarhk": 0x02923,
    "nearhk": 0x02924,
    "searhk": 0x02925,
    "swarhk": 0x02926,
    "nwnear": 0x02927,
    "nesear": 0x02928,
    "seswar": 0x02929,
    "swnwar": 0x0292A,
    "rarrc": 0x02933,
    "cudarrr": 0x02935,
    "ldca": 0x02936,
    "rdca": 0x02937,
    "cudarrl": 0x02938,
    "larrpl": 0x02939,
    "curarrm": 0x0293C,
    "cularrp": 0x0293D,
    "rarrpl": 0x02945,
    "harrcir": 0x02948,
    "Uarrocir": 0x02949,
    "lurdshar": 0x0294A,
    "ldrushar": 0x0294B,
    "lHar": 0x02962,
    "uHar": 0x02963,
    "rHar": 0x02964,
    "dHar": 0x02965,
    "luruhar": 0x02966,
    "ldrdhar": 0x02967,
    "ruluhar": 0x02968,
    "rdldhar": 0x02969,
    "lharul": 0x0296A,
    "llhard": 0x0296B,
    "rharul": 0x0296C,
    "lrhard": 0x0296D,
    "udhar": 0x0296E,
    "duhar": 0x0296F,
    "erarr": 0x02971,
    "simrarr": 0x02972,
    "larrsim": 0x02973,
    "rarrsim": 0x02974,
    "rarrap": 0x02975,
    "ltlarr": 0x02976,
    "gtrarr": 0x02978,
    "subrarr": 0x02979,
    "suplarr": 0x0297B,
    "lfisht": 0x0297C,
    "rfisht": 0x0297D,
    "ufisht": 0x0297E,
    "dfisht": 0x0297F,

    ############################### 0x02980 Miscellaneous Mathematical Symbols-B
    "lbrke": 0x0298B,
    "rbrke": 0x0298C,
    "lbrkslu": 0x0298D,
    "rbrksld": 0x0298E,
    "lbrksld": 0x0298F,
    "rbrkslu": 0x02990,
    "langd": 0x02991,
    "rangd": 0x02992,
    "lparlt": 0x02993,
    "rpargt": 0x02994,
    "gtlPar": 0x02995,
    "ltrPar": 0x02996,
    "vzigzag": 0x0299A,
    "angrtvbd": 0x0299D,
    "ange": 0x029A4,
    "range": 0x029A5,
    "dwangle": 0x029A6,
    "uwangle": 0x029A7,
    "angmsdaa": 0x029A8,
    "angmsdab": 0x029A9,
    "angmsdac": 0x029AA,
    "angmsdad": 0x029AB,
    "angmsdae": 0x029AC,
    "angmsdaf": 0x029AD,
    "angmsdag": 0x029AE,
    "angmsdah": 0x029AF,
    "bemptyv": 0x029B0,
    "demptyv": 0x029B1,
    "cemptyv": 0x029B2,
    "raemptyv": 0x029B3,
    "laemptyv": 0x029B4,
    "ohbar": 0x029B5,
    "omid": 0x029B6,
    "opar": 0x029B7,
    "operp": 0x029B9,
    "olcross": 0x029BB,
    "odsold": 0x029BC,
    "olcir": 0x029BE,
    "ofcir": 0x029BF,
    "olt": 0x029C0,
    "ogt": 0x029C1,
    "cirscir": 0x029C2,
    "cirE": 0x029C3,
    "solb": 0x029C4,
    "bsolb": 0x029C5,
    "boxbox": 0x029C9,
    "trisb": 0x029CD,
    "rtriltri": 0x029CE,
    "race": 0x029DA,
    "acE": 0x029DB,
    "iinfin": 0x029DC,
    "nvinfin": 0x029DE,
    "eparsl": 0x029E3,
    "smeparsl": 0x029E4,
    "eqvparsl": 0x029E5,
    "lozf": 0x029EB,
    "dsol": 0x029F6,

    ############################### 0x02A00
    "qint": 0x02A0C,
    "fpartint": 0x02A0D,
    "cirfnint": 0x02A10,
    "awint": 0x02A11,
    "rppolint": 0x02A12,
    "scpolint": 0x02A13,
    "npolint": 0x02A14,
    "pointint": 0x02A15,
    "quatint": 0x02A16,
    "intlarhk": 0x02A17,
    "pluscir": 0x02A22,
    "plusacir": 0x02A23,
    "simplus": 0x02A24,
    "plusdu": 0x02A25,
    "plussim": 0x02A26,
    "plustwo": 0x02A27,
    "mcomma": 0x02A29,
    "minusdu": 0x02A2A,
    "loplus": 0x02A2D,
    "roplus": 0x02A2E,
    "timesd": 0x02A30,
    "timesbar": 0x02A31,
    "smashp": 0x02A33,
    "lotimes": 0x02A34,
    "rotimes": 0x02A35,
    "otimesas": 0x02A36,
    "Otimes": 0x02A37,
    "odiv": 0x02A38,
    "triplus": 0x02A39,
    "triminus": 0x02A3A,
    "tritime": 0x02A3B,
    "iprod": 0x02A3C,
    "amalg": 0x02A3F,
    "capdot": 0x02A40,
    "ncup": 0x02A42,
    "ncap": 0x02A43,
    "capand": 0x02A44,
    "cupor": 0x02A45,
    "cupcap": 0x02A46,
    "capcup": 0x02A47,
    "cupbrcap": 0x02A48,
    "capbrcup": 0x02A49,
    "cupcup": 0x02A4A,
    "capcap": 0x02A4B,
    "ccups": 0x02A4C,
    "ccaps": 0x02A4D,
    "ccupssm": 0x02A50,
    "And": 0x02A53,
    "Or": 0x02A54,
    "andand": 0x02A55,
    "oror": 0x02A56,
    "orslope": 0x02A57,
    "andslope": 0x02A58,
    "andv": 0x02A5A,
    "orv": 0x02A5B,
    "andd": 0x02A5C,
    "ord": 0x02A5D,
    "wedbar": 0x02A5F,
    "sdote": 0x02A66,
    "simdot": 0x02A6A,
    "congdot": 0x02A6D,
    "apacir": 0x02A6F,
    "eplus": 0x02A71,
    "pluse": 0x02A72,
    "Esim": 0x02A73,
    "Colone": 0x02A74,
    "eDDot": 0x02A77,
    "equivDD": 0x02A78,
    "ltcir": 0x02A79,
    "gtcir": 0x02A7A,
    "ltquest": 0x02A7B,
    "gtquest": 0x02A7C,
    "les": 0x02A7D,
    "ges": 0x02A7E,
    "lesdot": 0x02A7F,
    "gesdot": 0x02A80,
    "lesdoto": 0x02A81,
    "gesdoto": 0x02A82,
    "lesdotor": 0x02A83,
    "gesdotol": 0x02A84,
    "lnap": 0x02A89,
    "gnap": 0x02A8A,
    "lsime": 0x02A8D,
    "gsime": 0x02A8E,
    "lsimg": 0x02A8F,
    "gsiml": 0x02A90,
    "lgE": 0x02A91,
    "glE": 0x02A92,
    "lesges": 0x02A93,
    "gesles": 0x02A94,
    "elsdot": 0x02A97,
    "egsdot": 0x02A98,
    "el": 0x02A99,
    "eg": 0x02A9A,
    "siml": 0x02A9D,
    "simg": 0x02A9E,
    "simlE": 0x02A9F,
    "simgE": 0x02AA0,
    "glj": 0x02AA4,
    "gla": 0x02AA5,
    "ltcc": 0x02AA6,
    "gtcc": 0x02AA7,
    "lescc": 0x02AA8,
    "gescc": 0x02AA9,
    "smt": 0x02AAA,
    "lat": 0x02AAB,
    "smte": 0x02AAC,
    "late": 0x02AAD,
    "bumpE": 0x02AAE,
    "prE": 0x02AAF,
    "pre": 0x02AAF,
    "prnE": 0x02AB5,
    "scnE": 0x02AB6,
    "Pr": 0x02ABB,
    "Sc": 0x02ABC,
    "subdot": 0x02ABD,
    "supdot": 0x02ABE,
    "subplus": 0x02ABF,
    "supplus": 0x02AC0,
    "submult": 0x02AC1,
    "supmult": 0x02AC2,
    "subedot": 0x02AC3,
    "supedot": 0x02AC4,
    "subsim": 0x02AC7,
    "supsim": 0x02AC8,
    "csub": 0x02ACF,
    "csup": 0x02AD0,
    "csube": 0x02AD1,
    "csupe": 0x02AD2,
    "subsup": 0x02AD3,
    "supsub": 0x02AD4,
    "subsub": 0x02AD5,
    "supsup": 0x02AD6,
    "suphsub": 0x02AD7,
    "supdsub": 0x02AD8,
    "forkv": 0x02AD9,
    "topfork": 0x02ADA,
    "mlcp": 0x02ADB,
    "Dashv": 0x02AE4,
    "Vdashl": 0x02AE6,
    "Barv": 0x02AE7,
    "vBar": 0x02AE8,
    "vBarv": 0x02AE9,
    "Vbar": 0x02AEB,
    "Not": 0x02AEC,
    "bNot": 0x02AED,
    "rnmid": 0x02AEE,
    "cirmid": 0x02AEF,
    "midcir": 0x02AF0,
    "topcir": 0x02AF1,
    "nhpar": 0x02AF2,
    "parsim": 0x02AF3,

    ############################### 0x03000 CJK Symbols and Punctuation (0x03000-0x0303F)
    "Lang": 0x0300A,
    "Rang": 0x0300B,
    "lbbrk": 0x03014,
    "rbbrk": 0x03015,
    "lopar": 0x03018,
    "ropar": 0x03019,
    "lobrk": 0x0301A,
    "robrk": 0x0301B,

    ############################### Hiragana (0x03040-0x0309F)

    ############################### Katakana (0x030A0-0x030FF)

    ############################### 0x0E000 Private Use Area

    ############################### 0x0F000 Private Use Area

    ############################### 0x0F500 Private Use Area
    "loang": 0x0F558,
    "roang": 0x0F559,
    "xlarr": 0x0F576,
    "xrarr": 0x0F577,
    "xharr": 0x0F578,
    "xlArr": 0x0F579,
    "xrArr": 0x0F57A,
    "xhArr": 0x0F57B,
    "xmap": 0x0F57D,
    "dzigrarr": 0x0F5A2,

    ############################### 0x0F900 CJK Compatibility Ideographs (0x0F900-0x0FAFF)

    ############################### 0x0FB00
    "fflig": 0x0FB00,
    "filig": 0x0FB01,
    "fllig": 0x0FB02,
    "ffilig": 0x0FB03,
    "ffllig": 0x0FB04,

    ############################### 0x1D400 (Mathematical Alphanumeric Symbols)
    "Ascr": 0x1D49C,
    "Cscr": 0x1D49E,
    "Dscr": 0x1D49F,
    "Gscr": 0x1D4A2,
    "Jscr": 0x1D4A5,
    "Kscr": 0x1D4A6,
    "Nscr": 0x1D4A9,
    "Oscr": 0x1D4AA,
    "Pscr": 0x1D4AB,
    "Qscr": 0x1D4AC,
    "Sscr": 0x1D4AE,
    "Tscr": 0x1D4AF,
    "Uscr": 0x1D4B0,
    "Vscr": 0x1D4B1,
    "Wscr": 0x1D4B2,
    "Xscr": 0x1D4B3,
    "Yscr": 0x1D4B4,
    "Zscr": 0x1D4B5,
    "ascr": 0x1D4B6,
    "bscr": 0x1D4B7,
    "cscr": 0x1D4B8,
    "dscr": 0x1D4B9,
    "fscr": 0x1D4BB,
    "hscr": 0x1D4BD,
    "iscr": 0x1D4BE,
    "jscr": 0x1D4BF,
    "kscr": 0x1D4C0,
    "mscr": 0x1D4C2,
    "nscr": 0x1D4C3,
    "pscr": 0x1D4C5,
    "qscr": 0x1D4C6,
    "rscr": 0x1D4C7,
    "sscr": 0x1D4C8,
    "tscr": 0x1D4C9,
    "uscr": 0x1D4CA,
    "vscr": 0x1D4CB,
    "wscr": 0x1D4CC,
    "xscr": 0x1D4CD,
    "yscr": 0x1D4CE,
    "zscr": 0x1D4CF,

    ############################### 0x1D500 Mathematical Alphanumeric Symbols
    "Afr": 0x1D504,
    "Bfr": 0x1D505,
    "Dfr": 0x1D507,
    "Efr": 0x1D508,
    "Ffr": 0x1D509,
    "Gfr": 0x1D50A,
    "Jfr": 0x1D50D,
    "Kfr": 0x1D50E,
    "Lfr": 0x1D50F,
    "Mfr": 0x1D510,
    "Nfr": 0x1D511,
    "Ofr": 0x1D512,
    "Pfr": 0x1D513,
    "Qfr": 0x1D514,
    "Sfr": 0x1D516,
    "Tfr": 0x1D517,
    "Ufr": 0x1D518,
    "Vfr": 0x1D519,
    "Wfr": 0x1D51A,
    "Xfr": 0x1D51B,
    "Yfr": 0x1D51C,
    "afr": 0x1D51E,
    "bfr": 0x1D51F,
    "cfr": 0x1D520,
    "dfr": 0x1D521,
    "efr": 0x1D522,
    "ffr": 0x1D523,
    "gfr": 0x1D524,
    "hfr": 0x1D525,
    "ifr": 0x1D526,
    "jfr": 0x1D527,
    "kfr": 0x1D528,
    "lfr": 0x1D529,
    "mfr": 0x1D52A,
    "nfr": 0x1D52B,
    "ofr": 0x1D52C,
    "pfr": 0x1D52D,
    "qfr": 0x1D52E,
    "rfr": 0x1D52F,
    "sfr": 0x1D530,
    "tfr": 0x1D531,
    "ufr": 0x1D532,
    "vfr": 0x1D533,
    "wfr": 0x1D534,
    "xfr": 0x1D535,
    "yfr": 0x1D536,
    "zfr": 0x1D537,
    "Aopf": 0x1D538,
    "Bopf": 0x1D539,
    "Dopf": 0x1D53B,
    "Eopf": 0x1D53C,
    "Fopf": 0x1D53D,
    "Gopf": 0x1D53E,
    "Iopf": 0x1D540,
    "Jopf": 0x1D541,
    "Kopf": 0x1D542,
    "Lopf": 0x1D543,
    # "imped": 0x1D543
    "Mopf": 0x1D544,
    "Oopf": 0x1D546,
    "Sopf": 0x1D54A,
    "Topf": 0x1D54B,
    "Uopf": 0x1D54C,
    "Vopf": 0x1D54D,
    "Wopf": 0x1D54E,
    "Xopf": 0x1D54F,
    "Yopf": 0x1D550,
    ############################### 0x1D600 Mathematical Alphanumeric Symbols

    ############################### 0x1D700 Mathematical Alphanumeric Symbols

    ############################### 0x1D800 (empty)
    }

######################################################################

if __name__ == '__main__':
    util.run.main(analyze)
