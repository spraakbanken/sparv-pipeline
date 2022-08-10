"""Parse XML source file."""

import copy
import re
import unicodedata
import xml.etree.ElementTree as etree
from itertools import chain
from typing import List

from sparv.api import (Config, Headers, Namespaces, Output, Source, SourceFilename, SourceStructure,
                       SourceStructureParser, SparvErrorMessage, Text, get_logger, importer, util)

logger = get_logger(__name__)


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
    Config("xml_import.elements", [], description="List of elements and attributes in source file. Only needed for "
                                                  "renaming or when used as input to other annotations, as everything "
                                                  "is parsed whether listed or not."),
    Config("xml_import.skip", [], description="Elements and attributes to skip. "
                                              "Use elementname:@contents to skip contents as well."),
    Config("xml_import.header_elements", [], description="Elements containing header metadata. Contents will not be "
                                                         "included in corpus text."),
    Config("xml_import.header_data", [], description="List of header elements and attributes from which to extract "
                                                     "metadata."),
    Config("xml_import.prefix", "", description="Optional prefix to add to annotation names."),
    Config("xml_import.remove_namespaces", False, description="Remove XML namespaces upon import."),
    Config("xml_import.encoding", util.constants.UTF8, description="Encoding of source file. Defaults to UTF-8."),
    Config("xml_import.keep_control_chars", False, description="Set to True if control characters should not be "
                                                               "removed from the text."),
    Config("xml_import.normalize", "NFC", description="Normalize input using any of the following forms: "
                                                      "'NFC', 'NFKC', 'NFD', and 'NFKD'.")
], structure=XMLStructure)
def parse(filename: SourceFilename = SourceFilename(),
          source_dir: Source = Source(),
          elements: list = Config("xml_import.elements"),
          skip: list = Config("xml_import.skip"),
          header_elements: list = Config("xml_import.header_elements"),
          header_data: list = Config("xml_import.header_data"),
          prefix: str = Config("xml_import.prefix"),
          remove_namespaces: bool = Config("xml_import.remove_namespaces"),
          encoding: str = Config("xml_import.encoding"),
          keep_control_chars: bool = Config("xml_import.keep_control_chars"),
          normalize: str = Config("xml_import.normalize")):
    """Parse XML source file and create annotation files.

    Args:
        filename: Source filename.
        source_dir: Directory containing source files.
        elements: List of elements and attributes in source file. Only needed for renaming, as everything is
            parsed whether listed or not.
        skip: Elements and attributes to skip. Use elementname:@contents to skip contents as well.
        header_elements: Elements containing header metadata. Contents will not be included in corpus text.
        header_data: List of header elements and attributes from which to extract metadata.
        prefix: Optional prefix to add to annotations.
        encoding: Encoding of source file. Defaults to UTF-8.
        keep_control_chars: Set to True to keep control characters in the text.
        normalize: Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            Defaults to 'NFC'.
    """
    parser = SparvXMLParser(elements, skip, header_elements, header_data, source_dir, encoding, prefix,
                            remove_namespaces, keep_control_chars, normalize)
    parser.parse(filename)
    parser.save()


