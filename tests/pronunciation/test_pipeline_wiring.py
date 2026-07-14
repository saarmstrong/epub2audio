"""End-to-end wiring test for the pronunciation dictionary.

This is the regression guard for the M10 blocker: a configured
``pronunciation_dictionary`` must actually reach the synthesis engine.  It
proves the full chain — ``Settings.pronunciation_dictionary`` → converter
``load_lexicon`` → Director hint emission → Kokoro adapter respelling
substitution → text passed to the engine — is connected.

The test captures the text handed to the engine by a spy wrapped in a real
``KokoroProvider``, so it exercises the production render path (not a mock of
it).  It is gated on FFmpeg because ``convert_epub`` encodes audio.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from epub2audio.config import Settings
from epub2audio.models import AudioChunk
from epub2audio.pipeline.converter import convert_epub
from epub2audio.providers.kokoro import KokoroProvider
from epub2audio.tts.fake import FakeTTSEngine
from tests.fixtures.builders import build_simple_epub3

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="FFmpeg is required to run convert_epub end-to-end",
)


class _TextCapturingEngine:
    """A TTS engine spy that records every text it is asked to synthesize.

    Delegates the actual (silent) synthesis to :class:`FakeTTSEngine` so the
    pipeline still produces valid audio.
    """

    def __init__(self) -> None:
        self.texts: list[str] = []
        self._delegate = FakeTTSEngine()

    def synthesize(self, text: str, *, voice: str, language: str, speed: float) -> list[AudioChunk]:
        self.texts.append(text)
        return self._delegate.synthesize(text, voice=voice, language=language, speed=speed)


def _write_lexicon(path: Path) -> None:
    path.write_text(
        'pronunciations:\n  Ono-Sendai:\n    respelling: "Oh-no Sen-DYE"\n',
        encoding="utf-8",
    )


def test_configured_dictionary_reaches_engine(tmp_path: Path) -> None:
    """A configured dictionary rewrites the term in the text sent to the engine."""
    epub_path = build_simple_epub3(
        tmp_path / "book.epub",
        chapters=[("Chapter One", "Case jacked into the Ono-Sendai deck.")],
    )
    lexicon_path = tmp_path / "pronunciations.yaml"
    _write_lexicon(lexicon_path)

    engine = _TextCapturingEngine()
    provider = KokoroProvider(engine)
    settings = Settings(pronunciation_dictionary=lexicon_path)

    convert_epub(epub_path, tmp_path / "out", settings, provider)

    joined = " ".join(engine.texts)
    assert "Oh-no Sen-DYE" in joined, f"respelling not applied; got: {engine.texts!r}"
    assert "Ono-Sendai" not in joined, f"original term leaked; got: {engine.texts!r}"


def test_without_dictionary_term_is_untouched(tmp_path: Path) -> None:
    """With no dictionary configured, the original text reaches the engine verbatim."""
    epub_path = build_simple_epub3(
        tmp_path / "book.epub",
        chapters=[("Chapter One", "Case jacked into the Ono-Sendai deck.")],
    )

    engine = _TextCapturingEngine()
    provider = KokoroProvider(engine)
    settings = Settings()  # no pronunciation_dictionary

    convert_epub(epub_path, tmp_path / "out", settings, provider)

    joined = " ".join(engine.texts)
    assert "Ono-Sendai" in joined
    assert "Oh-no Sen-DYE" not in joined
