# M1-Tester Task Contract

**Agent:** Tester  
**Milestone:** 1 — Inspectable EPUB Plan  
**Tasks:** M1-12 through M1-17  
**Date assigned:** 2026-07-12  
**Depends on:** M1-architect (models.py, errors.py) and M1-epub-engineer (epub/ modules) must be complete

---

## M1-12 — Write `tests/fixtures/builders.py`

### Goal

A programmatic EPUB factory that builds test fixtures using ebooklib. No copyrighted content — all text must be generated placeholder content.

### Public API

```python
def build_simple_epub3(
    output_path: Path,
    title: str = "Test Book",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
    include_cover: bool = True,
) -> Path:
    """Build a simple EPUB3 with nav document and optional cover.

    Args:
        output_path: Where to write the .epub file.
        title: Book title metadata.
        author: Book author metadata.
        chapters: List of (chapter_title, chapter_text) tuples.
                  Defaults to 2 chapters with placeholder text.
        include_cover: If True, embed a minimal 1x1 PNG cover image.

    Returns:
        The output_path after writing.
    """

def build_simple_epub2(
    output_path: Path,
    title: str = "Test Book EPUB2",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
) -> Path:
    """Build a simple EPUB2 with NCX toc.ncx.

    Args:
        output_path: Where to write the .epub file.
        title: Book title metadata.
        author: Book author metadata.
        chapters: List of (chapter_title, chapter_text) tuples.
                  Defaults to 2 chapters with placeholder text.

    Returns:
        The output_path after writing.
    """

def build_multi_chapter_single_file(
    output_path: Path,
    title: str = "Multi-Chapter Single File",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
) -> Path:
    """Build an EPUB where multiple chapters exist in a single XHTML file.

    Chapter headings use <h1> elements with id attributes.
    The nav document references fragment anchors (e.g., chapter1.xhtml#ch-2).

    Returns:
        The output_path after writing.
    """
```

### Default placeholder text

When `chapters` is not provided, use:

```python
DEFAULT_CHAPTERS = [
    (
        "Chapter One",
        "This is the first chapter of the test book. "
        "It contains placeholder text for testing purposes only. "
        "The quick brown fox jumps over the lazy dog. " * 20,
    ),
    (
        "Chapter Two",
        "This is the second chapter of the test book. "
        "More placeholder text follows here for testing. "
        "Pack my box with five dozen liquor jugs. " * 20,
    ),
]
```

### Cover image

When `include_cover=True`, embed a minimal 1×1 white PNG (create programmatically with `struct` + zlib — do not use Pillow which is not a dependency). Store the bytes as a constant `_MINIMAL_PNG`.

### Notes

- Use ebooklib (`from ebooklib import epub`) to build EPUB files.
- All chapter XHTML must be valid XHTML5 with a proper `<!DOCTYPE html>` declaration.
- Reading order **must match nav/NCX order**, not filename alphabetical order. Verify this by making chapter 2's XHTML filename alphabetically precede chapter 1's (e.g., `a_chapter.xhtml` for chapter 2, `b_chapter.xhtml` for chapter 1) so that tests can verify spine order is used.
- All docstrings and type annotations required.

---

## M1-13 — Generate `tests/fixtures/simple_epub3.epub`

### Goal

Run the builder and commit the generated fixture.

### Command

```python
# In tests/fixtures/builders.py or a standalone script:
# python -c "from tests.fixtures.builders import build_simple_epub3; from pathlib import Path; build_simple_epub3(Path('tests/fixtures/simple_epub3.epub'))"
```

### Requirements

- 2 chapters, cover image, EPUB3 nav doc
- Must be readable by ebooklib
- Must not contain any copyrighted content
- File size should be < 50 KB

---

## M1-14 — Generate `tests/fixtures/simple_epub2.epub`

### Goal

Run the builder and commit the generated fixture.

### Command

```python
# python -c "from tests.fixtures.builders import build_simple_epub2; from pathlib import Path; build_simple_epub2(Path('tests/fixtures/simple_epub2.epub'))"
```

### Requirements

- 2 chapters, NCX `toc.ncx`
- Must be readable by ebooklib
- Must not contain any copyrighted content
- File size should be < 50 KB

---

## M1-15 — Write `tests/epub/test_metadata.py`

### Goal

Tests for `BookMetadata` extraction.

