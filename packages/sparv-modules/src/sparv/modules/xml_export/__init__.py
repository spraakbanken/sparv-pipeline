"""XML export in various formats."""

from sparv.api import Config

from . import preserved_format, pretty, scrambled

__config__ = [
    Config(
        "xml_export.filename",
        default="{file}_export.xml",
        description="Filename pattern for resulting XML files, with '{file}' representing the source name.",
        datatype=str,
        pattern=r".*\{file\}.*",
    ),
    Config("xml_export.annotations", description="Sparv annotations to include.", datatype=list[str]),
    Config(
        "xml_export.source_annotations",
        description="List of annotations and attributes from the source data to include or exclude.\n\n"
        "All annotations will be included by default. If you list annotations here, only those will be included, "
        "unless you also include the special value '...'. Annotations and attributes can be renamed by using the "
        "following syntax:\n\n"
        "  - annotation as new_annotation_name\n"
        "  - annotation:attribute as new_attribute_name\n\n"
        "To exclude annotations or attributes, prefix them with 'not '. If `source_annotations` *only* contains "
        "annotations that are prefixed with 'not ', then all other annotations will be included by default, and "
        "'...' is not needed.",
        datatype=list[str],
    ),
    Config(
        "xml_export.header_annotations",
        description="List of headers from the source data to include.\n\n"
        "All headers will be included by default. The headers must first have been parsed by the importer, e.g. by "
        "using the `xml_import.header_elements` setting.",
        datatype=list[str],
    ),
    Config(
        "xml_export.include_empty_attributes",
        default=False,
        description="Whether to include attributes even when they are empty.",
        datatype=bool,
    ),
]
