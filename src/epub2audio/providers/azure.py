"""Azure Cognitive Services TTS provider adapter stub for epub2audio.

This module defines the :class:`AzureProvider` adapter, which will map
:class:`~epub2audio.providers.base.NarrationProvider` onto the Azure
Cognitive Services Text-to-Speech API (Azure TTS).

**Mapping strategy (per ADR-003, §2 — "no business logic in providers")**:
Azure TTS is controlled via SSML (Speech Synthesis Markup Language).  When
implemented, this adapter will translate the segment's
:class:`~epub2audio.models.NarrationDirection` (mood, pace, intensity) and
any :class:`~epub2audio.models.EmphasisHint` annotations into an SSML
document with appropriate ``<prosody>``, ``<emphasis>``, and ``<break>``
tags.  Pronunciation hints (Milestone 10) will be rendered as
``<phoneme>`` elements.  The SSML string is stored in
``ProviderRequest.payload["ssml"]``.

No analysis or rewriting is performed here; the direction and emphasis values
come entirely from the Director.

**Current status**: stub only.  Both methods raise :exc:`NotImplementedError`.
No Azure SDK dependency is introduced; this module uses only stdlib and
epub2audio's own models.
"""

from __future__ import annotations

from epub2audio.config import Settings
from epub2audio.models import AudioChunk, NarrationDirection, NarrationSegment
from epub2audio.providers.base import ProviderRequest


class AzureProvider:
    """Stub Azure Cognitive Services TTS provider adapter.

    Structurally satisfies :class:`~epub2audio.providers.base.NarrationProvider`.
    Both methods raise :exc:`NotImplementedError` until the adapter is
    implemented in a future milestone.

    When implemented, this provider will:

    * Resolve the effective :class:`~epub2audio.models.NarrationDirection`
      (segment override or scene default).
    * Map mood/pace/intensity to SSML ``<prosody>`` attributes (``rate``,
      ``pitch``, ``volume``).
    * Map :class:`~epub2audio.models.EmphasisHint` annotations to SSML
      ``<emphasis>`` elements with matching ``level`` attributes.
    * Map :class:`~epub2audio.models.PronunciationHint` terms to
      ``<phoneme>`` elements (Milestone 10).
    * Store the final SSML document string in
      ``ProviderRequest.payload["ssml"]``.
    * Call the Azure TTS API with the SSML, returning one or more
      :class:`~epub2audio.models.AudioChunk` objects.
    """

    def render(
        self,
        segment: NarrationSegment,
        defaults: NarrationDirection,
        settings: Settings,
    ) -> ProviderRequest:
        """Map a narration segment to an Azure SSML-based provider request.

        Args:
            segment: One directed unit of narration from the plan.
            defaults: Scene-level delivery instruction.
            settings: Application-wide settings (voice, language, speed).

        Raises:
            NotImplementedError: Always — the Azure adapter is not yet
                implemented.
        """
        raise NotImplementedError(
            "AzureProvider.render() is not yet implemented. "
            "This stub proves the NarrationProvider interface; "
            "full implementation is planned for a future milestone."
        )

    def synthesize(self, request: ProviderRequest) -> list[AudioChunk]:
        """Call the Azure TTS API with the SSML payload and return audio chunks.

        Args:
            request: The :class:`~epub2audio.providers.base.ProviderRequest`
                produced by :meth:`render`.  The SSML document is in
                ``request.payload["ssml"]``.

        Raises:
            NotImplementedError: Always — the Azure adapter is not yet
                implemented.
        """
        raise NotImplementedError(
            "AzureProvider.synthesize() is not yet implemented. "
            "This stub proves the NarrationProvider interface; "
            "full implementation is planned for a future milestone."
        )
