"""Unit tests for :mod:`epub2audio.pronunciation.lexicon`.

Covers: PronunciationEntry, PronunciationLexicon (lookup/find_terms/empty),
load_lexicon (all 4 YAML forms), error handling, and the no-import-from-
providers/director boundary.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from epub2audio.pronunciation import PronunciationEntry, PronunciationLexicon, load_lexicon

# ---------------------------------------------------------------------------
# PronunciationEntry
# ---------------------------------------------------------------------------


class TestPronunciationEntry:
    def test_fields_accessible(self) -> None:
        e = PronunciationEntry(term="Ono-Sendai", ipa="/oʊnoʊ/", respelling="Oh-no")
        assert e.term == "Ono-Sendai"
        assert e.ipa == "/oʊnoʊ/"
        assert e.respelling == "Oh-no"

    def test_defaults_are_none(self) -> None:
        e = PronunciationEntry(term="Hosaka")
        assert e.ipa is None
        assert e.respelling is None

    def test_to_hint_carries_all_fields(self) -> None:
        e = PronunciationEntry(term="Ono-Sendai", ipa="/x/", respelling="Oh-no")
        h = e.to_hint()
        assert h.term == "Ono-Sendai"
        assert h.ipa == "/x/"
        assert h.respelling == "Oh-no"

    def test_to_hint_none_fields(self) -> None:
        h = PronunciationEntry(term="X").to_hint()
        assert h.ipa is None
        assert h.respelling is None


# ---------------------------------------------------------------------------
# PronunciationLexicon
# ---------------------------------------------------------------------------


class TestPronunciationLexiconEmpty:
    def test_empty_lookup_returns_none(self) -> None:
        lex = PronunciationLexicon.empty()
        assert lex.lookup("anything") is None

    def test_empty_find_terms_returns_empty(self) -> None:
        lex = PronunciationLexicon.empty()
        assert lex.find_terms("some text with Ono-Sendai in it") == []


class TestPronunciationLexiconLookup:
    def test_hit(self) -> None:
        lex = PronunciationLexicon(
            {"Ono-Sendai": PronunciationEntry(term="Ono-Sendai", respelling="Oh-no")}
        )
        assert lex.lookup("Ono-Sendai") is not None

    def test_miss(self) -> None:
        lex = PronunciationLexicon({"Ono-Sendai": PronunciationEntry(term="Ono-Sendai")})
        assert lex.lookup("ono-sendai") is None  # case-sensitive

    def test_case_sensitive(self) -> None:
        lex = PronunciationLexicon({"ABC": PronunciationEntry(term="ABC")})
        assert lex.lookup("ABC") is not None
        assert lex.lookup("abc") is None


class TestFindTerms:
    def _make(self, **kwargs: str) -> PronunciationLexicon:
        """Build a lexicon from term=respelling keyword args."""
        return PronunciationLexicon(
            {k: PronunciationEntry(term=k, respelling=v) for k, v in kwargs.items()}
        )

    def test_single_match(self) -> None:
        lex = self._make(**{"Ono-Sendai": "Oh-no"})
        matches = lex.find_terms("Case jacked into the Ono-Sendai deck.")
        assert [e.term for e in matches] == ["Ono-Sendai"]

    def test_no_match(self) -> None:
        lex = self._make(**{"Ono-Sendai": "Oh-no"})
        assert lex.find_terms("Nothing relevant here.") == []

    def test_multiple_terms_ordered_by_position(self) -> None:
        lex = self._make(**{"Hosaka": "Ho-SAH-kah", "Ono-Sendai": "Oh-no"})
        text = "She held an Ono-Sendai in one hand and a Hosaka in the other."
        terms = [e.term for e in lex.find_terms(text)]
        assert terms == ["Ono-Sendai", "Hosaka"]

    def test_longest_match_wins_no_overlap(self) -> None:
        # "Tessier-Ashpool" and "Ashpool" — longer should win for the span
        lex = PronunciationLexicon(
            {
                "Tessier-Ashpool": PronunciationEntry(
                    term="Tessier-Ashpool", respelling="Tess-ee-ay"
                ),
                "Ashpool": PronunciationEntry(term="Ashpool", respelling="Ash-pool"),
            }
        )
        text = "They entered the Tessier-Ashpool estate."
        matches = lex.find_terms(text)
        terms = [e.term for e in matches]
        # Tessier-Ashpool consumed the span; Ashpool should NOT appear
        assert "Tessier-Ashpool" in terms
        assert "Ashpool" not in terms

    def test_no_partial_word_match(self) -> None:
        # "Sendai" should not match inside "Ono-Sendai" if they're separate entries
        lex = self._make(**{"Sendai": "SEN-dai"})
        text = "He jacked into the Ono-Sendai."
        assert lex.find_terms(text) == []  # "Sendai" is part of a hyphenated term

    def test_deduplicated(self) -> None:
        # Same term appearing twice → only one entry
        lex = self._make(**{"Ono-Sendai": "Oh-no"})
        matches = lex.find_terms("Ono-Sendai and Ono-Sendai again.")
        assert len(matches) == 1

    def test_empty_text(self) -> None:
        lex = self._make(**{"Ono-Sendai": "Oh-no"})
        assert lex.find_terms("") == []


# ---------------------------------------------------------------------------
# load_lexicon — YAML forms
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, content: str, name: str = "pronunciations.yaml") -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_load_none_path_returns_empty() -> None:
    lex = load_lexicon(None)
    assert lex.lookup("anything") is None


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    lex = load_lexicon(tmp_path / "does_not_exist.yaml")
    assert lex.find_terms("anything") == []


def test_load_empty_file_returns_empty(tmp_path: Path) -> None:
    p = _write(tmp_path, "")
    assert load_lexicon(p).find_terms("text") == []


def test_load_form1_string_value(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        Ono-Sendai: Oh-no Sen-DYE
        Hosaka: Ho-SAH-kah
        """,
    )
    lex = load_lexicon(p)
    e = lex.lookup("Ono-Sendai")
    assert e is not None
    assert e.respelling == "Oh-no Sen-DYE"
    assert e.ipa is None
    assert lex.lookup("Hosaka") is not None


