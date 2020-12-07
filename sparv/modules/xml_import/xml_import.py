"""Parse XML source file."""

import copy
import logging
import unicodedata
import xml.etree.ElementTree as etree
from itertools import chain
from pathlib import Path
from typing import List

from sparv import Config, Document, Headers, Output, OutputData, Source, SourceStructureParser, SourceStructure, Text, importer, util

log = logging.getLogger(__name__)


class XMLStructure(SourceStructureParser):
    """Class to get and store XML structure."""

    def setup(self):
        """Return setup wizard."""
        return {
            "type": "select",
            "name": "scan_xml",
            "message": "What type of scan do you want to do?",
            "choices": [
                {"name": "Scan ALL my files, since markup may differ between them "
                         "(this might take some time if the corpus is big).", "value": "all"},
                {"name": "Scan ONE of my files at random. All files contain the same markup, so scanning "
                         "one is enough.", "value": "one"}
            ]
        }

    def get_annotations(self, corpus_config: dict) -> List[str]:
        """Get, store and return XML structure."""
        if self.annotations is None:
            elements = set()
            xml_files = self.source_dir.glob("**/*.xml")
            if self.answers.get("scan_xml") == "all":
                for xml_file in xml_files:
                    elements = elements.union(analyze_xml(xml_file))
            else:
                elements = analyze_xml(next(xml_files))

            self.annotations = sorted(elements)
        return self.annotations


