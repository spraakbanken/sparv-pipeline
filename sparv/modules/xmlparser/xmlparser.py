import os
import unicodedata
import xml.etree.ElementTree as etree
from sparv import util
from sparv import *


@annotator("XML import.", importer=True)
def parse(doc: str = Document,
          source_dir: str = Source,
          elements: str = Config("xml_elements", []),
          skip: list = [],
          headers: list = [],
          header_elements: list = [],
          prefix: str = "",
          encoding: str = util.UTF8,
          normalize: str = "NFC"):
    """Parse XML source file and create annotation files."""
    if isinstance(elements, str):
        elements = elements.split()
    if isinstance(skip, str):
        skip = skip.split()
    if isinstance(headers, str):
        headers = headers.split()
    if isinstance(header_elements, str):
        header_annotations = header_elements.split()

    parser = SparvXMLParser(elements, skip, headers, header_elements, encoding, source_dir, prefix,
                            normalize)
    parser.parse(doc)
    parser.save()


class SparvXMLParser:
    """XML parser class for parsing XML."""

    def __init__(self, elements=[], skip=(), headers=[], header_elements=[], encoding=util.UTF8,
                 source_dir="src", prefix="", normalize="NFC"):

        self.source_dir = source_dir
        self.encoding = encoding
        self.normalize = normalize
        self.doc = None
        self.prefix = prefix

        self.pos = 0  # Current position in the text data
        self.subpos = 0  # Subposition for tags with same position
        self.tagstack = []
        self.targets = {}  # Index of elements and attributes that will be renamed during import
        self.data = {}  # Metadata collected during parsing
        self.text = []  # Text data of the document collected during parsing

        # Parse elements argument

        def elsplit(elem):
            elem = elem.replace(r"\:", ";")
            tag, _, attr = elem.partition(":")
            tag = tag.replace(";", ":")
            attr = attr.replace(";", ":")
            return tag, attr

        all_elems = set()
        for element in elements:
            element, _, target = element.partition(">")
            element, attr = elsplit(element)
            all_elems.add((element, attr))
            all_elems.add((element, ""))  # Make sure that the bare element is added as well

            if target:
                target_element, target_attr = elsplit(target)
                if element and attr:
                    assert target_element and target_attr
                self.targets.setdefault(element, {"attrs": {}})
                self.targets[element]["target"] = target_element
                self.data.setdefault(target_element, {"attrs": set(), "elements": []})
                if target_attr:
                    self.targets[element]["attrs"][attr] = target_attr
                    self.data[target_element]["attrs"].add(target_attr)
            else:
                self.data.setdefault(element, {"attrs": set(), "elements": []})
                if attr:
                    self.data[element]["attrs"].add(attr)

        # TODO: Headers

        self.skipped_elems = set(elsplit(elem) for elem in skip)
        assert self.skipped_elems.isdisjoint(all_elems), "skip and elements must be disjoint"

    def parse(self, doc):
        """Parse XML and build data structure."""
        self.doc = doc

        # Source path
        if ":" in doc:
            doc, _, doc_chunk = doc.partition(":")
            source_file = os.path.join(self.source_dir, doc, doc_chunk + ".xml")
        else:
            source_file = os.path.join(self.source_dir, doc + ".xml")

        def handle_element(element):
            start, start_subpos, end, end_subpos, name_orig, attrs = element

            # Handle possible skipping of element and attributes
            if (name_orig, "") in self.skipped_elems:
                return
            if (name_orig, "*") in self.skipped_elems:
                attrs = {}
            for attr in attrs.copy():
                if (name_orig, attr) in self.skipped_elems:
                    attrs.pop(attr)

            if name_orig in self.targets:
                name = self.targets[name_orig]["target"]
                attrs_tmp = {}
                for attr in attrs:
                    attrs_tmp[self.targets[name_orig]["attrs"].get(attr, attr)] = attrs[attr]
                attrs = attrs_tmp
            else:
                name = name_orig

            self.data.setdefault(name, {"attrs": set(), "elements": []})
            self.data[name]["attrs"].update(set(attrs.keys()))

            self.data[name]["elements"].append(
                (start, start_subpos, end, end_subpos, name_orig, attrs)
            )

        def iter_tree(element, start_pos=0, start_subpos=0):
            # Skip whole element and all its contents?
            if (element.tag, "@contents") in self.skipped_elems:
                if element.tail:
                    self.text.append(element.tail)
                return 0, len(element.tail or ""), 0
            element_length = 0
            if element.text:
                element_length = len(element.text)
                self.text.append(element.text)
            child_tail = None
            for child in element:
                if not element_length:
                    start_subpos += 1
                else:
                    start_subpos = 0
                child_length, child_tail, end_subpos = iter_tree(child, start_pos + element_length, start_subpos)
                element_length += child_length + child_tail
            end_pos = start_pos + element_length
            if child_tail == 0:
                end_subpos += 1
            else:
                end_subpos = 0
            handle_element([start_pos, start_subpos, end_pos, end_subpos, element.tag, element.attrib])
            if element.tail:
                self.text.append(element.tail)
            return element_length, len(element.tail or ""), end_subpos

        tree = etree.parse(source_file)
        root = tree.getroot()
        iter_tree(root)

    def save(self):
        """Save text data and annotation files to disk."""
        text = unicodedata.normalize("NFC", "".join(self.text))
        util.write_corpus_text(self.doc, text)
        structure = []

        for element in self.data:
            spans = []
            original_elements = []
            attributes = {attr: [] for attr in self.data[element]["attrs"]}
            for instance in self.data[element]["elements"]:
                start, start_subpos, end, end_subpos, original_element, attrs = instance
                spans.append(((start, start_subpos), (end, end_subpos)))
                original_elements.append(original_element)
                for attr in attributes:
                    attributes[attr].append(attrs.get(attr, ""))

            full_element = "{}.{}".format(self.prefix, element) if self.prefix else element
            util.write_annotation(self.doc, full_element, spans)
            # util.write_annotation(self.doc, "{}:@original".format(element), original_elements)
            structure.append(full_element)

            for attr in attributes:
                full_attr = "{}.{}".format(self.prefix, attr) if self.prefix else attr
                util.write_annotation(self.doc, "{}:{}".format(full_element, full_attr), attributes[attr])
                structure.append("{}:{}".format(full_element, full_attr))

        util.write_data(self.doc, "@structure", "\n".join(structure))


if __name__ == "__main__":
    util.run.main(parse)
