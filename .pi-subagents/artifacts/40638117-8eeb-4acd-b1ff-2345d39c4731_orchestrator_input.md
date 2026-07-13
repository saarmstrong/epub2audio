# Task for orchestrator

You are the Orchestrator for epub2audio. Begin Milestone 3 — Kokoro Integration.

## Current state

- Milestone 2 is ✅ Complete (reviewer-approved 2026-07-12).
- 112 tests passing, 5 skipped (FFmpeg-gated e2e).
- `tasks/active/` contains only `DEFECT-003` (segment resume, deferred to M4).
- `src/epub2audio/tts/kokoro.py` and `src/epub2audio/tts/voices.py` are stubs.
- `tests/tts/` directory exists but contains no tests.

## What you must do

Create two task contract files and update `docs/status.md`. Do NOT write feature code.

---

## Agent assignments for M3

### TTS Engineer → `tasks/active/M3-tts-engineer.md`

Tasks: M3-01 through M3-04.

**M3-01 — Write `src/epub2audio/tts/kokoro.py`: KokoroTTSEngine**

ALL kokoro library imports must live inside this file and inside try/except blocks so the module remains importable when the `tts` extras are not installed.

```python
class KokoroTTSEngine:
    """TTS engine backed by the local Kokoro neural TTS model.

    All kokoro imports are isolated in this module. Importing this class
    is always safe; instantiation raises MissingDependencyError when the
    kokoro package is not installed.
    """
    def __init__(self, lang_code: str = "a") -> None: ...
    def synthesize(self, text: str, *, voice: str, language: str, speed: float) -> list[AudioChunk]: ...
```

Implementation notes:
- In `__init__`: `try: from kokoro import KPipeline` → on ImportError raise `MissingDependencyError("kokoro")`.
- Store `self._pipeline = KPipeline(lang_code=lang_code)`.
- `synthesize`: map `language` to a lang_code via `tts/voices.py:get_lang_code()`. Call `self._pipeline(text, voice=voice, speed=speed)`. Collect **all** pieces from the generator: `[AudioChunk(sample_rate=piece_sr, data=piece_audio) for _, piece_sr, piece_audio in generator]`. Validate sample_rate from the pipeline (do not hardcode 24000).
- Must satisfy `isinstance(KokoroTTSEngine.__new__(KokoroTTSEngine), TTSEngine)` structurally (Protocol check at class definition, not instantiation, to allow import without model).
- No kokoro imports at module level or outside try/except.

Acceptance: `uv run mypy src/epub2audio/tts/kokoro.py` → 0 errors. `python -c "from epub2audio.tts.kokoro import KokoroTTSEngine"` succeeds without kokoro installed.

**M3-02 — Write `src/epub2audio/tts/voices.py`: voice catalogue and language map**

```python
# Language code map (Kokoro lang_code values)
LANGUAGE_MAP: dict[str, str] = {
    "en-us": "a",
    "en-gb": "b",
    "fr-fr": "f",
    "ja":    "j",
    "ko":    "k",
    "cmn":   "z",
    "zh":    "z",
}

# Curated voice catalogue: voice_id → human-readable description
VOICE_CATALOGUE: dict[str, str] = {
    "af_heart":   "Afrikaans Heart (default)",
    "af_bella":   "Afrikaans Bella",
    "af_sarah":   "Afrikaans Sarah",
    "am_adam":    "American Adam",
    "am_michael": "American Michael",
    "bf_emma":    "British Emma",
    "bf_isabella":"British Isabella",
    "bm_george":  "British George",
    "bm_lewis":   "British Lewis",
}

def get_lang_code(language: str) -> str:
    """Return the Kokoro lang_code for a BCP-47 language tag.

    Raises UnsupportedLanguageError for unsupported languages.
    """

def list_voices() -> list[tuple[str, str]]:
    """Return sorted list of (voice_id, description) pairs."""
```

Acceptance: `uv run mypy src/epub2audio/tts/voices.py` → 0 errors.

**M3-03 — Extend `src/epub2audio/cli.py`: `voices` command**

```python
@app.command()
def voices() -> None:
    """List available Kokoro TTS voices."""
```

Output: Rich table with columns `Voice ID` and `Description`, one row per entry in `VOICE_CATALOGUE`, sorted by voice ID. Print a footer: `f"{len(VOICE_CATALOGUE)} voices available."`.

