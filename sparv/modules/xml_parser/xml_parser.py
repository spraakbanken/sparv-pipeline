"""Parse XML source file."""

import copy
import logging
import unicodedata
import xml.etree.ElementTree as etree
from pathlib import Path

from sparv import Config, Document, Source, importer, util

log = logging.getLogger(__name__)


@importer("XML import", source_type="xml", outputs=Config("xml_parser.elements", []), config=[
    Config("xml_parser.elements", []),
    Config("xml_parser.skip", []),
    Config("xml_parser.header_elements", []),
    Config("xml_parser.header_data", []),
    Config("xml_parser.prefix", ""),
    Config("xml_parser.encoding", util.UTF8),
    Config("xml_parser.normalize", "NFC")
])
def parse(doc: Document = Document(),
          source_dir: Source = Source(),
          elements: list = Config("xml_parser.elements"),
          skip: list = Config("xml_parser.skip"),
          header_elements: list = Config("xml_parser.header_elements"),
          header_data: list = Config("xml_parser.header_data"),
          prefix: str = Config("xml_parser.prefix"),
          encoding: str = Config("xml_parser.encoding"),
          normalize: str = Config("xml_parser.normalize")):
    """Parse XML source file and create annotation files.

    Args:
        doc: Source document name.
        source_dir: Directory containing source documents.
        elements: List of elements and attributes in source document. Only needed for renaming, as everything is
            parsed whether listed or not.
        skip: Elements and attributes to skip. Use elementname:@contents to skip contents as well.
        header_elements: Elements containing header metadata. Contents will not be included in corpus text.
        header_data: List of header elements and attributes from which to extract metadata.
        prefix: Optional prefix to add to annotations.
        encoding: Encoding of source document. Defaults to UTF-8.
        normalize: Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            Defaults to 'NFC'.
    """
    parser = SparvXMLParser(elements, skip, header_elements, header_data, encoding, source_dir, prefix,
                            normalize)
    parser.parse(doc)
    parser.save()


