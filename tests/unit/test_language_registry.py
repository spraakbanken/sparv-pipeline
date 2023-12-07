from typing import Optional

import pytest

from sparv.core.registry import LanguageRegistry


@pytest.fixture()
def language_registry() -> LanguageRegistry:
    return LanguageRegistry()


class TestLanguageRegistry:
    def check(self, tested: Optional[str], expected: str):
        assert tested == expected

    @pytest.mark.parametrize("lang, expected", [("swe", "Swedish"), ("xxx", "xxx")])
    @pytest.mark.unit
    @pytest.mark.noexternal
    def test_add_language_succeeds(self, language_registry: LanguageRegistry, lang: str, expected: str):
        res = language_registry.add_language(lang)
        self.check(res, expected)
        self.check(language_registry[lang], expected)
