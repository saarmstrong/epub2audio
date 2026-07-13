# M5 — Tester Task: Chapter-Detection Edge Case Tests

**Milestone:** 5 — Chapter-detection hardening  
**Agent:** Tester  
**Depends on:** M5-epub-engineer (partial — fixture builders can be written in parallel)  
**Blocks:** M5-reviewer

---

## Overview

Create test fixtures and tests for complex chapter-detection scenarios:
multi-file chapters, single-file with multiple chapters, and edge cases.

---

## Test Fixtures to Create

### `tests/fixtures/builders.py` additions

```python
def build_multifile_chapter_epub(output_path: Path) -> Path:
    """EPUB where one logical chapter spans multiple spine documents.
    
    Creates:
    - ch01_part1.xhtml (has TOC entry "Chapter 1", 300 words)
    - ch01_part2.xhtml (no TOC entry, 200 words, continues chapter 1)
    - ch01_part3.xhtml (no TOC entry, 150 words, continues chapter 1)
    - ch02.xhtml (has TOC entry "Chapter 2", 400 words)
    
    Expected: 2 chapters, first has 3 source_docs.
    """

def build_singlefile_multichapter_epub(output_path: Path) -> Path:
    """EPUB where one document contains multiple chapters via h1 tags.
    
    Creates:
    - chapters.xhtml containing:
      - <h1 id="prologue">Prologue</h1> + 200 words
      - <h1 id="ch1">Chapter 1</h1> + 300 words
      - <h1 id="ch2">Chapter 2</h1> + 250 words
    - TOC with fragment links: #prologue, #ch1, #ch2
    
    Expected: 3 chapters, each with fragment-scoped source_doc.
    """

def build_fragment_toc_epub(output_path: Path) -> Path:
    """EPUB with TOC entries using fragments within same file.
    
    Creates:
    - content.xhtml with multiple sections
    - TOC: "Part 1" → content.xhtml#part1, "Part 2" → content.xhtml#part2
    
    Expected: 2 chapters split at fragment boundaries.
    """

def build_titlepage_epub(output_path: Path) -> Path:
    """EPUB with epub:type="titlepage" document.
    
    Expected: titlepage excluded (score < 0), other chapters included.
    """

def build_continued_chapter_epub(output_path: Path) -> Path:
    """EPUB with 'Chapter 1 (continued)' pattern.
    
    Creates:
    - ch01.xhtml (TOC: "Chapter 1")
    - ch01_cont.xhtml (heading: "Chapter 1 (continued)", no TOC entry)
    - ch02.xhtml (TOC: "Chapter 2")
    
    Expected: 2 chapters, first merges both ch01 documents.
    """

def build_roman_numeral_chapters_epub(output_path: Path) -> Path:
    """EPUB with Roman numeral chapter headings.
    
    Creates chapters titled "I", "II", "III", "IV"
    
    Expected: All 4 chapters detected via heading pattern match.
    """

def build_mixed_heading_epub(output_path: Path) -> Path:
    """EPUB mixing h1 and h2 for chapters.
    
    Some books use h1 for parts and h2 for chapters within parts.
    
    Creates:
    - Part 1 (h1) containing Chapter 1 (h2), Chapter 2 (h2)
    - Part 2 (h1) containing Chapter 3 (h2)
    
    Expected: Detect both parts AND chapters, or just chapters depending on scoring.
    """
```

---

## Test Cases

### `tests/epub/test_chapter_merge.py` (new file)

```python
class TestMultiFileChapterMerge:
    """Tests for D1: merging consecutive spine docs into one chapter."""
    
    def test_consecutive_docs_without_toc_merged(self, tmp_path):
        """Docs following a TOC-entry doc without their own entries are merged."""
    
    def test_merged_chapter_has_all_source_docs(self, tmp_path):
        """Chapter.source_docs contains all merged document paths."""
    
    def test_merged_chapter_word_count_is_sum(self, tmp_path):
        """Chapter.word_count sums words from all merged docs."""
    
    def test_merge_stops_at_next_toc_entry(self, tmp_path):
        """Merge does not include docs that have their own TOC entry."""
    
    def test_continued_pattern_triggers_merge(self, tmp_path):
        """'Chapter N (continued)' heading triggers merge with preceding chapter."""
    
    def test_standalone_low_score_doc_not_merged(self, tmp_path):
        """A low-score doc not adjacent to a chapter is excluded, not merged."""
```

