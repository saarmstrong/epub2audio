"""Tests for text.segment — chapter text → TextSegment[] segmentation.

All tests import ``segment_text`` from ``epub2audio.text.segment``.
If the module is still a stub when collected, every test will be skipped with
a clear message.

# TODO(pending-impl): all tests below require a real segment.py implementation.
"""

from __future__ import annotations

import hashlib

import pytest

# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

try:
    from epub2audio.text.segment import segment_text

    _IMPL_AVAILABLE = True
except (ImportError, AttributeError):
    _IMPL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _IMPL_AVAILABLE,
    reason="epub2audio.text.segment is not yet implemented (stub)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SHORT_PARA = "The quick brown fox jumps over the lazy dog."
_KNOWN_WORDS = ["elephant", "rhinoceros", "hippopotamus", "extraordinary", "consequence"]


def _make_long_paragraph(n_sentences: int = 5) -> str:
    """Return a paragraph of n_sentences, each a distinct simple sentence."""
    return " ".join(
        f"This is sentence number {i} and it contains several words."
        for i in range(1, n_sentences + 1)
    )


# ---------------------------------------------------------------------------
# Basic splitting behaviour
# ---------------------------------------------------------------------------


def test_paragraph_boundary_splits() -> None:
    """Two paragraphs separated by a blank line produce at least 2 segments."""
    text = "First paragraph here.\n\nSecond paragraph here."
    segments = segment_text(text)
    assert len(segments) >= 2


def test_single_short_paragraph_gives_one_segment() -> None:
    """A short paragraph that fits inside max_chars produces exactly 1 segment."""
    segments = segment_text(_SHORT_PARA)
    assert len(segments) == 1
    assert segments[0].text.strip() == _SHORT_PARA.strip()


def test_long_text_split_by_char_limit() -> None:
    """Text exceeding max_chars is split into multiple segments."""
    long_text = (_SHORT_PARA + " ") * 20  # ~880 chars
    segments = segment_text(long_text, max_chars=500)
    assert len(segments) >= 2


def test_all_text_preserved_after_split() -> None:
    """No text is dropped: reassembling segments recovers all words."""
    text = _make_long_paragraph(8)
    segments = segment_text(text, max_chars=100)
    rejoined = " ".join(s.text for s in segments)
    for word in text.split():
        assert word in rejoined, f"Word '{word}' lost after segmentation"


# ---------------------------------------------------------------------------
# No mid-word splits
# ---------------------------------------------------------------------------


def test_no_segment_ends_mid_word() -> None:
    """Every segment ends at a word boundary (no trailing partial word)."""
    long_text = "abcdefgh " * 60  # simple repeated words
    segments = segment_text(long_text, max_chars=100)
    for seg in segments:
        # A segment ending mid-word would end in the middle of "abcdefgh".
        # The simplest proxy: each segment's stripped text should end with
        # the complete word "abcdefgh" or punctuation, not a fragment of it.
        stripped = seg.text.strip()
        if stripped:
            assert not stripped.endswith(("abcd", "abcde", "abcdef", "abcdefg")), (
                f"Segment appears cut mid-word: {seg.text!r}"
            )


def test_no_mid_word_split_on_arbitrary_text() -> None:
    """Segment boundaries fall between words, not inside them."""
    text = " ".join(_KNOWN_WORDS * 30)  # ~650 chars
    segments = segment_text(text, max_chars=100)
    for seg in segments:
        first = seg.text.strip().split()[0] if seg.text.strip() else ""
        assert first in _KNOWN_WORDS or first == "", f"Unexpected word fragment at start: {first!r}"


# ---------------------------------------------------------------------------
# No mid-number splits
# ---------------------------------------------------------------------------


def test_decimal_number_not_split() -> None:
    """A decimal number like '3.14' is never broken across two segments."""
    prefix = "word " * 95  # ~475 chars
    text = prefix + "3.14 more words here."
    segments = segment_text(text, max_chars=500)
    reassembled = " ".join(s.text for s in segments)
    assert "3.14" in reassembled, "Decimal number was lost or split across segments"
    for seg in segments:
        assert not seg.text.rstrip().endswith("3."), (
            f"Segment ends with '3.' suggesting '3.14' was split: {seg.text!r}"
        )


