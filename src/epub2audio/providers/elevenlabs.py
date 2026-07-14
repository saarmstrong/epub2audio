"""ElevenLabs TTS provider adapter stub for epub2audio.

This module defines the :class:`ElevenLabsProvider` adapter, which will map
:class:`~epub2audio.providers.base.NarrationProvider` onto the ElevenLabs
text-to-speech API.

**Mapping strategy (per ADR-003, §2 — "no business logic in providers")**:
ElevenLabs exposes per-request voice settings (stability, similarity boost,
style exaggeration) and an optional voice prompting / acting instruction field.
When implemented, this adapter will:

* Map :class:`~epub2audio.models.NarrationDirection` pace and intensity to
  ElevenLabs ``voice_settings`` (``stability``, ``similarity_boost``,
  ``style``).
* Derive an optional textual acting prompt from the direction's mood and
  store it in ``ProviderRequest.payload["prompt"]`` when intensity is high
  enough to warrant it.
* Store the ``voice_settings`` dict in
  ``ProviderRequest.payload["voice_settings"]``.

No analysis or rewriting is performed here; the direction values come entirely
from the Director.

**Current status**: stub only.  Both methods raise :exc:`NotImplementedError`.
No ElevenLabs SDK dependency is introduced; this module uses only stdlib and
epub2audio's own models.
"""

from __future__ import annotations

from epub2audio.config import Settings
from epub2audio.models import AudioChunk, NarrationDirection, NarrationSegment
from epub2audio.providers.base import ProviderRequest


class ElevenLabsProvider:
    """Stub ElevenLabs TTS provider adapter.

    Structurally satisfies :class:`~epub2audio.providers.base.NarrationProvider`.
    Both methods raise :exc:`NotImplementedError` until the adapter is
    implemented in a future milestone.

    When implemented, this provider will:

    * Resolve the effective :class:`~epub2audio.models.NarrationDirection`
      (segment override or scene default).
    * Map pace to ElevenLabs ``stability`` and ``similarity_boost`` values
      (slower/calmer pace → higher stability).
    * Map intensity to ``style`` exaggeration (higher intensity → more
      expressive style).
    * Optionally derive a short acting-instruction prompt from mood and store
      it in ``ProviderRequest.payload["prompt"]``.
    * Store all voice settings in
      ``ProviderRequest.payload["voice_settings"]``.
    * Call the ElevenLabs TTS API, returning one or more
      :class:`~epub2audio.models.AudioChunk` objects.
    """

    def render(
        self,
        segment: NarrationSegment,
        defaults: NarrationDirection,
        settings: Settings,
    ) -> ProviderRequest:
        """Map a narration segment to an ElevenLabs-specific provider request.

        Args:
            segment: One directed unit of narration from the plan.
            defaults: Scene-level delivery instruction.
            settings: Application-wide settings (voice, language, speed).

        Raises:
            NotImplementedError: Always — the ElevenLabs adapter is not yet
                implemented.
        """
        raise NotImplementedError(
            "ElevenLabsProvider.render() is not yet implemented. "
            "This stub proves the NarrationProvider interface; "
            "full implementation is planned for a future milestone."
        )

    def synthesize(self, request: ProviderRequest) -> list[AudioChunk]:
        """Call the ElevenLabs TTS API and return audio chunks.

        Args:
            request: The :class:`~epub2audio.providers.base.ProviderRequest`
                produced by :meth:`render`.  Voice settings are in
                ``request.payload["voice_settings"]``.

        Raises:
            NotImplementedError: Always — the ElevenLabs adapter is not yet
                implemented.
        """
        raise NotImplementedError(
            "ElevenLabsProvider.synthesize() is not yet implemented. "
            "This stub proves the NarrationProvider interface; "
            "full implementation is planned for a future milestone."
        )