class SparvXMLParser:
    """XML parser class for parsing XML."""

    def __init__(self, elements: list, skip: list, header_elements: list, header_data: list, source_dir: Source,
                 encoding: str = util.constants.UTF8, prefix: str = "", remove_namespaces: bool = False,
                 keep_control_chars: bool = True, normalize: str = "NFC"):
        """Initialize XML parser."""
        self.source_dir = source_dir
        self.encoding = encoding
        self.keep_control_chars = keep_control_chars
        self.normalize = normalize
        self.file = None
        self.prefix = prefix
        self.remove_namespaces = remove_namespaces
        self.header_elements = header_elements
        self.header_data = {}
        self.unprocessed_header_data_elems = set()

        self.targets = {}  # Index of elements and attributes that will be renamed during import
        self.data = {}  # Metadata collected during parsing
        self.text = []  # Text data of the source file collected during parsing
        self.namespace_mapping = {}  # Mapping of namespace prefix --> uri
        self.namespace_mapping_reversed = {}  # Mapping of uri --> namespace prefix

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
        for element, target in sorted(util.misc.parse_annotation_list(elements)):
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

        for header in header_data:
            header_source, _, header_target = header.partition(" as ")
            if not header_target:
                raise SparvErrorMessage("The header '{}' needs to be bound to a target element.".format(header))
            header_source, _, header_source_attrib = header_source.partition(":")
            header_source_root, _, header_source_rest = header_source.partition("/")
            self.header_data.setdefault(header_source_root, {})
            self.header_data[header_source_root].setdefault(header_source_rest, [])
            self.header_data[header_source_root][header_source_rest].append({
                "source": header_source_attrib,
                "target": elsplit(header_target)
            })
            self.unprocessed_header_data_elems.add(header_source_root)

        self.skipped_elems = set(elsplit(elem) for elem in skip)
        assert self.skipped_elems.isdisjoint(all_elems), "skip and elements must be disjoint"

    def parse(self, file):
        """Parse XML and build data structure."""
        self.file = file
        header_data = {}
        source_file = self.source_dir.get_path(self.file, ".xml")

        def handle_element(element):
            """Handle element renaming, skipping and collection of data."""
            start, start_subpos, end, end_subpos, name_orig, attrs = element

            # Handle possible skipping of element and attributes
            if (name_orig, "") in self.skipped_elems:
                return
            if (name_orig, "*") in self.skipped_elems:
                attrs = {}
            for attr in attrs.copy():
                attr_name = get_sparv_name(attr)
                if (name_orig, attr_name) in self.skipped_elems:
                    attrs.pop(attr)

            if name_orig in self.targets:
                # Rename element and/or attributes
                name = self.targets[name_orig]["target"]
                attrs_tmp = {}
                for attr in attrs:
                    attr_name = get_sparv_name(attr)
                    attrs_tmp[self.targets[name_orig]["attrs"].get(attr_name, attr_name)] = attrs[attr]
                attrs = attrs_tmp
            else:
                name = name_orig

            # Save attrs in data
            self.data.setdefault(name, {"attrs": set(), "elements": []})
            attr_keys = [get_sparv_name(attr) for attr in attrs.keys()]
            self.data[name]["attrs"].update(set(attr_keys))

            # Add attribute data collected from header
            if name in header_data:
                attrs.update(header_data[name])
                self.data[name]["attrs"].update(set(header_data[name].keys()))
                del header_data[name]

            attrs = {get_sparv_name(k): v for k, v in attrs.items()}
            self.data[name]["elements"].append(
                (start, start_subpos, end, end_subpos, name_orig, attrs)
            )

        def handle_raw_header(element: etree.Element, tag_name: str, start_pos: int, start_subpos: int):
            """Save full header XML as string."""
            # Save header as XML
            tmp_element = copy.deepcopy(element)
            tmp_element.tail = ""
            if self.remove_namespaces:
                for e in tmp_element.iter():
                    remove_namespaces(e)
            self.data.setdefault(tag_name, {"attrs": {util.constants.HEADER_CONTENTS}, "elements": []})
            self.data[tag_name]["elements"].append(
                (start_pos, start_subpos, start_pos, start_subpos, tag_name,
                 {util.constants.HEADER_CONTENTS: etree.tostring(tmp_element, method="xml", encoding="UTF-8").decode()})
            )
            handle_header_data(element, tag_name)

        def handle_header_data(element: etree.Element, tag_name: str = None):
            """Extract header metadata."""
            if tag_name in self.unprocessed_header_data_elems:
                self.unprocessed_header_data_elems.remove(tag_name)
            for e in element.iter():
                if self.remove_namespaces:
                    remove_namespaces(e)
                else:
                    # Extract and register all namespaces from the header and its children
                    get_sparv_name(e.tag)
            for header_path, header_sources in self.header_data.get(tag_name, {}).items():
                if not header_path:
                    header_element = element
                else:
                    xpath = annotation_to_xpath(header_path)
                    header_element = element.find(xpath)

                if header_element is not None:
                    for header_source in header_sources:
                        if header_source["source"]:
                            source_name = annotation_to_xpath(header_source["source"])
                            header_value = header_element.attrib.get(source_name)
                        else:
                            header_value = header_element.text.strip()

                        if header_value:
                            header_data.setdefault(header_source["target"][0], {})
                            header_data[header_source["target"][0]][header_source["target"][1]] = header_value
                else:
                    logger.warning(f"Header data '{tag_name}/{header_path}' was not found in source data.")

        def iter_ns_declarations():
            """Iterate over namespace declarations in the source file."""
            for _, (prefix, uri) in etree.iterparse(source_file, events=["start-ns"]):
                self.namespace_mapping[prefix] = uri
                self.namespace_mapping_reversed[uri] = prefix
                yield prefix, uri

        def get_sparv_name(xml_name: str):
            """Get the sparv notation of a tag or attr name with regards to XML namespaces."""
            ns_uri, tag = get_namespace(xml_name)
            if self.remove_namespaces:
                return tag
            tag_name = xml_name
            if ns_uri:
                ns_prefix = self.namespace_mapping_reversed.get(ns_uri, "")
                if not ns_prefix:
                    for prefix, uri in iter_ns_declarations():
                        if uri == ns_uri:
                            ns_prefix = prefix
                            break
                tag_name = f"{ns_prefix}{util.constants.XML_NAMESPACE_SEP}{tag}"
            return tag_name

        def annotation_to_xpath(path: str):
            """Convert a sparv header path into a real xpath."""
            sep = re.escape(util.constants.XML_NAMESPACE_SEP)
            m = re.finditer(fr"([^/+:]+){sep}", path) or []
            for i in m:
                uri = "{" + self.namespace_mapping[i.group(1)] + "}"
                path = re.sub(re.escape(i.group(0)), uri, path, count=1)
            return path

        def remove_namespaces(element: etree.Element):
            """Remove namespaces from element and its attributes."""
            uri, _ = get_namespace(element.tag)
            if uri:
                element.tag = element.tag[len("{" + uri + "}"):]
            for k in list(element.attrib.keys()):
                uri, _ = get_namespace(k)
                if uri:
                    element.set(k[len("{" + uri + "}"):], element.attrib[k])
                    element.attrib.pop(k)

        def iter_tree(element: etree.Element, start_pos: int = 0, start_subpos: int = 0):
            """Walk through whole XML and handle elements and text data."""
            tag_name = get_sparv_name(element.tag)

            if (tag_name, "@contents") in self.skipped_elems:
                # Skip whole element and all its contents
                if element.tail:
                    self.text.append(element.tail)
                return 0, len(element.tail or ""), 0
            elif tag_name in self.header_elements:
                if element.tail:
                    self.text.append(element.tail)
                handle_raw_header(element, tag_name, start_pos, start_subpos)
                return 0, len(element.tail or ""), 0
            elif tag_name in self.header_data:
                handle_header_data(element, tag_name)
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
            handle_element([start_pos, start_subpos, end_pos, end_subpos, tag_name, element.attrib])
            if element.tail:
                self.text.append(element.tail)
            return element_length, len(element.tail or ""), end_subpos

        if self.keep_control_chars and not self.normalize:
            try:
                tree = etree.parse(source_file)
            except Exception as e:
                raise SparvErrorMessage(f"The XML input file could not be parsed. Error: {str(e)}")
            root = tree.getroot()
        else:
            text = source_file.read_text(encoding="utf-8")
            if not self.keep_control_chars:
                text = util.misc.remove_control_characters(text)
            if self.normalize:
                text = unicodedata.normalize(self.normalize, text)
            try:
                root = etree.fromstring(text)
            except Exception as e:
                raise SparvErrorMessage(f"The XML input file could not be parsed. Error: {str(e)}")

        iter_tree(root)

        if header_data:
            logger.warning("Some header data could not be bound to target elements.")

        if self.unprocessed_header_data_elems:
            logger.warning("{} header data element{} {} not found in source data: '{}'.".format(
                "Some" if len(self.unprocessed_header_data_elems) > 1 else "One",
                "s" if len(self.unprocessed_header_data_elems) > 1 else "",
                "were" if len(self.unprocessed_header_data_elems) > 1 else "was",
                "', '".join(self.unprocessed_header_data_elems)
            ))

    def save(self):
        """Save text data and annotation files to disk."""
        text = "".join(self.text)
        Text(self.file).write(text)
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
            if attributes and spans:
                attr_names, attr_values = list(zip(*attributes.items()))
                spans, *attr_values = list(zip(*sorted(zip(spans, *attr_values), key=lambda x: x[0])))
                attributes = dict(zip(attr_names, attr_values))
            else:
                spans.sort()

            Output(full_element, source_file=self.file).write(spans)

            for attr in attributes:
                full_attr = "{}.{}".format(self.prefix, attr) if self.prefix else attr
                Output("{}:{}".format(full_element, full_attr), source_file=self.file).write(attributes[attr],
                                                                                             allow_newlines=is_header)
                if element not in self.header_elements:
                    structure.append("{}:{}".format(full_element, full_attr))

        # Save list of all elements and attributes to a file (needed for export)
        SourceStructure(self.file).write(structure)

        if header_elements:
            # Save list of all header elements to a file
            Headers(self.file).write(header_elements)

        # Save namespace mapping (URI to prefix)
        if self.namespace_mapping:
            Namespaces(self.file).write(self.namespace_mapping)


def get_namespace(xml_name: str):
    """Search for a namespace in tag and return a tuple (URI, tagname)."""
    m = re.match(r"\{(.*)\}(.+)", xml_name)
    return (m.group(1), m.group(2)) if m else ("", xml_name)


def analyze_xml(source_file):
    """Analyze an XML file and return a list of elements and attributes."""
    elements = set()

    parser = etree.iterparse(source_file, events=("start-ns", "start"))
    event, root = next(parser)
    namespace_map = {}

    for event, element in chain([(event, root)], parser):
        if event == "start-ns":
            prefix, uri = element
            namespace_map[uri] = prefix
        elif event == "start":
            tagname = element.tag
            uri, tag = get_namespace(tagname)
            if uri:
                prefix = namespace_map[uri]
                tagname = f"{prefix}{util.constants.XML_NAMESPACE_SEP}{tag}"
            elements.add(tagname)
            for attr in element.attrib:
                elements.add(f"{tagname}:{attr}")
            root.clear()

    return elements
