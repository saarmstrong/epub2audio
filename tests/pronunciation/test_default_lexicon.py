"""Tests for the bundled default pronunciation dictionary and lexicon merging."""

from __future__ import annotations

from pathlib import Path

from epub2audio.pronunciation import (
    PronunciationLexicon,
    build_lexicon,
    load_default_lexicon,
)


def test_default_lexicon_loads_and_is_non_empty() -> None:
    lex = load_default_lexicon()
    assert len(lex) > 0
    # A few representative, unambiguous entries.
    assert lex.lookup("Mr") is not None
    assert lex.lookup("Mr").respelling == "Mister"
    assert lex.lookup("genre") is not None


def test_default_lexicon_has_no_context_dependent_homographs() -> None:
    # Context-dependent words must NOT be active defaults (they'd be wrong
    # half the time via blind substitution).
    lex = load_default_lexicon()
    for term in ("the", "The", "read", "lead", "live", "wind", "a"):
        assert lex.lookup(term) is None, f"{term!r} should not be an active default"


def test_build_lexicon_defaults_only() -> None:
    lex = build_lexicon(None, include_defaults=True)
    assert len(lex) == len(load_default_lexicon())


def test_build_lexicon_no_defaults_is_empty_without_user_file() -> None:
    lex = build_lexicon(None, include_defaults=False)
    assert isinstance(lex, PronunciationLexicon)
    assert len(lex) == 0


def test_user_entries_override_defaults(tmp_path: Path) -> None:
    user = tmp_path / "p.yaml"
    user.write_text(
        'pronunciations:\n  Mr: "Mistah"\n  Ono-Sendai: "Oh-no Sen-DYE"\n',
        encoding="utf-8",
    )
    lex = build_lexicon(user, include_defaults=True)
    # User override wins for a shared term...
    assert lex.lookup("Mr").respelling == "Mistah"
    # ...user-only term is present...
    assert lex.lookup("Ono-Sendai").respelling == "Oh-no Sen-DYE"
    # ...and untouched defaults remain.
    assert lex.lookup("genre") is not None


def test_include_defaults_false_uses_only_user_file(tmp_path: Path) -> None:
    user = tmp_path / "p.yaml"
    user.write_text('pronunciations:\n  Hosaka: "Ho-SAH-kah"\n', encoding="utf-8")
    lex = build_lexicon(user, include_defaults=False)
    assert len(lex) == 1
    assert lex.lookup("Hosaka") is not None
    assert lex.lookup("Mr") is None


def test_default_respellings_apply_in_text() -> None:
    lex = load_default_lexicon()
    found = {e.term for e in lex.find_terms("The genre was macabre, said Mr Case.")}
    assert "genre" in found
    assert "macabre" in found
    assert "Mr" in found
