from typing import Optional
import pycountry


class LanguageRegistry(dict):
    """Registry for installed languages."""

    def add_language(self, lang: str) -> str:
        if lang not in self:
            langcode, _, suffix = lang.partition("-")
            iso_lang = self.get_language_name_by_part3(langcode)
            if iso_lang:
                self[lang] = f"{iso_lang} ({suffix})" if suffix else iso_lang
            else:
                self[lang] = lang
        return self[lang]

    @staticmethod
    def get_language_name_by_part3(part3: str) -> Optional[str]:
        lang = pycountry.languages.get(alpha_3=part3)
        return lang.name if lang else None

    @staticmethod
    def get_language_part1_by_part3(part3: str) -> Optional[str]:
        lang = pycountry.languages.get(alpha_3=part3)
        return lang.alpha_2 if lang else None
