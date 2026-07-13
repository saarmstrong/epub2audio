# M6 — Audio Engineer Task: Product Integration & FFmpeg Hardening

**Milestone:** 6 — Release readiness  
**Agent:** Audio Engineer  
**Depends on:** None  
**Blocks:** M6-tester, M6-reviewer

---

## Overview

Complete product integration for M5 chapter detection features and fix the FFmpeg
loudnorm silence issue. This addresses DEFECT-004 and DEFECT-005.

---

## Deliverables

### D1: Wire `finalize_chapters()` into Product Path (DEFECT-004)

The M5 merge/split logic exists but is dead code from the user's perspective.

**Changes needed:**

1. **`src/epub2audio/cli.py`** (~line 77):
   ```python
   # Before:
   chapters = select_chapters(candidates)
   
   # After:
   chapters = finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)
   ```

2. **`src/epub2audio/pipeline/planner.py`** (~line 40):
   ```python
   # Before:
   chapters = select_chapters(candidates)
   
   # After:  
   chapters = finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)
   ```

3. **Update imports** in both files to include `finalize_chapters`.

### D2: Converter Fragment Handling (DEFECT-004 part 2)

`converter._load_chapter_text()` doesn't handle `#fragment` in source_docs.

**Changes needed in `src/epub2audio/pipeline/converter.py`:**

```python
def _load_chapter_text(book_path: Path, chapter: Chapter) -> str:
    book = open_epub(book_path)
    texts: list[str] = []
    
    for doc_path in chapter.source_docs:
        # Split path#fragment
        if "#" in doc_path:
            bare_path, fragment = doc_path.split("#", 1)
        else:
            bare_path, fragment = doc_path, None
        
        item = book.get_item_with_href(bare_path)
        if item is None:
            log.warning("Chapter %r: source doc %r not found", chapter.chapter_id, bare_path)
            continue
        
        content: bytes = item.get_content()
        
        # Determine end_fragment from next source_doc if same file
        end_fragment = _get_end_fragment(chapter.source_docs, doc_path)
        
        texts.append(xhtml_to_text(content, start_fragment=fragment, end_fragment=end_fragment))
    
    return "\n\n".join(texts)

def _get_end_fragment(source_docs: list[str], current: str) -> str | None:
    """Get the fragment from the next source_doc if it's in the same file."""
    # Implementation details...
```

### D3: FFmpeg Loudnorm Silence Guard (DEFECT-005)

`loudnorm` returns exit 234 on FakeTTS pure-silence input (`measured_I=-inf`).

**Changes needed in `src/epub2audio/audio/normalize.py`:**

1. Parse the first-pass loudnorm output for `measured_I`, `measured_TP`, etc.
2. If any measurement is `-inf` or `inf`, skip the second pass and copy through:
   ```python
   def normalize_loudness(input_path: Path, output_path: Path) -> None:
       # First pass: measure
       measurements = _measure_loudness(input_path)
       
       # Check for degenerate values (silence)
       if _is_degenerate(measurements):
           log.warning("Input appears to be silence; skipping normalization")
           shutil.copy(input_path, output_path)
           return
       
       # Second pass: normalize with measured values
       _apply_loudnorm(input_path, output_path, measurements)
   ```

3. Add a test with pure-silence WAV input to verify graceful degradation.

### D4: Verify Product Path Works End-to-End

After D1-D3, verify:
```bash
# Test merge scenario
uv run epub2audio inspect tests/fixtures/multifile_chapter.epub
# Should show merged source_docs

# Test split scenario  
uv run epub2audio inspect tests/fixtures/singlefile_multichapter.epub
# Should show fragment-based chapters

# Test convert (if FFmpeg available)
uv run epub2audio convert tests/fixtures/simple_epub3.epub -o /tmp/test
# Should produce valid MP3s
```

---

## Files to Modify

- `src/epub2audio/cli.py` — wire finalize_chapters
- `src/epub2audio/pipeline/planner.py` — wire finalize_chapters
- `src/epub2audio/pipeline/converter.py` — fragment handling in _load_chapter_text
- `src/epub2audio/audio/normalize.py` — silence guard for loudnorm

---

## Exit Criteria

- [ ] `finalize_chapters()` called in both `cli.py` and `planner.py`
- [ ] `converter._load_chapter_text()` handles `#fragment` source_docs correctly
- [ ] `normalize_loudness()` gracefully handles silent input (no exit 234)
- [ ] `inspect` shows merged/split chapters
- [ ] All existing tests pass
- [ ] `uv run mypy src/epub2audio` passes
- [ ] `uv run ruff check src/` passes
