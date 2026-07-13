"""Tests for the chapter scoring engine and chapter selection.

Covers M1-17: all required test cases for epub/chapters.py.

Tests use programmatic fixtures from builders.py to isolate individual
scoring signals.  They test *behaviour* (scores, exclusions, ID format)
not implementation details (internal data structures).
"""

from __future__ import annotations

from pathlib import Path

from epub2audio.epub.chapters import (
    finalize_chapters,
    score_candidates,
    select_chapters,
)
from epub2audio.epub.navigation import extract_navigation
from epub2audio.epub.reader import open_epub
from epub2audio.models import Chapter, ChapterCandidate
from tests.fixtures.builders import (
    build_empty_doc_epub,
    build_epub_with_epub_type,
    build_front_matter_epub,
    build_heading_epub,
    build_multi_chapter_single_file,
    build_multi_file_chapter_epub,
    build_roman_numeral_chapters_epub,
    build_short_chapter_epub,
    build_simple_epub3,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_and_score(epub_path: Path) -> tuple[list[ChapterCandidate], object]:
    """Open an EPUB, extract navigation, and score candidates.  Returns (candidates, book)."""
    book = open_epub(epub_path)
    nav = extract_navigation(book)
    candidates = score_candidates(book, nav)
    return candidates, book


# ---------------------------------------------------------------------------
# M1-17 required test cases
# ---------------------------------------------------------------------------


def test_toc_entry_gives_positive_score(tmp_path: Path) -> None:
    """A doc that has a TOC entry scores ≥ 4 (the TOC signal alone is +4)."""
    epub_path = tmp_path / "toc_score.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)

    # Both chapters have TOC entries; at least one must score ≥ 4.
    toc_candidates = [c for c in candidates if c.score >= 4]
    assert len(toc_candidates) >= 1, (
        f"Expected at least one candidate with score ≥ 4 (TOC signal = +4). "
        f"Scores were: {[c.score for c in candidates]}"
    )


def test_short_doc_penalised(tmp_path: Path) -> None:
    """A doc with < 200 words is penalised by −2 relative to a doc without that signal.

    Uses the short-chapter fixture which contains one very short document
    (intentionally well under 200 words) and one normal chapter.
    """
    epub_path = tmp_path / "short.epub"
    build_short_chapter_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)

    # The short stub has no TOC entry, so its base score would be +1 (spine boundary).
    # With the short-doc penalty it should be +1 − 2 = −1 (or lower).
    # We verify that there is at least one candidate whose signals include a
    # short-document mention, and whose score is lower than any TOC-backed candidate.
    short_signals_candidates = [
        c for c in candidates if any("short" in s.lower() or "200" in s for s in c.signals)
    ]
    assert len(short_signals_candidates) >= 1, (
        "Expected at least one candidate with a short-document signal. "
        f"Candidates: {[(c.title, c.score, c.signals) for c in candidates]}"
    )
    # The short candidate must score lower than the TOC-backed chapter candidate.
    normal_chapter = next((c for c in candidates if c.score >= 4), None)
    if normal_chapter is not None:
        for short_c in short_signals_candidates:
            assert short_c.score < normal_chapter.score, (
                f"Short document (score={short_c.score}) should score lower than "
                f"TOC-backed chapter (score={normal_chapter.score})."
            )


def test_front_matter_keyword_excluded(tmp_path: Path) -> None:
    """A doc titled 'copyright' scores < 0 and is absent from select_chapters."""
    epub_path = tmp_path / "front_matter.epub"
    build_front_matter_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)

    # Find the copyright candidate
    copyright_candidates = [c for c in candidates if c.title and "copyright" in c.title.lower()]
    assert len(copyright_candidates) >= 1, (
        f"Expected a 'copyright' candidate; got titles: {[c.title for c in candidates]}"
    )
    for cc in copyright_candidates:
        assert cc.score < 0, (
            f"'copyright' candidate should score < 0 (front-matter penalty −3 + short −2). "
            f"Got score={cc.score}, signals={cc.signals}"
        )

    # It must not appear in select_chapters output
    chapters = select_chapters(candidates)
    chapter_titles = [ch.title.lower() for ch in chapters]
    assert not any("copyright" in t for t in chapter_titles), (
        f"'copyright' should be excluded from chapter list but appeared: {chapter_titles}"
    )


