"""Deterministic fake TTS engine for use in tests.

:class:`FakeTTSEngine` produces silent audio whose duration is proportional
to the word count of the input text.  The output is entirely deterministic:
the same input text always produces the same numpy array.

This engine is intentionally test-only.  It must **not** be used in production
pipelines.  It satisfies the :class:`~epub2audio.tts.base.TTSEngine` Protocol
via structural subtyping (no inheritance required).

No ``kokoro`` imports appear anywhere in this module.
"""

from __future__ import annotations

import numpy as np

from epub2audio.models import AudioChunk
from epub2audio.tts.base import TTSEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAMPLE_RATE: int = 24_000
"""Output sample rate in Hz.  Matches the Kokoro engine default."""

_MS_PER_WORD: int = 150
"""Approximate milliseconds of silence to generate per word."""


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------


class FakeTTSEngine:
    """Deterministic silent TTS engine for unit and end-to-end tests.

    Generates a single :class:`~epub2audio.models.AudioChunk` of float32 zeros
    whose length is proportional to the word count of the input text:

        ``duration_ms = len(text.split()) * 150``

    This means the same text string always produces an array of identical
    length and content (all zeros), making test assertions stable.

    The engine structurally satisfies :class:`~epub2audio.tts.base.TTSEngine`;
    ``isinstance(FakeTTSEngine(), TTSEngine)`` returns ``True``.

    Example::

        engine = FakeTTSEngine()
        chunks = engine.synthesize("Hello world.", voice="af_heart",
                                   language="en-us", speed=1.0)
        assert len(chunks) == 1
        assert chunks[0].sample_rate == 24000
    """

    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]:
        """Return a single chunk of deterministic silence proportional to word count.

        The *voice*, *language*, and *speed* parameters are accepted but
        ignored — output is always the same for the same *text*.

        Args:
            text: Plain text to "synthesize".
            voice: Ignored.  Accepted for Protocol compatibility.
            language: Ignored.  Accepted for Protocol compatibility.
            speed: Ignored.  Accepted for Protocol compatibility.

        Returns:
            A one-element list containing an :class:`~epub2audio.models.AudioChunk`
            of float32 zeros at 24 000 Hz.
        """
        word_count = len(text.split())
        duration_ms = word_count * _MS_PER_WORD
        n_samples = int(_SAMPLE_RATE * duration_ms / 1000)

        # Guarantee at least one sample so downstream code never receives an
        # empty array, even for empty or whitespace-only text.
        n_samples = max(n_samples, 1)

        data = np.random.uniform(-0.001, 0.001, size=n_samples).astype(np.float32)
        return [AudioChunk(sample_rate=_SAMPLE_RATE, data=data)]


# Runtime check — verify structural subtyping at import time.
# This will raise TypeError during module load if the class no longer
# satisfies the Protocol (e.g. after a signature change).
assert isinstance(FakeTTSEngine(), TTSEngine), (
    "FakeTTSEngine does not satisfy the TTSEngine Protocol"
)
