from sparv import wizard
from sparv.core import registry


@wizard(config_keys=[
    "import.importer"
])
def setup_wizard(_: dict):
    """Return wizard question regarding input format."""
    importers = []
    for module_name in registry.annotators:
        for f_name in registry.annotators[module_name]:
            annotator = registry.annotators[module_name][f_name]
            if annotator["type"] == registry.Annotator.importer:
                importers.append((f"{module_name}:{f_name}", annotator))
    max_len = max(len(n) for n, _ in importers)
    question = [{
        "type": "select",
        "name": "import.importer",
        "choices": [{
            "name": "{:{width}}   {description} (*.{file_extension})".format(importer_name, width=max_len, **importer),
            "value": importer_name,
        } for importer_name, importer in importers],
        "message": "Choose an importer based on your type of source files:"
    }]
    return question