def test_load_form2_dict_value(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        Neuromancer:
          ipa: "/njʊəroʊˈmænsər/"
          respelling: Nyu-ro-MAN-ser
        """,
    )
    lex = load_lexicon(p)
    e = lex.lookup("Neuromancer")
    assert e is not None
    assert e.ipa == "/njʊəroʊˈmænsər/"
    assert e.respelling == "Nyu-ro-MAN-ser"


def test_load_form2_null_value(tmp_path: Path) -> None:
    p = _write(tmp_path, "Hosaka:\n")
    lex = load_lexicon(p)
    e = lex.lookup("Hosaka")
    assert e is not None
    assert e.ipa is None
    assert e.respelling is None


def test_load_form3_pronunciations_wrapper(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        pronunciations:
          Ono-Sendai: Oh-no Sen-DYE
          Hosaka: Ho-SAH-kah
        """,
    )
    lex = load_lexicon(p)
    assert lex.lookup("Ono-Sendai") is not None
    assert lex.lookup("Hosaka") is not None


def test_load_form3_null_inner(tmp_path: Path) -> None:
    p = _write(tmp_path, "pronunciations:\n")
    lex = load_lexicon(p)
    assert lex.find_terms("anything") == []


def test_load_form4_bare_list(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        - Ono-Sendai
        - Hosaka
        - Tessier-Ashpool
        """,
    )
    lex = load_lexicon(p)
    for term in ("Ono-Sendai", "Hosaka", "Tessier-Ashpool"):
        e = lex.lookup(term)
        assert e is not None
        assert e.ipa is None
        assert e.respelling is None


def test_load_form1_mixed_ipa_and_string(tmp_path: Path) -> None:
    """Single file mixing string respellings and dict entries."""
    p = _write(
        tmp_path,
        """
        Ono-Sendai: Oh-no Sen-DYE
        Neuromancer:
          ipa: "/njʊəroʊˈmænsər/"
          respelling: Nyu-ro-MAN-ser
        """,
    )
    lex = load_lexicon(p)
    assert lex.lookup("Ono-Sendai") is not None
    assert lex.lookup("Neuromancer") is not None


def test_load_invalid_yaml_raises_valueerror(tmp_path: Path) -> None:
    p = _write(tmp_path, "key: [unclosed")
    with pytest.raises(ValueError, match="Could not parse"):
        load_lexicon(p)


def test_load_wrong_top_level_type_raises(tmp_path: Path) -> None:
    p = _write(tmp_path, "42\n")
    with pytest.raises(ValueError, match="mapping or list"):
        load_lexicon(p)


def test_load_list_with_non_string_raises(tmp_path: Path) -> None:
    p = _write(tmp_path, "- 123\n")
    with pytest.raises(ValueError, match="must be strings"):
        load_lexicon(p)


def test_load_unknown_dict_keys_ignored(tmp_path: Path) -> None:
    """Unknown keys inside a per-entry dict are silently ignored."""
    p = _write(
        tmp_path,
        """
        Ono-Sendai:
          ipa: "/x/"
          respelling: Oh-no
          future_field: ignored
        """,
    )
    lex = load_lexicon(p)
    e = lex.lookup("Ono-Sendai")
    assert e is not None
    assert e.ipa == "/x/"


# ---------------------------------------------------------------------------
# Boundary: pronunciation/ does not import from director/ or providers/
# ---------------------------------------------------------------------------


def test_pronunciation_package_does_not_import_director() -> None:
    import importlib

    mod = importlib.import_module("epub2audio.pronunciation.lexicon")
    src = Path(mod.__file__).read_text()  # type: ignore[arg-type]
    assert "from epub2audio.director" not in src
    assert "import epub2audio.director" not in src


def test_pronunciation_package_does_not_import_providers() -> None:
    import importlib

    mod = importlib.import_module("epub2audio.pronunciation.lexicon")
    src = Path(mod.__file__).read_text()  # type: ignore[arg-type]
    assert "from epub2audio.providers" not in src
    assert "import epub2audio.providers" not in src
