import ast
import pathlib
import re
import string
import sys

import pytest

from call_switcher import i18n

PACKAGE = pathlib.Path(i18n.__file__).parent


def _source_texts() -> set[str]:
    """Every literal passed to _() in the app's modules."""
    texts = set()
    for path in PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                texts.add(node.args[0].value)
    return texts


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("language", [code for code in i18n.LANGUAGES if code != "en"])
def test_catalog_is_complete(language):
    catalog = i18n.CATALOG[language]
    assert sorted(_source_texts() - catalog.keys()) == [], "missing translations"
    assert sorted(catalog.keys() - _source_texts()) == [], "unused translations"


@pytest.mark.parametrize("language", [code for code in i18n.LANGUAGES if code != "en"])
def test_placeholders_match(language):
    for source, translated in i18n.CATALOG[language].items():
        assert _fields(translated) == _fields(source), (source, translated)


def test_translation_and_fallback():
    try:
        i18n.set_language("fr")
        assert i18n._("Call {number}", number="044") == "Appeler le 044"
        i18n.set_language("xx")
        assert i18n.get_language() == "en"
        assert i18n._("Call {number}", number="044") == "Call 044"
    finally:
        i18n.set_language("en")


def test_detect_language():
    assert i18n.detect_language(["ja-JP", "pt-BR", "de-CH"]) == "pt"
    assert i18n.detect_language(["fr_CH"]) == "fr"
    assert i18n.detect_language(["ja-JP"]) == "en"
    assert i18n.detect_language([]) == "en"
    assert i18n.detect_language() in i18n.LANGUAGES


@pytest.mark.skipif(sys.platform != "linux", reason="macOS and Windows ask the system")
@pytest.mark.parametrize("env, expected", [
    ({"LANGUAGE": "ja:it:de", "LANG": "fr_CH.UTF-8"}, "it"),
    ({"LC_ALL": "pt_BR.UTF-8", "LANG": "de_CH.UTF-8"}, "pt"),
    ({"LC_MESSAGES": "es_ES.UTF-8", "LANG": "de_CH.UTF-8"}, "es"),
    ({"LANG": "de_CH.UTF-8"}, "de"),
    ({"LANG": "C.UTF-8"}, "en"),
    ({}, "en"),
])
def test_detect_language_from_environment(monkeypatch, env, expected):
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    assert i18n.detect_language() == expected


def test_no_hardcoded_german_left():
    for path in PACKAGE.rglob("*.py"):
        if path.name != "i18n.py":
            assert not re.search(r'"[^"\n]*[äöüÄÖÜß][^"\n]*"', path.read_text(encoding="utf-8")), path.name
