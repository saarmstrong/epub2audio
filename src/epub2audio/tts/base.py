"""TTSEngine Protocol definition for epub2audio.

All TTS engine implementations must satisfy this Protocol.  The Protocol is
``@runtime_checkable`` so that ``isinstance(engine, TTSEngine)`` can be used
in guard clauses and tests without importing concrete engine classes.

Canonical Protocol (from ``docs/architecture.md``)::

    class TTSEngine(Protocol):
        def synthesize(
            self,
            text: str,
            *,
            voice: str,
            language: str,
            speed: float,
        ) -> list[AudioChunk]: ...

Implementations:
    - :class:`epub2audio.tts.kokoro.KokoroTTSEngine` — production engine
    - :class:`epub2audio.tts.fake.FakeTTSEngine` — deterministic test engine
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from epub2audio.models import AudioChunk


@runtime_checkable
class TTSEngine(Protocol):
    """Protocol that all TTS engine implementations must satisfy.

    Callers depend only on this interface; concrete engine classes are
    selected at configuration time and injected into the pipeline.

    Any class that implements :meth:`synthesize` with the correct signature
    implicitly satisfies this Protocol, regardless of inheritance.
    """

    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]:
        """Synthesize *text* and return one or more audio chunks.

        Args:
            text: Plain narration text to be spoken.  Must not be empty.
                Callers are responsible for normalization and segmentation
                before calling this method.
            voice: Engine-specific voice identifier (e.g. ``"af_heart"``).
            language: BCP-47 language tag used to select pronunciation rules
                (e.g. ``"en-us"``).
            speed: Speaking rate multiplier.  ``1.0`` is normal speed;
                values < 1.0 slow down, > 1.0 speed up.

        Returns:
            One or more :class:`~epub2audio.models.AudioChunk` objects
            containing the synthesized audio.  Callers must concatenate
            multiple chunks in order to produce the complete audio for the
            segment.
        """
        ...  # pragma: no cover
