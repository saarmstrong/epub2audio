"""Tests for natural-reading cleanup: footnote/superscript stripping and
hard-exclusion of non-narrative front/back-matter titles.
"""

from __future__ import annotations

from epub2audio.epub.chapters import _is_hard_front_matter_title
from epub2audio.epub.cleanup import xhtml_to_text


class TestSuperscriptAndNoteStripping:
    def test_superscript_number_marker_removed(self) -> None:
        html = b"<html><body><p>The system failed<sup>3</sup> that night.</p></body></html>"
        assert xhtml_to_text(html) == "The system failed that night."

    def test_superscript_symbol_marker_removed(self) -> None:
        html = b"<html><body><p>A caveat<sup>*</sup> applies here.</p></body></html>"
        assert xhtml_to_text(html) == "A caveat applies here."

    def test_note_anchor_without_epubtype_removed(self) -> None:
        html = (
            b"<html><body><p>See the report"
            b'<a href="notes.xhtml#fn7">7</a> for more.</p></body></html>'
        )
        assert xhtml_to_text(html) == "See the report for more."

    def test_epubtype_noteref_still_removed(self) -> None:
        html = b'<html><body><p>Text<a epub:type="noteref" href="#n1">1</a> here.</p></body></html>'
        assert xhtml_to_text(html) == "Text here."

    def test_ordinal_superscript_preserved(self) -> None:
        # A letter superscript (ordinal) is NOT a footnote marker and is kept.
        html = b"<html><body><p>She placed 19<sup>th</sup>.</p></body></html>"
        assert "th" in xhtml_to_text(html)

    def test_plain_link_text_not_stripped(self) -> None:
        # A normal anchor with real words and a non-note href is preserved.
        html = (
            b"<html><body><p>Visit "
            b'<a href="https://example.com">the website</a> today.</p></body></html>'
        )
        out = xhtml_to_text(html)
        assert "the website" in out


class TestInlineMerging:
    """Drop-cap / small-caps openings must not be split into separate words."""

    def test_dropcap_smallcaps_opening_not_split(self) -> None:
        # The Neuromancer opening: 'T' drop cap + 'HE SKY ABOVE' small-caps.
        # Must read 'THE SKY ABOVE ...', never 'T HE ...' (which a TTS says as
        # 'Tee-hee').
        html = (
            b'<html><body><p><span class="sans"><span>T</span>'
            b'<span class="smallcap"><span>HE SKY ABOVE</span></span></span>'
            b"<span> the port was grey.</span></p></body></html>"
        )
        out = xhtml_to_text(html)
        assert out == "THE SKY ABOVE the port was grey."
        assert "T HE" not in out

    def test_adjacent_inline_spans_merge_without_space(self) -> None:
        html = b"<html><body><p>wo<span>rd</span>smith</p></body></html>"
        assert xhtml_to_text(html) == "wordsmith"

    def test_real_word_spacing_preserved(self) -> None:
        html = b"<html><body><p>the <em>quick</em> brown fox</p></body></html>"
        assert xhtml_to_text(html) == "the quick brown fox"

    def test_link_text_preserved_after_unwrap(self) -> None:
        html = (
            b"<html><body><p>Visit "
            b'<a href="https://example.com">the website</a> now.</p></body></html>'
        )
        assert xhtml_to_text(html) == "Visit the website now."


class TestHardFrontMatterTitles:
    def test_definitive_titles_excluded(self) -> None:
        for t in [
            "Copyright",
            "contents",
            "Table of Contents",
            "Acknowledgements",
            "Index",
            "Cover",
            "Title Page",
            "About the Author",
        ]:
            assert _is_hard_front_matter_title(t), t

    def test_also_by_and_praise_prefixes_excluded(self) -> None:
        for t in [
            "Also by William Gibson",
            "Titles by William Gibson",
            "Other Books by the Author",
            "Praise for Neuromancer",
        ]:
            assert _is_hard_front_matter_title(t), t

    def test_real_chapter_titles_not_excluded(self) -> None:
        for t in [
            "One",
            "Chapter 1",
            "Part 1: Chiba City Blues",
            "The Sky Above the Port",
            "Prologue",
            "Epilogue",
            None,
            "",
        ]:
            assert not _is_hard_front_matter_title(t), t

    def test_case_insensitive(self) -> None:
        assert _is_hard_front_matter_title("COPYRIGHT")
        assert _is_hard_front_matter_title("  Copyright  ")
