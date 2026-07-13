# M5 Tester Result

## Summary

All M5 tester deliverables are implemented and passing.  77 epub tests pass,
ruff is clean, and no files are staged.

---

## Deliverables

### 1. `tests/fixtures/builders.py` — 6 new builder functions

| Function | Description |
|---|---|
| `build_multifile_chapter_epub()` | One chapter across 3 spine files (`ch01_part1`, `ch01_part2`, `ch01_part3`, `ch02`). Continuation docs are < 200 words → score −1 → excluded from `select_chapters` → merged by `merge_consecutive_chapters`. |
| `build_singlefile_multichapter_epub()` | Single `chapters.xhtml` with Prologue + Chapter 1 + Chapter 2 in `<section id=...>` elements; TOC uses `#prologue`, `#ch1`, `#ch2` fragment links. |
| `build_fragment_toc_epub()` | `content.xhtml` with Part 1 / Part 2 sections; TOC links `content.xhtml#part1` and `content.xhtml#part2`. |
| `build_titlepage_epub()` | Convenience wrapper: delegates to `build_epub_with_epub_type(_, "titlepage", ...)`. |
| `build_continued_chapter_epub()` | `ch01.xhtml` (full, TOC) → `ch01_cont.xhtml` (heading `"Chapter 1 (continued)"`, short, no TOC → score −1) → `ch02.xhtml` (full, TOC). Merge folds `ch01_cont` into `ch01`. |
| `build_roman_numeral_chapters_epub()` | Four chapters titled I, II, III, IV; each has a TOC entry and h1 matching the `[IVXLCDM]+` regex branch. |

---

### 2. `tests/epub/test_chapter_merge.py` — 8 tests (new file)

`class TestMultiFileChapterMerge`:

| Test | What it checks |
|---|---|
| `test_consecutive_docs_without_toc_merged` | Continuation docs merge → 2 chapters total |
| `test_merged_chapter_has_all_source_docs` | All 3 parts appear in `source_docs` |
| `test_merged_chapter_word_count_is_sum` | Post-merge `word_count` > pre-merge |
| `test_merge_stops_at_next_toc_entry` | ch02 (TOC entry) stays separate |
| `test_continued_heading_doc_merged_with_predecessor` | `"Chapter 1 (continued)"` pattern merges |
| `test_front_matter_doc_between_chapters_not_merged` | copyright/index never appear in `source_docs` |
| `test_independent_chapters_unchanged_by_merge` | Two independent chapters keep exactly 1 `source_doc` each |
| `test_merged_source_docs_are_in_spine_order` | `source_docs` list is in spine reading order |

---

### 3. `tests/epub/test_chapter_split.py` — 9 tests (new file)

`class TestSingleFileChapterSplit`:

| Test | What it checks |
|---|---|
| `test_multiple_h1_triggers_split_signal` | `multiple_h1 -1` signal fires on multi-h1 doc |
| `test_fragment_toc_entries_create_chapters` | Fragment TOC → 2 chapters |
| `test_split_chapters_have_correct_fragments` | `source_doc` contains `path#fragment` |
| `test_split_chapter_text_extraction` | Each fragment yields non-empty, mutually exclusive text |
| `test_split_preserves_reading_order` | Prologue < Chapter 1 < Chapter 2 |
| `test_no_split_for_single_toc_entry` | One-entry docs keep no `#` in `source_doc` |
| `test_no_split_for_single_h1` | Single-h1 doc not split |
| `test_split_chapter_word_counts_positive` | Every fragment-chapter has `word_count > 0` |
| `test_split_titles_come_from_toc` | Chapter titles come from TOC, not file title |

---

### 4. `tests/epub/test_cleanup_fragments.py` — 9 tests (new file)

`class TestFragmentExtraction` (unit tests for `xhtml_to_text` with fragment args):

| Test | What it checks |
|---|---|
| `test_extract_from_start_fragment` | `start_fragment="part2"` → only Part Two text |
| `test_extract_from_start_fragment_yields_nonempty_text` | Fragment extraction is non-empty |
| `test_extract_fragment_range` | `beta→gamma` → beta only, not alpha or gamma |
| `test_extract_first_fragment_range` | `alpha→beta` → alpha only |
| `test_full_text_when_no_fragments` | No args → all sections present |
| `test_full_document_word_count_exceeds_fragment_count` | Full doc > any single fragment |
| `test_missing_start_fragment_falls_back_to_full_text` | Missing id → graceful full-text fallback |
| `test_heading_fragment_extracts_correct_content` | h1-level id → correct sibling-pruning |
| `test_end_fragment_none_extracts_to_end_of_document` | `end_fragment=None` → no premature cutoff |

---

### 5. `tests/epub/test_chapters.py` — 2 new tests added

| Test | What it checks |
|---|---|
| `test_roman_numeral_heading_detected` | I/II/III/IV headings match regex, all 4 chapters detected |
| `test_loi_lot_excluded` | `epub:type="loi"` and `"lot"` score < 0, excluded from chapters |

Also cleaned up pre-existing ruff issues:
- Removed unused `merge_consecutive_chapters` / `split_multi_chapter_docs` imports
- Removed unused `chapters` variable in `test_seriespage_epub_type_excluded`

---

## Test Run Results

```
uv run pytest tests/epub/ -v -q
77 passed in 0.81s

uv run ruff check tests/
All checks passed!
```

### Out-of-scope failures noted

The 16 failures in `tests/pipeline/test_converter_resume.py` and `tests/test_e2e.py`
are **M4 pipeline/e2e tests** failing because FFmpeg is installed but returns exit
code 234 on the `loudnorm` filter (silent audio from `FakeTTSEngine` triggers
`measured_I=-inf`).  These tests are not gated by a skip condition that catches a
broken FFmpeg.

**Recommendation for M4/follow-up:** Add a `pytest.fixture` or `conftest.py`
`autouse` skip that detects FFmpeg `loudnorm` capability before running
pipeline integration tests.  This is out of M5 scope.

---

## Changed Files

| File | Change |
|---|---|
| `tests/fixtures/builders.py` | +6 builder functions |
| `tests/epub/test_chapters.py` | +2 new tests, 3 ruff cleanups |
| `tests/epub/test_chapter_merge.py` | **new** — 8 tests |
| `tests/epub/test_chapter_split.py` | **new** — 9 tests |
| `tests/epub/test_cleanup_fragments.py` | **new** — 9 tests |
