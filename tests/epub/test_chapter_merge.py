"""Tests for D1: multi-file chapter merging.

Covers :func:`epub2audio.epub.chapters.merge_consecutive_chapters` and its
integration with the full :func:`finalize_chapters` pipeline.

Fixtures
--------
- :func:`build_multifile_chapter_epub` — ch01 split across 3 spine docs
- :func:`build_continued_chapter_epub` — ch01_cont.xhtml with '(continued)' heading
- :func:`build_front_matter_epub` — copyright / index pages (must not merge)

Design note
-----------
These tests import the *public* API only (``finalize_chapters``,
``merge_consecutive_chapters``, ``score_candidates``, ``select_chapters``).
Internal helpers are not tested directly so tests survive refactors.
"""

from __future__ import annotations

from pathlib import Path

from epub2audio.epub.chapters import (
    finalize_chapters,
    merge_consecutive_chapters,
    score_candidates,
    select_chapters,
)
from epub2audio.epub.navigation import extract_navigation
from epub2audio.epub.reader import open_epub
from epub2audio.models import Chapter
from tests.fixtures.builders import (
    build_continued_chapter_epub,
    build_front_matter_epub,
    build_multifile_chapter_epub,
    build_simple_epub3,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finalize(epub_path: Path) -> list[Chapter]:
    """Open *epub_path*, run the full scoring + finalize pipeline."""
    book = open_epub(epub_path)
    nav = extract_navigation(book)
    candidates = score_candidates(book, nav)
    chapters = select_chapters(candidates)
    return finalize_chapters(chapters, candidates, nav, book)


def _score_then_merge(epub_path: Path) -> tuple[list[Chapter], list[Chapter]]:
    """Return (pre-merge chapters, post-merge chapters) without splitting."""
    book = open_epub(epub_path)
    nav = extract_navigation(book)
    candidates = score_candidates(book, nav)
    chapters = select_chapters(candidates)
    merged = merge_consecutive_chapters(chapters, candidates, nav)
    return chapters, merged


# ---------------------------------------------------------------------------
# TestMultiFileChapterMerge
# ---------------------------------------------------------------------------


class TestMultiFileChapterMerge:
    """Behaviour tests for merging consecutive spine docs into one chapter."""

    def test_consecutive_docs_without_toc_merged(self, tmp_path: Path) -> None:
        """Docs immediately following a TOC-entry doc with no own TOC entry are merged.

        The 3-part fixture has ch01_part2 and ch01_part3 with no TOC entries
        and short content (score -1 each).  After finalize, Chapter 1 should
        absorb both continuations and only 2 chapters should remain.
        """
        epub_path = tmp_path / "merge_basic.epub"
        build_multifile_chapter_epub(epub_path)
        chapters = _finalize(epub_path)

        assert len(chapters) == 2, (
            f"Expected 2 chapters after merging continuations; "
            f"got {len(chapters)}: {[ch.title for ch in chapters]}"
        )

    def test_merged_chapter_has_all_source_docs(self, tmp_path: Path) -> None:
        """Chapter.source_docs contains every file that was merged into it.

        Chapter 1 should list ch01_part1.xhtml, ch01_part2.xhtml, AND
        ch01_part3.xhtml in that order.
        """
        epub_path = tmp_path / "merge_source_docs.epub"
        build_multifile_chapter_epub(epub_path)
        chapters = _finalize(epub_path)

        ch1 = chapters[0]
        assert "ch01_part1.xhtml" in ch1.source_docs, (
            f"ch01_part1.xhtml missing from source_docs: {ch1.source_docs}"
        )
        assert "ch01_part2.xhtml" in ch1.source_docs, (
            f"ch01_part2.xhtml not merged into Chapter 1: {ch1.source_docs}"
        )
        assert "ch01_part3.xhtml" in ch1.source_docs, (
            f"ch01_part3.xhtml not merged into Chapter 1: {ch1.source_docs}"
        )

    def test_merged_chapter_word_count_is_sum(self, tmp_path: Path) -> None:
        """After merging, the chapter word count is at least as large as before.

        The pre-merge Chapter 1 covers only ch01_part1.xhtml.  The post-merge
        version additionally absorbs ch01_part2 and ch01_part3, so its
        word_count must be strictly greater.
        """
        epub_path = tmp_path / "merge_wc.epub"
        build_multifile_chapter_epub(epub_path)

        before, after = _score_then_merge(epub_path)

        ch1_before = next(c for c in before if c.title == "Chapter 1")
        ch1_after = next(c for c in after if c.title == "Chapter 1")

        assert ch1_after.word_count > ch1_before.word_count, (
            f"Merged word count ({ch1_after.word_count}) should exceed "
            f"pre-merge ({ch1_before.word_count}) because two continuations "
            f"were absorbed."
        )

    def test_merge_stops_at_next_toc_entry(self, tmp_path: Path) -> None:
        """Documents that have their own TOC entry are never absorbed into a predecessor.

        Chapter 2 has a TOC entry pointing at ch02.xhtml.  Even though it
        follows the continuation docs in the spine, it must remain a separate
        chapter.
        """
        epub_path = tmp_path / "merge_stop.epub"
        build_multifile_chapter_epub(epub_path)
        chapters = _finalize(epub_path)

        assert len(chapters) == 2, (
            f"Expected exactly 2 chapters; Chapter 2 should not be merged "
            f"into Chapter 1.  Got {len(chapters)} chapters."
        )
        ch2 = chapters[1]
        assert ch2.title == "Chapter 2", (
            f"Second chapter should still be 'Chapter 2', got {ch2.title!r}"
        )
        assert ch2.source_docs == ["ch02.xhtml"], (
            f"Chapter 2 must keep its own source_doc; got {ch2.source_docs}"
        )

    def test_continued_heading_doc_merged_with_predecessor(self, tmp_path: Path) -> None:
        """A doc with 'Chapter N (continued)' heading and no TOC entry is merged.

        The continued-chapter fixture places ch01_cont.xhtml (short, no TOC)
        between ch01.xhtml and ch02.xhtml.  The merge pass should absorb
        ch01_cont into Chapter 1.
        """
        epub_path = tmp_path / "merge_cont.epub"
        build_continued_chapter_epub(epub_path)
        chapters = _finalize(epub_path)

        assert len(chapters) == 2, (
            f"Expected 2 chapters; ch01_cont should be merged, not separate. "
            f"Got {len(chapters)}: {[ch.title for ch in chapters]}"
        )
        ch1 = chapters[0]
        assert "ch01.xhtml" in ch1.source_docs, (
            f"ch01.xhtml missing from Chapter 1 source_docs: {ch1.source_docs}"
        )
        assert "ch01_cont.xhtml" in ch1.source_docs, (
            f"ch01_cont.xhtml should be merged into Chapter 1: {ch1.source_docs}"
        )

    def test_front_matter_doc_between_chapters_not_merged(self, tmp_path: Path) -> None:
        """A doc with front/back-matter signals is excluded from merging.

        The front-matter fixture includes copyright.xhtml and index_page.xhtml,
        both of which carry front/back-matter keyword signals.  Neither should
        appear in any chapter's source_docs.
        """
        epub_path = tmp_path / "merge_frontmatter.epub"
        build_front_matter_epub(epub_path)
        chapters = _finalize(epub_path)

        all_source_docs: list[str] = [doc for ch in chapters for doc in ch.source_docs]
        assert not any("copyright" in doc for doc in all_source_docs), (
            f"copyright.xhtml should not appear in any chapter's source_docs: {all_source_docs}"
        )
        assert not any("index_page" in doc for doc in all_source_docs), (
            f"index_page.xhtml should not appear in any chapter's source_docs: {all_source_docs}"
        )

    def test_independent_chapters_unchanged_by_merge(self, tmp_path: Path) -> None:
        """Chapters that each have their own TOC entry keep exactly one source_doc.

        simple_epub3 has two chapters, both with TOC entries.  The merge pass
        must not alter either.
        """
        epub_path = tmp_path / "merge_independent.epub"
        build_simple_epub3(epub_path)
        before, after = _score_then_merge(epub_path)

        assert len(before) == len(after) == 2, (
            f"Expected 2 chapters before and after merge; before={len(before)}, after={len(after)}"
        )
        for ch in after:
            assert len(ch.source_docs) == 1, (
                f"Chapter '{ch.title}' has {len(ch.source_docs)} source_docs "
                f"but should only have 1 since it owns its TOC entry: "
                f"{ch.source_docs}"
            )

    def test_merged_source_docs_are_in_spine_order(self, tmp_path: Path) -> None:
        """Merged source_docs list preserves spine reading order."""
        epub_path = tmp_path / "merge_order.epub"
        build_multifile_chapter_epub(epub_path)
        chapters = _finalize(epub_path)

        ch1 = chapters[0]
        expected_order = ["ch01_part1.xhtml", "ch01_part2.xhtml", "ch01_part3.xhtml"]
        assert ch1.source_docs == expected_order, (
            f"Merged source_docs should be in spine order {expected_order}, got {ch1.source_docs}"
        )
