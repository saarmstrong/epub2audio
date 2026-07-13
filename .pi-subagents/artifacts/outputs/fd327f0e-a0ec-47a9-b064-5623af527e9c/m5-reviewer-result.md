# M5 Reviewer Sign-off — Chapter-Detection Hardening

**Result: APPROVED (detection layer).** Milestone 5 marked ✅ Complete per Orchestrator
decision. Two follow-up defects filed (DEFECT-004 product wiring, DEFECT-005 pre-existing
FFmpeg loudnorm) — neither blocks M5 detection-layer closure.

**Date:** 2026-07-12
**Reviewer:** Reviewer subagent

---

## 1. Gate Verification (M5 scope)

| Gate | Command | Result |
|---|---|---|
| Unit tests | `uv run pytest tests/epub/ -q` | **77 passed** ✅ |
| Type check | `uv run mypy src/epub2audio` | Success, 39 files, 0 errors (strict) ✅ |
| Lint | `uv run ruff check src/ tests/` | All checks passed ✅ |
| Format | `uv run ruff format --check src/ tests/` | 65 files formatted ✅ (after reviewer fix) |
| Regression | `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` | 2 chapters, correct spine order, nav excluded ✅ |

Full suite: **188 passed, 16 failed, 6 skipped, 1 xfailed**. All 16 failures are the
pre-existing FFmpeg `loudnorm` exit-234 issue (DEFECT-005), **0 failures in M5 scope**.

### Reviewer-applied fix
`ruff format --check` was red on 5 test/fixture files the Tester left with unformatted
assertion-string wrapping:
`tests/epub/test_chapter_split.py`, `tests/epub/test_chapters.py`,
`tests/epub/test_cleanup_fragments.py`, `tests/epub/test_chapter_merge.py`,
`tests/fixtures/builders.py`. Ran `ruff format` — mechanical whitespace only, no logic
change; all 77 epub tests still pass. (Matches the M4 reviewer precedent.)

---

## 2. Code Review — `epub/chapters.py` + `epub/cleanup.py`

- **`merge_consecutive_chapters()` (D1)** — folds continuation spine docs (no TOC entry,
  no front/back-matter or strong-exclusion signal) into the preceding chapter, appending
  `source_docs` and summing word counts. Gap-walk between consecutive chapters is correct.
  `_is_continuation_candidate` guards against absorbing copyright/title pages. ✅
- **`split_multi_chapter_docs()` (D2)** — splits a single-source-doc chapter when its
  document has ≥2 distinct TOC fragment anchors; emits `"path#fragment"` source_docs and
  estimates per-fragment word counts via fragment-bounded `xhtml_to_text`. ✅
- **`finalize_chapters()`** — clean orchestration: merge → split → `_renumber_chapters()`
  (fresh `chapter_id` / `stable_id`). Merge/split logic is well separated from scoring. ✅
- **D3 scoring** — `titlepage`/`halftitlepage` → −5 (strong-exclusion set, takes
  precedence over −3 front/back-matter); `multiple_h1` → −1 split signal; new epub:types
  (`seriespage`, `imprimatur`, `errata`, `loi`, `lot`) added to exclusion set. Documented
  in the module docstring table and inline signals. ✅
- **D4 fragment extraction** — `_extract_fragment` handles block containers
  (`section`/`div`/`article`/`main`) directly and carves heading/inline ranges in place;
  **degrades gracefully to whole-document text when the anchor is missing** — invalid
  fragment refs do not crash. ✅
- **No regression** — `simple_epub3` still yields 2 independent chapters (no false
  merge/split); empty docs still hard-excluded at −10.

---

## 3. Acceptance Criteria

| Criterion | Status | Evidence |
|---|---|---|
| Multi-file chapters can be merged | ✅¹ | `merge_consecutive_chapters()` + `test_chapter_merge.py` (8 tests) |
| Multi-chapter single-file can be split | ✅¹ | `split_multi_chapter_docs()` + `test_chapter_split.py` (9 tests) |

¹ Satisfied at the **detection layer** (unit-tested). See DEFECT-004 — not yet reachable
through the shipped `inspect`/`convert` product path.

---

## 4. Defects Filed

### DEFECT-004 (Medium, M6 follow-up) — `finalize_chapters()` not wired into product
- `cli.py:77` (`inspect`) and `pipeline/planner.py:40` (`convert`) call `select_chapters()`
  only; **never** `finalize_chapters()`. Merge/split is therefore dead code from the
  user's perspective — the manual `inspect multifile/singlefile` checks in the task
  cannot demonstrate merged/split output today.
- Coupled issue: `converter._load_chapter_text` (converter.py:104-108) calls
  `book.get_item_with_href(doc_path)` with the raw `"path#fragment"` string (returns
  `None` → text silently dropped) and calls `xhtml_to_text` **without** fragment bounds
  (duplicated full-doc text across split chapters). Wiring `finalize_chapters()` as-is
  would cause silent text loss/duplication for split chapters — the exact
  "text-completeness" adversarial risk.
- Suggested fix: call `finalize_chapters(select_chapters(...), candidates, nav, book)` in
  both `cli` and `planner`; split `doc_path` on `#` in `_load_chapter_text` and pass
  `start_fragment`/`end_fragment` to `xhtml_to_text`; add an e2e assertion that
  split-chapter text is non-empty and non-duplicated.

### DEFECT-005 (Medium, pre-existing M4 — NOT M5 scope) — FFmpeg `loudnorm` exit 234
- 16 M4 pipeline/e2e tests fail (previously skipped when FFmpeg absent). Root cause:
  `loudnorm` rejects `measured_I=-inf` filter args produced by FakeTTS pure-silence
  input. Recommend a silence guard in `audio/normalize.py` + FFmpeg skip guards, and CI
  coverage with real (non-silent) audio.

---

## 5. Bookkeeping Completed

- `docs/status.md` — M5 → ✅ Complete; current milestone advanced to M6; M5 sign-off block
  added; acceptance criteria updated; Active Tasks now lists DEFECT-004 / DEFECT-005.
- Moved to `tasks/completed/`: `M5-epub-engineer.md`, `M5-tester.md`, `M5-reviewer.md`.
- Created `tasks/active/DEFECT-004-finalize-chapters-not-wired.md`,
  `tasks/active/DEFECT-005-ffmpeg-loudnorm-exit234-skip-guards.md`.

---

## 6. Security / Boundary Checks
No `kokoro` imports outside `tts/kokoro.py`; no `epub/` imports inside `tts/` or `audio/`;
no `shell=True`; no narration/body text in any log statement (only chapter IDs, titles,
doc paths, word counts, signal strings).
