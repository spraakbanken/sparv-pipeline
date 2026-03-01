"""Parse XML source files."""

import copy
import operator
import re
import unicodedata
import xml.etree.ElementTree as etree  # noqa: N813
from collections.abc import Iterator
from itertools import chain
from pathlib import Path

from sparv.api import (
    Config,
    Headers,
    Namespaces,
    Output,
    Source,
    SourceFilename,
    SourceStructure,
    SourceStructureParser,
    SparvErrorMessage,
    Text,
    get_logger,
    importer,
    util,
)

logger = get_logger(__name__)


class XMLStructure(SourceStructureParser):
    """Class to get and store XML structure."""

    @staticmethod
    def setup() -> dict:
        """Return setup wizard."""
        return {
            "type": "select",
            "name": "scan_xml",
            "message": "What type of scan do you want to do?",
            "choices": [
                {
                    "name": "Scan ALL my files, since markup may differ between them "
                    "(this might take some time if the corpus is big).",
                    "value": "all",
                },
                {
                    "name": "Scan ONE of my files at random. All files contain the same markup, so scanning "
                    "one is enough.",
                    "value": "one",
                },
            ],
        }

    def get_annotations(self, corpus_config: dict) -> list[str]:  # noqa: ARG002
        """Get, store and return XML structure.

        Returns:
            List of elements and attributes in the XML file.
        """
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


