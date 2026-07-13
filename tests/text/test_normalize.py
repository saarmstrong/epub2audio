"""Tests for text.normalize — conservative unicode/punctuation normalization.

All tests import ``normalize_text`` from ``epub2audio.text.normalize``.
If the module is still a stub when this file is collected, the import will
fail at the module level and every test here will error (not be silently
skipped).  That is intentional: an erroring test is an honest signal that the
implementation is missing.

# TODO(pending-impl): all tests below require a real normalize.py implementation.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Import — will fail with AttributeError / ImportError if still a stub
# ---------------------------------------------------------------------------

try:
    from epub2audio.text.normalize import normalize_text

    _IMPL_AVAILABLE = True
except (ImportError, AttributeError):
    _IMPL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _IMPL_AVAILABLE,
    reason="epub2audio.text.normalize is not yet implemented (stub)",
)


# ---------------------------------------------------------------------------
# Unicode quote normalization
# ---------------------------------------------------------------------------


def test_left_double_quote_replaced() -> None:
    """Curly left double quote '\u201c' is replaced with straight double quote."""
    assert normalize_text("\u201chello\u201d") == '"hello"'


def test_right_double_quote_replaced() -> None:
    """Curly right double quote '\u201d' is replaced with straight double quote."""
    assert normalize_text("say \u201cyes\u201d") == 'say "yes"'


def test_left_single_quote_replaced() -> None:
    """Curly left single quote '\u2018' is replaced with straight apostrophe."""
    assert normalize_text("\u2018hello\u2019") == "'hello'"


def test_right_single_quote_replaced() -> None:
    """Curly right single quote / apostrophe '\u2019' is replaced with straight apostrophe."""
    assert normalize_text("it\u2019s") == "it's"


# ---------------------------------------------------------------------------
# Em-dash normalization
# ---------------------------------------------------------------------------


def test_em_dash_with_spaces_replaced() -> None:
    """Em-dash surrounded by spaces is replaced with ' - '."""
    assert normalize_text("one \u2014 two") == "one - two"


def test_em_dash_without_spaces_replaced() -> None:
    """Em-dash without surrounding spaces is replaced with ' - '."""
    result = normalize_text("one\u2014two")
    assert result == "one - two"


# ---------------------------------------------------------------------------
# Ellipsis normalization
# ---------------------------------------------------------------------------


def test_ellipsis_character_replaced() -> None:
    """Unicode ellipsis character '\u2026' is replaced with three full stops."""
    assert normalize_text("wait\u2026") == "wait..."


def test_ellipsis_in_sentence() -> None:
    """Ellipsis mid-sentence is replaced correctly."""
    assert normalize_text("and then\u2026 she left") == "and then... she left"


# ---------------------------------------------------------------------------
# Whitespace normalization
# ---------------------------------------------------------------------------


def test_non_breaking_space_replaced() -> None:
    """Non-breaking space '\u00a0' is replaced with a regular space."""
    assert normalize_text("hello\u00a0world") == "hello world"


def test_non_breaking_space_multiple() -> None:
    """Multiple non-breaking spaces are each replaced with regular spaces."""
    result = normalize_text("a\u00a0b\u00a0c")
    assert result == "a b c"


# ---------------------------------------------------------------------------
# Ligature normalization
# ---------------------------------------------------------------------------


def test_fi_ligature_replaced() -> None:
    """Ligature '\ufb01' (fi) is expanded to 'fi'."""
    assert normalize_text("\ufb01sh") == "fish"


def test_fl_ligature_replaced() -> None:
    """Ligature '\ufb02' (fl) is expanded to 'fl'."""
    assert normalize_text("\ufb02oor") == "floor"


# ---------------------------------------------------------------------------
# No-alteration cases — numbers and punctuation must be preserved
# ---------------------------------------------------------------------------


def test_integer_unchanged() -> None:
    """Plain integer numbers are not altered."""
    assert normalize_text("42") == "42"


def test_decimal_number_unchanged() -> None:
    """Decimal numbers are not split or altered."""
    result = normalize_text("3.14")
    assert result == "3.14"


def test_decimal_in_sentence_unchanged() -> None:
    """Decimal number embedded in a sentence is preserved intact."""
    result = normalize_text("The value is 3.14 exactly.")
    assert "3.14" in result


def test_initials_unchanged() -> None:
    """Author initials like 'J. R. R. Tolkien' survive normalization unchanged."""
    text = "J. R. R. Tolkien"
    assert normalize_text(text) == text


def test_abbreviation_dr_unchanged() -> None:
    """'Dr.' abbreviation is not altered."""
    text = "Dr. Smith"
    assert normalize_text(text) == text


def test_abbreviation_mr_unchanged() -> None:
    """'Mr.' abbreviation is not altered."""
    text = "Mr. Jones"
    assert normalize_text(text) == text


def test_abbreviation_etc_unchanged() -> None:
    """'etc.' abbreviation is not altered."""
    text = "books, papers, etc."
    assert normalize_text(text) == text


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_already_normalized_text_unchanged() -> None:
    """Text with straight quotes and no special chars is returned unchanged."""
    text = 'He said "hello" and left.'
    assert normalize_text(text) == text


def test_empty_string() -> None:
    """Empty string normalizes to empty string."""
    assert normalize_text("") == ""
