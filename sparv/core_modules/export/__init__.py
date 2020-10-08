from sparv import SourceStructure, wizard


@wizard(["export.source_annotations"], source_structure=True)
def import_wizard(answers, structure: SourceStructure):
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