### `tests/epub/test_chapter_split.py` (new file)

```python
class TestSingleFileChapterSplit:
    """Tests for D2: splitting single files with multiple chapters."""
    
    def test_multiple_h1_triggers_split(self, tmp_path):
        """Document with multiple h1 elements produces multiple chapters."""
    
    def test_fragment_toc_entries_create_chapters(self, tmp_path):
        """TOC entries with #fragment create separate chapters."""
    
    def test_split_chapters_have_correct_fragments(self, tmp_path):
        """Each split chapter's source_doc includes fragment identifier."""
    
    def test_split_chapter_text_extraction(self, tmp_path):
        """Text extraction for split chapter only includes its section."""
    
    def test_split_preserves_reading_order(self, tmp_path):
        """Split chapters appear in document order (by fragment position)."""
    
    def test_no_split_for_single_h1(self, tmp_path):
        """Document with only one h1 is not split."""
```

### `tests/epub/test_chapters.py` additions

```python
# Add to existing test file:

def test_titlepage_excluded(tmp_path):
    """epub:type='titlepage' scores < 0 and is excluded."""

def test_halftitlepage_excluded(tmp_path):
    """epub:type='halftitlepage' scores < 0 and is excluded."""

def test_roman_numeral_heading_detected(tmp_path):
    """Standalone Roman numeral headings (I, II, etc.) match chapter pattern."""

def test_seriespage_excluded(tmp_path):
    """epub:type='seriespage' is excluded."""

def test_loi_lot_excluded(tmp_path):
    """epub:type='loi' and 'lot' are excluded (list of illustrations/tables)."""
```

### `tests/epub/test_cleanup_fragments.py` (new file, if D4 implemented)

```python
class TestFragmentExtraction:
    """Tests for xhtml_to_text with fragment range support."""
    
    def test_extract_from_start_fragment(self, tmp_path):
        """Extract text starting from a specific fragment ID."""
    
    def test_extract_to_end_fragment(self, tmp_path):
        """Extract text up to but not including end fragment."""
    
    def test_extract_fragment_range(self, tmp_path):
        """Extract text between start and end fragments."""
    
    def test_full_text_when_no_fragments(self, tmp_path):
        """Default behavior unchanged when no fragments specified."""
    
    def test_missing_start_fragment_returns_empty(self, tmp_path):
        """Missing start fragment ID returns empty string (or raises)."""
```

---

## Edge Case Tests

### Error Handling

```python
def test_malformed_fragment_in_toc(tmp_path):
    """TOC entry with invalid fragment doesn't crash, logs warning."""

def test_empty_section_between_h1s(tmp_path):
    """Section with no text between h1s produces empty/skipped chapter."""

def test_circular_fragment_reference(tmp_path):
    """Fragment that references itself handled gracefully."""
```

### Real-World Patterns

```python
def test_gutenberg_style_epub(tmp_path):
    """Project Gutenberg style: one big file with TOC fragments."""

def test_calibre_split_epub(tmp_path):
    """Calibre-split EPUB: many small files, sequential spine."""

def test_mixed_spine_linear(tmp_path):
    """Spine with linear='no' items (auxiliary content) handled."""
```

---

## Exit Criteria

- [ ] All fixture builders created in `tests/fixtures/builders.py`
- [ ] `tests/epub/test_chapter_merge.py` created with 6+ tests
- [ ] `tests/epub/test_chapter_split.py` created with 6+ tests
- [ ] Fragment extraction tests (if D4 implemented)
- [ ] Edge case tests for error handling
- [ ] All tests pass with EPUB Engineer's implementation
- [ ] `uv run pytest tests/epub/ -v` all pass
- [ ] `uv run ruff check tests/` passes
