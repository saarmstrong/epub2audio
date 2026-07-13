# Task for reviewer

Run the full Milestone 3 review for epub2audio. This is the milestone sign-off review (M3-06).

## Context

Two agents completed M3 work in parallel:
- **TTS Engineer**: implemented tts/voices.py, tts/kokoro.py, and extended cli.py with `voices` and `doctor` commands
- **Tester**: wrote tests/tts/test_kokoro_smoke.py (6 opt-in smoke tests) and tests/tts/test_voices_command.py (5 passing CLI tests); added auto-skip hook to conftest.py

Current state: **117 passed, 11 skipped (6 smoke + 5 e2e FFmpeg), 0 failed**. All M3 tasks in tasks/completed/.

## M3-06 verification — run these commands explicitly

```bash
uv run epub2audio voices
uv run epub2audio doctor
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/epub2audio
```

Verify:
- `voices` produces a Rich table with ≥ 9 rows including `af_heart`, exits 0
- `doctor` prints a status line for each of: Python, FFmpeg, FFprobe, espeak-ng, kokoro, misaki, disk — exits 0 or 1 (not crashes), never exits 2+
- `inspect` and `convert --help` still work (no CLI regressions)

## Known issues to investigate

### 1. KokoroTTSEngine language scope (design question, low)
A `KokoroTTSEngine` instance is initialised with a fixed `lang_code` baked into `KPipeline`. The `synthesize()` method accepts a `language` parameter and validates it via `get_lang_code()`, but the pipeline itself uses the init-time lang_code. This means a single engine cannot switch languages mid-run. Confirm this is intentional per the architecture (it is), note it in the review, and confirm it is documented in the class docstring.

### 2. pyproject.toml mypy overrides accumulation (low)
The TTS Engineer added `[[tool.mypy.overrides]]` entries for kokoro and misaki. Verify the final pyproject.toml has no duplicate override stanzas and all overrides are still legitimate.

### 3. Kokoro smoke tests cannot be validated locally (kokoro not installed)
Assess the structural correctness of the 6 smoke tests by code review. Confirm they carry the correct markers and will skip in default `pytest tests/` runs.

### 4. doctor exit code correctness (medium)
The contract specifies: exit 0 if FFmpeg + FFprobe are present; exit 1 if either is missing. On this machine both are absent so exit 1 is expected. Verify the implementation actually exits 1 (not 0 with warnings) when required deps are missing, and exits 0 when they are present (review the code path for when FFmpeg is found).

### 5. Import boundary check
- No kokoro PyPI imports outside `tts/kokoro.py`
- No `epub/` imports in `tts/`
- `tts/kokoro.py` importable without kokoro package installed (run the check)

## Output

Fix any defects you find directly. For anything requiring kokoro or FFmpeg, give your best code-path assessment. End with **MILESTONE 3 SIGN-OFF: APPROVED** or **MILESTONE 3 SIGN-OFF: BLOCKED** and update `docs/status.md`.

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