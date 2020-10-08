import os
import re

from iso639 import languages

from sparv import wizard
from sparv.core import paths, registry


@wizard(config_keys=[
    "metadata.id",
    "metadata.name.eng",
    "metadata.language",
    "metadata.description"
])
def setup_wizard(_: dict):
    """Return wizard steps for setting metadata variables."""
    language_list = [{"value": lang, "name": languages.get(part3=lang).name if lang in languages.part3 else lang}
                     for lang in registry.languages]
    language_list.sort(key=lambda x: x["name"])
    language_default = {"value": "swe", "name": languages.get(part3="swe").name}

    questions = [
        {
            "type": "text",
            "name": "metadata.id",
            "message": "Machine name of corpus (a-z, 0-9, -):",
            "validate": lambda x: bool(re.match(r"^[a-z0-9-]+$", x))
        },
        {
            "type": "text",
            "name": "metadata.name.eng",
            "message": "Human readable name of corpus:"
        },
        {
            "type": "text",
            "name": "import.source_dir",
            "message": "Relative path to the current directory containing your source files:",
            "validate": lambda x: os.path.isdir(x),
            "default": paths.source_dir
        },
        {
            "type": "select",
            "name": "metadata.language",
            "message": "What language are your source files?",
            "choices": language_list,
            "default": language_default
        }
    ]
    return questions
