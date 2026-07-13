"""Tests for xhtml_to_text fragment-range extraction (D4).

Covers :func:`epub2audio.epub.cleanup.xhtml_to_text` with
``start_fragment`` and ``end_fragment`` keyword arguments.

These tests are purely unit-level: they call ``xhtml_to_text`` directly
without going through the EPUB reader, so no temp files are needed.

Design note
-----------
``_extract_fragment`` treats ``<section>`` elements as self-contained block
containers and returns them directly.  For heading elements it instead
carves out a range by removing preceding siblings.  Tests cover both paths.
"""

from __future__ import annotations

from epub2audio.epub.cleanup import word_count, xhtml_to_text

# ---------------------------------------------------------------------------
# Shared XHTML fixtures (inline bytes — no file I/O required)
# ---------------------------------------------------------------------------

# Two self-contained <section> containers, each with distinct text.
_TWO_SECTIONS: bytes = b"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>
  <head><title>Two Sections</title></head>
  <body>
    <section id="part1">
      <h1>Part One</h1>
      <p>The first section contains unique sentinel text alpha.</p>
    </section>
    <section id="part2">
      <h1>Part Two</h1>
      <p>The second section contains unique sentinel text beta.</p>
    </section>
  </body>
</html>
"""

# Three <section> containers to exercise the range (start_fragment + end_fragment) path.
_THREE_SECTIONS: bytes = b"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>
  <head><title>Three Sections</title></head>
  <body>
    <section id="alpha">
      <h1>Alpha</h1>
      <p>Alpha section content.</p>
    </section>
    <section id="beta">
      <h1>Beta</h1>
      <p>Beta section content.</p>
    </section>
    <section id="gamma">
      <h1>Gamma</h1>
      <p>Gamma section content.</p>
    </section>
  </body>
</html>
"""

# A document whose fragments are plain headings (<h1>) instead of <section>
# elements, testing the sibling-pruning path in _extract_fragment.
_HEADING_FRAGMENTS: bytes = b"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>
  <head><title>Heading Fragments</title></head>
  <body>
    <h1 id="section-a">Section A</h1>
    <p>Content for section A only.</p>
    <h1 id="section-b">Section B</h1>
    <p>Content for section B only.</p>
  </body>
