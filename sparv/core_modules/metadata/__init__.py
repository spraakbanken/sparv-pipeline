"""General metadata about corpus."""
import re

from sparv.api import Config, wizard
from sparv.core import registry

__config__ = [
    Config("metadata.id", description="Machine name of corpus (a-z, 0-9, -)"),
    Config("metadata.name", description="Human readable name of corpus"),
    Config("metadata.language", description="Language of source files (ISO 639-3)"),
    Config("metadata.variety", description="Language variety of source files (if applicable)"),
    Config("metadata.description", description="Description of corpus")
]


@wizard(config_keys=[
    "metadata.id",
    "metadata.name.eng",
    "metadata.name.swe",
    "metadata.language",
    "metadata.description.eng",
    "metadata.description.swe"
])
def setup_wizard(_: dict):
    """Return wizard steps for setting metadata variables."""
    language_list = [{"value": lang, "name": name} for lang, name in registry.languages.items()]
    language_list.sort(key=lambda x: x["name"])
    language_default = {"value": "swe", "name": registry.languages.get("swe", "Swedish")}

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
            "message": "Human readable name of corpus (in English):"
        },
        {
            "type": "text",
            "name": "metadata.name.swe",
            "message": "Human readable name of corpus (in Swedish):"
        },
        {
            "type": "select",
            "name": "metadata.language",
            "message": "What language are your source files?",
            "choices": language_list,
            "default": language_default
        },
        {
            "type": "text",
            "name": "metadata.description.eng",
            "message": "Short description of corpus (in English):",
            "multiline": True
        },
        {
            "type": "text",
            "name": "metadata.description.swe",
            "message": "Short description of corpus (in Swedish):",
            "multiline": True
        },
    ]
    return questions
