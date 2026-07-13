"""Tests for navigation extraction from EPUB files.

Covers M1-16: all required test cases for epub/navigation.py.

The most critical test here is ``test_spine_order_not_filename_order``.
The builders intentionally assign XHTML filenames so that alphabetical
filename order is the OPPOSITE of reading order:

    a_chapter_02.xhtml  →  Chapter Two   (sorts first alphabetically)
    b_chapter_01.xhtml  →  Chapter One   (sorts second alphabetically)

The spine and nav both declare reading order as Chapter One → Chapter Two.
A correct implementation follows the spine/nav; a broken one would sort
filenames and get the order backwards.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epub2audio.epub.navigation import extract_navigation
from epub2audio.epub.reader import open_epub
from epub2audio.models import NavigationEntry
from tests.fixtures.builders import (
    build_multi_chapter_single_file,
    build_no_nav_epub,
    build_simple_epub2,
    build_simple_epub3,
)

# ---------------------------------------------------------------------------
# Module-scoped book fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def epub3_entries(tmp_path_factory: pytest.TempPathFactory) -> list[NavigationEntry]:
    """Navigation entries from the simple EPUB3 fixture."""
    p = tmp_path_factory.mktemp("nav_epub3") / "simple.epub"
    build_simple_epub3(p)
    book = open_epub(p)
    return extract_navigation(book)


@pytest.fixture(scope="module")
def epub2_entries(tmp_path_factory: pytest.TempPathFactory) -> list[NavigationEntry]:
    """Navigation entries from the simple EPUB2 fixture."""
    p = tmp_path_factory.mktemp("nav_epub2") / "simple.epub"
    build_simple_epub2(p)
    book = open_epub(p)
    return extract_navigation(book)


@pytest.fixture(scope="module")
def fragment_entries(tmp_path_factory: pytest.TempPathFactory) -> list[NavigationEntry]:
    """Navigation entries from the multi-chapter-single-file fixture."""
    p = tmp_path_factory.mktemp("nav_frag") / "multi.epub"
    build_multi_chapter_single_file(p)
    book = open_epub(p)
    return extract_navigation(book)


# ---------------------------------------------------------------------------
# M1-16 required test cases
# ---------------------------------------------------------------------------


def test_epub3_nav_returns_two_entries(epub3_entries: list[NavigationEntry]) -> None:
    """EPUB3 fixture produces exactly 2 NavigationEntry objects."""
    assert len(epub3_entries) == 2


def test_epub2_ncx_returns_two_entries(epub2_entries: list[NavigationEntry]) -> None:
    """EPUB2 fixture produces exactly 2 NavigationEntry objects."""
    assert len(epub2_entries) == 2


def test_spine_order_not_filename_order(
    tmp_path: Path,
) -> None:
    """Navigation entries follow spine/nav order, NOT filename alphabetical order.

    The builder assigns:
        a_chapter_02.xhtml  →  Chapter Two   (sorts FIRST alphabetically)
        b_chapter_01.xhtml  →  Chapter One   (sorts SECOND alphabetically)

    Reading order (spine + nav) is Chapter One first, Chapter Two second.

    A correct implementation returns Chapter One as entry[0].
    A broken filename-sort implementation would return Chapter Two as entry[0].
    """
    epub_path = tmp_path / "spine_order.epub"
    build_simple_epub3(epub_path)
    book = open_epub(epub_path)
    entries = extract_navigation(book)

    assert len(entries) >= 2, "Expected at least 2 navigation entries"

    # The FIRST entry in reading order must be Chapter One.
    # If the implementation sorted by filename, it would be Chapter Two (a_ < b_).
    assert entries[0].title == "Chapter One", (
        f"First navigation entry should be 'Chapter One' (reading/spine order), "
        f"but got '{entries[0].title}'. "
        f"This indicates the implementation is using filename sort order instead of spine order."
    )
    assert entries[1].title == "Chapter Two", (
        f"Second navigation entry should be 'Chapter Two', but got '{entries[1].title}'."
    )

    # Also verify the filenames are indeed in the wrong alphabetical order,
    # confirming the test is actually exercising the spine-vs-alpha distinction.
    first_doc = entries[0].doc_path
    second_doc = entries[1].doc_path
    assert first_doc > second_doc, (
        f"Test invariant violated: first doc '{first_doc}' should sort AFTER "
        f"second doc '{second_doc}' alphabetically (to prove filename-order is wrong). "
        f"The builder may have changed its filename assignment scheme."
    )


def test_nav_titles_match_chapter_titles(epub3_entries: list[NavigationEntry]) -> None:
    """NavigationEntry titles match the chapter titles set during build."""
    titles = [e.title for e in epub3_entries]
    assert "Chapter One" in titles
    assert "Chapter Two" in titles


def test_epub3_fragment_resolution(fragment_entries: list[NavigationEntry]) -> None:
    """Fragment anchors in nav hrefs are split into doc_path and fragment fields.

    The multi-chapter-single-file builder creates links like
    ``chapter1.xhtml#ch-1`` which must be split into
    ``doc_path="chapter1.xhtml"`` and ``fragment="ch-1"``.
    """
    assert len(fragment_entries) >= 2

    for entry in fragment_entries:
        # doc_path must not contain a '#'
        assert "#" not in entry.doc_path, (
            f"doc_path '{entry.doc_path}' contains '#'; fragment was not split out."
        )

    # At least one entry must have a non-None fragment
    fragments = [e.fragment for e in fragment_entries if e.fragment is not None]
    assert len(fragments) >= 1, (
        "Expected at least one NavigationEntry with a fragment from multi-chapter fixture."
    )

    # The first fragment should be 'ch-1'
    first_entry_with_fragment = next(e for e in fragment_entries if e.fragment is not None)
    assert first_entry_with_fragment.fragment == "ch-1", (
        f"Expected first fragment to be 'ch-1', got '{first_entry_with_fragment.fragment}'."
    )


def test_epub2_ncx_fragment_resolution(
    tmp_path: Path,
) -> None:
    """Fragment anchors in NCX src attributes are split into doc_path + fragment.

    Build an EPUB2 whose NCX entries reference fragments and verify the split.
    """
    epub_path = tmp_path / "frag_epub2.epub"
    # Use multi-chapter single file with EPUB2 style — the builder adds NCX
    build_multi_chapter_single_file(epub_path)
    book = open_epub(epub_path)
    entries = extract_navigation(book)

    assert len(entries) >= 2

    for entry in entries:
        assert "#" not in entry.doc_path, (
            f"doc_path '{entry.doc_path}' still contains '#' — fragment not split."
        )

    fragments = [e.fragment for e in entries if e.fragment is not None]
    assert len(fragments) >= 1, "Expected at least one fragment in multi-chapter fixture."


def test_fallback_spine_order_on_no_nav(tmp_path: Path) -> None:
    """When an EPUB has no EPUB3 nav and an empty NCX navMap, falls back to spine order.

    Uses the ``build_no_nav_epub`` builder which produces an EPUB with a valid
    spine but an empty ``<navMap/>`` in the NCX (no nav entries).

    Expected: one :class:`NavigationEntry` per spine item with ``title=""``.
    """
    epub_path = tmp_path / "no_nav.epub"
    build_no_nav_epub(epub_path)
    book = open_epub(epub_path)
    entries = extract_navigation(book)

    # Should have one entry per non-nav spine item (default is 2 chapters)
    assert len(entries) >= 2, f"Expected at least 2 spine-fallback entries, got {len(entries)}."


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_navigation_entries_are_navigationentry_instances(
    epub3_entries: list[NavigationEntry],
) -> None:
    """extract_navigation returns a list of NavigationEntry instances."""
    assert all(isinstance(e, NavigationEntry) for e in epub3_entries)


def test_epub2_nav_titles_match(epub2_entries: list[NavigationEntry]) -> None:
    """EPUB2 NavigationEntry titles match the chapter titles set during build."""
    titles = [e.title for e in epub2_entries]
    assert "Chapter One" in titles
    assert "Chapter Two" in titles


def test_epub2_spine_order_not_filename_order(tmp_path: Path) -> None:
    """EPUB2: reading order from NCX/spine is used, not filename alphabetical order."""
    epub_path = tmp_path / "epub2_spine.epub"
    build_simple_epub2(epub_path)
    book = open_epub(epub_path)
    entries = extract_navigation(book)

    assert len(entries) >= 2
    assert entries[0].title == "Chapter One", (
        f"EPUB2: first entry should be 'Chapter One' (spine order), got '{entries[0].title}'."
    )