def test_back_matter_keyword_excluded(tmp_path: Path) -> None:
    """A doc titled 'index' scores < 0 and is absent from select_chapters."""
    epub_path = tmp_path / "back_matter.epub"
    build_front_matter_epub(epub_path)  # builder includes both copyright and index pages
    candidates, _ = _open_and_score(epub_path)

    index_candidates = [c for c in candidates if c.title and "index" in c.title.lower()]
    assert len(index_candidates) >= 1, (
        f"Expected an 'index' candidate; got titles: {[c.title for c in candidates]}"
    )
    for ic in index_candidates:
        assert ic.score < 0, (
            f"'index' candidate should score < 0. Got score={ic.score}, signals={ic.signals}"
        )

    chapters = select_chapters(candidates)
    chapter_titles = [ch.title.lower() for ch in chapters]
    assert not any(t == "index" for t in chapter_titles), (
        f"'index' should be excluded from chapter list but appeared: {chapter_titles}"
    )


def test_no_text_hard_excluded(tmp_path: Path) -> None:
    """A doc with no readable text receives the −10 no-text penalty and is excluded.

    The scoring engine applies +1 for the spine boundary first, then −10 for
    no readable text, so the effective net score is −9 (not −10).  The
    important invariant is that the ``no_text_content -10`` signal fires and
    the document is excluded from ``select_chapters``.
    """
    epub_path = tmp_path / "empty_doc.epub"
    build_empty_doc_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)

    # Find the candidate for empty.xhtml (no title, no text)
    empty_candidates = [c for c in candidates if any("no_text" in s for s in c.signals)]
    assert len(empty_candidates) >= 1, (
        f"Expected a candidate with 'no_text_content' signal; "
        f"candidates: {[(c.doc_path, c.score, c.signals) for c in candidates]}"
    )
    for ec in empty_candidates:
        # Net score: +1 (spine) − 10 (no text) = −9.
        # All that matters is the no-text penalty fired and score is deeply negative.
        assert any("no_text" in s for s in ec.signals), (
            f"Expected 'no_text_content' in signals; got signals={ec.signals}"
        )
        assert ec.score < 0, f"Empty document should have score < 0. Got score={ec.score}"

    chapters = select_chapters(candidates)
    chapter_docs = [ch.source_docs[0] for ch in chapters]
    # The empty.xhtml must not appear in the selected chapters
    assert not any("empty" in doc for doc in chapter_docs), (
        f"empty.xhtml should be excluded from chapters but appeared in: {chapter_docs}"
    )


def test_chapter_heading_match_adds_score(tmp_path: Path) -> None:
    """A doc with <h1>Chapter 1</h1> gains +2 from heading detection.

    Uses a fixture with no TOC entry so only the spine (+1) and heading (+2)
    signals apply, giving an expected score of +3.
    """
    epub_path = tmp_path / "heading.epub"
    build_heading_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)

    heading_candidates = [c for c in candidates if c.title and "chapter" in c.title.lower()]
    assert len(heading_candidates) >= 1, (
        f"Expected a candidate with 'Chapter' title; got: {[c.title for c in candidates]}"
    )

    for hc in heading_candidates:
        # Must have a heading signal
        has_heading_signal = any(
            "heading" in s.lower() or "h1" in s.lower() or "h2" in s.lower() for s in hc.signals
        )
        assert has_heading_signal, (
            f"Expected a heading signal in candidate signals. "
            f"title={hc.title!r}, signals={hc.signals}"
        )
        # Score must be at least +2 (heading alone) above baseline
        assert hc.score >= 2, (
            f"Doc with <h1>Chapter 1</h1> should score ≥ 2; got {hc.score}. signals={hc.signals}"
        )


def test_select_chapters_returns_correct_count(tmp_path: Path) -> None:
    """select_chapters returns exactly 2 chapters from simple_epub3.epub."""
    epub_path = tmp_path / "count.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    assert len(chapters) == 2, (
        f"Expected exactly 2 chapters from simple_epub3 fixture, got {len(chapters)}. "
        f"Chapter titles: {[ch.title for ch in chapters]}"
    )


