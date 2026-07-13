"""Unit tests for KokoroProvider render() mapping and synthesize() delegation.

Uses FakeTTSEngine throughout — no real Kokoro install required.
"""

from __future__ import annotations

import pytest

from epub2audio.config import Settings
from epub2audio.models import (
    EmphasisHint,
    NarrationDirection,
    NarrationSegment,
)
from epub2audio.providers.base import NarrationProvider, ProviderRequest
from epub2audio.providers.kokoro import KokoroProvider, _normalize_for_kokoro
from epub2audio.tts.fake import FakeTTSEngine

# ---------------------------------------------------------------------------
# Shared helpers / factories
# ---------------------------------------------------------------------------

_DEFAULTS = NarrationDirection(mood="calm and measured", pace=0.95, intensity=0.1)
_SETTINGS = Settings(voice="af_heart", language="en-us", speed=1.0)
_SETTINGS_FAST = Settings(voice="af_heart", language="en-us", speed=1.5)


def _seg(
    text: str = "The sky was dark.",
    *,
    seg_id: str = "ch001-sc01-seg0000-aabbccdd",
    pause_after_ms: int = 300,
    direction: NarrationDirection | None = None,
    pace: float = 0.95,
) -> NarrationSegment:
    return NarrationSegment(
        id=seg_id,
        type="narration",
        speaker="narrator",
        text=text,
        direction=direction,
        pause_after_ms=pause_after_ms,
        pace=pace,
        emphasis=[EmphasisHint(phrase="dark", level="light")],
        pronunciation_hints=[],
    )


def _provider() -> KokoroProvider:
    return KokoroProvider(FakeTTSEngine())


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_kokoro_provider_satisfies_narration_provider_protocol() -> None:
    assert isinstance(_provider(), NarrationProvider)


# ---------------------------------------------------------------------------
# render() — field mapping
# ---------------------------------------------------------------------------


def test_render_returns_provider_request() -> None:
    req = _provider().render(_seg(), _DEFAULTS, _SETTINGS)
    assert isinstance(req, ProviderRequest)


def test_render_segment_id_copied() -> None:
    seg = _seg(seg_id="ch004-sc02-seg0007-deadbeef")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert req.segment_id == "ch004-sc02-seg0007-deadbeef"


def test_render_voice_from_settings() -> None:
    settings = Settings(voice="af_sky", language="en-us", speed=1.0)
    req = _provider().render(_seg(), _DEFAULTS, settings)
    assert req.voice == "af_sky"


def test_render_language_from_settings() -> None:
    settings = Settings(voice="af_heart", language="en-gb", speed=1.0)
    req = _provider().render(_seg(), _DEFAULTS, settings)
    assert req.language == "en-gb"


def test_render_pause_after_ms_copied_from_segment() -> None:
    seg = _seg(pause_after_ms=700)
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert req.pause_after_ms == 700


def test_render_payload_is_empty_dict() -> None:
    req = _provider().render(_seg(), _DEFAULTS, _SETTINGS)
    assert req.payload == {}


# ---------------------------------------------------------------------------
# render() — speed mapping
# ---------------------------------------------------------------------------


def test_render_speed_inherits_defaults_pace_when_no_override() -> None:
    # segment.direction is None → use defaults.pace
    seg = _seg(direction=None)
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    expected = round(_DEFAULTS.pace * _SETTINGS.speed, 3)
    assert req.speed == expected


def test_render_speed_uses_segment_override_when_present() -> None:
    override = NarrationDirection(mood="tense and urgent", pace=1.1, intensity=0.7)
    seg = _seg(direction=override)
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    expected = round(override.pace * _SETTINGS.speed, 3)
    assert req.speed == expected


def test_render_speed_override_differs_from_defaults() -> None:
    # Sanity: the two paths produce different speeds for different paces.
    override = NarrationDirection(mood="urgent", pace=1.1, intensity=0.8)
    seg_override = _seg(direction=override)
    seg_default = _seg(direction=None)
    req_override = _provider().render(seg_override, _DEFAULTS, _SETTINGS)
    req_default = _provider().render(seg_default, _DEFAULTS, _SETTINGS)
    assert req_override.speed != req_default.speed


def test_render_speed_scales_with_settings_speed() -> None:
    seg = _seg(direction=None)
    req_normal = _provider().render(seg, _DEFAULTS, _SETTINGS)
    req_fast = _provider().render(seg, _DEFAULTS, _SETTINGS_FAST)
    assert req_fast.speed > req_normal.speed


