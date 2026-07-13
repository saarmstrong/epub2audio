"""Shared fixtures for the pipeline test suite.

Provides:
- ``CountingFakeTTSEngine``  — FakeTTSEngine wrapper that records every
  ``synthesize()`` call so tests can assert how many segments were synthesized.
- ``fake_tts_engine``        — standard FakeTTSEngine fixture.
- ``fake_tts_engine_with_counter`` — CountingFakeTTSEngine fixture.
"""

from __future__ import annotations

from typing import Any

import pytest

from epub2audio.models import AudioChunk
from epub2audio.tts.base import TTSEngine
from epub2audio.tts.fake import FakeTTSEngine

# ---------------------------------------------------------------------------
# Counting engine (class-level, importable by tests that need two instances)
# ---------------------------------------------------------------------------


class CountingFakeTTSEngine:
    """FakeTTSEngine wrapper that tracks every ``synthesize()`` call.

    Useful for asserting that a resumed run skips already-synthesized segments
    (``call_count == 0``) or that a config change causes full re-synthesis
    (``call_count == first_run_call_count``).

    The engine satisfies :class:`~epub2audio.tts.base.TTSEngine` structurally,
    so it can be passed to ``convert_epub`` directly.

    Attributes:
        call_count: Number of times ``synthesize()`` has been called.
        calls: List of dicts recording every call's arguments.
    """

    def __init__(self) -> None:
        self.call_count: int = 0
        self.calls: list[dict[str, Any]] = []
        self._delegate = FakeTTSEngine()

    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]:
        """Delegate to FakeTTSEngine, recording the call first."""
        self.call_count += 1
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "language": language,
                "speed": speed,
            }
        )
        return self._delegate.synthesize(text, voice=voice, language=language, speed=speed)


# Runtime Protocol check — fail fast if signature drifts.
assert isinstance(CountingFakeTTSEngine(), TTSEngine), (
    "CountingFakeTTSEngine does not satisfy the TTSEngine Protocol"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_tts_engine() -> FakeTTSEngine:
    """A standard :class:`~epub2audio.tts.fake.FakeTTSEngine` instance."""
    return FakeTTSEngine()


@pytest.fixture
def fake_tts_engine_with_counter() -> CountingFakeTTSEngine:
    """A :class:`CountingFakeTTSEngine` that records every ``synthesize()`` call.

    Use this fixture when a test needs to assert *how many* segments were
    synthesized, e.g. to verify that a resumed run skips cached segments.

    For tests that need two independent counting engines (e.g. first run vs
    second run), instantiate :class:`CountingFakeTTSEngine` directly inside
    the test function.
    """
    return CountingFakeTTSEngine()
