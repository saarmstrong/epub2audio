"""Tests for BookMetadata extraction from EPUB files.

Covers M1-15: all required test cases for epub/metadata.py.
Tests are written against the public API (open_epub + extract_metadata)
and will pass once the Architect's models.py and EPUB Engineer's epub/
modules are complete.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epub2audio.epub.metadata import extract_metadata
from epub2audio.epub.reader import open_epub
from epub2audio.models import BookMetadata
from tests.fixtures.builders import build_simple_epub2, build_simple_epub3

# ---------------------------------------------------------------------------
# Session-scoped book fixtures (avoid re-opening the same file repeatedly)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def epub3_book(tmp_path_factory: pytest.TempPathFactory) -> object:
    """Open the simple EPUB3 fixture and return the EpubBook."""
    p = tmp_path_factory.mktemp("epub3") / "simple_epub3.epub"
    build_simple_epub3(p, title="Test Book", author="Test Author")
    return open_epub(p)


@pytest.fixture(scope="module")
def epub2_book(tmp_path_factory: pytest.TempPathFactory) -> object:
    """Open the simple EPUB2 fixture and return the EpubBook."""
    p = tmp_path_factory.mktemp("epub2") / "simple_epub2.epub"
    build_simple_epub2(p, title="Test Book EPUB2", author="Test Author")
    return open_epub(p)


@pytest.fixture(scope="module")
def epub3_metadata(epub3_book: object) -> BookMetadata:
    """Extract metadata from the EPUB3 fixture."""
    return extract_metadata(epub3_book)


@pytest.fixture(scope="module")
def epub2_metadata(epub2_book: object) -> BookMetadata:
    """Extract metadata from the EPUB2 fixture."""
    return extract_metadata(epub2_book)


# ---------------------------------------------------------------------------
# M1-15 required test cases
# ---------------------------------------------------------------------------


def test_title_extracted(epub3_metadata: BookMetadata) -> None:
    """Extracted title matches the book title set during build."""
    assert epub3_metadata.title == "Test Book"


def test_author_extracted(epub3_metadata: BookMetadata) -> None:
    """Extracted author matches the author set during build."""
    assert epub3_metadata.author == "Test Author"


def test_language_extracted(epub3_metadata: BookMetadata) -> None:
    """Extracted language is 'en' for the default test fixtures."""
    assert epub3_metadata.language == "en"


def test_identifier_extracted(epub3_metadata: BookMetadata) -> None:
    """Extracted identifier is a non-empty string."""
    assert isinstance(epub3_metadata.identifier, str)
    assert len(epub3_metadata.identifier) > 0


def test_missing_publisher_is_none(epub3_metadata: BookMetadata) -> None:
    """When no publisher is set, BookMetadata.publisher is None."""
    # The builder never sets a publisher, so it must fall back to None.
    assert epub3_metadata.publisher is None


def test_title_fallback_on_empty(tmp_path: Path) -> None:
    """When title is empty/missing, fallback is 'Unknown Title'."""
    # Build a book with an empty title
    epub_path = tmp_path / "no_title.epub"
    build_simple_epub3(epub_path, title="")
    book = open_epub(epub_path)
    meta = extract_metadata(book)
    assert meta.title == "Unknown Title"


def test_author_fallback_on_empty(tmp_path: Path) -> None:
    """When author is missing, fallback is 'Unknown Author'."""
    epub_path = tmp_path / "no_author.epub"
    # Build with a whitespace-only author to trigger fallback
    build_simple_epub3(epub_path, author="")
    book = open_epub(epub_path)
    meta = extract_metadata(book)
    assert meta.author == "Unknown Author"


# ---------------------------------------------------------------------------
# Additional coverage: EPUB2 metadata extraction
# ---------------------------------------------------------------------------


def test_epub2_title_extracted(epub2_metadata: BookMetadata) -> None:
    """EPUB2 fixture: title is extracted correctly from OPF."""
    assert epub2_metadata.title == "Test Book EPUB2"


def test_epub2_author_extracted(epub2_metadata: BookMetadata) -> None:
    """EPUB2 fixture: author is extracted correctly from OPF."""
    assert epub2_metadata.author == "Test Author"


def test_epub2_language_extracted(epub2_metadata: BookMetadata) -> None:
    """EPUB2 fixture: language field is 'en'."""
    assert epub2_metadata.language == "en"


def test_metadata_is_bookmetadata_instance(epub3_metadata: BookMetadata) -> None:
    """extract_metadata returns a BookMetadata instance."""
    assert isinstance(epub3_metadata, BookMetadata)
