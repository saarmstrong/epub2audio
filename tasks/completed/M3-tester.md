# M3 — Tester Task Contract

_Assigned: 2026-07-12_
_Milestone: 3 — Kokoro Integration_
_Agent: Tester_

---

## Scope

Write tests for the Kokoro TTS engine and the two new CLI commands added by the
TTS Engineer in M3-01 through M3-04.

Do **not** implement features. Do **not** modify any file under `src/`.

Dependencies:
- M3-01 (`KokoroTTSEngine`) and M3-02 (`voices.py`) must be delivered by the
  TTS Engineer before `test_kokoro_smoke.py` can be finalised (though you may
  write the file skeleton in parallel).
- M3-03 (`voices` command) and M3-04 (`doctor` command) must be delivered before
  `test_voices_command.py` can be run.

---

## M3-05 — `tests/tts/test_kokoro_smoke.py`

Create the directory `tests/tts/` with an `__init__.py`, then write the smoke
test file.

### File header

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

### Required test cases

```python
def test_kokoro_import_without_package_raises_missing_dependency(monkeypatch):
    """Importing KokoroTTSEngine when kokoro is absent raises MissingDependencyError, not ImportError.

    Strategy: use monkeypatch to make 'kokoro' unimportable by inserting a
    broken entry into sys.modules, then attempt to instantiate KokoroTTSEngine,
    and assert MissingDependencyError is raised.
    """
    import sys
    import importlib

    # Remove cached module to force re-import in __init__
    monkeypatch.delitem(sys.modules, "kokoro", raising=False)
    monkeypatch.setitem(sys.modules, "kokoro", None)  # type: ignore[arg-type]

    # Re-import the engine module so the try/except block runs fresh
    import epub2audio.tts.kokoro as kokoro_mod
    importlib.reload(kokoro_mod)

    from epub2audio.errors import MissingDependencyError
    with pytest.raises(MissingDependencyError):
        kokoro_mod.KokoroTTSEngine()


def test_kokoro_synthesize_returns_audio_chunks():
    """synthesize() returns a non-empty list of AudioChunk objects (requires model)."""
    from epub2audio.tts.kokoro import KokoroTTSEngine
    from epub2audio.models import AudioChunk

    engine = KokoroTTSEngine()
    chunks = engine.synthesize(
        "Hello, world.",
        voice="af_heart",
        language="en-us",
        speed=1.0,
    )
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, AudioChunk) for c in chunks)


def test_kokoro_synthesize_is_deterministic():
    """Same text + voice + speed → same total output array length (requires model)."""
    from epub2audio.tts.kokoro import KokoroTTSEngine

    engine = KokoroTTSEngine()
    kwargs = dict(voice="af_heart", language="en-us", speed=1.0)
    chunks_a = engine.synthesize("Hello, world.", **kwargs)
    chunks_b = engine.synthesize("Hello, world.", **kwargs)

    total_a = sum(len(c.data) for c in chunks_a)
    total_b = sum(len(c.data) for c in chunks_b)
    assert total_a == total_b


def test_kokoro_sample_rate_from_pipeline():
    """AudioChunk.sample_rate is set from the pipeline, not hardcoded to 24000."""
    from epub2audio.tts.kokoro import KokoroTTSEngine

    engine = KokoroTTSEngine()
    chunks = engine.synthesize(
        "Sample rate test.",
        voice="af_heart",
        language="en-us",
        speed=1.0,
    )
    assert len(chunks) > 0
    # Just verify sample_rate is a positive integer coming from the pipeline.
    # Do not assert it equals 24000 — the pipeline dictates the value.
    assert all(isinstance(c.sample_rate, int) and c.sample_rate > 0 for c in chunks)


def test_kokoro_unsupported_language_raises():
    """synthesize() with an unsupported language raises UnsupportedLanguageError."""
    from epub2audio.tts.kokoro import KokoroTTSEngine
    from epub2audio.errors import UnsupportedLanguageError

    engine = KokoroTTSEngine()
    with pytest.raises(UnsupportedLanguageError):
        engine.synthesize(
            "Bonjour.",
            voice="af_heart",
            language="xx-zz",  # unsupported
            speed=1.0,
        )


def test_kokoro_empty_text_returns_chunk():
    """synthesize('') returns at least one AudioChunk (pipeline handles empty input)."""
    from epub2audio.tts.kokoro import KokoroTTSEngine
    from epub2audio.models import AudioChunk

    engine = KokoroTTSEngine()
    chunks = engine.synthesize(
        "",
        voice="af_heart",
        language="en-us",
        speed=1.0,
    )
    assert isinstance(chunks, list)
    assert all(isinstance(c, AudioChunk) for c in chunks)
```

### Marker registration

Ensure `slow` and `requires_model` markers are registered in `pyproject.toml`
(under `[tool.pytest.ini_options]` → `markers`). If they are already registered
from a previous milestone, do not duplicate them.

### Run without model (expected behaviour)

```
uv run pytest tests/tts/test_kokoro_smoke.py -v
```
All tests in this file must be **skipped** (not fail) when invoked without the
`-m "slow and requires_model"` selector — because `pytestmark` causes them to be
collected but not run unless the marks are selected. Do **not** add explicit
`pytest.skip()` calls; let the mark system do the work.

Verify with:
```
uv run pytest tests/ -v    # smoke tests NOT included by default
```

---

## CLI smoke tests — `tests/tts/test_voices_command.py`

This file requires **no model** and must pass in normal CI.

```python
"""CLI smoke tests for the voices and doctor commands.

These tests do not require the kokoro model or package.
They test the CLI entry-points added in M3-03 and M3-04.
"""
import subprocess
import sys


def test_voices_command_exits_zero():
    """epub2audio voices exits 0."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "voices"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_voices_command_output_contains_af_heart():
    """voices output mentions af_heart (the default voice)."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "voices"],
        capture_output=True,
        text=True,
    )
    assert "af_heart" in result.stdout, result.stdout


def test_voices_command_output_contains_count():
    """voices output contains the voice count footer line."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "voices"],
        capture_output=True,
        text=True,
    )
    assert "voices available" in result.stdout, result.stdout


def test_doctor_command_exits():
    """epub2audio doctor exits 0 or 1 (not crashes or other codes)."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "doctor"],
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}: {result.stderr}"
    )


def test_doctor_shows_python_version():
    """doctor output contains 'Python' and a version string."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "doctor"],
        capture_output=True,
        text=True,
    )
    # Python version line should appear in stdout
    assert "Python" in result.stdout or "Python" in result.stderr, (
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Should contain a dotted version number like 3.12.x
    assert any(
        char.isdigit() for char in result.stdout + result.stderr
    ), "No version digits found in doctor output"
```

---

## Cross-cutting requirements

- `tests/tts/__init__.py` must exist (empty file is fine).
- `uv run ruff check tests/tts/` → clean.
- `uv run mypy tests/tts/test_kokoro_smoke.py tests/tts/test_voices_command.py` → 0 errors
  (or consistent with how the rest of `tests/` is type-checked).
- `uv run pytest tests/ -v` → all **112** existing tests still pass; new CLI tests
  in `test_voices_command.py` also pass; smoke tests in `test_kokoro_smoke.py` are
  collected but not selected (no regression, no spurious failure).

---

## Done criteria

- `tests/tts/__init__.py` created.
- `tests/tts/test_kokoro_smoke.py` written with all 6 test functions.
- `tests/tts/test_voices_command.py` written with all 5 test functions.
- All acceptance gates above pass.
- This file moved to `tasks/completed/`.
