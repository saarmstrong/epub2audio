"""Provider-adapter package for epub2audio (Layer 2 of the narration pipeline).

This package defines the :class:`~epub2audio.providers.base.NarrationProvider`
Protocol and the :class:`~epub2audio.providers.base.ProviderRequest` model
(Layer-2 contract), together with stub adapters for future providers.

See ``docs/decisions/003-narration-pipeline.md`` for the three-layer architecture:

    Layer 1 — Director   (``director/``) — business logic, provider-neutral
    Layer 2 — Provider   (``providers/``) — mapping only: plan → provider controls
    Layer 3 — Engine     (``tts/``)        — raw model I/O

Usage::

    from epub2audio.providers import NarrationProvider, ProviderRequest
    from epub2audio.providers import KokoroProvider, build_kokoro_provider
    from epub2audio.providers import OpenAIProvider, GeminiProvider
    from epub2audio.providers import AzureProvider, ElevenLabsProvider
"""

from epub2audio.providers.azure import AzureProvider
from epub2audio.providers.base import NarrationProvider, ProviderRequest
from epub2audio.providers.elevenlabs import ElevenLabsProvider
from epub2audio.providers.gemini import GeminiProvider
from epub2audio.providers.kokoro import KokoroProvider, build_kokoro_provider
from epub2audio.providers.openai import OpenAIProvider

__all__ = [
    "AzureProvider",
    "ElevenLabsProvider",
    "GeminiProvider",
    "KokoroProvider",
    "NarrationProvider",
    "OpenAIProvider",
    "ProviderRequest",
    "build_kokoro_provider",
]
