"""NarrationProvider Protocol and ProviderRequest model for epub2audio.

This module defines the **Layer-2** contract between the pipeline and
provider adapters.  See ``docs/decisions/003-narration-pipeline.md`` (ADR-003)
for the full three-layer architecture.

Design note — why ``ProviderRequest`` lives here and not in ``models.py``
---------------------------------------------------------------------------
``models.py`` is the base layer and carries *provider-neutral* Director output
(``NarrationPlan``, ``NarrationSegment``, etc.).  ``ProviderRequest`` is the
*output of a provider adapter's* ``render()`` call — a provider-specific
container that may carry SSML, instruction strings, or other engine controls
in its ``payload`` field.  Keeping it here (not in ``models.py``) preserves
the principle stated in ADR-003 §2: "The plan is provider-neutral: no SSML,
no Kokoro tokens, no engine-specific fields ever appear in it."
``ProviderRequest`` is *not* a plan model; it is a Layer-2 artefact.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from epub2audio.config import Settings
from epub2audio.models import AudioChunk, NarrationDirection, NarrationSegment


class ProviderRequest(BaseModel):
    """Provider-agnostic container passed opaquely from ``render()`` to ``synthesize()``.

    The pipeline constructs a :class:`ProviderRequest` by calling
    :meth:`NarrationProvider.render`, then passes it unchanged to
    :meth:`NarrationProvider.synthesize`.  No pipeline code inspects or
    modifies any field after ``render()`` returns.

    ``text`` may differ from :attr:`~epub2audio.models.NarrationSegment.text`
    by adapter-applied punctuation or whitespace adjustments (e.g. ensuring a
    trailing period so Kokoro produces falling intonation).  This is
    explicitly **not** prose rewriting — the semantic content must be a direct
    representation of the source segment text.

    ``pause_after_ms`` is carried through from the narration plan so the
    audio-assembly stage can insert silence between segments.  In Milestone 9
    the pipeline does *not* insert silence yet; the field is reserved for a
    future milestone.
    """

    model_config = ConfigDict(frozen=True)

    segment_id: str
    """Stable identifier sourced from :attr:`~epub2audio.models.NarrationSegment.id`.

    Used by the pipeline for progress tracking and resume keying across runs.
    """

    text: str
    """The text actually sent to the synthesis engine.

    An adapter MAY adjust punctuation or whitespace for better synthesis
    quality (e.g. appending a trailing sentence-ending punctuation mark).
    This is NOT prose rewriting — the semantic content must faithfully
    represent the source segment text.
    """

    voice: str
    """Engine-specific voice identifier (e.g. ``"af_heart"`` for Kokoro)."""

    language: str
    """BCP-47 language tag (e.g. ``"en-us"``)."""

    speed: float
    """Speaking-rate multiplier derived from pace and settings.

    ``1.0`` is normal speed; values below ``1.0`` slow down, above ``1.0``
    speed up.  The adapter computes this from
    :attr:`~epub2audio.models.NarrationDirection.pace` scaled by
    :attr:`~epub2audio.config.Settings.speed`.
    """

    pause_after_ms: int
    """Silence to insert after this segment, in milliseconds.

    Carried through from :attr:`~epub2audio.models.NarrationSegment.pause_after_ms`.
    The pipeline decides whether to apply it; in Milestone 9 it does **not**
    insert silence yet.
    """

    payload: dict[str, Any]
    """Provider-specific extras — empty for Kokoro; populated by other adapters.

    The pipeline never inspects this field; only the adapter that populated it
    knows how to consume it.  Expected shapes by provider:

    - **Kokoro**: ``{}`` (empty — all controls are expressed via ``text``,
      ``voice``, ``speed``).
    - **OpenAI / Gemini**: ``{"instructions": "<natural-language narration cue>"}``
    - **Azure**: ``{"ssml": "<speak>...</speak>"}``
    - **ElevenLabs**: ``{"voice_settings": {...}, "prompt": "<optional cue>"}``
    """


@runtime_checkable
class NarrationProvider(Protocol):
    """Layer-2 contract between the pipeline and a TTS provider adapter.

    A provider adapter is a **thin mapper only** — it translates a
    Director-produced :class:`~epub2audio.models.NarrationSegment` (with
    inherited scene defaults from :class:`~epub2audio.models.NarrationDirection`)
    into a :class:`ProviderRequest`, then executes the raw synthesis call.

    **No business logic belongs in an adapter.**  Scene analysis, dialogue
    detection, pacing decisions, and emphasis computation all live in the
    Director (Layer 1, ``director/``).  A provider adapter only:

    * maps plan fields to provider-specific controls (voice id, speed, SSML,
      instruction text, etc.);
    * applies pronunciation substitutions from the lexicon (Milestone 10);
    * optionally splits overly long text into sub-calls and concatenates the
      resulting :class:`~epub2audio.models.AudioChunk` objects;
    * makes the raw engine / HTTP call.

    **Adding a new provider = implementing this one interface.**  No changes
    to the Director, pipeline, or audio assembly are required.

    This Protocol is ``@runtime_checkable`` so
    ``isinstance(adapter, NarrationProvider)`` can be used in guard clauses
    and tests without importing concrete adapter classes.
    """

    def render(
        self,
        segment: NarrationSegment,
        defaults: NarrationDirection,
        settings: Settings,
    ) -> ProviderRequest:
        """Map one narration plan segment into a provider-specific request.

        The adapter resolves the effective delivery direction by falling back
        to ``defaults`` when ``segment.direction`` is ``None``, then derives
        provider-specific controls (voice, speed, payload) from the combined
        direction and ``settings``.

        Args:
            segment: One directed unit of narration from the
                :class:`~epub2audio.models.NarrationPlan`.
            defaults: Scene-level delivery instruction; used when the segment
                has no per-segment
                :attr:`~epub2audio.models.NarrationSegment.direction` override.
            settings: Application-wide settings supplying base ``voice``,
                ``language``, and ``speed``.

        Returns:
            A fully populated :class:`ProviderRequest` ready for
            :meth:`synthesize`.
        """
        ...  # pragma: no cover

    def synthesize(self, request: ProviderRequest) -> list[AudioChunk]:
        """Execute the raw synthesis call and return audio chunks in order.

        A provider MAY internally split text that exceeds the engine's
        maximum token length and concatenate the chunks from all sub-calls
        before returning.  The pipeline always receives a single ordered list.

        Args:
            request: The :class:`ProviderRequest` produced by :meth:`render`.

        Returns:
            One or more :class:`~epub2audio.models.AudioChunk` objects in
            reading order.  Callers must concatenate them to produce the
            complete audio for the segment.
        """
        ...  # pragma: no cover