@importer("XML import", file_extension="xml", outputs=Config("xml_import.elements", []), config=[
    Config("xml_import.elements", [], description="List of elements and attributes in source document. Only needed for "
                                                  "renaming or when used as input to other annotations, as everything "
                                                  "is parsed whether listed or not."),
    Config("xml_import.skip", [], description="Elements and attributes to skip. "
                                              "Use elementname:@contents to skip contents as well."),
    Config("xml_import.header_elements", [], description="Elements containing header metadata. Contents will not be "
                                                         "included in corpus text."),
    Config("xml_import.header_data", [], description="List of header elements and attributes from which to extract "
                                                     "metadata."),
    Config("xml_import.prefix", "", description="Optional prefix to add to annotation names."),
    Config("xml_import.encoding", util.UTF8, description="Encoding of source document. Defaults to UTF-8."),
    Config("xml_import.keep_control_chars", False, description="Set to True if control characters should not be "
                                                               "removed from the text."),
    Config("xml_import.normalize", "NFC", description="Normalize input using any of the following forms: "
                                                      "'NFC', 'NFKC', 'NFD', and 'NFKD'.")
], structure=XMLStructure)
def parse(doc: Document = Document(),
          source_dir: Source = Source(),
          elements: list = Config("xml_import.elements"),
          skip: list = Config("xml_import.skip"),
          header_elements: list = Config("xml_import.header_elements"),
          header_data: list = Config("xml_import.header_data"),
          prefix: str = Config("xml_import.prefix"),
          encoding: str = Config("xml_import.encoding"),
          keep_control_chars: bool = Config("xml_import.keep_control_chars"),
          normalize: str = Config("xml_import.normalize")):
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
        keep_control_chars: Set to True to keep control characters in the text.
        normalize: Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            Defaults to 'NFC'.
    """
    parser = SparvXMLParser(elements, skip, header_elements, header_data, encoding, source_dir, prefix,
                            keep_control_chars, normalize)
    parser.parse(doc)
    parser.save()


class SparvXMLParser:
    """XML parser class for parsing XML."""

    def __init__(self, elements: list, skip: list, header_elements: list, headers: list, encoding: str = util.UTF8,
                 source_dir: str = "src", prefix: str = "", keep_control_chars: bool = True, normalize: str = "NFC"):
        """Initialize XML parser."""
        self.source_dir = source_dir
        self.encoding = encoding
        self.keep_control_chars = keep_control_chars
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
        renames = {}
        # Element list needs to be sorted to handle plain elements before attributes
        for element, target in sorted(util.parse_annotation_list(elements)):
            element, attr = elsplit(element)
            all_elems.add((element, attr))

            if target:
                # Element and/or attribute should be renamed during import
                if not attr:
                    renames[element] = target
                    target_element = target
                    target_attr = ""
                else:
                    target_element = renames.get(element, element)
                    target_attr = target
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
            self.headers[header_source_root].setdefault(header_source_rest, [])
            self.headers[header_source_root][header_source_rest].append({
                "source": header_source_attrib,
                "target": elsplit(header_target)
            })

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
            self.data.setdefault(element.tag, {"attrs": {util.HEADER_CONTENTS}, "elements": []})
            self.data[element.tag]["elements"].append(
                (start_pos, start_subpos, start_pos, start_subpos, element.tag,
                 {util.HEADER_CONTENTS: etree.tostring(tmp_element, method="xml", encoding="UTF-8").decode()})
            )

            handle_header_data(element)

        def handle_header_data(element: etree.Element):
            """Extract header metadata."""
            for header_path, header_sources in self.headers.get(element.tag, {}).items():
                if not header_path:
                    header_element = element
                else:
                    header_element = element.find(header_path)

                if header_element is not None:
                    for header_source in header_sources:
                        if header_source["source"]:
                            header_value = header_element.attrib.get(header_source["source"])
                        else:
                            header_value = header_element.text.strip()

                        if header_value:
                            header_data.setdefault(header_source["target"][0], {})
                            header_data[header_source["target"][0]][header_source["target"][1]] = header_value

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

        if self.keep_control_chars:
            tree = etree.parse(source_file)
            root = tree.getroot()
        else:
            with open(source_file) as f:
                text = f.read()
            text = util.remove_control_characters(text)
            root = etree.fromstring(text)

        iter_tree(root)

        if header_data:
            log.warning("Some header data could not be bound to target elements.")

    def save(self):
        """Save text data and annotation files to disk."""
        text = unicodedata.normalize("NFC", "".join(self.text))
        Text(self.doc).write(text)
        structure = []
        header_elements = []

        for element in self.data:
            is_header = False
            spans = []
            attributes = {attr: [] for attr in self.data[element]["attrs"]}
            for instance in self.data[element]["elements"]:
                start, start_subpos, end, end_subpos, _original_element, attrs = instance
                spans.append(((start, start_subpos), (end, end_subpos)))
                for attr in attributes:
                    attributes[attr].append(attrs.get(attr, ""))

            full_element = "{}.{}".format(self.prefix, element) if self.prefix else element

            if element in self.header_elements:
                is_header = True
                header_elements.append(full_element)
            else:
                structure.append(full_element)

            # Sort spans and annotations by span position (required by Sparv)
            if attributes:
                attr_names, attr_values = list(zip(*attributes.items()))
                spans, *attr_values = list(zip(*sorted(zip(spans, *attr_values), key=lambda x: x[0])))
                attributes = dict(zip(attr_names, attr_values))
            else:
                spans.sort()

            Output(full_element, doc=self.doc).write(spans)

            for attr in attributes:
                full_attr = "{}.{}".format(self.prefix, attr) if self.prefix else attr
                Output("{}:{}".format(full_element, full_attr), doc=self.doc).write(attributes[attr],
                                                                                    allow_newlines=is_header)
                if element not in self.header_elements:
                    structure.append("{}:{}".format(full_element, full_attr))

        # Save list of all elements and attributes to a file (needed for export)
        SourceStructure(self.doc).write(structure)

        if header_elements:
            # Save list of all header elements to a file
            Headers(self.doc).write(header_elements)


def analyze_xml(source_file):
    """Analyze an XML file and return a list of elements and attributes."""
    elements = set()

    parser = etree.iterparse(source_file, events=("start", "end"))
    event, root = next(parser)

    for event, element in chain([(event, root)], parser):
        if event == "start":
            elements.add(element.tag)
            for attr in element.attrib:
                elements.add(f"{element.tag}:{attr}")
            root.clear()

    return elements
