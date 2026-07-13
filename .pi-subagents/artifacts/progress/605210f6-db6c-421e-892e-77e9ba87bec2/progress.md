# M4 Reviewer Progress

**Status: COMPLETE — Milestone 4 APPROVED (conditional on CI FFmpeg run)**

## Gates (all green)
- `uv run pytest tests/ -v` → 145 passed, 24 skipped
- `uv run mypy src/epub2audio` → Success, 39 files, 0 errors
- `uv run ruff check src/ tests/` → All checks passed
- `uv run ruff format --check src/ tests/` → 62 files formatted

## Reviewer-applied fix
- `ruff format` on `tests/pipeline/test_segment_resume.py` (Tester left 2 assertions
  unformatted → format gate was red). Mechanical whitespace only; 19 tests still pass.

## DEFECT-003 verification
- Persistent work dir under output dir (`.epub2audio-work/<chapter_id>/`) — D1 ✓
- `manifest.segments` populated w/ `audio_path` + `status="done"`, merged by hash — D2 ✓
- Resume reuses cached WAVs via `segment_needs_synthesis()` — D3 ✓
- Cleanup respects `keep_intermediates`; work dir survives interrupt — D5 ✓
- Two-tier invalidation (D4) is conservative-only (documented limitation; safe)

## Boundaries/security: clean
- No kokoro imports outside tts/kokoro.py (doctor __version__ read excepted)
- No epub imports in tts/ or audio/; no shell=True; no book text in logs

## Bookkeeping
- docs/status.md updated: M4 → Complete, sign-off block added, 2 acceptance criteria → ✅
- Moved M4-audio-engineer, M4-tester, M4-reviewer, DEFECT-003 → tasks/completed/
- No staged files
