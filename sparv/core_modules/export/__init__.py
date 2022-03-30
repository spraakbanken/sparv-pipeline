from sparv.api import Config, SourceStructureParser, wizard

__config__ = [
    Config("export.default", description="List of exporters to use by default"),
    Config("export.annotations", description="List of automatic annotations to include in export"),
    Config("export.source_annotations", description="List of annotations and attributes from the source to include"),
    Config("export.word", description="Annotation to use as token text in export"),
    Config("export.remove_module_namespaces",
           description="Remove module name prefixes from annotation names in export"),
    Config("export.sparv_namespace", description="Prefix to add to the names of all automatically created annotations"),
    Config("export.source_namespace", description="Prefix to add to the names of all annotations from source"),
    Config("export.scramble_on", description="What annotation to use as the smallest unit when scrambling")
]


@wizard(["export.source_annotations"], source_structure=True)
def import_wizard(answers, structure: SourceStructureParser):
    """Return wizard for selecting what source annotations to keep."""
    questions = [
        {
            "type": "select",
            "name": "_keep_source",
            "message": "What existing annotations from the source files do you want to keep?",
            "choices": [
                {"name": "All of them", "value": "all", "short": "All"},
                {"name": "Some of them; I’ll list which ones I want to keep.", "value": "whitelist",
                 "short": "Keep some"},
                {"name": "Most of them; I’ll list which ones to exclude.", "value": "blacklist",
                 "short": "Discard some"}
                # {"name": "None of them; Do not choose this if you want to export to XML!", "value": []}
            ]
        },
        {
            "when": lambda x: x.get("_keep_source") == "whitelist",
            "type": "checkbox",
            "name": "export.source_annotations",
            "message": "Select the annotations to keep:",
            "choices": structure.get_annotations
        },
        {
            "when": lambda x: x.get("_keep_source") == "blacklist",
            "type": "checkbox",
            "name": "export.source_annotations",
            "message": "Select the annotations to exclude:",
            "choices": [{
                "name": annotation,
                "value": f"not {annotation}"
            } for annotation in structure.get_annotations(answers)]
        }
    ]
    return questions
