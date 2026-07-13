"""Conservative unicode and punctuation normalisation for TTS narration.

All substitutions are character-level replacements that preserve meaning and
pronunciation intent.  No words, numbers, proper nouns, abbreviations, or
initials are altered.

The normalisation pipeline is intentionally minimal: only characters that TTS
engines handle poorly or inconsistently are changed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Normalisation table
# ---------------------------------------------------------------------------

# Each entry is (original, replacement).  Pairs are applied in order via
# str.translate where possible (single-codepoint → single-codepoint), and
# as direct str.replace calls for multi-character patterns.

_SINGLE_CHAR_MAP: dict[int, str] = {
    # Curly / typographic quotation marks → straight ASCII equivalents
    ord("\u201c"): '"',  # LEFT DOUBLE QUOTATION MARK  "
    ord("\u201d"): '"',  # RIGHT DOUBLE QUOTATION MARK "
    ord("\u2018"): "'",  # LEFT SINGLE QUOTATION MARK  '
    ord("\u2019"): "'",  # RIGHT SINGLE QUOTATION MARK '
    ord("\u201a"): "'",  # SINGLE LOW-9 QUOTATION MARK ‚
    ord("\u201e"): '"',  # DOUBLE LOW-9 QUOTATION MARK „
    ord("\u2039"): "'",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK ‹
    ord("\u203a"): "'",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK ›
    ord("\u00ab"): '"',  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK «
    ord("\u00bb"): '"',  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK »
    # Ellipsis
    ord("\u2026"): "...",  # HORIZONTAL ELLIPSIS …
    # Non-breaking space → regular space
    ord("\u00a0"): " ",  # NO-BREAK SPACE
    ord("\u202f"): " ",  # NARROW NO-BREAK SPACE
    ord("\u2009"): " ",  # THIN SPACE
    # Ligatures
    ord("\ufb01"): "fi",  # LATIN SMALL LIGATURE FI ﬁ
    ord("\ufb02"): "fl",  # LATIN SMALL LIGATURE FL ﬂ
    ord("\ufb00"): "ff",  # LATIN SMALL LIGATURE FF ﬀ
    ord("\ufb03"): "ffi",  # LATIN SMALL LIGATURE FFI ﬃ
    ord("\ufb04"): "ffl",  # LATIN SMALL LIGATURE FFL ﬄ
}

# Multi-character replacements applied after the translate pass.
# Order matters: longer patterns must come before shorter sub-patterns.
_MULTI_CHAR_REPLACEMENTS: list[tuple[str, str]] = [
    # Em-dash with surrounding spaces → spaced hyphen
    (" \u2014 ", " - "),  # EM DASH with spaces
    # Em-dash without spaces → spaced hyphen (common in older typography)
    ("\u2014", " - "),  # bare EM DASH
    # En-dash used as range separator or hyphen substitute
    (" \u2013 ", " - "),  # EN DASH with spaces
    ("\u2013", "-"),  # bare EN DASH (e.g. "pages 3–5")
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Normalize unicode punctuation in text for TTS consumption.

    Applies conservative character-level substitutions:

    - Curly / typographic quotes → straight ASCII quotes
    - Em-dashes and en-dashes → hyphens (with appropriate spacing)
    - Ellipsis character → three dots
    - Non-breaking and narrow spaces → regular spaces
    - Latin ligatures (ﬁ, ﬂ, ﬀ, ﬃ, ﬄ) → decomposed equivalents

    Numbers, decimal points, proper nouns, abbreviations, and initials are
    never modified.

    Args:
        text: Plain text to normalize (post-HTML-cleanup).

    Returns:
        Normalized text with the substitutions described above applied.
    """
    # Phase 1: single-codepoint substitutions via str.translate (fast path).
    result = text.translate(_SINGLE_CHAR_MAP)

    # Phase 2: multi-character pattern replacements.
    for original, replacement in _MULTI_CHAR_REPLACEMENTS:
        result = result.replace(original, replacement)

    return result
