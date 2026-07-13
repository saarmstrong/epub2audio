"""Kokoro provider adapter for epub2audio (Layer 2).

:class:`KokoroProvider` translates a Director-produced
:class:`~epub2audio.models.NarrationSegment` into a
:class:`~epub2audio.providers.base.ProviderRequest` and delegates raw
synthesis to an injected :class:`~epub2audio.tts.base.TTSEngine`.

This is a **mapping-only** adapter.  It contains no scene analysis, no
dialogue detection, and no pacing decisions — all of those live in the
Director (Layer 1, ``director/``).  The only things it does are:

- Resolve effective pace from the segment direction (or scene default).
- Compute the final ``speed`` parameter (pace × base speed, clamped).
- Apply conservative punctuation/whitespace normalization so Kokoro
  produces natural falling intonation at sentence ends.
- Delegate raw synthesis to the injected Layer-3 engine.

Pronunciation-dictionary substitution will be added here in Milestone 10
(search for ``TODO(M10)``).

Dependency injection
--------------------
The constructor accepts any object satisfying the
:class:`~epub2audio.tts.base.TTSEngine` Protocol.  This means tests can pass
:class:`~epub2audio.tts.fake.FakeTTSEngine` without ever importing or
installing the real ``kokoro`` package.  The module-level factory
:func:`build_kokoro_provider` is the *only* place that touches
:class:`~epub2audio.tts.kokoro.KokoroTTSEngine`.
"""

from __future__ import annotations

import re

from epub2audio.config import Settings
from epub2audio.models import AudioChunk, NarrationDirection, NarrationSegment
from epub2audio.providers.base import ProviderRequest
from epub2audio.tts.base import TTSEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Kokoro's accepted speed range (from voices.py / KPipeline contract).
_SPEED_MIN: float = 0.25
_SPEED_MAX: float = 4.0

# Characters that already end a sentence well for Kokoro — no "." appended.
_SENTENCE_ENDINGS: frozenset[str] = frozenset('.?!\u2026,;:"\u2019\u201d)')

