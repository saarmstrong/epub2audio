# M5 — EPUB Engineer Task: Chapter-Detection Hardening

**Milestone:** 5 — Chapter-detection hardening  
**Agent:** EPUB Engineer  
**Depends on:** None  
**Blocks:** M5-tester, M5-reviewer

---

## Overview

Harden the chapter-detection scoring engine to handle complex real-world EPUB structures:
1. **Multi-file chapter merging** — Multiple spine documents that form one logical chapter
2. **Single-file chapter splitting** — One document containing multiple logical chapters
3. **Scoring threshold tuning** — Better handling of edge cases

This completes two acceptance criteria:
- "Multi-file chapters can be merged" ⬜
- "Multi-chapter single-file can be split" ⬜

---

## Deliverables

### D1: Multi-File Chapter Merging

Some EPUBs split a single logical chapter across multiple XHTML files (e.g., for
reader pagination). These should be merged into one `Chapter` with multiple
`source_docs`.

**Heuristics for merging:**
1. Consecutive spine items where only the first has a TOC entry
2. Consecutive spine items where subsequent items have low scores (0-1) and no
   independent heading
3. Spine items with titles like "Chapter 1 (continued)" or "Part 2.2"
4. Documents with `epub:type="chapter"` followed by documents with no epub:type

**Implementation:**
- Add `merge_consecutive_chapters()` function in `chapters.py`
- Call after `select_chapters()` to combine multi-doc chapters
- Update `Chapter.source_docs` to include all merged documents
- Combine word counts from all merged documents

**Example scenario:**
```
spine: ch01_part1.xhtml, ch01_part2.xhtml, ch02.xhtml
TOC: "Chapter 1" → ch01_part1.xhtml, "Chapter 2" → ch02.xhtml

Result:
- Chapter(source_docs=["ch01_part1.xhtml", "ch01_part2.xhtml"])
- Chapter(source_docs=["ch02.xhtml"])
```

### D2: Single-File Chapter Splitting

Some EPUBs pack multiple chapters into one XHTML file, delimited by `<h1>` or
`<h2>` elements. These should be split into multiple `Chapter` objects.

**Heuristics for splitting:**
1. Multiple `<h1>` elements in one document → split at each h1
2. Multiple `<h2>` elements that match chapter patterns → split at each h2
3. TOC entries pointing to fragments (`doc.xhtml#ch2`) within the same file

**Implementation:**
- Add `split_multi_chapter_docs()` function in `chapters.py`
- Detect fragment-based TOC entries (entries with `#fragment`)
- Parse the document to find heading boundaries
- Create separate `Chapter` objects for each section
- Add `fragment` field to `Chapter.source_docs` entries to track sub-document scope

**Model change needed:**
```python
# In models.py, extend source_docs or add a new field:
class ChapterSection(BaseModel):
    doc_path: str
    fragment_start: str | None  # Element ID where this section starts
    fragment_end: str | None    # Element ID where this section ends (exclusive)
```

Alternatively, keep `source_docs: list[str]` but support `"path.xhtml#fragment"`
format.

**Example scenario:**
```
spine: chapters.xhtml (contains h1 "Prologue", h1 "Chapter 1", h1 "Chapter 2")
TOC: "Prologue" → chapters.xhtml#prologue
     "Chapter 1" → chapters.xhtml#ch1
     "Chapter 2" → chapters.xhtml#ch2

Result:
- Chapter(source_docs=["chapters.xhtml#prologue"])
- Chapter(source_docs=["chapters.xhtml#ch1"])  
- Chapter(source_docs=["chapters.xhtml#ch2"])
```

### D3: Scoring Threshold Refinements

Tune the scoring engine based on common edge cases:

| Adjustment | Rationale |
|------------|-----------|
| `epub:type="titlepage"` → -5 | Stronger exclusion for title pages |
| `epub:type="halftitlepage"` → -5 | Half-title pages are never chapters |
| Multiple h1 in doc → -1 to parent doc | Signals this doc should be split |
| Doc referenced by >1 TOC entry → flag for split | Strong split signal |
| Filename contains "split" or "part" + number → merge candidate | Common pattern |

**Add these epub:types to exclusion set:**
- `titlepage`, `halftitlepage`, `seriespage`, `imprimatur`, `loi` (list of illustrations),
  `lot` (list of tables), `errata`

### D4: Update `xhtml_to_text` for Fragment Extraction

Modify `cleanup.py` to support extracting text from a specific fragment range:

```python
def xhtml_to_text(
    content: bytes,
    *,
    start_fragment: str | None = None,
    end_fragment: str | None = None,
) -> str:
    """Extract narration text, optionally limited to a fragment range."""
```

This is needed for D2 so split chapters only include their section's text.

---

## Implementation Plan

1. **Phase 1: Model updates** (if needed)
   - Decide: extend `source_docs` to support fragments, or add `ChapterSection`
   - Consult Architect if adding a new model
   
2. **Phase 2: Scoring refinements (D3)**
   - Add new epub:types to exclusion set
   - Adjust weights
   - Add split-detection signals

3. **Phase 3: Multi-file merging (D1)**
   - Implement `merge_consecutive_chapters()`
   - Write unit tests

4. **Phase 4: Single-file splitting (D2)**
   - Implement `split_multi_chapter_docs()`  
   - Update `xhtml_to_text` for fragment extraction (D4)
   - Write unit tests

5. **Phase 5: Integration**
   - Wire merge/split into `select_chapters()` or create `finalize_chapters()`
   - Update the planner to handle new chapter structures
   - Verify existing tests still pass

---

## Test Verification

Before marking complete:

```bash
# All existing tests pass
uv run pytest tests/epub/ -v

# New multi-file merge tests
uv run pytest tests/epub/test_chapters.py -k merge -v

# New single-file split tests
uv run pytest tests/epub/test_chapters.py -k split -v

# Full test suite
uv run pytest tests/ -v

# Type checking
uv run mypy src/epub2audio
```

---

## Files to Modify

- `src/epub2audio/epub/chapters.py` — main scoring engine changes
- `src/epub2audio/epub/cleanup.py` — fragment extraction support
- `src/epub2audio/models.py` — possibly add ChapterSection or extend source_docs
- `tests/fixtures/builders.py` — new fixture builders for edge cases

---

## Exit Criteria

- [ ] Multi-file chapters merge into single Chapter with combined source_docs
- [ ] Single-file multi-chapter docs split into separate Chapters
- [ ] Fragment-based TOC entries create correct chapter boundaries
- [ ] New scoring adjustments don't break existing tests
- [ ] All existing tests still pass
- [ ] `uv run mypy src/epub2audio` passes
- [ ] `uv run ruff check src/` passes
