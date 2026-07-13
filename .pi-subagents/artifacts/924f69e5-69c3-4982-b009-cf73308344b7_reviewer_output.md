# Milestone 6 — FINAL Reviewer Sign-off

**Result: APPROVED. The epub2audio project is complete.** 🎉

Date: 2026-07-12
Reviewer: Reviewer agent

---

## Summary

Milestone 6 (release readiness) is verified complete. Both blocking defects
(DEFECT-004, DEFECT-005) are fixed and confirmed end-to-end on a machine with
FFmpeg + FFprobe installed (so the full suite runs with no FFmpeg-gated skips).
All quality gates are green. Documentation and packaging artifacts are present.

---

## Gates (verified this run)

| Gate | Result |
|---|---|
| `uv run pytest tests/ -q` | **204 passed, 6 skipped, 1 xfailed** |
| `uv run mypy src/epub2audio` | Success, 39 files, 0 errors (strict) |
| `uv run ruff check src/ tests/` | All checks passed |
| `uv run ruff format --check src/ tests/` | 65 files already formatted |

The 6 skips are the Kokoro model-gated smoke tests; the 1 xfail is the documented
conservative two-tier config-invalidation follow-up. FFmpeg + FFprobe resolve at
`/opt/homebrew/bin`, so the e2e/pipeline suite runs (no silent skips).

---

## DEFECT-004 — finalize_chapters wiring + converter fragment handling — FIXED

- `src/epub2audio/cli.py:77` (`inspect`) now calls
  `finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)`.
- `src/epub2audio/pipeline/planner.py:40` (`convert`) calls the same. Merge/split
  now reaches the shipped product path (previously dead code reachable only via
  unit tests).
- `converter._load_chapter_text` strips the optional `#fragment` suffix, looks up
  the EPUB item by bare path, and forwards `start_fragment`/`end_fragment` to
  `xhtml_to_text`. `_get_end_fragment()` derives the exclusive end boundary from
  the next same-file fragment entry. This prevents both silent text drop (fragment
  path → `get_item_with_href` → None) and duplication (full-doc text per split
  chapter). Reviewed the code directly — logic is correct.

**inspect verification (no regression from wiring):**
- `simple_epub3.epub` → 2 chapters in spine reading order (Chapter One =
  `b_chapter_01.xhtml`, Chapter Two = `a_chapter_02.xhtml`), nav.xhtml excluded.
- `simple_epub2.epub` → 2 chapters, same spine order. Confirms spine order used,
  not filename order.

## DEFECT-005 — loudnorm exit 234 on silent input — FIXED

- `audio/normalize.py` adds `_is_degenerate()` silence guard: non-finite pass-1
  measurement (`-inf`/`inf`/`nan`, as FakeTTS silence yields) → pass 2 skipped,
  file copied through, avoiding FFmpeg exit 234.
- Explicit `-f wav` on the pass-2 `.tmp` output (and `-f mp3` in the encoder) so
  FFmpeg ≥ 8 doesn't fail to infer format from the `.tmp` extension.
- The 16 previously-failing tests now pass: `test_converter_resume.py` +
  `test_segment_resume.py` + `test_e2e.py` → **32 passed, 1 xfailed** with FFmpeg
  installed.

---

## Documentation / packaging

- `README.md` (5074 B), `CHANGELOG.md` (1444 B), `LICENSE` (MIT, 1080 B) all
  present at repo root.

---

## Security / boundary checks

- No `kokoro` imports outside `tts/kokoro.py` for synthesis. The only other is
  the guarded `import kokoro` in `cli.py` `doctor` for `__version__` (accepted
  since M3).
- No `epub/` imports inside `tts/` or `audio/`.
- No `shell=True` anywhere.
- No narration/body text in log statements (only chapter IDs, titles, doc paths,
  segment indices, word counts, config keys).

---

## Sign-off actions performed

- `docs/status.md` updated: M6 → ✅ Complete, final sign-off block added, all
  acceptance criteria updated to ✅ (or ✅ with note), active-task list cleared.
- Moved to `tasks/completed/`: M6-audio-engineer.md, M6-docs-engineer.md,
  M6-tester.md, M6-reviewer.md, DEFECT-004, DEFECT-005.
- Restored `tasks/active/.gitkeep` (removed as a side effect of moving the last
  files out of the directory).

---

## Residual risks

1. **Converter fragment glue lacks a dedicated e2e regression test.**
   `_load_chapter_text` / `_get_end_fragment` are covered indirectly by
   `test_cleanup_fragments.py` (the `xhtml_to_text` start/end-fragment layer) and
   `test_chapter_split.py` (split detection), but no test converts a single-file
   multi-chapter EPUB end-to-end and asserts split-chapter MP3 text is non-empty
   and non-duplicated. The glue is small and reviewed as correct; this is a
   coverage gap, not a defect. Recommended future follow-up (non-blocking).
2. **Two-tier config invalidation is conservative** (documented xfail, carried
   from M4): any config change clears all segment WAVs — never reuses stale
   audio, but re-synthesizes on encoding-only changes. Documented follow-up.
3. **CI must run the FFmpeg integration suite** — verified locally here; CI
   should install FFmpeg and exercise the integration-marked tests before release.

No blockers.