# Collapse any run of whitespace (tabs, multiple spaces, newlines within a
# segment) to a single space.  Segments from the Director are already short,
# but EPUB cleanup may leave stray whitespace inside a paragraph.
_WHITESPACE_RE = re.compile(r"[ \t\r\n]+")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_for_kokoro(text: str) -> str:
    """Apply conservative punctuation/whitespace normalization for Kokoro.

    This is **not** prose rewriting: the words are unchanged.  We only:

    1. Collapse runs of internal whitespace to single spaces.
    2. Ensure the text ends with sentence-ending punctuation so Kokoro
       produces natural falling intonation rather than an abrupt cut-off.

    Args:
        text: The segment text from the narration plan.

    Returns:
        The text, whitespace-normalized and punctuation-terminated.
    """
    # 1. Collapse internal whitespace.
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    if not normalized:
        return normalized

    # 2. Ensure trailing sentence-ending punctuation.
    if normalized[-1] not in _SENTENCE_ENDINGS:
        normalized += "."

    return normalized


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp *value* into the closed range ``[low, high]``."""
    return max(low, min(high, value))


def _effective_direction(
    segment: NarrationSegment,
    defaults: NarrationDirection,
) -> NarrationDirection:
    """Return the direction that applies to *segment*.

    Uses the per-segment override when present; falls back to the scene
    *defaults* otherwise.

    Args:
        segment: The narration segment being rendered.
        defaults: Scene-level delivery defaults from the :class:`NarrationPlan`.

    Returns:
        The resolved :class:`~epub2audio.models.NarrationDirection`.
    """
    return segment.direction if segment.direction is not None else defaults


# ---------------------------------------------------------------------------
# KokoroProvider
# ---------------------------------------------------------------------------


class KokoroProvider:
    """Layer-2 Kokoro adapter satisfying the :class:`~epub2audio.providers.base.NarrationProvider` Protocol.

    Translates Director-produced :class:`~epub2audio.models.NarrationSegment`
    objects into :class:`~epub2audio.providers.base.ProviderRequest` objects
    and delegates synthesis to an injected Layer-3
    :class:`~epub2audio.tts.base.TTSEngine`.

    **Mapping only** — no scene analysis, no dialogue detection, no pacing
    computation.  Those are the Director's responsibility.

    Args:
        engine: Any object satisfying the
            :class:`~epub2audio.tts.base.TTSEngine` Protocol.  In production
            this will be a :class:`~epub2audio.tts.kokoro.KokoroTTSEngine`;
            in tests a :class:`~epub2audio.tts.fake.FakeTTSEngine`.

    Example::

        from epub2audio.tts.fake import FakeTTSEngine
        from epub2audio.providers.kokoro import KokoroProvider
        from epub2audio.config import Settings

        provider = KokoroProvider(FakeTTSEngine())
        request = provider.render(segment, defaults, Settings())
        chunks = provider.synthesize(request)
    """

    def __init__(self, engine: TTSEngine) -> None:
        self._engine = engine

    def render(
        self,
        segment: NarrationSegment,
        defaults: NarrationDirection,
        settings: Settings,
    ) -> ProviderRequest:
        """Map one narration plan segment into a Kokoro-ready request.

        Steps:

        1. Resolve effective direction (per-segment override or scene default).
        2. Compute speed: ``pace × settings.speed``, clamped to ``[0.25, 4.0]``.
        3. Apply Kokoro punctuation/whitespace normalization to the text.

        The ``payload`` dict is empty: Kokoro expresses everything via
        ``text``, ``voice``, and ``speed``.

        Args:
            segment: One directed narration segment from the plan.
            defaults: Scene-level delivery defaults; used when the segment
                has no per-segment direction override.
            settings: Application-wide settings supplying ``voice``,
                ``language``, and base ``speed``.

        Returns:
            A :class:`~epub2audio.providers.base.ProviderRequest` ready for
            :meth:`synthesize`.
        """
        direction = _effective_direction(segment, defaults)

        # Speed = plan pace × user base speed, clamped to Kokoro's valid range.
        raw_speed = direction.pace * settings.speed
        speed = round(_clamp(raw_speed, _SPEED_MIN, _SPEED_MAX), 3)

        # TODO(M10): apply pronunciation-dictionary substitutions here,
        # before normalization, so phoneme hints reach the synthesis engine.
        text = _normalize_for_kokoro(segment.text)

        return ProviderRequest(
            segment_id=segment.id,
            text=text,
            voice=settings.voice,
            language=settings.language,
            speed=speed,
            pause_after_ms=segment.pause_after_ms,
            payload={},
        )

    def synthesize(self, request: ProviderRequest) -> list[AudioChunk]:
        """Execute raw synthesis via the injected Layer-3 engine.

        Delegates directly to :meth:`~epub2audio.tts.base.TTSEngine.synthesize`
        using the fields from *request*.  Any Kokoro-internal long-text
        splitting is handled by the engine itself; this adapter does not
        second-guess it.

        Args:
            request: The :class:`~epub2audio.providers.base.ProviderRequest`
                produced by :meth:`render`.

        Returns:
            One or more :class:`~epub2audio.models.AudioChunk` objects in
            reading order.

        Raises:
            UnsupportedLanguageError: Propagated from the engine if
                ``request.language`` is not in the supported language map.
        """
        return self._engine.synthesize(
            request.text,
            voice=request.voice,
            language=request.language,
            speed=request.speed,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_kokoro_provider(lang_code: str = "a") -> KokoroProvider:
    """Construct a production :class:`KokoroProvider` backed by a real Kokoro engine.

    This is the **only** place in the codebase that imports or instantiates
    :class:`~epub2audio.tts.kokoro.KokoroTTSEngine`.  All other callers use
    either this factory or inject a :class:`~epub2audio.tts.fake.FakeTTSEngine`
    directly.

    Args:
        lang_code: Kokoro language code (``"a"`` for en-us, ``"b"`` for en-gb,
            etc.).  See :data:`~epub2audio.tts.voices.LANGUAGE_MAP` for the
            full mapping.

    Returns:
        A :class:`KokoroProvider` wrapping a fresh
        :class:`~epub2audio.tts.kokoro.KokoroTTSEngine`.

    Raises:
        MissingDependencyError: If the ``kokoro`` package is not installed.
    """
    from epub2audio.tts.kokoro import KokoroTTSEngine

    engine = KokoroTTSEngine(lang_code=lang_code)
    return KokoroProvider(engine)