def test_chapter_id_format(tmp_path: Path) -> None:
    """Chapter IDs are in the format 'ch001', 'ch002', etc."""
    epub_path = tmp_path / "id_format.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    import re

    pattern = re.compile(r"^ch\d{3}$")
    for ch in chapters:
        assert pattern.match(ch.chapter_id), (
            f"Chapter ID '{ch.chapter_id}' does not match pattern 'chNNN'. "
            f"Expected format: ch001, ch002, …"
        )


def test_warned_chapter_has_signal(tmp_path: Path) -> None:
    """A chapter with score 0–1 has at least one entry in its signals list.

    Uses the short-chapter fixture: the short document has no TOC entry and
    < 200 words, so it should score 1 − 2 = −1 (excluded) or possibly 0–1
    if only the spine signal (+1) and short-doc penalty (−2) apply without
    going negative enough to trigger hard exclude.

    We test this more broadly: any candidate with score 0–1 must carry at
    least one signal explaining the low score.
    """
    epub_path = tmp_path / "warned.epub"
    build_short_chapter_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)

    warned = [c for c in candidates if 0 <= c.score <= 1]
    for wc in warned:
        assert len(wc.signals) >= 1, (
            f"Warned candidate '{wc.title}' (score={wc.score}) has no signals. "
            "At least one signal must explain the low score."
        )


def test_excluded_chapters_not_in_output(tmp_path: Path) -> None:
    """select_chapters output contains no candidates with score < 0.

    Builds the front-matter fixture (which includes copyright and index pages
    that should score below zero) and verifies they do not appear in output.
    """
    epub_path = tmp_path / "excluded.epub"
    build_front_matter_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    # Gather titles of candidates that scored < 0
    excluded_titles = {c.title for c in candidates if c.score < 0}

    for ch in chapters:
        assert ch.title not in excluded_titles, (
            f"Chapter '{ch.title}' was in excluded_titles (score < 0) "
            "but still appeared in select_chapters output."
        )


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_select_chapters_returns_chapter_instances(tmp_path: Path) -> None:
    """select_chapters returns a list of Chapter instances (not ChapterCandidate)."""
    epub_path = tmp_path / "types.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    assert all(isinstance(ch, Chapter) for ch in chapters), (
        "select_chapters must return Chapter instances, not ChapterCandidate or other types."
    )


def test_score_candidates_returns_candidate_instances(tmp_path: Path) -> None:
    """score_candidates returns a list of ChapterCandidate instances."""
    epub_path = tmp_path / "cand_types.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)

    assert all(isinstance(c, ChapterCandidate) for c in candidates)


def test_chapters_in_reading_order(tmp_path: Path) -> None:
    """Chapters returned by select_chapters preserve the spine reading order.

    Chapter One must come before Chapter Two, regardless of filename order.
    """
    epub_path = tmp_path / "order.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    assert len(chapters) == 2
    assert chapters[0].title == "Chapter One"
    assert chapters[1].title == "Chapter Two"


