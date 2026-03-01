# ruff: noqa: N999
"""Settings related to import."""

import os

from sparv.api import Config, wizard
from sparv.core import registry
from sparv.core.paths import paths

__config__ = [
    Config("import.text_annotation", description="Annotation representing a text", datatype=str),
    Config("import.source_dir", paths.source_dir, description="Directory containing corpus source files", datatype=str),
    Config(
        "import.importer",
        default="xml_import:parse",
        description="Importer to use",
        datatype=str,
        choices=lambda: [
            f"{module_name}:{f_name}"
            for module_name in registry.modules
            for f_name, annotator in registry.modules[module_name].functions.items()
            if annotator["type"] == registry.Annotator.importer
        ],
    ),
    Config("import.keep_control_chars", False, description="Set to True to keep control characters", datatype=bool),
    Config(
        "import.keep_unassigned_chars", False, description="Set to True to keep unassigned characters", datatype=bool
    ),
    Config(
        "import.normalize",
        default="NFC",
        description="Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'",
        datatype=str,
        choices=("NFC", "NFKC", "NFD", "NFKD"),
    ),
    Config("import.encoding", "UTF-8", description="Encoding of source files", datatype=str),
]


@wizard(config_keys=["import.importer", "import.source_dir"])
def setup_wizard(_: dict) -> list[dict]:
    """Return wizard question regarding source path and input format."""
    questions = [
        {
            "type": "path",
            "name": "import.source_dir",
            "message": "Relative path to the current directory containing your source files:",
            "validate": os.path.isdir,
            "default": paths.source_dir,
        }
    ]

    importers = []
    for module_name in registry.modules:
        for f_name, annotator in registry.modules[module_name].functions.items():
            if annotator["type"] == registry.Annotator.importer:
                importers.append((f"{module_name}:{f_name}", annotator))
    max_len = max(len(n) for n, _ in importers)
    questions.append(
        {
            "type": "select",
            "name": "import.importer",
            "choices": [
                {
                    "name": "{:{width}}   {description} (*.{file_extension})".format(
                        importer_name, width=max_len, **importer
                    ),
                    "value": importer_name,
                }
                for importer_name, importer in importers
            ],
            "message": "Choose an importer based on your type of source files:",
        }
    )
    return questions