The existing `inspect` and `convert` commands must not regress.

Acceptance: `uv run epub2audio voices` prints a table with at least 9 rows.

**M3-04 — Extend `src/epub2audio/cli.py`: `doctor` command**

```python
@app.command()
def doctor() -> None:
    """Check the epub2audio environment and dependencies."""
```

Checks (print ✅ or ❌ for each):
1. **Python** — `sys.version` (always passes; shows version string)
2. **FFmpeg** — `shutil.which("ffmpeg")` → path or "not found"
3. **FFprobe** — `shutil.which("ffprobe")` → path or "not found"
4. **espeak-ng** — `shutil.which("espeak-ng")` → path or "not found"
5. **kokoro package** — `try: import kokoro; kokoro.__version__` → version or "not installed"
6. **misaki package** — `try: import misaki; misaki.__version__` → version or "not installed"
7. **Disk space** — `shutil.disk_usage(".")` → show free GB

Exit code 0 if all required dependencies (FFmpeg, FFprobe) are present; exit code 1 if any required dep is missing. `espeak-ng`, kokoro, and misaki are optional (warn, not error).

Acceptance: `uv run epub2audio doctor` exits 0 or 1 (depending on what's installed) and prints a readable table. `uv run mypy src/epub2audio/cli.py` → 0 errors.

**Done criteria for TTS Engineer contract:**
- All 4 tasks fully implemented
- `uv run mypy src/epub2audio/tts/kokoro.py src/epub2audio/tts/voices.py src/epub2audio/cli.py` → 0 errors
- `uv run ruff check` → clean
- `uv run pytest tests/ -v` → existing 112 tests still pass (no regressions)
- `uv run epub2audio voices` and `uv run epub2audio doctor` both work
- Task moved to `tasks/completed/`

---

### Tester → `tasks/active/M3-tester.md`

Tasks: M3-05 + CLI smoke tests.

**M3-05 — Write `tests/tts/test_kokoro_smoke.py`**

```python
"""Smoke tests for KokoroTTSEngine.

Requires the kokoro package AND the Kokoro model to be downloaded.
These tests are opt-in only — they do NOT run in normal CI.

Run with:
    uv run pytest tests/tts/test_kokoro_smoke.py -v -m "slow and requires_model"
"""

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.requires_model]
```

Required test cases:
```python
def test_kokoro_import_without_package_raises_missing_dependency():
    """Importing KokoroTTSEngine when kokoro is absent raises MissingDependencyError, not ImportError."""
    # Use importlib + monkeypatching to simulate missing kokoro; confirm MissingDependencyError raised

def test_kokoro_synthesize_returns_audio_chunks():
    """synthesize() returns a non-empty list of AudioChunk objects (requires model)."""

def test_kokoro_synthesize_is_deterministic():
    """Same text + voice + speed → same output length (requires model)."""

def test_kokoro_sample_rate_from_pipeline():
    """AudioChunk.sample_rate is set from the pipeline, not hardcoded."""

def test_kokoro_unsupported_language_raises():
    """synthesize() with an unsupported language raises UnsupportedLanguageError."""

def test_kokoro_empty_text_returns_chunk():
    """synthesize('') returns at least one AudioChunk (pipeline handles empty input)."""
```

**CLI smoke tests — `tests/tts/test_voices_command.py`** (new file, no model required):
```python
def test_voices_command_exits_zero():
    """epub2audio voices exits 0."""

def test_voices_command_output_contains_af_heart():
    """voices output mentions af_heart (the default voice)."""

def test_doctor_command_exits():
    """epub2audio doctor exits 0 or 1 (not crashes)."""

def test_doctor_shows_python_version():
    """doctor output contains 'Python' and a version string."""
```

Use `subprocess.run(["uv", "run", "epub2audio", ...], capture_output=True)` or `typer.testing.CliRunner` for CLI tests.

**Done criteria for Tester contract:**
- `tests/tts/test_kokoro_smoke.py` written and mypy/ruff clean
- `tests/tts/test_voices_command.py` written and passing
- `uv run pytest tests/ -v` → all 112 existing tests still pass; new CLI tests pass; smoke tests skip correctly without `-m "slow and requires_model"`
- Task moved to `tasks/completed/`

---

## After creating the two contracts

1. Update `docs/status.md`: Milestone 3 is now In Progress.
2. Do NOT write feature code.

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