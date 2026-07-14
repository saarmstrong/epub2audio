"""Tests for Settings fields added in Milestone 12.

Covers:
- output_format extended to include "both"
- provider field with kokoro-only validator
- scene_analysis bool flag
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from epub2audio.config import Settings

# ---------------------------------------------------------------------------
# output_format: "both"
# ---------------------------------------------------------------------------


class TestOutputFormatBoth:
    def test_both_accepted(self) -> None:
        s = Settings(output_format="both")
        assert s.output_format == "both"

    def test_both_case_normalized(self) -> None:
        s = Settings(output_format="BOTH")
        assert s.output_format == "both"

    def test_both_whitespace_normalized(self) -> None:
        s = Settings(output_format=" both ")
        assert s.output_format == "both"

    def test_mp3_still_accepted(self) -> None:
        assert Settings(output_format="mp3").output_format == "mp3"

    def test_m4b_still_accepted(self) -> None:
        assert Settings(output_format="m4b").output_format == "m4b"

    def test_default_is_mp3(self) -> None:
        assert Settings().output_format == "mp3"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(output_format="ogg")


# ---------------------------------------------------------------------------
# provider field
# ---------------------------------------------------------------------------


class TestProvider:
    def test_default_is_kokoro(self) -> None:
        assert Settings().provider == "kokoro"

    def test_kokoro_explicit(self) -> None:
        assert Settings(provider="kokoro").provider == "kokoro"

    def test_kokoro_case_normalized(self) -> None:
        assert Settings(provider="KOKORO").provider == "kokoro"

    def test_kokoro_whitespace_normalized(self) -> None:
        assert Settings(provider="  kokoro  ").provider == "kokoro"

    def test_unsupported_provider_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(provider="openai")
        # Error message should list supported providers
        error_text = str(exc_info.value)
        assert "kokoro" in error_text

    def test_unsupported_provider_message_mentions_stubs(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            Settings(provider="azure")
        error_text = str(exc_info.value)
        assert "not yet selectable" in error_text or "stubs" in error_text

    @pytest.mark.parametrize("bad_provider", ["openai", "gemini", "azure", "elevenlabs", "gpt4"])
    def test_unsupported_providers_all_raise(self, bad_provider: str) -> None:
        with pytest.raises(ValidationError):
            Settings(provider=bad_provider)


# ---------------------------------------------------------------------------
# scene_analysis field
# ---------------------------------------------------------------------------


class TestSceneAnalysis:
    def test_default_is_true(self) -> None:
        assert Settings().scene_analysis is True

    def test_false_accepted(self) -> None:
        assert Settings(scene_analysis=False).scene_analysis is False

    def test_true_explicit(self) -> None:
        assert Settings(scene_analysis=True).scene_analysis is True
