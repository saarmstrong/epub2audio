# Task for reviewer

Run the full Milestone 2 review for epub2audio. This is the milestone sign-off review.

## Context

Three agents completed M2 work in parallel:
- **TTS Engineer**: fixed DEFECT-002 (word_count), extended epub/cleanup.py (full HTML→text), wrote text/normalize.py, text/segment.py, text/pauses.py, tts/base.py (TTSEngine Protocol), tts/fake.py (FakeTTSEngine)
- **Audio Engineer**: wrote utils/subprocess.py, utils/files.py, audio/chunks.py, audio/concatenate.py, audio/encode.py, audio/normalize.py, audio/metadata.py, audio/validate.py, pipeline/planner.py, pipeline/manifest.py, pipeline/resume.py, pipeline/converter.py, extended cli.py with `convert` command (16 flags)
- **Tester**: wrote tests/test_e2e.py, tests/text/test_normalize.py, tests/text/test_segment.py, tests/audio/test_encode.py, tests/pipeline/test_manifest.py

Current state: **112 passed, 5 skipped (FFmpeg absent), 0 failed**. All tasks in tasks/completed/.

## Your checklist

Run the full "Review Checklist — Every Task" and "Milestone Sign-off Checklist" from your role definition.

## Known issues to investigate — start here

### 1. ChapterResult.duration_seconds is always 0.0 (medium — likely blocker)
`pipeline/converter.py` never probes the final MP3 for duration. It writes `ChapterResult(duration_seconds=0.0, ...)` as a placeholder. `tests/test_e2e.py::test_convert_epub_chapter_duration_positive` asserts `duration_seconds > 0` — this test will **fail** when FFmpeg is available. Fix: after `validate_mp3`, run an ffprobe call to read the duration and store it on `ChapterResult`. You have `edit` access to fix this.

### 2. test_encode.py mock path (low)
`tests/audio/test_encode.py` mocks `'epub2audio.audio.encode.run_command'`. Verify that `src/epub2audio/audio/encode.py` imports `run_command` with a direct `from epub2audio.utils.subprocess import run_command` (not `import epub2audio.utils.subprocess`), so the mock path resolves correctly.

### 3. pyproject.toml mypy python_version changed 3.11 → 3.12 (low)
TTS Engineer bumped this for numpy 2.x stubs. Verify the change is documented and does not silently mask real 3.11 compatibility issues in the code.

### 4. 5 e2e integration tests are skipped (FFmpeg absent)
`tests/test_e2e.py` tests skip cleanly when `shutil.which("ffmpeg")` is None. FFmpeg is not installed on this machine. You cannot fully validate M2-21 ("verify all fixture chapters produce valid MP3s") without FFmpeg. Assess whether to:
  a) Give conditional approval (tests are structurally correct; FFmpeg validation deferred to CI)
  b) Block sign-off pending FFmpeg install

### 5. embed_metadata cover art uses .jpg temp extension regardless of image format (very low)
Cosmetic — FFmpeg detects format from bytes, not extension. Confirm this is acceptable.

## Run these commands

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/epub2audio
uv run epub2audio inspect tests/fixtures/simple_epub3.epub
uv run epub2audio convert --help
```

## Security check

- No `shell=True` in any subprocess calls anywhere
- No `kokoro` imports outside `tts/kokoro.py`
- No `epub/` imports inside `tts/` or `audio/`
- No book content in any log statements

## Output

Fix issues 1 and 2 directly (you have `edit` access). For anything requiring FFmpeg to validate, give your best assessment of the code path correctness. End with **MILESTONE 2 SIGN-OFF: APPROVED** or **MILESTONE 2 SIGN-OFF: BLOCKED** and update `docs/status.md`.

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