def test_render_speed_clamped_to_max() -> None:
    # pace=4.0 × settings.speed=4.0 = 16.0 → clamped to 4.0
    extreme_dir = NarrationDirection(mood="extreme", pace=4.0, intensity=1.0)
    seg = _seg(direction=extreme_dir)
    extreme_settings = Settings(voice="af_heart", language="en-us", speed=4.0)
    req = _provider().render(seg, _DEFAULTS, extreme_settings)
    assert req.speed == 4.0


def test_render_speed_clamped_to_min() -> None:
    # pace=0.1 × settings.speed=0.1 → clamped to 0.25
    slow_dir = NarrationDirection(mood="glacial", pace=0.1, intensity=0.0)
    seg = _seg(direction=slow_dir)
    slow_settings = Settings(voice="af_heart", language="en-us", speed=0.25)
    req = _provider().render(seg, _DEFAULTS, slow_settings)
    assert req.speed == 0.25


# ---------------------------------------------------------------------------
# render() — punctuation / whitespace normalization (no prose rewriting)
# ---------------------------------------------------------------------------


def test_render_text_words_unchanged() -> None:
    """Core invariant: normalization must not alter word content."""
    source = "The rain  fell on  the  neon  street"
    seg = _seg(text=source)
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    # Strip the appended terminal period before comparing words.
    rendered_words = req.text.rstrip(".?!").split()
    source_words = source.split()
    assert rendered_words == source_words


def test_render_adds_trailing_period_when_missing() -> None:
    seg = _seg(text="The rain fell")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert req.text.endswith(".")


def test_render_does_not_duplicate_existing_period() -> None:
    seg = _seg(text="The rain fell.")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert not req.text.endswith("..")
    assert req.text.endswith(".")


def test_render_does_not_duplicate_question_mark() -> None:
    seg = _seg(text="Are you there?")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert req.text == "Are you there?"


def test_render_does_not_duplicate_exclamation() -> None:
    seg = _seg(text="Run now!")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert req.text == "Run now!"


def test_render_collapses_internal_whitespace() -> None:
    seg = _seg(text="The  rain\t\nfell.")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    assert "  " not in req.text
    assert "\t" not in req.text
    assert "\n" not in req.text


def test_render_no_ssml_or_engine_tokens_in_text() -> None:
    seg = _seg(text="He walked slowly into the room.")
    req = _provider().render(seg, _DEFAULTS, _SETTINGS)
    for tag in ("<speak", "<prosody", "<phoneme", "<emphasis"):
        assert tag not in req.text


# ---------------------------------------------------------------------------
# synthesize() — delegation to injected engine
# ---------------------------------------------------------------------------


def test_synthesize_returns_audio_chunks() -> None:
    provider = _provider()
    req = provider.render(_seg(), _DEFAULTS, _SETTINGS)
    chunks = provider.synthesize(req)
    assert len(chunks) >= 1


def test_synthesize_chunks_have_correct_sample_rate() -> None:
    provider = _provider()
    req = provider.render(_seg(), _DEFAULTS, _SETTINGS)
    chunks = provider.synthesize(req)
    assert all(c.sample_rate == 24_000 for c in chunks)


def test_synthesize_delegates_to_injected_engine() -> None:
    """synthesize() passes req.text/voice/language/speed to the engine."""
    from tests.pipeline.conftest import CountingFakeTTSEngine

    engine = CountingFakeTTSEngine()
    provider = KokoroProvider(engine)
    req = provider.render(_seg(text="Hello world."), _DEFAULTS, _SETTINGS)
    provider.synthesize(req)

    assert engine.call_count == 1
    call = engine.calls[0]
    assert call["text"] == req.text
    assert call["voice"] == req.voice
    assert call["language"] == req.language
    assert call["speed"] == req.speed


# ---------------------------------------------------------------------------
# _normalize_for_kokoro() — unit-level white-box tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hello world", "Hello world."),
        ("Hello world.", "Hello world."),
        ("Hello world?", "Hello world?"),
        ("Hello world!", "Hello world!"),
        ("Hello  world", "Hello world."),
        ("  leading and trailing  ", "leading and trailing."),
        ("", ""),
    ],
)
def test_normalize_for_kokoro(raw: str, expected: str) -> None:
    assert _normalize_for_kokoro(raw) == expected