### Test cases (all required)

```python
def test_title_extracted():
    """Extracted title matches the book title set during build."""

def test_author_extracted():
    """Extracted author matches the author set during build."""

def test_language_extracted():
    """Extracted language is 'en' for the default test fixtures."""

def test_identifier_extracted():
    """Extracted identifier is a non-empty string."""

def test_missing_publisher_is_none():
    """When no publisher is set, BookMetadata.publisher is None."""

def test_title_fallback_on_empty():
    """When title is empty/missing, fallback is 'Unknown Title'."""

def test_author_fallback_on_empty():
    """When author is missing, fallback is 'Unknown Author'."""
```

### Notes

- Use `simple_epub3.epub` and `simple_epub2.epub` fixtures.
- Use `open_epub` + `extract_metadata` — test behaviour, not implementation.
- Use `pytest.fixture` for book objects where reuse makes tests cleaner.

---

## M1-16 — Write `tests/epub/test_navigation.py`

### Goal

Tests for navigation extraction, especially reading order correctness.

### Test cases (all required)

```python
def test_epub3_nav_returns_two_entries():
    """EPUB3 fixture produces exactly 2 NavigationEntry objects."""

def test_epub2_ncx_returns_two_entries():
    """EPUB2 fixture produces exactly 2 NavigationEntry objects."""

def test_spine_order_not_filename_order():
    """Navigation entries follow spine order, not filename alphabetical order.

    The builders.py intentionally assigns filenames so alphabetical ≠ reading order.
    This test verifies the first entry is 'Chapter One' regardless of filename sort.
    """

def test_nav_titles_match_chapter_titles():
    """NavigationEntry titles match the chapter titles set during build."""

def test_epub3_fragment_resolution():
    """Fragment anchors in nav hrefs are split into doc_path + fragment fields."""

def test_epub2_ncx_fragment_resolution():
    """Fragment anchors in NCX src are split into doc_path + fragment fields."""

def test_fallback_spine_order_on_no_nav():
    """When an EPUB has neither nav nor NCX, one entry per spine item is returned."""
```

### Notes

- Use all three fixture types: `simple_epub3.epub`, `simple_epub2.epub`, and (for the fallback test) a programmatically-built no-nav EPUB using `builders.py`.
- The `test_spine_order_not_filename_order` test is the most critical test in Milestone 1. Make it unambiguous.

---

## M1-17 — Write `tests/epub/test_chapters.py`

### Goal

Tests for the scoring engine and chapter selection.

### Test cases (all required)

```python
def test_toc_entry_gives_positive_score():
    """A doc that has a TOC entry scores ≥ 4."""

def test_short_doc_penalised():
    """A doc with < 200 words is penalised by −2."""

def test_front_matter_keyword_excluded():
    """A doc titled 'copyright' scores < 0 and is excluded from select_chapters."""

def test_back_matter_keyword_excluded():
    """A doc titled 'index' scores < 0 and is excluded from select_chapters."""

def test_no_text_hard_excluded():
    """A doc with no readable text scores ≤ −10 and is excluded."""

def test_chapter_heading_match_adds_score():
    """A doc with <h1>Chapter 1</h1> gains +2 from heading detection."""

def test_select_chapters_returns_correct_count():
    """select_chapters returns exactly 2 chapters from simple_epub3.epub."""

def test_chapter_id_format():
    """Chapter IDs are in the format 'ch001', 'ch002', etc."""

def test_warned_chapter_has_signal():
    """A chapter with score 0–1 has at least one entry in its signals list."""

def test_excluded_chapters_not_in_output():
    """select_chapters output contains no excluded chapters (score < 0)."""
```

### Notes

- Build targeted fixtures using `builders.py` for edge cases (front matter, empty docs).
- Test `score_candidates` and `select_chapters` independently.
- Test behaviour, not implementation details.

---

## Done criteria

- [ ] `tests/fixtures/builders.py` fully implemented
- [ ] `tests/fixtures/simple_epub3.epub` generated and committed
- [ ] `tests/fixtures/simple_epub2.epub` generated and committed
- [ ] All test files written with all required test cases
- [ ] `uv run pytest tests/epub/ -v` passes with zero failures and zero suppressed tests
- [ ] No copyrighted content anywhere in tests or fixtures
- [ ] Task moved to `tasks/completed/`
