# DEFECT-003 — Segment-level resume is non-functional (manifest segments never persisted)

**Found by:** Reviewer, during Milestone 2 sign-off (2026-07-12)
**Severity:** Medium (feature gap, not a correctness/data-loss bug)
**Scope:** Deferred to Milestone 4 (Reliability: resume, manifest, report)

## Steps to reproduce

1. Start a conversion, interrupt it after chapter 1 completes.
2. Restart with `--resume`.
3. Observe that every segment of every chapter is re-synthesized from scratch.

## Expected behaviour

Per `M2-18` step 2 ("Check resume; skip segments whose WAV already exists and
matches hash"), a resumed run should skip segments that were already synthesized.

## Actual behaviour

`pipeline/converter.py`:
- `_new_manifest(...)` creates the manifest with `segments=[]`.
- Each per-chapter manifest rewrite copies `segments=manifest.segments`, which
  stays `[]` for the whole run — `_process_chapter` builds `TextSegment` objects
  locally but never appends them (with a populated `audio_path`) to the manifest.
- Consequently `_find_manifest_segment(...)` always returns `None`, so the
  resume branch is never taken.
- Additionally, segment WAVs are written under a `tempfile.TemporaryDirectory`
  (`work_dir`) that is deleted when `convert_epub` returns, and `chapter_work`
  is `shutil.rmtree`'d after each chapter — so no segment WAV survives across
  runs even if the manifest referenced it.

The manifest *is* written before synthesis and updated after each chapter
(satisfying the M2-17 manifest-write requirement), and `check_resume`
fingerprint/config-hash validation works. Only the segment-skip cache is inert.

## Relevant locations

- `src/epub2audio/pipeline/converter.py`: `_new_manifest` (segments=[]),
  per-chapter loop (segments never populated), `_process_chapter`
  (segment WAVs in temp dir, never persisted, `audio_path` never set).
- `src/epub2audio/pipeline/resume.py`: `segment_needs_synthesis` is correct but
  unreachable in practice because the manifest carries no segments.

## Suggested fix (M4)

- Write segment WAVs to a persistent per-book work directory (not the OS temp
  dir) so they survive across runs.
- Populate `manifest.segments` with each `TextSegment` including a resolved
  `audio_path` and status, and rewrite after each segment/chapter.
- On resume, match by `normalized_hash` and reuse the on-disk WAV.

## Notes

The acceptance criterion "Interrupted conversions resume" is already marked
incomplete (⬜) in `docs/status.md`. This defect exists to track the concrete
code gap for Milestone 4. It does **not** block Milestone 2, whose success
condition is producing valid MP3s with the FakeTTS engine.
