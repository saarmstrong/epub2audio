"""Google Gemini TTS provider adapter stub for epub2audio.

This module defines the :class:`GeminiProvider` adapter, which will map
:class:`~epub2audio.providers.base.NarrationProvider` onto the Google Gemini
text-to-speech API.

**Mapping strategy (per ADR-003, §2 — "no business logic in providers")**:
Gemini, like OpenAI, supports natural-language narration instructions embedded
alongside the synthesis request.  When implemented, this adapter will derive
an instruction string from the segment's
:class:`~epub2audio.models.NarrationDirection` (mood, pace, intensity) and
store it in ``ProviderRequest.payload["instructions"]``.  No analysis or
rewriting is performed here; the direction values come entirely from the
Director.

**Current status**: stub only.  Both methods raise :exc:`NotImplementedError`.
No Google Gemini SDK dependency is introduced; this module uses only stdlib
and epub2audio's own models.
"""

from __future__ import annotations

from epub2audio.config import Settings
from epub2audio.models import AudioChunk, NarrationDirection, NarrationSegment
from epub2audio.providers.base import ProviderRequest


class GeminiProvider:
    """Stub Google Gemini TTS provider adapter.

    Structurally satisfies :class:`~epub2audio.providers.base.NarrationProvider`.
    Both methods raise :exc:`NotImplementedError` until the adapter is
    implemented in a future milestone.

    When implemented, this provider will:

    * Resolve the effective :class:`~epub2audio.models.NarrationDirection`
      (segment override or scene default).
    * Derive a natural-language narration instruction string from mood, pace,
      and intensity (similar to :class:`OpenAIProvider`, adapted to the
      Gemini API's prompt schema).
    * Set ``ProviderRequest.payload["instructions"]`` to that string.
    * Call the Gemini TTS API with the text and instructions, returning one
      or more :class:`~epub2audio.models.AudioChunk` objects.
    """

    def render(
        self,
        segment: NarrationSegment,
        defaults: NarrationDirection,
        settings: Settings,
    ) -> ProviderRequest:
        """Map a narration segment to a Gemini-specific provider request.

        Args:
            segment: One directed unit of narration from the plan.
            defaults: Scene-level delivery instruction.
            settings: Application-wide settings (voice, language, speed).

        Raises:
            NotImplementedError: Always — the Gemini adapter is not yet
                implemented.
        """
        raise NotImplementedError(
            "GeminiProvider.render() is not yet implemented. "
            "This stub proves the NarrationProvider interface; "
            "full implementation is planned for a future milestone."
        )

    def synthesize(self, request: ProviderRequest) -> list[AudioChunk]:
        """Call the Gemini TTS API and return audio chunks.

        Args:
            request: The :class:`~epub2audio.providers.base.ProviderRequest`
                produced by :meth:`render`.

        Raises:
            NotImplementedError: Always — the Gemini adapter is not yet
                implemented.
        """
        raise NotImplementedError(
            "GeminiProvider.synthesize() is not yet implemented. "
            "This stub proves the NarrationProvider interface; "
            "full implementation is planned for a future milestone."
        )
