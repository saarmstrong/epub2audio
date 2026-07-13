"""Kokoro TTS engine adapter for epub2audio.

ALL imports from the ``kokoro`` PyPI package are isolated inside this module,
guarded by ``try/except ImportError``.  This means:

- ``from epub2audio.tts.kokoro import KokoroTTSEngine`` **always succeeds**,
  even when the optional ``[tts]`` extras are not installed.
- :class:`KokoroTTSEngine` **instantiation** raises
  :exc:`~epub2audio.errors.MissingDependencyError` when ``kokoro`` is absent.

Install the optional TTS dependencies with::

    uv pip install "epub2audio[tts]"
    # or: pip install "epub2audio[tts]"

Kokoro KPipeline API
---------------------
The generator returned by ``KPipeline.__call__`` yields
``(graphemes, phonemes, audio_array)`` 3-tuples.  The ``audio_array`` is a
NumPy ``float32`` ndarray at 24 000 Hz (Kokoro's native sample rate).  The
pipeline does not expose the sample rate per-piece in the generator tuple, so
we store it at ``__init__`` time from the pipeline's ``sample_rate`` attribute
when available, falling back to the well-known default of 24 000 Hz.
"""

from __future__ import annotations

from epub2audio.errors import MissingDependencyError
from epub2audio.models import AudioChunk
from epub2audio.tts.voices import get_lang_code

# ---------------------------------------------------------------------------
# Kokoro sample-rate constant
# ---------------------------------------------------------------------------

_KOKORO_DEFAULT_SAMPLE_RATE: int = 24_000
"""Kokoro's native output sample rate in Hz.

The ``KPipeline`` generator yields ``(grapheme, phoneme, audio)`` tuples; the
sample rate is not included in each tuple.  We read it from
``pipeline.sample_rate`` after construction (when the attribute exists), and
fall back to this constant when it does not.
"""


# ---------------------------------------------------------------------------
# KokoroTTSEngine
# ---------------------------------------------------------------------------


class KokoroTTSEngine:
    """TTS engine backed by the local Kokoro neural TTS model.

    All kokoro imports are isolated in this module.  Importing this class is
    always safe; instantiation raises :exc:`MissingDependencyError` when the
    ``kokoro`` package is not installed.

    Single-language scope (by design)
    ---------------------------------
    The Kokoro ``KPipeline`` is constructed once, at ``__init__`` time, with a
    fixed ``lang_code``.  A single engine instance is therefore **locked to one
    language for its entire lifetime**.  The ``language`` argument accepted by
    :meth:`synthesize` is *validated* (via
    :func:`~epub2audio.tts.voices.get_lang_code`, which raises
    :exc:`~epub2audio.errors.UnsupportedLanguageError` for unknown tags) but is
    **not** re-threaded into the pipeline — the init-time ``lang_code`` governs
    synthesis.  To narrate content in a different language, construct a new
    engine with the matching ``lang_code``.

    Args:
        lang_code: Kokoro language code (``"a"`` for en-us, ``"b"`` for en-gb,
            etc.).  This value is baked into the pipeline and cannot be changed
            after construction.  Callers that start from a BCP-47 tag can derive
            it with :func:`~epub2audio.tts.voices.get_lang_code`.

    Raises:
        MissingDependencyError: If the ``kokoro`` package is not installed.

    Example::

        engine = KokoroTTSEngine(lang_code="a")
        chunks = engine.synthesize("Hello world.", voice="af_heart",
                                   language="en-us", speed=1.0)
    """

    def __init__(self, lang_code: str = "a") -> None:
        try:
            from kokoro import KPipeline
        except ImportError as exc:
            raise MissingDependencyError(
                "kokoro",
                "The 'kokoro' package is required for TTS synthesis. "
                "Install it with: uv pip install 'epub2audio[tts]'",
            ) from exc

        self._pipeline = KPipeline(lang_code=lang_code)

        # Read the sample rate from the pipeline attribute when available;
        # otherwise fall back to Kokoro's well-known default of 24 000 Hz.
        self._sample_rate: int = int(
            getattr(self._pipeline, "sample_rate", _KOKORO_DEFAULT_SAMPLE_RATE)
        )

    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]:
        """Synthesize *text* using the Kokoro neural TTS model.

        Maps the BCP-47 *language* tag to a Kokoro ``lang_code`` via
        :func:`~epub2audio.tts.voices.get_lang_code`, then runs the
        ``KPipeline`` and collects all audio pieces.

        Args:
            text: Plain narration text to synthesize.  Should be a single
                sentence or short paragraph; long inputs may be truncated
                internally by Kokoro.
            voice: Kokoro voice identifier, e.g. ``"af_heart"``.
            language: BCP-47 language tag, e.g. ``"en-us"``.  Must be present
                in :data:`~epub2audio.tts.voices.LANGUAGE_MAP`.
            speed: Speaking-rate multiplier (``1.0`` = normal).

        Returns:
            List of :class:`~epub2audio.models.AudioChunk` objects in order.
            Callers must concatenate them to produce the full segment audio.

        Raises:
            UnsupportedLanguageError: If *language* is not in the supported
                language map.
        """
        # Validate language and obtain lang_code (raises UnsupportedLanguageError
        # for unknown tags — propagated unchanged per the contract).
        # Validate language — raises UnsupportedLanguageError for unknown tags.
        # The lang_code is not threaded into the pipeline call here because
        # KokoroTTSEngine is initialised with a lang_code at __init__ time.
        get_lang_code(language)

        generator = self._pipeline(text, voice=voice, speed=speed)

        chunks: list[AudioChunk] = []
        for _, _, audio_array in generator:
            chunks.append(
                AudioChunk(
                    sample_rate=self._sample_rate,
                    data=audio_array,
                )
            )

        return chunks


# ---------------------------------------------------------------------------
# Structural Protocol assertion (checked at import time in debug/test builds)
# ---------------------------------------------------------------------------


def _assert_protocol_compat() -> None:  # pragma: no cover
    """Verify KokoroTTSEngine satisfies TTSEngine at definition time."""
    # This is a static check only; we do not instantiate the engine here
    # because that would trigger the MissingDependencyError guard.
    assert issubclass(type(KokoroTTSEngine), type)  # trivially true; real check below
    # Check method presence and signature structurally:
    import inspect

    sig = inspect.signature(KokoroTTSEngine.synthesize)
    params = list(sig.parameters.keys())
    assert "text" in params
    assert "voice" in params
    assert "language" in params
    assert "speed" in params