class SparvXMLParser:
    """XML parser class for parsing XML."""

    def __init__(self, elements: list, skip: list, header_elements: list, headers: list, encoding: str = util.UTF8,
                 source_dir: str = "src", prefix: str = "", normalize: str = "NFC"):
        """Initialize XML parser."""
        self.source_dir = source_dir
        self.encoding = encoding
        self.normalize = normalize
        self.doc = None
        self.prefix = prefix
        self.header_elements = header_elements
        self.headers = {}

        self.pos = 0  # Current position in the text data
        self.subpos = 0  # Sub-position for tags with same position
        self.tagstack = []
        self.targets = {}  # Index of elements and attributes that will be renamed during import
        self.data = {}  # Metadata collected during parsing
        self.text = []  # Text data of the document collected during parsing

        # Parse elements argument

        def elsplit(elem):
            """Split element and attribute."""
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
            all_elems.add((element, ""))  # Make sure that the element without attributes is added as well

            if target:
                # Element and/or attribute should be renamed during import
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

        for header in headers:
            header_source, _, header_target = header.partition(" as ")
            if not header_target:
                raise util.SparvErrorMessage("The header '{}' needs to be bound to a target element.".format(header))
            header_source, _, header_source_attrib = header_source.partition(":")
            header_source_root, _, header_source_rest = header_source.partition("/")
            self.headers.setdefault(header_source_root, {})
            self.headers[header_source_root][header_source_rest] = {
                "source": header_source_attrib,
                "target": elsplit(header_target)
            }

        self.skipped_elems = set(elsplit(elem) for elem in skip)
        assert self.skipped_elems.isdisjoint(all_elems), "skip and elements must be disjoint"

    def parse(self, doc):
        """Parse XML and build data structure."""
        self.doc = doc
        header_data = {}

        # Source path
        if ":" in doc:
            doc, _, doc_chunk = doc.partition(":")
            source_file = Path(self.source_dir, doc, doc_chunk + ".xml")
        else:
            source_file = Path(self.source_dir, doc + ".xml")

        def handle_element(element):
            """Handle element renaming, skipping and collection of data."""
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
                # Rename element and/or attributes
                name = self.targets[name_orig]["target"]
                attrs_tmp = {}
                for attr in attrs:
                    attrs_tmp[self.targets[name_orig]["attrs"].get(attr, attr)] = attrs[attr]
                attrs = attrs_tmp
            else:
                name = name_orig

            self.data.setdefault(name, {"attrs": set(), "elements": []})
            self.data[name]["attrs"].update(set(attrs.keys()))

            # Add attribute data collected from header
            if name in header_data:
                attrs.update(header_data[name])
                self.data[name]["attrs"].update(set(header_data[name].keys()))
                del header_data[name]

            self.data[name]["elements"].append(
                (start, start_subpos, end, end_subpos, name_orig, attrs)
            )

        def handle_raw_header(element: etree.Element, start_pos: int, start_subpos: int):
            """Save full header XML as string."""
            # Save header as XML
            tmp_element = copy.deepcopy(element)
            tmp_element.tail = ""
            self.data.setdefault(element.tag, {"attrs": {util.HEADER_CONTENT}, "elements": []})
            self.data[element.tag]["elements"].append(
                (start_pos, start_subpos, start_pos, start_subpos, element.tag,
                 {util.HEADER_CONTENT: etree.tostring(tmp_element, method="xml", encoding="UTF-8").decode()})
            )

            handle_header_data(element)

        def handle_header_data(element: etree.Element):
            """Extract header metadata."""
            for header_path, header_info in self.headers.get(element.tag, {}).items():
                if not header_path:
                    header_element = element
                else:
                    header_element = element.find(header_path)

                if header_element is not None:
                    if header_info["source"]:
                        header_value = header_element.attrib.get(header_info["source"])
                    else:
                        header_value = header_element.text.strip()

                    if header_value:
                        header_data.setdefault(header_info["target"][0], {})
                        header_data[header_info["target"][0]][header_info["target"][1]] = header_value

        def iter_tree(element: etree.Element, start_pos: int = 0, start_subpos: int = 0):
            """Walk though whole XML and handle elements and text data."""
            if (element.tag, "@contents") in self.skipped_elems:
                # Skip whole element and all its contents
                if element.tail:
                    self.text.append(element.tail)
                return 0, len(element.tail or ""), 0
            elif element.tag in self.header_elements:
                if element.tail:
                    self.text.append(element.tail)
                handle_raw_header(element, start_pos, start_subpos)
                return 0, len(element.tail or ""), 0
            elif element.tag in self.headers:
                handle_header_data(element)
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

        if header_data:
            log.warning("Some header data could not be bound to target elements.")

    def save(self):
        """Save text data and annotation files to disk."""
        text = unicodedata.normalize("NFC", "".join(self.text))
        util.write_corpus_text(self.doc, text)
        structure = []
        header_elements = []

        for element in self.data:
            is_header = False
            spans = []
            attributes = {attr: [] for attr in self.data[element]["attrs"]}
            for instance in self.data[element]["elements"]:
                start, start_subpos, end, end_subpos, original_element, attrs = instance
                spans.append(((start, start_subpos), (end, end_subpos)))
                for attr in attributes:
                    attributes[attr].append(attrs.get(attr, ""))

            full_element = "{}.{}".format(self.prefix, element) if self.prefix else element

            if element in self.header_elements:
                is_header = True
                header_elements.append(full_element)
            else:
                structure.append(full_element)

            util.write_annotation(self.doc, full_element, spans)

            for attr in attributes:
                full_attr = "{}.{}".format(self.prefix, attr) if self.prefix else attr
                util.write_annotation(self.doc, "{}:{}".format(full_element, full_attr), attributes[attr],
                                      allow_newlines=is_header)
                if element not in self.header_elements:
                    structure.append("{}:{}".format(full_element, full_attr))

        # Save list of all elements and attributes to a file (needed for export)
        util.write_structure(self.doc, structure)

        if header_elements:
            # Save list of all header elements to a file
            util.write_data(self.doc, util.corpus.HEADERS_FILE, "\n".join(header_elements))
