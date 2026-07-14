"""Tests for the four stub provider adapters.

Verifies that each stub structurally satisfies the NarrationProvider Protocol
but raises NotImplementedError from both render() and synthesize().
"""

from __future__ import annotations

import pytest

from epub2audio.config import Settings
from epub2audio.models import NarrationDirection, NarrationSegment
from epub2audio.providers.azure import AzureProvider
from epub2audio.providers.base import NarrationProvider, ProviderRequest
from epub2audio.providers.elevenlabs import ElevenLabsProvider
from epub2audio.providers.gemini import GeminiProvider
from epub2audio.providers.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_DEFAULTS = NarrationDirection(mood="neutral narration", pace=1.0, intensity=0.2)
_SETTINGS = Settings(voice="af_heart", language="en-us", speed=1.0)

_DUMMY_SEGMENT = NarrationSegment(
    id="ch001-sc01-seg0000-dummy",
    type="narration",
    speaker="narrator",
    text="The door swung open.",
    direction=None,
    pause_after_ms=300,
    pace=1.0,
    emphasis=[],
    pronunciation_hints=[],
)

_DUMMY_REQUEST = ProviderRequest(
    segment_id="ch001-sc01-seg0000-dummy",
    text="The door swung open.",
    voice="af_heart",
    language="en-us",
    speed=1.0,
    pause_after_ms=300,
    payload={},
)

# ---------------------------------------------------------------------------
# Parameterised test over all four stubs
# ---------------------------------------------------------------------------

_STUB_CLASSES = [OpenAIProvider, GeminiProvider, AzureProvider, ElevenLabsProvider]
_STUB_IDS = ["openai", "gemini", "azure", "elevenlabs"]


@pytest.mark.parametrize("cls", _STUB_CLASSES, ids=_STUB_IDS)
def test_stub_satisfies_narration_provider_protocol(cls: type) -> None:
    """Each stub class is structurally a NarrationProvider."""
    assert isinstance(cls(), NarrationProvider)


@pytest.mark.parametrize("cls", _STUB_CLASSES, ids=_STUB_IDS)
def test_stub_render_raises_not_implemented(cls: type) -> None:
    provider = cls()
    with pytest.raises(NotImplementedError):
        provider.render(_DUMMY_SEGMENT, _DEFAULTS, _SETTINGS)


@pytest.mark.parametrize("cls", _STUB_CLASSES, ids=_STUB_IDS)
def test_stub_synthesize_raises_not_implemented(cls: type) -> None:
    provider = cls()
    with pytest.raises(NotImplementedError):
        provider.synthesize(_DUMMY_REQUEST)


@pytest.mark.parametrize("cls", _STUB_CLASSES, ids=_STUB_IDS)
def test_stub_not_implemented_error_messages_are_informative(cls: type) -> None:
    """Error messages should say the adapter is not yet implemented (not a bare raise)."""
    provider = cls()
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        provider.render(_DUMMY_SEGMENT, _DEFAULTS, _SETTINGS)
