# -*- coding: utf-8 -*-

"""
A parser for pseudo-XML documents.
Pseudo-XML is almost like XML, but admits overlapping elements.
"""
import re
import sparv.util as util
import unicodedata
from sparv.xmlanalyzer import problematic_entity, html_entities  # , is_control_code

# TODO: lägg till metadata-annoteringar, ungefär som i obsolete/tei_parser.py
# ELLER: skapa ett annat skript: headerparser.py, som endast parsar och annoterar metadata

REGEXP_TOKEN = re.compile(r"([^\W_\d]+|\d+| +|\s|.)", re.UNICODE)
# This above regexp specifies possible tokens,
# between each token an anchor point is inserted
# Note: the first group matches sequences of letters,
# but we cannot use \w directly, since it matches [_\d], so we have to
# exclude these in the first group above, hence [^\W_\d];
# idea taken from http://stackoverflow.com/questions/1673749


def parse(source, text, elements=[], annotations=[], skip=(), overlap=(), header="teiheader", encoding=util.UTF8,
          prefix="", fileid="", fileids="", headers="", header_annotations="", skip_if_empty="", skip_entities="",
          autoclose="", allow_xml_chars=False):
    """Parse one pseudo-xml source file, into the specified corpus."""
    if isinstance(elements, str):
        elements = elements.split()
    if isinstance(annotations, str):
        annotations = annotations.split()
    if isinstance(skip, str):
        skip = skip.split()
    if isinstance(overlap, str):
        overlap = overlap.split()
    if isinstance(headers, str):
        headers = headers.split()
    if isinstance(header_annotations, str):
        header_annotations = header_annotations.split()
    if isinstance(skip_if_empty, str):
        skip_if_empty = skip_if_empty.split()
    if isinstance(skip_entities, str):
        skip_entities = skip_entities.split()
    if isinstance(autoclose, str):
        autoclose = autoclose.split()
    allow_xml_chars = util.strtobool(allow_xml_chars)
    assert len(elements) == len(annotations), "elements and annotations must be the same length"
    assert prefix or (fileid and fileids), "either prefix or both fileid and fileids must be set"
    if not header:
        header = "teiheader"
    header = header.split()

    if fileid and fileids:
        FILEIDS = util.read_annotation(fileids)
        prefix = FILEIDS[fileid]

    def elsplit(elem):
        elem = elem.replace("\:", ";")
        tag, _, attr = elem.partition(":")
        tag = tag.replace(";", ":")
        attr = attr.replace(";", ":")
        return tag, attr

    elem_order = [(elsplit(elem), annotation)
                  for elemgroup, annotation in zip(elements, annotations)
                  for elem in elemgroup.split("+")]

    elem_annotations = {}
    for pair in elem_order:
        elem_annotations.setdefault(pair[0], []).append(pair[1])

    head_annotations = dict((elsplit(head), annotation)
                            for head, annotation in zip(headers, header_annotations))

    skipped_elems = set(elsplit(elem) for elem in skip)
    assert skipped_elems.isdisjoint(elem_annotations), "skip and elements must be disjoint"

    can_overlap = set((t1, t2) for tags in overlap
                      for t1 in tags.split("+") for t2 in tags.split("+") if t1 != t2)

    with open(source) as SRC:
        content = SRC.read()
        content = unicodedata.normalize("NFC", content)  # Normalize characters to precomposed form (NFKC can also be used)
    parser = XMLParser(elem_annotations, skipped_elems, can_overlap, header, prefix, text, len(content.encode(util.UTF8)), head_annotations, skip_if_empty, skip_entities, autoclose, elem_order, allow_xml_chars)
    parser.feed(content)
    parser.close()


######################################################################

from html.parser import HTMLParser


