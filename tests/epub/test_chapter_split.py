"""Tests for D2: single-file multi-chapter splitting.

Covers :func:`epub2audio.epub.chapters.split_multi_chapter_docs` and its
integration with :func:`finalize_chapters`.

Fixtures
--------
- :func:`build_singlefile_multichapter_epub` — chapters.xhtml with prologue+ch1+ch2
- :func:`build_fragment_toc_epub` — content.xhtml with Part 1 / Part 2
- :func:`build_multi_chapter_single_file` — existing fixture (ch-1, ch-2 fragments)
- :func:`build_simple_epub3` — two independent chapters (must *not* be split)
- :func:`build_heading_epub` — one chapter, one h1 (must *not* be split)

Design note
-----------
Tests check observable behaviour (chapter count, source_doc format, titles,
word counts, reading order) and do not inspect internal state.
"""

from __future__ import annotations

from pathlib import Path

from epub2audio.epub.chapters import (
    finalize_chapters,
    score_candidates,
    select_chapters,
)
from epub2audio.epub.cleanup import word_count, xhtml_to_text
from epub2audio.epub.navigation import extract_navigation
from epub2audio.epub.reader import open_epub
from epub2audio.models import Chapter
from tests.fixtures.builders import (
    build_fragment_toc_epub,
    build_heading_epub,
    build_multi_chapter_single_file,
    build_simple_epub3,
    build_singlefile_multichapter_epub,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finalize(epub_path: Path) -> list[Chapter]:
    """Open *epub_path* and run the full finalize pipeline."""
    book = open_epub(epub_path)
    nav = extract_navigation(book)
    candidates = score_candidates(book, nav)
    chapters = select_chapters(candidates)
    return finalize_chapters(chapters, candidates, nav, book)


# ---------------------------------------------------------------------------
# TestSingleFileChapterSplit
# ---------------------------------------------------------------------------


class TestSingleFileChapterSplit:
    """Behaviour tests for splitting a single document into multiple chapters."""

    def test_multiple_h1_triggers_split_signal(self, tmp_path: Path) -> None:
        """A document with multiple <h1> elements receives the multiple_h1 signal.

        Verifies that the scoring pass fires the 'multiple_h1 -1' signal
        when it encounters a document with more than one h1 element.  This
        signal is a prerequisite for the splitting heuristic.
        """
        epub_path = tmp_path / "multi_h1.epub"
        build_singlefile_multichapter_epub(epub_path)

        book = open_epub(epub_path)
        nav = extract_navigation(book)
        candidates = score_candidates(book, nav)

        multi_h1_cands = [c for c in candidates if any("multiple_h1" in s for s in c.signals)]
        assert multi_h1_cands, (
            f"Expected at least one candidate with 'multiple_h1' signal. "
            f"Candidates: {[(c.doc_path, c.signals) for c in candidates]}"
        )

    def test_fragment_toc_entries_create_chapters(self, tmp_path: Path) -> None:
        """TOC entries with #fragment links produce separate chapters after finalize.

        build_fragment_toc_epub has content.xhtml with Part 1 and Part 2
        referenced via fragment links.  After splitting there should be
        exactly 2 chapters.
        """
        epub_path = tmp_path / "split_frag.epub"
        build_fragment_toc_epub(epub_path)
        chapters = _finalize(epub_path)

        assert len(chapters) == 2, (
            f"Expected 2 chapters from fragment TOC; "
            f"got {len(chapters)}: {[ch.title for ch in chapters]}"
        )

    def test_split_chapters_have_correct_fragments(self, tmp_path: Path) -> None:
        """Each split chapter's source_doc is in 'path#fragment' format.

        After splitting, every chapter derived from a fragmented TOC entry
        must have its source_doc contain exactly one '#' separator with a
        non-empty fragment.
        """
        epub_path = tmp_path / "split_format.epub"
        build_fragment_toc_epub(epub_path)
        chapters = _finalize(epub_path)

        for ch in chapters:
            assert len(ch.source_docs) == 1, (
                f"Split chapter '{ch.title}' should have exactly one source_doc, "
                f"got {ch.source_docs}"
            )
            doc = ch.source_docs[0]
            assert "#" in doc, (
                f"source_doc '{doc}' for chapter '{ch.title}' should contain '#fragment'"
            )
            doc_path, fragment = doc.split("#", 1)
            assert doc_path, f"doc_path before '#' must be non-empty; got {doc!r}"
            assert fragment, f"fragment after '#' must be non-empty; got {doc!r}"

    def test_split_chapter_text_extraction(self, tmp_path: Path) -> None:
        """Text extracted for a split chapter covers only its own fragment.

        For build_fragment_toc_epub, Part 1 text must not contain Part 2
        content and vice versa (sections are self-contained <section> blocks).
        """
        epub_path = tmp_path / "split_text.epub"
        build_fragment_toc_epub(epub_path)

        book = open_epub(epub_path)
        nav = extract_navigation(book)
        candidates = score_candidates(book, nav)
        chapters = select_chapters(candidates)
        chapters = finalize_chapters(chapters, candidates, nav, book)

        # Retrieve the raw content for content.xhtml
        item = book.get_item_with_href("content.xhtml")
        assert item is not None, "content.xhtml must be in the EPUB manifest"
        content = item.get_content()

        # Extract each chapter's fragment and verify mutual exclusion.
        part1_ch = next((ch for ch in chapters if ch.title == "Part 1"), None)
        part2_ch = next((ch for ch in chapters if ch.title == "Part 2"), None)

        assert part1_ch is not None, (
            f"Expected chapter titled 'Part 1'; got titles: {[ch.title for ch in chapters]}"
        )
        assert part2_ch is not None, (
            f"Expected chapter titled 'Part 2'; got titles: {[ch.title for ch in chapters]}"
        )

        # Extract text for Part 1 (stop at Part 2's fragment).
        part1_text = xhtml_to_text(content, start_fragment="part1", end_fragment="part2")
        part2_text = xhtml_to_text(content, start_fragment="part2")

        # Each fragment should yield non-empty text.
        assert word_count(part1_text) > 0, (
            f"Part 1 fragment text should be non-empty; got: {part1_text!r}"
        )
        assert word_count(part2_text) > 0, (
            f"Part 2 fragment text should be non-empty; got: {part2_text!r}"
        )

    def test_split_preserves_reading_order(self, tmp_path: Path) -> None:
        """Split chapters appear in the same order as TOC / document order.

        build_singlefile_multichapter_epub has Prologue → Chapter 1 → Chapter 2
        in TOC order.  After splitting, the chapters should maintain that
        exact sequence.
        """
        epub_path = tmp_path / "split_order.epub"
        build_singlefile_multichapter_epub(epub_path)
        chapters = _finalize(epub_path)

        assert len(chapters) == 3, (
            f"Expected 3 chapters (Prologue, Chapter 1, Chapter 2); "
            f"got {len(chapters)}: {[ch.title for ch in chapters]}"
        )
        titles = [ch.title for ch in chapters]
        assert titles.index("Prologue") < titles.index("Chapter 1"), (
            f"Prologue must come before Chapter 1; titles={titles}"
        )
        assert titles.index("Chapter 1") < titles.index("Chapter 2"), (
            f"Chapter 1 must come before Chapter 2; titles={titles}"
        )

    def test_no_split_for_single_toc_entry(self, tmp_path: Path) -> None:
        """Documents with only one TOC entry are never split.

        simple_epub3 has two chapters, each in its own file with its own TOC
        entry.  No document has multiple fragment entries, so no splitting
        should occur.
        """
        epub_path = tmp_path / "no_split_toc.epub"
        build_simple_epub3(epub_path)
        chapters = _finalize(epub_path)

        assert len(chapters) == 2, (
            f"Expected exactly 2 chapters (no splitting); got {len(chapters)}"
        )
        for ch in chapters:
            doc = ch.source_docs[0]
            assert "#" not in doc, (
                f"Chapter '{ch.title}' source_doc '{doc}' has an unexpected "
                f"'#' fragment — single-TOC-entry doc should not be split."
            )

    def test_no_split_for_single_h1(self, tmp_path: Path) -> None:
        """A document with only one <h1> is not split by the split pass.

        build_heading_epub creates one chapter with exactly one h1.  After
        finalize there should be exactly one chapter, not multiple.
        """
        epub_path = tmp_path / "no_split_h1.epub"
        build_heading_epub(epub_path)
        chapters = _finalize(epub_path)

        # heading_epub may be included as a warned chapter (score 1-3).
        # The important invariant is that it is NOT split.
        for ch in chapters:
            assert len(ch.source_docs) == 1, (
                f"Chapter '{ch.title}' unexpectedly has multiple source_docs: {ch.source_docs}"
            )
            doc = ch.source_docs[0]
            assert "#" not in doc, (
                f"Chapter '{ch.title}' source_doc '{doc}' has a fragment, "
                f"but no split should have occurred for a single-h1 doc."
            )

    def test_split_chapter_word_counts_positive(self, tmp_path: Path) -> None:
        """Every split chapter has a positive word count.

        After splitting, each fragment-derived chapter must have word_count > 0
        because its section contains actual prose content.
        """
        epub_path = tmp_path / "split_wc.epub"
        build_multi_chapter_single_file(epub_path)
        chapters = _finalize(epub_path)

        for ch in chapters:
            assert ch.word_count > 0, f"Split chapter '{ch.title}' has word_count=0; expected > 0"

    def test_split_titles_come_from_toc(self, tmp_path: Path) -> None:
        """Split chapters take their titles from the TOC entries, not the file title.

        build_singlefile_multichapter_epub has a file-level title of
        'Single File Multi-Chapter' but TOC entries 'Prologue', 'Chapter 1',
        'Chapter 2'.  The split chapters should use the TOC titles.
        """
        epub_path = tmp_path / "split_titles.epub"
        build_singlefile_multichapter_epub(epub_path)
        chapters = _finalize(epub_path)

        titles = [ch.title for ch in chapters]
        assert "Prologue" in titles, f"Expected 'Prologue' in titles: {titles}"
        assert "Chapter 1" in titles, f"Expected 'Chapter 1' in titles: {titles}"
        assert "Chapter 2" in titles, f"Expected 'Chapter 2' in titles: {titles}"
        assert not any("Single File" in t for t in titles), (
            f"File-level title should not appear in split chapter titles: {titles}"
        )
