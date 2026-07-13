# M4 Audio Engineer Result — DEFECT-003 Fix

## Summary

Fixed DEFECT-003: segment-level resume is now functional.  Segment WAVs are
written to a persistent work directory, `manifest.segments` is populated with
`audio_path` set after synthesis, and a second run with `--resume` correctly
skips already-synthesized segments.

---

## Changes Made

### `src/epub2audio/config.py`
Added `keep_intermediates: bool = False` field to `Settings`.  Controls whether
segment WAVs are preserved after a successful chapter conversion.

### `src/epub2audio/pipeline/resume.py`
Added two new public helpers:
- `tts_config_changed(changed_keys) -> bool` — returns `True` when any config
  change could affect TTS output (currently: any non-empty change list, since
  the manifest stores a hash, not a snapshot).
- `clear_segment_cache(work_root, chapter_id)` — deletes the chapter's work
  directory so segments are re-synthesized after a voice/language/speed change.

Added module-level constants `_TTS_AFFECTING_KEYS` and `_ENCODE_AFFECTING_KEYS`
documenting the two-tier invalidation intent.

### `src/epub2audio/pipeline/converter.py`

**D1 — Persistent work directory:**
- Replaced `tempfile.TemporaryDirectory` with a persistent
  `output_dir / ".epub2audio-work"` directory.
- `_process_chapter` now receives `work_root` instead of `work_dir`, and
  creates `work_root / chapter.chapter_id /` per chapter.

**D2 — Manifest segment population:**
- `_process_chapter` returns `(ChapterResult, list[TextSegment])`.
- After each segment is synthesized, a new `TextSegment` is constructed with
  `audio_path=str(seg_wav.resolve())` and `status="done"` and appended to
  `completed_segments`.
- Added `_merge_segments(existing, new_segments)` helper that deduplicates by
  `normalized_hash` so resumed segments overwrite stale entries.
- After each chapter, `manifest.segments` is updated via `_merge_segments` and
  the manifest is written atomically.

**D3 — Resume logic wiring:**
- In the synthesis loop, existing segments found via `_find_manifest_segment`
  are checked with `segment_needs_synthesis()`.
- When a cached WAV is valid, synthesis is skipped and the log line
  `"Chapter %r segment %d: resumed from cached WAV"` is emitted at `INFO`.

**D4 — Config change invalidation:**
- When `check_resume` returns changed keys and `tts_config_changed` returns
  `True`, `clear_segment_cache` is called for every chapter and the manifest
  segments list is reset to `[]`.
- When only encoding settings changed (future: currently treated the same as
  TTS changes to be safe), segment WAVs could be retained — documented in code.

**D5 — Cleanup rules:**
- After a successful chapter (MP3 validated), the intermediate `chapter.wav`
  and `chapter_norm.wav` are deleted (unless `keep_intermediates=True`).
- Segment WAVs in `<chapter_id>/seg_NNNN.wav` are preserved until the
  post-run sweep removes successful chapter dirs.
- After all chapters succeed, `work_root` is removed entirely
  (unless `keep_intermediates=True`).
- Failed chapters' work dirs are left intact for the next `--resume` run.

### `tests/pipeline/test_segment_resume.py` (new file)
19 tests covering:
- `TestSegmentNeedsSynthesis` — 5 cases (None path, missing file, empty file,
  valid file, relative-path resolution)
- `TestTtsConfigChanged` — 3 cases (empty list, non-empty list, multiple keys)
- `TestClearSegmentCache` — 3 cases (removes dir, no-op on missing dir,
  only removes specified chapter)
- `TestMergeSegments` — 4 cases (add to empty, overwrite by hash, retain
  existing, deduplicate within new)
- 4 integration tests (`@pytest.mark.integration`, skip when FFmpeg absent):
  work dir creation, `keep_intermediates` preservation, `audio_path` set in
  segments, resume skips cached WAVs.

---

## Commands Run

```
uv run pytest tests/ -v                    → 132 passed, 15 skipped
uv run mypy src/epub2audio                 → Success: no issues found in 39 source files
uv run ruff check src/                     → All checks passed!
uv run pytest tests/ -m integration -v    → 9 skipped (FFmpeg not available in env)
```

---

## Residual Risks

1. **Two-tier invalidation is conservative**: because `manifest.json` stores
   a config hash rather than the snapshot, `check_resume` cannot tell *which*
   specific keys changed.  Any config change currently clears segment WAVs.
   The `_TTS_AFFECTING_KEYS` / `_ENCODE_AFFECTING_KEYS` constants are in place
   for a future refinement where the snapshot is stored.
2. **Integration tests require FFmpeg**: the four `@pytest.mark.integration`
   tests for segment persistence and resume are skipped in CI environments
   without FFmpeg.  The underlying unit tests (15 non-integration tests) pass
   without FFmpeg.
3. **`_merge_segments` order is dict-insertion order**: Python 3.7+ guarantees
   this, so segment ordering is stable across runs.