class XMLParser(HTMLParser):
    def __init__(self, elem_annotations, skipped_elems, can_overlap, header_elem, prefix, textfile, corpus_size, head_annotations={}, skip_if_empty=[], skip_entities=[], autoclose=[], elem_order=[], allow_xml_chars=False):
        HTMLParser.__init__(self, convert_charrefs=False)
        self.errors = False
        self.reset()
        self.tagstack = []
        self.header_elem = header_elem
        self.inside_header = False
        self.elem_annotations = elem_annotations
        self.elem_order = elem_order
        self.text_roots = set([re.split(r"(?<!\\)\.", header[0])[0].replace(r"\.", ".") for header in list(head_annotations.keys())])
        head_annotations = dict(((k[0].replace(r"\.", "."), k[1]), v) for k, v in list(head_annotations.items()))
        self.head_annotations = head_annotations
        self.skip_if_empty = skip_if_empty
        self.skip_entities = skip_entities
        self.skipped_elems = skipped_elems
        self.skipped = {}
        self.autoclose = autoclose
        self.allow_xml_chars = allow_xml_chars
        self.can_overlap = can_overlap
        self.prefix = prefix
        self.textfile = textfile
        self.position = 0
        # self.max_nr_zeros = len(str(corpus_size))
        self.pos2anchor = {}
        self.anchor2pos = {}
        self.anchor2line = {}
        self.textbuffer = []
        self.dbs = dict((annot, {}) for annots in list(elem_annotations.values()) for annot in annots)
        self.header_temp = dict((header, "") for header in list(head_annotations.values()))
        self.header_dbs = dict((header, {}) for header in list(head_annotations.values()))
        util.resetIdent(self.prefix, maxidents=corpus_size)

    def pos(self):
        return "{%d:%d} " % self.getpos()

    def close(self):
        """This should be called at the end of the file. If in parser mode,
        it saves the corpus text and the annotations to files.
        """
        while self.tagstack:
            t, a, _ = self.tagstack[0]
            if t not in self.autoclose:
                util.log.error(self.pos() + "(at EOF) Autoclosing tag </%s>, starting at %s", t, a)
                self.errors = True
            else:
                util.log.info(self.pos() + "(at EOF) Autoclosing tag </%s>, starting at %s", t, a)
            self.handle_endtag(t)
        self.anchor()

        if self.skipped:
            new_elements = sorted(list(self.skipped.items()), key=lambda x: (-x[1], x[0]))
            new_elements_ann = " ".join(".".join([x[0][0].replace(":", "_"), x[0][1]]) if not x[0][1] is None else x[0][0].replace(":", "_") for x in new_elements)
            new_elements_ele = " ".join(":".join([x[0][0].replace(":", "\\:"), x[0][1]]) if not x[0][1] is None else x[0][0].replace(":", "\\:") for x in new_elements)
            if not self.elem_annotations:
                util.log.info("Found elements:")
                print()
                print("vrt_structs_annotations = " + new_elements_ann)
                print("vrt_structs             = " + new_elements_ele)
                print("xml_elements    = " + new_elements_ele)
                print("xml_annotations = " + new_elements_ann)
                print()
            else:
                print()
                print("xml_skip = " + new_elements_ele)
                print()

        # Only save results if no errors occured
        if not self.errors:
            text = u"".join(self.textbuffer)
            util.write_corpus_text(self.textfile, text, self.pos2anchor)
            if self.elem_order:
                for elem in self.elem_order:
                    annot, db = elem[1], self.dbs[elem[1]]
                    util.write_annotation(annot, db)
            else:
                for annot, db in list(self.dbs.items()):
                    util.write_annotation(annot, db)
            for header, db in list(self.header_dbs.items()):
                util.write_annotation(header, db)

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
            self.anchor2line[anchor] = "(%d:%d)" % self.getpos()
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
        path = ".".join(tag[0] for tag in reversed(self.tagstack))
        path = path + "." + name if path else name
        if path in self.header_elem or name in self.header_elem or self.inside_header:
            self.inside_header = True
            # return

        elem_attrs = attrs + [("", "")]
        if not self.inside_header:
            # Check if we are skipping this element
            for attr, value in elem_attrs:
                elem = (name, attr)
                if not (elem in self.elem_annotations or elem in self.skipped_elems or (attr != "" and (name, "*") in self.skipped_elems)):
                    self.skipped_elems.add(elem)
                    if attr:
                        if (name, "") in self.elem_annotations:
                            util.log.warning(self.pos() + "Skipping XML attribute <%s %s=%s>", name, attr, value)
                            self.skipped[(name, attr)] = len(self.tagstack)
                        else:
                            util.log.warning(self.pos() + "Skipping XML element <%s %s=%s>", name, attr, value)
                            self.skipped[(name, attr)] = len(self.tagstack)
                    elif not attrs:
                        util.log.warning(self.pos() + "Skipping XML element <%s>", name)
                        self.skipped[(name, None)] = len(self.tagstack)

        # We use a reversed stack (push from the left), to simplify
        # searching for elements below the top of the stack:
        self.tagstack.insert(0, (name, self.anchor(), elem_attrs))
        # Should we automatically close this tag?
        if name in self.autoclose:
            self.handle_endtag(name)
            self.anchor()

    def handle_endtag(self, name):
        """When there is a closing tag, we look for the matching open tag
        in the stack. Since we allow overlapping elements, the open tag
        need not be first in the stack.

        We create an edge from the name, start and end anchor, and add it
        to the corresponding annotation. Each xml attr also gets added to
        an annotation. The annotation group depends on the tag name.
        """
        # Retrieve the open tag in the tagstack:
        try:
            ix = [t[0] for t in self.tagstack].index(name)
        except ValueError:
            util.log.error(self.pos() + "Closing element </%s>, but it is not open", name)
            self.errors = True
            return

        name, start, attrs = self.tagstack.pop(ix)

        if self.inside_header:
            path = ".".join(tag[0] for tag in reversed(self.tagstack))
            path = path + "." + name if path else name
            self.inside_header = (path not in self.header_elem and name not in self.header_elem)
            name = ".".join(tag[0] for tag in reversed(self.tagstack)) + "." + name
            for attr, value in attrs:
                try:
                    annotation = self.head_annotations[name, attr]
                    self.header_temp[annotation] = value
                except KeyError:
                    pass
        else:
            end = self.anchor()
            overlaps = [t[:2] for t in self.tagstack[:ix]
                        if ((name, t[0]) not in self.can_overlap and (name, "*") not in self.can_overlap and (t[0], "*") not in self.can_overlap)]
            if overlaps:
                overlapping_elems = ["<%s> [%s:]" % (t[0], self.anchor2line[t[1]]) for t in overlaps]
                util.log.warning(self.pos() + "Tag <%s> [%s:%s], overlapping with %s",
                                 name, self.anchor2line[start], self.anchor2line[end], ", ".join(overlapping_elems))

            if not ((start == end or (start < end and self.textbuffer[-1].strip() == "")) and name in self.skip_if_empty):
                edge = util.mkEdge(name, (start, end))
                for attr, value in attrs:
                    try:
                        annotations = self.elem_annotations[name, attr]
                        for annotation in annotations:
                            self.dbs[annotation][edge] = value
                    except KeyError:
                        pass

            if name in self.text_roots and not self.tagstack:
                headedge = util.mkEdge("header", (start, end))
                for headann, headval in list(self.header_temp.items()):
                    self.header_dbs[headann][headedge] = headval
                    self.header_temp[headann] = ""

    def handle_data(self, content):
        """Plain text data are tokenized and each 'token' is added to the text."""
        if not self.allow_xml_chars:
            if "&" in content:
                util.log.error(self.pos() + "XML special character: &")
                self.errors = True
            if "<" in content:
                util.log.error(self.pos() + "XML special character: <")
                self.errors = True
            if ">" in content:
                util.log.error(self.pos() + "XML special character: >")
                self.errors = True
        if self.position == 0 and isinstance(content, str):
            content = content.lstrip(u"\ufeff")
        if self.inside_header:
            element_path = ".".join(tag[0] for tag in reversed(self.tagstack))
            if (element_path, "TEXT") in self.head_annotations:
                self.header_temp[self.head_annotations[(element_path, "TEXT")]] += re.sub(r"\s{2,}", " ", content)
            return
        for token in REGEXP_TOKEN.split(content):
            self.add_token(token)

    def handle_charref(self, name):
        """Character references &#nnn; are translated to unicode."""
        entity = '#' + name
        if name in self.skip_entities:
            return
        if problematic_entity(entity):
            util.log.error(self.pos() + "Control character reference: &%s;", entity)
            self.errors = True
            return
        if name.startswith('x'):
            code = int(name[1:], 16)
        else:
            code = int(name)

        if self.inside_header:
            element_path = ".".join(tag[0] for tag in reversed(self.tagstack))
            if (element_path, "TEXT") in self.head_annotations:
                self.header_temp[self.head_annotations[(element_path, "TEXT")]] += chr(code)
            return
        self.add_token(chr(code))

    def handle_entityref(self, name):
        """Entity refs &bullet; are looked up in a database and
        added as single tokens.
        """
        if name in self.skip_entities:
            return
        if problematic_entity(name):
            util.log.error(self.pos() + "Unknown HTML entity: &%s;", name)
            self.errors = True
            return
        code = html_entities[name]

        if self.inside_header:
            element_path = ".".join(tag[0] for tag in reversed(self.tagstack))
            if (element_path, "TEXT") in self.head_annotations:
                self.header_temp[self.head_annotations[(element_path, "TEXT")]] += chr(code)
            return

        self.add_token(chr(code))

    def handle_comment(self, comment):
        """XML comments are added as annotations themselves."""
        if "--" in comment or comment.endswith('-'):
            util.log.error(self.pos() + "Comment contains '--' or ends with '-'")
            self.errors = True
        if self.inside_header:
            # We skip everything in the header for now, so no need to warn about a skipped comment here
            # util.log.warning(self.pos() + "[SKIPPING] Comment in TEI header")
            return
        util.log.info(self.pos() + "Comment: %d characters wide", len(comment))
        self.handle_starttag('comment', [('value', comment)])
        self.handle_endtag('comment')

    def handle_pi(self, data):
        """XML processing instructions are not allowed,
        except for the single <?XML...> on the first line.
        """
        if data.startswith(u'xml ') and data.endswith(u'?'):
            if not (self.getpos()[0] == 1 and self.getpos()[1] <= 1):
                util.log.error(self.pos() + "XML declaration not first in file")
                self.errors = True
        else:
            util.log.error(self.pos() + "Unknown processing instruction: <?%s>", data)
            self.errors = True

    def handle_decl(self, decl):
        """SGML declarations <!...> are not allowed."""
        util.log.info(self.pos() + "SGML declaration: <!%s>", decl)


######################################################################

if __name__ == '__main__':
    util.run.main(parse)
