"""Unit tests for sparv.modules.cwb.cwb."""

from __future__ import annotations

from typing import Any

import pytest

from sparv.modules.cwb import cwb


class LoggerStub:
    """Capture warning calls from cwb_escape."""

    def __init__(self) -> None:
        """Initialize warning storage."""
        self.warnings: list[tuple[str, tuple[Any, ...]]] = []

    def warning(self, msg: str, *args: Any) -> None:
        """Store a warning message and its format arguments."""
        self.warnings.append((msg, args))


@pytest.mark.parametrize(
    ("name", "escaped"),
    [
        ("segment.POS", "segment-pos"),
        ("Ålder_2", "alder_2"),
        ("déjà.vu", "deja-vu"),
        ("Ærø", "aero"),
        ("text:Custom.Attr", "text:custom-attr"),
    ],
)
def test_cwb_escape_converts_to_valid_cwb_characters(
    monkeypatch: pytest.MonkeyPatch, name: str, escaped: str
) -> None:
    """Test that convertible characters are normalized without warnings."""
    logger = LoggerStub()
    monkeypatch.setattr(cwb, "logger", logger)

    assert cwb.cwb_escape(name) == escaped
    assert logger.warnings == []


def test_cwb_escape_replaces_unsupported_characters_with_underscore(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that unsupported characters are replaced with underscores (or hyphens in the case of periods) and logged."""
    logger = LoggerStub()
    monkeypatch.setattr(cwb, "logger", logger)

    assert cwb.cwb_escape("name / value!") == "name___value_"

    assert len(logger.warnings) == 1
    assert logger.warnings[0][1][0] == "name / value!"
    assert logger.warnings[0][1][1] == "name___value_"
    assert "' '" in logger.warnings[0][1][2]
    assert "'/'" in logger.warnings[0][1][2]
    assert "'!'" in logger.warnings[0][1][2]


def test_cwb_escape_prefixes_leading_digits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that CWB names do not start with digits."""
    logger = LoggerStub()
    monkeypatch.setattr(cwb, "logger", logger)

    assert cwb.cwb_escape("123.name") == "_123-name"

    assert len(logger.warnings) == 1
    assert logger.warnings[0][1] == ("123.name", "_123-name")