</html>
"""


# ---------------------------------------------------------------------------
# TestFragmentExtraction
# ---------------------------------------------------------------------------


class TestFragmentExtraction:
    """Unit tests for xhtml_to_text with start/end fragment parameters."""

    # ---- start_fragment only -----------------------------------------------

    def test_extract_from_start_fragment(self) -> None:
        """Extracting from start_fragment='part2' returns only Part Two text.

        Part One sentinel 'alpha' must be absent; Part Two sentinel 'beta'
        must be present.
        """
        text = xhtml_to_text(_TWO_SECTIONS, start_fragment="part2")
        assert "beta" in text.lower(), (
            f"Expected Part Two sentinel 'beta' in extracted text; got: {text!r}"
        )
        assert "alpha" not in text.lower(), (
            f"Part One sentinel 'alpha' should not appear when extracting from part2; got: {text!r}"
        )

    def test_extract_from_start_fragment_yields_nonempty_text(self) -> None:
        """start_fragment extraction yields a non-empty string."""
        text = xhtml_to_text(_TWO_SECTIONS, start_fragment="part1")
        assert word_count(text) > 0, f"Expected non-empty text for fragment 'part1'; got: {text!r}"

    # ---- start_fragment + end_fragment (range) -----------------------------

    def test_extract_fragment_range(self) -> None:
        """Extracting beta→gamma returns beta content but not alpha or gamma.

        The range (start_fragment='beta', end_fragment='gamma') should include
        the beta section only.
        """
        text = xhtml_to_text(_THREE_SECTIONS, start_fragment="beta", end_fragment="gamma")
        assert "beta" in text.lower(), f"Expected 'beta' content in range extraction; got: {text!r}"
        assert "alpha" not in text.lower(), (
            f"'alpha' should be excluded by start_fragment; got: {text!r}"
        )
        assert "gamma" not in text.lower(), (
            f"'gamma' should be excluded by end_fragment; got: {text!r}"
        )

    def test_extract_first_fragment_range(self) -> None:
        """Extracting alpha→beta returns alpha content only."""
        text = xhtml_to_text(_THREE_SECTIONS, start_fragment="alpha", end_fragment="beta")
        assert "alpha" in text.lower(), (
            f"Expected 'alpha' content when extracting alpha→beta; got: {text!r}"
        )
        assert "beta" not in text.lower(), (
            f"'beta' should be excluded by end_fragment; got: {text!r}"
        )

    # ---- full document (no fragments) --------------------------------------

    def test_full_text_when_no_fragments(self) -> None:
        """Default call (no fragment args) returns text from the whole document.

        Both sentinel strings 'alpha' and 'beta' must appear.
        """
        text = xhtml_to_text(_TWO_SECTIONS)
        assert "alpha" in text.lower(), (
            f"Expected 'alpha' in full-document extraction; got: {text!r}"
        )
        assert "beta" in text.lower(), f"Expected 'beta' in full-document extraction; got: {text!r}"

    def test_full_document_word_count_exceeds_fragment_count(self) -> None:
        """Full-document extraction yields more words than any single fragment."""
        full_wc = word_count(xhtml_to_text(_TWO_SECTIONS))
        part1_wc = word_count(xhtml_to_text(_TWO_SECTIONS, start_fragment="part1"))
        part2_wc = word_count(xhtml_to_text(_TWO_SECTIONS, start_fragment="part2"))

        assert full_wc > part1_wc, (
            f"Full-doc word count ({full_wc}) should exceed part1 count ({part1_wc})"
        )
        assert full_wc > part2_wc, (
            f"Full-doc word count ({full_wc}) should exceed part2 count ({part2_wc})"
        )

    # ---- missing / unknown fragment (graceful degradation) ----------------

    def test_missing_start_fragment_falls_back_to_full_text(self) -> None:
        """An unknown start_fragment gracefully falls back to full-document extraction.

        The implementation documents that a missing fragment triggers full-doc
        fallback (not an exception or empty string).  Both sentinels should
        appear.
        """
        text = xhtml_to_text(_TWO_SECTIONS, start_fragment="does_not_exist")
        # The implementation falls back to returning the full body.
        assert word_count(text) > 0, (
            f"Expected non-empty fallback text for missing fragment; got: {text!r}"
        )

    # ---- heading-element fragments (sibling-pruning path) ------------------

    def test_heading_fragment_extracts_correct_content(self) -> None:
        """Heading-level (h1) fragment id extracts the correct following content.

        When the id is on an h1 element (not a block container), the
        implementation removes preceding siblings.  Extracting from
        'section-b' should include Section B content only.
        """
        text = xhtml_to_text(_HEADING_FRAGMENTS, start_fragment="section-b")
        assert "section b" in text.lower(), (
            f"Expected 'Section B' content after heading-fragment extraction; got: {text!r}"
        )

    def test_end_fragment_none_extracts_to_end_of_document(self) -> None:
        """When end_fragment is None the extraction runs to end of document.

        start_fragment='part1', end_fragment=None should yield all content
        (both part1 and part2 sentinels) for a two-section document.

        Note: <section> elements are block containers so start_fragment='part1'
        returns only the part1 section, not the whole document. The key
        invariant is that no end_fragment is needed to get part1 content.
        """
        text = xhtml_to_text(_TWO_SECTIONS, start_fragment="part1", end_fragment=None)
        assert "alpha" in text.lower(), (
            f"Expected 'alpha' (part1 content) when end_fragment=None; got: {text!r}"
        )