# ---------------------------------------------------------------------------
# No abbreviation splits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "abbrev",
    ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "St.", "vs.", "etc."],
)
def test_abbreviation_not_split(abbrev: str) -> None:
    """Common abbreviations are never treated as sentence-ending periods."""
    prefix = "Some words. " * 10  # ~120 chars
    text = prefix + f"{abbrev} Something important follows here."
    segments = segment_text(text, max_chars=200)
    abbrev_root = abbrev.rstrip(".")
    for seg in segments:
        if abbrev_root in seg.text:
            assert abbrev in seg.text, (
                f"Abbreviation '{abbrev}' appears stripped of period in: {seg.text!r}"
            )


# ---------------------------------------------------------------------------
# No splits between initials
# ---------------------------------------------------------------------------


def test_initials_stay_together() -> None:
    """Author initials like 'J. R. R. Tolkien' are not split across segments."""
    prefix = "Long text before. " * 8  # ~144 chars to push near boundary
    text = prefix + "J. R. R. Tolkien wrote the book."
    segments = segment_text(text, max_chars=200)
    tolkien_seg = next((s for s in segments if "Tolkien" in s.text), None)
    assert tolkien_seg is not None, "'Tolkien' was lost after segmentation"
    assert "J." in tolkien_seg.text, (
        f"Initials 'J.' missing from the segment containing 'Tolkien': {tolkien_seg.text!r}"
    )


# ---------------------------------------------------------------------------
# TextSegment field correctness
# ---------------------------------------------------------------------------


def test_source_hash_is_sha256_of_text() -> None:
    """TextSegment.source_hash is the SHA-256 hex digest of the segment text."""
    segments = segment_text(_SHORT_PARA)
    assert len(segments) >= 1
    seg = segments[0]
    expected = hashlib.sha256(seg.text.encode()).hexdigest()
    assert seg.source_hash == expected


def test_source_hash_deterministic() -> None:
    """Same input text produces the same source_hash on repeated calls."""
    segs_a = segment_text(_SHORT_PARA)
    segs_b = segment_text(_SHORT_PARA)
    assert len(segs_a) == len(segs_b)
    for a, b in zip(segs_a, segs_b, strict=True):
        assert a.source_hash == b.source_hash


def test_normalized_hash_deterministic() -> None:
    """Same input text produces the same normalized_hash on repeated calls."""
    segs_a = segment_text(_SHORT_PARA)
    segs_b = segment_text(_SHORT_PARA)
    for a, b in zip(segs_a, segs_b, strict=True):
        assert a.normalized_hash == b.normalized_hash


def test_normalized_hash_is_hex_string() -> None:
    """normalized_hash is a 64-character hex string (SHA-256)."""
    segments = segment_text(_SHORT_PARA)
    for seg in segments:
        assert len(seg.normalized_hash) == 64
        assert all(c in "0123456789abcdef" for c in seg.normalized_hash)


def test_status_defaults_to_pending() -> None:
    """TextSegment.status is 'pending' by default."""
    segments = segment_text(_SHORT_PARA)
    for seg in segments:
        assert seg.status == "pending"


def test_audio_path_defaults_to_none() -> None:
    """TextSegment.audio_path is None by default."""
    segments = segment_text(_SHORT_PARA)
    for seg in segments:
        assert seg.audio_path is None


def test_word_count_matches_text() -> None:
    """TextSegment.word_count equals len(seg.text.split())."""
    segments = segment_text(_SHORT_PARA)
    for seg in segments:
        assert seg.word_count == len(seg.text.split())


def test_returns_list_of_text_segments() -> None:
    """segment_text returns a list of TextSegment instances."""
    from epub2audio.models import TextSegment

    segments = segment_text(_SHORT_PARA)
    assert isinstance(segments, list)
    assert len(segments) > 0
    for seg in segments:
        assert isinstance(seg, TextSegment)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_string_returns_empty_list() -> None:
    """Empty string produces no segments."""
    segments = segment_text("")
    assert segments == []


def test_whitespace_only_returns_empty_list() -> None:
    """Whitespace-only input produces no segments."""
    segments = segment_text("   \n\n   ")
    assert segments == []


def test_multiple_paragraphs_all_preserved() -> None:
    """All paragraphs from a multi-paragraph input appear in output segments."""
    paragraphs = [f"Paragraph {i}: " + "text here. " * 3 for i in range(5)]
    text = "\n\n".join(paragraphs)
    segments = segment_text(text)
    full = " ".join(s.text for s in segments)
    for i in range(5):
        assert f"Paragraph {i}" in full
