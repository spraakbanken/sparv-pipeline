"""Settings related to export."""

from typing import Optional

from sparv.api import Config, SourceStructureParser, wizard

__config__ = [
    Config(
        "export.default",
        default=["xml_export:pretty"],
        description="List of exporters to use by default",
        datatype=list,
    ),
    Config("export.annotations", description="List of automatic annotations to include in export", datatype=list),
    Config(
        "export.source_annotations",
        description="List of annotations and attributes from the source to include",
        datatype=list,
    ),
    Config(
        "export.word", default="<token:word>", description="Annotation to use as token text in export", datatype=str
    ),
    Config(
        "export.remove_module_namespaces",
        default=True,
        description="Remove module name prefixes from annotation names in export",
        datatype=bool,
    ),
    Config(
        "export.sparv_namespace",
        default="",
        description="Prefix to add to the names of all automatically created annotations",
        datatype=str | None,
    ),
    Config(
        "export.source_namespace",
        default="",
        description="Prefix to add to the names of all annotations from source",
        datatype=str | None,
    ),
    Config(
        "export.scramble_on",
        default="<sentence>",
        description="What annotation to use as the smallest unit when scrambling",
        datatype=str,
    ),
]


@wizard(["export.source_annotations"], source_structure=True)
def import_wizard(answers: dict, structure: SourceStructureParser) -> list[dict]:
    """Return wizard for selecting what source annotations to keep."""
    return [
        {
            "type": "select",
            "name": "_keep_source",
            "message": "What existing annotations from the source files do you want to keep?",
            "choices": [
                {"name": "All of them", "value": "all", "short": "All"},
                {
                    "name": "Some of them; I'll list which ones I want to keep.",
                    "value": "whitelist",
                    "short": "Keep some",
                },
                {
                    "name": "Most of them; I'll list which ones to exclude.",
                    "value": "blacklist",
                    "short": "Discard some",
                },
                # {"name": "None of them; Do not choose this if you want to export to XML!", "value": []}
            ],
        },
        {
            "when": lambda x: x.get("_keep_source") == "whitelist",
            "type": "checkbox",
            "name": "export.source_annotations",
            "message": "Select the annotations to keep:",
            "choices": structure.get_annotations,
        },
        {
            "when": lambda x: x.get("_keep_source") == "blacklist",
            "type": "checkbox",
            "name": "export.source_annotations",
            "message": "Select the annotations to exclude:",
            "choices": [
                {"name": annotation, "value": f"not {annotation}"} for annotation in structure.get_annotations(answers)
            ],
        },
    ]
