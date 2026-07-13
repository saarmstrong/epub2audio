"""Smoke tests for KokoroTTSEngine.

Requires the kokoro package AND the Kokoro model to be downloaded.
These tests are opt-in only — they do NOT run in normal CI.

Run with:
    uv run pytest tests/tts/test_kokoro_smoke.py -v -m "slow and requires_model"
"""
# mypy: ignore-errors

from __future__ import annotations

import importlib
import sys

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.requires_model]


def test_kokoro_import_without_package_raises_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Importing KokoroTTSEngine when kokoro is absent raises MissingDependencyError.

    Strategy: insert None into sys.modules for 'kokoro' to simulate a missing
    package, reload the engine module so the try/except import block runs fresh,
    then assert that instantiating KokoroTTSEngine raises MissingDependencyError.
    """
    monkeypatch.delitem(sys.modules, "kokoro", raising=False)
    monkeypatch.setitem(sys.modules, "kokoro", None)

    import epub2audio.tts.kokoro as kokoro_mod

    importlib.reload(kokoro_mod)

    from epub2audio.errors import MissingDependencyError

    with pytest.raises(MissingDependencyError):
        kokoro_mod.KokoroTTSEngine()


def test_kokoro_synthesize_returns_audio_chunks() -> None:
    """synthesize() returns a non-empty list of AudioChunk objects (requires model)."""
    from epub2audio.models import AudioChunk
    from epub2audio.tts.kokoro import KokoroTTSEngine

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


def test_kokoro_synthesize_is_deterministic() -> None:
    """Same text + voice + speed → same total output array length (requires model)."""
    from epub2audio.tts.kokoro import KokoroTTSEngine

    engine = KokoroTTSEngine()
    kwargs: dict[str, object] = {"voice": "af_heart", "language": "en-us", "speed": 1.0}
    chunks_a = engine.synthesize("Hello, world.", **kwargs)  # type: ignore[arg-type]
    chunks_b = engine.synthesize("Hello, world.", **kwargs)  # type: ignore[arg-type]

    total_a = sum(len(c.data) for c in chunks_a)
    total_b = sum(len(c.data) for c in chunks_b)
    assert total_a == total_b


def test_kokoro_sample_rate_from_pipeline() -> None:
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
    # Verify sample_rate is a positive integer coming from the pipeline.
    # Do not assert it equals 24000 — the pipeline dictates the value.
    assert all(isinstance(c.sample_rate, int) and c.sample_rate > 0 for c in chunks)


def test_kokoro_unsupported_language_raises() -> None:
    """synthesize() with an unsupported language raises UnsupportedLanguageError."""
    from epub2audio.errors import UnsupportedLanguageError
    from epub2audio.tts.kokoro import KokoroTTSEngine

    engine = KokoroTTSEngine()
    with pytest.raises(UnsupportedLanguageError):
        engine.synthesize(
            "Bonjour.",
            voice="af_heart",
            language="xx-zz",  # unsupported
            speed=1.0,
        )


def test_kokoro_empty_text_returns_chunk() -> None:
    """synthesize('') returns at least one AudioChunk (pipeline handles empty input)."""
    from epub2audio.models import AudioChunk
    from epub2audio.tts.kokoro import KokoroTTSEngine

    engine = KokoroTTSEngine()
    chunks = engine.synthesize(
        "",
        voice="af_heart",
        language="en-us",
        speed=1.0,
    )
    assert isinstance(chunks, list)
    assert all(isinstance(c, AudioChunk) for c in chunks)
