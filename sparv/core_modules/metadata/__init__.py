"""General metadata about corpus."""
import re

from iso639 import languages

from sparv import Config, wizard
from sparv.core import registry

__config__ = [
    Config("metadata.id", description="Machine name of corpus (a-z, 0-9, -)"),
    Config("metadata.name", description="Human readable name of corpus"),
    Config("metadata.language", description="Language of source files (ISO 639-3)"),
    Config("metadata.description", description="Description of corpus")
]


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
            "type": "select",
            "name": "metadata.language",
            "message": "What language are your source files?",
            "choices": language_list,
            "default": language_default
        }
    ]
    return questions
