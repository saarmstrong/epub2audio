# Task for tester

Read tasks/active/M5-tester.md and write tests for chapter-detection hardening.

Previous step result:
# M5 EPUB Engineer Result

## Summary

All four deliverables of M5 Chapter-Detection Hardening are implemented and passing.

---

## D1: Multi-File Chapter Merging

**`merge_consecutive_chapters(chapters, candidates, nav_entries) → list[Chapter]`** added to `chapters.py`.

Algorithm: for each chapter, scan spine items between it and the next chapter. Any item with no TOC entry and no front/back-matter exclusion signals is merged (appended to `source_docs`, word counts summed).

Fixture `build_multi_file_chapter_epub` creates:
- `ch01_part1.xhtml` (TOC entry: "Chapter One")
- `ch01_part2.xhtml` (no TOC entry, continuation)
- `ch02.xhtml` (TOC entry: "Chapter Two")

Result: Chapter One has `source_docs=["ch01_part1.xhtml", "ch01_part2.xhtml"]`.

---

## D2: Single-File Chapter Splitting

**`split_multi_chapter_docs(chapters, nav_entries, book) → list[Chapter]`** added to `chapters.py`.

Algorithm: for each chapter whose single source doc has ≥ 2 TOC entries with distinct fragment anchors, expand into one Chapter per fragment. Each split chapter gets `source_docs=["path.xhtml#fragment"]`. Word counts are estimated via `xhtml_to_text(content, start_fragment=..., end_fragment=...)`.

Uses existing fixture `build_multi_chapter_single_file` (chapter1.xhtml with TOC entries `#ch-1`, `#ch-2`).

---

## D3: Scoring Refinements

1. **`_STRONG_EXCLUSION_EPUB_TYPES`** (`titlepage`, `halftitlepage`) → **-5** penalty (stronger than the general -3).
2. **`_FRONT_BACK_MATTER_EPUB_TYPES`** extended with `seriespage`, `imprimatur`, `errata` → -3 penalty.
3. **Multiple h1 signal**: docs with >1 `<h1>` element get `-1` (`multiple_h1(N) -1` signal) as a split indicator.

---

## D4: Fragment Extraction

**`xhtml_to_text(content, *, start_fragment=None, end_fragment=None)`** updated in `cleanup.py`.

- New `_extract_fragment(body, start_fragment, end_fragment)` helper.
- Block containers (`section`, `div`, `article`, `main`) with matching id are returned directly.
- Heading/inline elements: preceding siblings removed; trailing content removed if `end_fragment` given.

---

## `finalize_chapters()`

Orchestrates the full post-selection pipeline:
1. `merge_consecutive_chapters()`
2. `split_multi_chapter_docs()`
3. `_renumber_chapters()` — resets chapter_id to ch001…chNNN and recomputes stable_id.

---

## Test Results

```
uv run pytest tests/ -v
159 passed, 24 skipped (TTS smoke tests, require optional kokoro package)

uv run pytest tests/epub/test_chapters.py -k merge -v
4 passed

uv run pytest tests/epub/test_chapters.py -k split -v
5 passed

uv run mypy src/epub2audio
Success: no issues found in 39 source files

uv run ruff check src/
All checks passed!
```

---

## Changed Files

- `src/epub2audio/epub/cleanup.py`
- `src/epub2audio/epub/chapters.py`
- `tests/fixtures/builders.py`
- `tests/epub/test_chapters.py`


Output saved to: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/outputs/c8f7b46c-5b7e-4e95-a3b0-caea955e2572/m5-epub-engineer-result.md (2.8 KB, 87 lines). Read this file if needed.

Create test fixtures and tests for:

1. **tests/fixtures/builders.py** additions:
   - `build_multifile_chapter_epub()` - one chapter spanning multiple docs
   - `build_singlefile_multichapter_epub()` - one doc with multiple h1 chapters
   - `build_fragment_toc_epub()` - TOC with #fragment links
   - `build_titlepage_epub()` - epub:type=titlepage exclusion
   - `build_continued_chapter_epub()` - 'Chapter N (continued)' pattern

2. **tests/epub/test_chapter_merge.py** (new file):
   - Test consecutive docs merge correctly
   - Test merged chapter has all source_docs
   - Test word count sums correctly

3. **tests/epub/test_chapter_split.py** (new file):
   - Test multiple h1 triggers split
   - Test fragment TOC entries create chapters
   - Test split preserves reading order

Run all tests: uv run pytest tests/ -v

---
Update progress at: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/progress/c8f7b46c-5b7e-4e95-a3b0-caea955e2572/progress.md

---
**Output:**
Write your findings to exactly this path: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/outputs/c8f7b46c-5b7e-4e95-a3b0-caea955e2572/m5-tester-result.md
This path is authoritative for this run.
Ignore any other output filename or output path mentioned elsewhere, including output destinations in the base agent prompt, system prompt, or task instructions.

## Acceptance Contract
Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```