@importer(
    "XML import",
    file_extension="xml",
    outputs=[Config("xml_import.elements"), Config("xml_import.header_data")],
    config=[
        Config(
            "xml_import.elements",
            [],
            description="List of elements and attributes present in the source files.\n\n"
            "All elements and attributes are parsed whether listed here or not, so this is only needed when using "
            "an element or attribute from the source files as input for another module, to let Sparv know where it "
            "comes from.\n\n"
            "Another use for this setting is to rename elements and attributes during import, using the following "
            "syntax:\n\n"
            "  - element as new_element_name\n"
            "  - element:attribute as new_attribute_name\n\n"
            "Note that this is usually not needed, as renames can be done during the export step instead.",
            datatype=list[str],
        ),
        Config(
            "xml_import.skip",
            [],
            description="List of elements and attributes to skip during import.\n\n"
            "Use `elementname:@contents` to skip contents as well.\n\n"
            "Using this without also skipping the contents is usually not needed, as you can control what is included "
            "during the export step instead.",
            datatype=list[str],
        ),
        Config(
            "xml_import.header_elements",
            [],
            description="List of elements whose contents should not be included in the corpus text, but may be "
            "included as-is in some output formats, e.g. XML.\n\n"
            "This is mainly used for header elements. If the main goal is to exclude elements or their contents, see "
            "`xml_import.skip` instead.\n\n"
            "For XML output, use the `xml_export.header_annotations` setting to specify which of these elements "
            "should be included or excluded. By default, all header elements are included.",
            datatype=list[str],
        ),
        Config(
            "xml_import.header_data",
            [],
            description="List of header elements and attributes from which to extract metadata.\n\n"
                "Use the following syntax:\n\n"
                "  - element:attribute as target_annotation:target_attribute\n"
                "  - element as target_annotation:target_attribute\n"
                "  - element/nested_element/nested_element:attribute as target_annotation:target_attribute\n\n"
                "Where `element` is the name of the header element, `attribute` is the name of the "
                "attribute to extract, and `target_annotation` is the name of the annotation to which the "
                "value should be bound under the name `target_attribute`. The `target_annotation` needs to be a parent "
                "or ancestor of the header.\n\n"
                "If the source `attribute` is omitted, the text content of the element will be used as the value.\n\n"
                "When using nested elements, the first `element` should is the name of the root header element, and "
                "the rest of the path is the nested element(s).\n\n"
                "This setting is separate from the `xml_import.header_elements` setting, and can be used with or "
                "without it. Without `xml_import.header_elements`, the header data will both be extracted as metadata "
                "and included in the corpus text.",
            datatype=list[str],
        ),
        Config("xml_import.prefix", description="Optional prefix to add to annotation names.", datatype=str),
        Config("xml_import.remove_namespaces", False, description="Remove XML namespaces upon import.", datatype=bool),
        Config(
            "xml_import.encoding",
            util.constants.UTF8,
            description="Encoding of source file. Defaults to UTF-8.",
            datatype=str,
        ),
        Config(
            "xml_import.keep_control_chars",
            False,
            description="Set to `true` if control characters should not be removed from the text.",
            datatype=bool,
        ),
        Config(
            "xml_import.keep_unassigned_chars",
            False,
            description="Set to `true` to keep unassigned characters.",
            datatype=bool,
        ),
        Config(
            "xml_import.normalize",
            default="NFC",
            description="Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.",
            datatype=str,
            choices=("NFC", "NFKC", "NFD", "NFKD"),
        ),
    ],
    structure=XMLStructure,
)
def parse(
    filename: SourceFilename = SourceFilename(),
    source_dir: Source = Source(),
    elements: list = Config("xml_import.elements"),
    skip: list = Config("xml_import.skip"),
    header_elements: list = Config("xml_import.header_elements"),
    header_data: list = Config("xml_import.header_data"),
    prefix: str | None = Config("xml_import.prefix"),
    remove_namespaces: bool = Config("xml_import.remove_namespaces"),
    encoding: str = Config("xml_import.encoding"),
    keep_control_chars: bool = Config("xml_import.keep_control_chars"),
    keep_unassigned_chars: bool = Config("xml_import.keep_unassigned_chars"),
    normalize: str = Config("xml_import.normalize"),
) -> None:
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
        remove_namespaces: Set to True to remove any namespaces.
        encoding: Encoding of source file. Defaults to UTF-8.
        keep_control_chars: Set to True to keep control characters in the text.
        keep_unassigned_chars: Set to True to keep unassigned characters.
        normalize: Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
            Defaults to 'NFC'.
    """
    parser = SparvXMLParser(
        elements,
        skip,
        header_elements,
        header_data,
        source_dir,
        encoding,
        prefix,
        remove_namespaces,
        keep_control_chars,
        keep_unassigned_chars,
        normalize,
    )
    parser.parse(filename)
    parser.save()


class SparvXMLParser:
    """XML parser class for parsing XML."""

    def __init__(
        self,
        elements: list,
        skip: list,
        header_elements: list,
        header_data: list,
        source_dir: Source,
        encoding: str = util.constants.UTF8,
        prefix: str | None = None,
        remove_namespaces: bool = False,
        keep_control_chars: bool = False,
        keep_unassigned_chars: bool = False,
        normalize: str = "NFC",
    ) -> None:
        """Initialize XML parser.

        Args:
            elements: List of elements and attributes in source file. Only needed for renaming, as everything is
                parsed whether listed or not.
            skip: Elements and attributes to skip. Use elementname:@contents to skip contents as well.
            header_elements: Elements containing header metadata. Contents will not be included in corpus text.
            header_data: List of header elements and attributes from which to extract metadata.
            source_dir: Directory containing source files.
            encoding: Encoding of source file. Defaults to UTF-8.
            prefix: Optional prefix to add to annotations.
            remove_namespaces: Set to True to remove any namespaces.
            keep_control_chars: Set to True to keep control characters in the text.
            keep_unassigned_chars: Set to True to keep unassigned characters.
            normalize: Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
                Defaults to 'NFC'.

        Raises:
            SparvErrorMessage: If the XML source file could not be parsed.
        """
        self.source_dir = source_dir
        self.encoding = encoding
        self.keep_control_chars = keep_control_chars
        self.keep_unassigned_chars = keep_unassigned_chars
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

        def elsplit(elem: str) -> tuple[str, str]:
            """Split element and attribute.

            Args:
                elem: Element string to split.

            Returns:
                Tuple containing the element and attribute names.
            """
            elem = elem.replace(r"\:", ";")
            tag, _, attr = elem.partition(":")
            tag = tag.replace(";", ":")
            attr = attr.replace(";", ":")
            return tag, attr

        all_elems = set()
        renames = {}
        # Element list needs to be sorted to handle plain elements before attributes
        for element, target in sorted(util.misc.parse_annotation_list(elements)):
            element, attr = elsplit(element)  # noqa: PLW2901
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
                raise SparvErrorMessage(f"The header '{header}' needs to be bound to a target element.")
            header_source, _, header_source_attrib = header_source.partition(":")
            header_source_root, _, header_source_rest = header_source.partition("/")
            self.header_data.setdefault(header_source_root, {})
            self.header_data[header_source_root].setdefault(header_source_rest, [])
            self.header_data[header_source_root][header_source_rest].append(
                {"source": header_source_attrib, "target": elsplit(header_target)}
            )
            self.unprocessed_header_data_elems.add(header_source_root)

        self.skipped_elems = {elsplit(elem) for elem in skip}
        assert self.skipped_elems.isdisjoint(all_elems), "skip and elements must be disjoint"

    def parse(self, file: SourceFilename) -> None:
        """Parse XML and build data structure.

        Args:
            file: Source filename.

        Raises:
            SparvErrorMessage: If the XML source file could not be parsed.
        """
        self.file = file
        header_data = {}
        source_file = self.source_dir.get_path(self.file, ".xml")

        def handle_element(element: list) -> None:
            """Handle element renaming, skipping and collection of data."""
            start, start_subpos, end, end_subpos, name_orig, attrs = element

            # Handle possible skipping of element and attributes
            if self.skipped_elems:
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
            attr_keys = [get_sparv_name(attr) for attr in attrs]
            self.data[name]["attrs"].update(set(attr_keys))

            # Add attribute data collected from header
            if name in header_data:
                attrs.update(header_data[name])
                self.data[name]["attrs"].update(set(header_data[name].keys()))
                del header_data[name]

            attrs = {get_sparv_name(k): v for k, v in attrs.items()}
            self.data[name]["elements"].append((start, start_subpos, end, end_subpos, name_orig, attrs))

        def handle_raw_header(element: etree.Element, tag_name: str, start_pos: int, start_subpos: int) -> None:
            """Save full header XML as string."""
            # Save header as XML
            tmp_element = copy.deepcopy(element)
            tmp_element.tail = ""
            if self.remove_namespaces:
                for e in tmp_element.iter():
                    remove_namespaces(e)
            self.data.setdefault(tag_name, {"attrs": {util.constants.HEADER_CONTENTS}, "elements": []})
            self.data[tag_name]["elements"].append(
                (
                    start_pos,
                    start_subpos,
                    start_pos,
                    start_subpos,
                    tag_name,
                    {
                        util.constants.HEADER_CONTENTS: etree.tostring(
                            tmp_element, method="xml", encoding="UTF-8"
                        ).decode()
                    },
                )
            )
            handle_header_data(element, tag_name)

        def handle_header_data(element: etree.Element, tag_name: str | None = None) -> None:
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
                    logger.warning("Header data '%s/%s' was not found in source data.", tag_name, header_path)

        def iter_ns_declarations() -> Iterator[tuple[str, str]]:
            """Iterate over namespace declarations in the source file.

            Yields:
                tuple: Namespace prefix and URI.
            """
            for _, (prefix, uri) in etree.iterparse(source_file, events=["start-ns"]):
                self.namespace_mapping[prefix] = uri
                self.namespace_mapping_reversed[uri] = prefix
                yield prefix, uri

        def get_sparv_name(xml_name: str) -> str:
            """Return the sparv notation of a tag or attr name with regard to XML namespaces."""
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

        def annotation_to_xpath(path: str) -> str:
            """Convert a sparv header path into a real xpath.

            Args:
                path: The sparv header path to convert.

            Returns:
                The converted xpath.
            """
            sep = re.escape(util.constants.XML_NAMESPACE_SEP)
            m = re.finditer(rf"([^/+:]+){sep}", path) or []
            for i in m:
                uri = "{" + self.namespace_mapping[i.group(1)] + "}"
                path = re.sub(re.escape(i.group(0)), uri, path, count=1)
            return path

        def remove_namespaces(element: etree.Element) -> None:
            """Remove namespaces from element and its attributes."""
            uri, _ = get_namespace(element.tag)
            if uri:
                element.tag = element.tag[len("{" + uri + "}") :]
            for k in element.attrib.copy():
                uri, _ = get_namespace(k)
                if uri:
                    element.set(k[len("{" + uri + "}") :], element.attrib[k])
                    element.attrib.pop(k)

        def iter_tree(element: etree.Element, start_pos: int = 0, start_subpos: int = 0) -> None:
            """Walk through whole XML and handle elements and text data."""
            tag_name = get_sparv_name(element.tag)

            if (tag_name, "@contents") in self.skipped_elems:
                # Skip whole element and all its contents
                if element.tail:
                    self.text.append(element.tail)
                return 0, len(element.tail or ""), 0
            if tag_name in self.header_elements:
                if element.tail:
                    self.text.append(element.tail)
                handle_raw_header(element, tag_name, start_pos, start_subpos)
                return 0, len(element.tail or ""), 0
            if tag_name in self.header_data:
                handle_header_data(element, tag_name)
            element_length = 0
            if element.text:
                element_length = len(element.text)
                self.text.append(element.text)
            child_tail = None
            for child in element:
                child_start_subpos = start_subpos + 1 if not element_length else 0
                child_length, child_tail, end_subpos = iter_tree(child, start_pos + element_length, child_start_subpos)
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

        if self.keep_control_chars and self.keep_unassigned_chars and not self.normalize:
            try:
                tree = etree.parse(source_file)
            except Exception as e:
                raise SparvErrorMessage(f"The XML source file could not be parsed. Error: {e!s}") from None
            root = tree.getroot()
        else:
            text = source_file.read_text(encoding="utf-8")
            if not self.keep_control_chars:
                text = util.misc.remove_control_characters(text)
            if not self.keep_unassigned_chars:
                text = util.misc.remove_unassigned_characters(text)
            if self.normalize:
                text = unicodedata.normalize(self.normalize, text)
            try:
                root = etree.fromstring(text)
            except Exception as e:
                raise SparvErrorMessage(f"The XML source file could not be parsed. Error: {e!s}") from None

        iter_tree(root)

        if header_data:
            logger.warning("Some header data could not be bound to target elements.")

        if self.unprocessed_header_data_elems:
            logger.warning(
                "%s header data element%s %s not found in source data: '%s'.",
                "Some" if len(self.unprocessed_header_data_elems) > 1 else "One",
                "s" if len(self.unprocessed_header_data_elems) > 1 else "",
                "were" if len(self.unprocessed_header_data_elems) > 1 else "was",
                "', '".join(self.unprocessed_header_data_elems),
            )

    def save(self) -> None:
        """Save text data and annotation files to disk."""
        text = "".join(self.text)
        Text(self.file).write(text)
        structure = []
        header_elements = []

        for element in self.data:
            spans = []
            attributes = {attr: [] for attr in self.data[element]["attrs"]}
            for instance in self.data[element]["elements"]:
                start, start_subpos, end, end_subpos, _original_element, attrs = instance
                spans.append(((start, start_subpos), (end, end_subpos)))
                for attr in attributes:  # noqa: PLC0206
                    attributes[attr].append(attrs.get(attr, ""))

            full_element = f"{self.prefix}.{element}" if self.prefix else element

            if element in self.header_elements:
                header_elements.append(full_element)
            else:
                structure.append(full_element)

            # Sort spans and annotations by span position (required by Sparv)
            if attributes and spans:
                attr_names, attr_values = list(zip(*attributes.items(), strict=True))
                spans, *attr_values = list(
                    zip(*sorted(zip(spans, *attr_values, strict=True), key=operator.itemgetter(0)), strict=True)
                )
                attributes = dict(zip(attr_names, attr_values, strict=True))
            else:
                spans.sort()

            Output(full_element, source_file=self.file).write(spans)

            for attr in attributes:
                full_attr = f"{self.prefix}.{attr}" if self.prefix else attr
                Output(f"{full_element}:{full_attr}", source_file=self.file).write(attributes[attr])
                if element not in self.header_elements:
                    structure.append(f"{full_element}:{full_attr}")

        # Save list of all elements and attributes to a file (needed for export)
        SourceStructure(self.file).write(structure)

        if header_elements:
            # Save list of all header elements to a file
            Headers(self.file).write(header_elements)

        # Save namespace mapping (URI to prefix)
        if self.namespace_mapping:
            Namespaces(self.file).write(self.namespace_mapping)


def get_namespace(xml_name: str) -> tuple[str, str]:
    """Search for a namespace in a tag and return a tuple (URI, tagname).

    Args:
        xml_name: The XML name to search for a namespace in.

    Returns:
        A tuple containing the namespace URI and the tag name.
    """
    m = re.match(r"\{(.*)}(.+)", xml_name)
    return (m.group(1), m.group(2)) if m else ("", xml_name)


def analyze_xml(source_file: Path) -> set:
    """Analyze an XML file and return a list of elements and attributes.

    Args:
        source_file: The XML file to analyze.

    Returns:
        A set of elements and attributes found in the XML file.
    """
    elements = set()

    parser = etree.iterparse(source_file, events=("start-ns", "start"))
    event, root = next(parser)
    namespace_map = {}

    for event, element in chain([(event, root)], parser):  # noqa: B020
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
            elements.update(f"{tagname}:{attr}" for attr in element.attrib)
            root.clear()

    return elements