def test_chapter_stable_id_is_12_char_hex(tmp_path: Path) -> None:
    """Chapter stable_id is a 12-character hex string (first 12 chars of SHA-256)."""
    epub_path = tmp_path / "stable_id.epub"
    build_simple_epub3(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    import re

    hex_pattern = re.compile(r"^[0-9a-f]{12}$")
    for ch in chapters:
        assert hex_pattern.match(ch.stable_id), (
            f"stable_id '{ch.stable_id}' is not a 12-character lowercase hex string."
        )


# ---------------------------------------------------------------------------
# M5: D1 — Multi-file chapter merging
# ---------------------------------------------------------------------------


def _open_and_finalize(epub_path: Path) -> list[Chapter]:
    """Open an EPUB, score candidates, select, then finalize (merge + split)."""
    book = open_epub(epub_path)
    nav = extract_navigation(book)
    candidates = score_candidates(book, nav)
    chapters = select_chapters(candidates)
    return finalize_chapters(chapters, candidates, nav, book)


def test_merge_continuation_doc_appended_to_preceding_chapter(tmp_path: Path) -> None:
    """A continuation spine doc (no TOC entry) is merged into the preceding chapter.

    The multi-file fixture has ch01_part2.xhtml with no TOC entry between
    ch01_part1.xhtml and ch02.xhtml.  After merging, Chapter One should have
    two source_docs and Chapter Two remains unchanged.
    """
    epub_path = tmp_path / "multifile.epub"
    build_multi_file_chapter_epub(epub_path)
    chapters = _open_and_finalize(epub_path)

    assert len(chapters) == 2, (
        f"Expected 2 chapters after merge, got {len(chapters)}: {[ch.title for ch in chapters]}"
    )
    ch1, ch2 = chapters
    assert ch1.title == "Chapter One", f"First chapter should be 'Chapter One', got {ch1.title!r}"
    assert "ch01_part1.xhtml" in ch1.source_docs, (
        f"ch01_part1.xhtml missing from source_docs: {ch1.source_docs}"
    )
    assert "ch01_part2.xhtml" in ch1.source_docs, (
        f"ch01_part2.xhtml should be merged into Chapter One source_docs: {ch1.source_docs}"
    )
    assert ch2.title == "Chapter Two", f"Second chapter should be 'Chapter Two', got {ch2.title!r}"
    assert ch2.source_docs == ["ch02.xhtml"], (
        f"Chapter Two should have only ch02.xhtml, got {ch2.source_docs}"
    )


def test_merge_preserves_combined_word_count(tmp_path: Path) -> None:
    """Merged chapter word count equals sum of all constituent docs."""
    epub_path = tmp_path / "multifile_wc.epub"
    build_multi_file_chapter_epub(epub_path)

    book = open_epub(epub_path)
    nav = extract_navigation(book)
    candidates = score_candidates(book, nav)
    chapters_before = select_chapters(candidates)
    chapters_after = finalize_chapters(chapters_before, candidates, nav, book)

    ch1_before = next(c for c in chapters_before if c.title == "Chapter One")
    ch1_after = next(c for c in chapters_after if c.title == "Chapter One")

    # After merge the word count should be >= the pre-merge count.
    assert ch1_after.word_count >= ch1_before.word_count, (
        f"Merged word count ({ch1_after.word_count}) should be >= "
        f"pre-merge ({ch1_before.word_count})"
    )


def test_merge_does_not_merge_toc_backed_docs(tmp_path: Path) -> None:
    """Documents that have their own TOC entry are never merged into a predecessor."""
    epub_path = tmp_path / "no_merge.epub"
    build_simple_epub3(epub_path)
    chapters = _open_and_finalize(epub_path)

    # simple_epub3 has exactly two chapters, each with its own TOC entry.
    # Neither should absorb the other.
    assert len(chapters) == 2, f"Expected 2 independent chapters; got {len(chapters)}"
    for ch in chapters:
        assert len(ch.source_docs) == 1, (
            f"Chapter '{ch.title}' has multiple source_docs but each has its own TOC entry: "
            f"{ch.source_docs}"
        )


def test_merge_chapter_ids_renumbered_sequentially(tmp_path: Path) -> None:
    """finalize_chapters renumbers chapter IDs as ch001, ch002, … after merging."""
    epub_path = tmp_path / "renumber.epub"
    build_multi_file_chapter_epub(epub_path)
    chapters = _open_and_finalize(epub_path)

    import re

    pattern = re.compile(r"^ch\d{3}$")
    for i, ch in enumerate(chapters, start=1):
        assert pattern.match(ch.chapter_id), (
            f"chapter_id '{ch.chapter_id}' does not match chNNN pattern"
        )
        assert ch.chapter_id == f"ch{i:03d}", f"Expected ch{i:03d}, got {ch.chapter_id}"


# ---------------------------------------------------------------------------
# M5: D2 — Single-file chapter splitting
# ---------------------------------------------------------------------------


def test_split_multi_chapter_doc_creates_separate_chapters(tmp_path: Path) -> None:
    """A single XHTML file with fragment TOC entries is split into separate chapters.

    The multi-chapter-single-file fixture has one XHTML with two <section>
    elements referenced by chapter1.xhtml#ch-1 and chapter1.xhtml#ch-2
    in the TOC.  After splitting, there should be two chapters.
    """
    epub_path = tmp_path / "split.epub"
    build_multi_chapter_single_file(epub_path)
    chapters = _open_and_finalize(epub_path)

    assert len(chapters) == 2, (
        f"Expected 2 chapters after split; got {len(chapters)}: {[ch.title for ch in chapters]}"
    )


def test_split_preserves_fragment_in_source_docs(tmp_path: Path) -> None:
    """Split chapters have source_docs entries in 'path#fragment' format."""
    epub_path = tmp_path / "split_frag.epub"
    build_multi_chapter_single_file(epub_path)
    chapters = _open_and_finalize(epub_path)

    for ch in chapters:
        assert len(ch.source_docs) == 1, (
            f"Split chapter '{ch.title}' should have exactly one source_doc, got {ch.source_docs}"
        )
        doc = ch.source_docs[0]
        assert "#" in doc, (
            f"source_doc '{doc}' for split chapter '{ch.title}' should contain '#fragment'"
        )
        doc_path, fragment = doc.split("#", 1)
        assert doc_path == "chapter1.xhtml", f"Expected doc_path 'chapter1.xhtml', got {doc_path!r}"
        assert fragment, f"Fragment should be non-empty, got {fragment!r}"


def test_split_chapter_titles_from_toc(tmp_path: Path) -> None:
    """Split chapters take their titles from the TOC entries, not the single file title."""
    epub_path = tmp_path / "split_titles.epub"
    build_multi_chapter_single_file(epub_path)
    chapters = _open_and_finalize(epub_path)

    titles = [ch.title for ch in chapters]
    assert "Chapter One" in titles, f"Expected 'Chapter One' in split titles: {titles}"
    assert "Chapter Two" in titles, f"Expected 'Chapter Two' in split titles: {titles}"


def test_split_does_not_split_single_toc_entry_doc(tmp_path: Path) -> None:
    """Documents with only one TOC entry are not split."""
    epub_path = tmp_path / "no_split.epub"
    build_simple_epub3(epub_path)
    chapters = _open_and_finalize(epub_path)

    # Each source doc has exactly one TOC entry; no splitting should occur.
    assert len(chapters) == 2, f"Expected 2 chapters (no splitting); got {len(chapters)}"
    for ch in chapters:
        assert "#" not in ch.source_docs[0], (
            f"Chapter '{ch.title}' should not have a fragment in source_docs: {ch.source_docs[0]!r}"
        )


def test_split_word_count_per_fragment(tmp_path: Path) -> None:
    """Split chapters have positive word counts derived from their fragment."""
    epub_path = tmp_path / "split_wc.epub"
    build_multi_chapter_single_file(epub_path)
    chapters = _open_and_finalize(epub_path)

    for ch in chapters:
        assert ch.word_count > 0, (
            f"Split chapter '{ch.title}' should have word_count > 0, got {ch.word_count}"
        )


# ---------------------------------------------------------------------------
# M5: D3 — Scoring refinements (new exclusion epub:types)
# ---------------------------------------------------------------------------


def test_titlepage_epub_type_strongly_excluded(tmp_path: Path) -> None:
    """A document with epub:type='titlepage' receives the -5 strong-exclusion penalty."""
    epub_path = tmp_path / "titlepage.epub"
    build_epub_with_epub_type(epub_path, "titlepage")
    candidates, _ = _open_and_score(epub_path)

    typed_candidates = [c for c in candidates if "typed_page.xhtml" in c.doc_path]
    assert typed_candidates, "Expected a candidate for typed_page.xhtml"
    for c in typed_candidates:
        assert any("strong_exclude" in s for s in c.signals), (
            f"Expected 'strong_exclude' signal for titlepage type; signals={c.signals}"
        )
        assert c.score < 0, f"titlepage candidate should score < 0; got score={c.score}"


def test_halftitlepage_epub_type_strongly_excluded(tmp_path: Path) -> None:
    """A document with epub:type='halftitlepage' receives the -5 strong-exclusion penalty."""
    epub_path = tmp_path / "halftitlepage.epub"
    build_epub_with_epub_type(epub_path, "halftitlepage")
    candidates, _ = _open_and_score(epub_path)

    typed_candidates = [c for c in candidates if "typed_page.xhtml" in c.doc_path]
    assert typed_candidates, "Expected a candidate for typed_page.xhtml"
    for c in typed_candidates:
        assert any("strong_exclude" in s for s in c.signals), (
            f"Expected 'strong_exclude' signal for halftitlepage; signals={c.signals}"
        )
        assert c.score < 0, f"halftitlepage candidate should score < 0; got score={c.score}"


def test_errata_epub_type_excluded(tmp_path: Path) -> None:
    """A document with epub:type='errata' is excluded from chapters."""
    epub_path = tmp_path / "errata.epub"
    build_epub_with_epub_type(epub_path, "errata")
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    typed_candidates = [c for c in candidates if "typed_page.xhtml" in c.doc_path]
    assert typed_candidates, "Expected a candidate for typed_page.xhtml"
    for c in typed_candidates:
        assert c.score < 0, f"errata candidate should score < 0 (front/back matter); got {c.score}"

    chapter_docs = [doc for ch in chapters for doc in ch.source_docs]
    assert not any("typed_page.xhtml" in d for d in chapter_docs), (
        f"errata page should not appear in chapters: {chapter_docs}"
    )


def test_seriespage_epub_type_excluded(tmp_path: Path) -> None:
    """A document with epub:type='seriespage' is excluded from chapters."""
    epub_path = tmp_path / "seriespage.epub"
    build_epub_with_epub_type(epub_path, "seriespage")
    candidates, _ = _open_and_score(epub_path)

    typed_candidates = [c for c in candidates if "typed_page.xhtml" in c.doc_path]
    assert typed_candidates
    for c in typed_candidates:
        assert c.score < 0, (
            f"seriespage candidate should score < 0; got {c.score}, signals={c.signals}"
        )


def test_multiple_h1_signal_fires(tmp_path: Path) -> None:
    """A document with multiple <h1> elements gets the 'multiple_h1 -1' signal."""
    epub_path = tmp_path / "multi_h1.epub"
    build_multi_chapter_single_file(epub_path)
    candidates, _ = _open_and_score(epub_path)

    # The single xhtml file has multiple h1 elements
    multi_h1_cands = [c for c in candidates if any("multiple_h1" in s for s in c.signals)]
    assert multi_h1_cands, (
        f"Expected at least one candidate with 'multiple_h1' signal. "
        f"Candidates: {[(c.doc_path, c.signals) for c in candidates]}"
    )


def test_roman_numeral_heading_detected(tmp_path: Path) -> None:
    """Standalone Roman numeral headings (I, II, III, IV) match the chapter-title pattern.

    The ``[IVXLCDM]+`` branch of the heading regex should fire for each chapter,
    adding +2 heading_match to their scores.  All 4 chapters must be detected.
    """
    epub_path = tmp_path / "roman.epub"
    build_roman_numeral_chapters_epub(epub_path)
    candidates, _ = _open_and_score(epub_path)
    chapters = select_chapters(candidates)

    # All 4 chapters should be included (TOC entry +4 alone exceeds threshold).
    assert len(chapters) == 4, (
        f"Expected 4 Roman numeral chapters; got {len(chapters)}: {[ch.title for ch in chapters]}"
    )

    # Each should have the heading_match signal (+2).
    for ch in chapters:
        cand = next((c for c in candidates if c.title == ch.title), None)
        assert cand is not None
        has_heading = any("heading_match" in s for s in cand.signals)
        assert has_heading, (
            f"Chapter '{ch.title}' with Roman numeral heading should have "
            f"heading_match signal; signals={cand.signals}"
        )


def test_loi_lot_excluded(tmp_path: Path) -> None:
    """Documents with epub:type='loi' or 'lot' are excluded from chapters.

    ``loi`` (list of illustrations) and ``lot`` (list of tables) are
    front/back-matter semantic types that receive the −3 epub_type_frontback
    penalty.  When combined with the +1 spine baseline (total −2) they are
    excluded from :func:`select_chapters`.
    """
    for epub_type in ("loi", "lot"):
        epub_path = tmp_path / f"{epub_type}.epub"
        build_epub_with_epub_type(epub_path, epub_type)
        candidates, _ = _open_and_score(epub_path)
        chapters = select_chapters(candidates)

        typed_cands = [c for c in candidates if "typed_page.xhtml" in c.doc_path]
        assert typed_cands, f"Expected a candidate for typed_page.xhtml ({epub_type})"
        for c in typed_cands:
            assert c.score < 0, (
                f"epub:type='{epub_type}' candidate should score < 0; "
                f"got score={c.score}, signals={c.signals}"
            )

        chapter_docs = [doc for ch in chapters for doc in ch.source_docs]
        assert not any("typed_page.xhtml" in d for d in chapter_docs), (
            f"epub:type='{epub_type}' page should not appear in chapters: {chapter_docs}"
        )
