"""Integration test: Director → KokoroProvider drives the full pipeline.

This test verifies that the three-layer pipeline (Director → KokoroProvider
→ FakeTTSEngine) produces valid per-chapter MP3 output end-to-end.

Skipped automatically when FFmpeg is not available (identical pattern to the
existing tests/test_e2e.py tests).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


@pytest.mark.integration
def test_provider_pipeline_produces_mp3s(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """convert_epub with KokoroProvider(FakeTTSEngine) produces per-chapter MP3s.

    Asserts:
    - Exactly 2 MP3 files created (one per chapter).
    - Report has no errors.
    - Each ChapterResult has a positive duration (real audio encoded).
    - Each chapter output_path exists on disk.
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path, output_format="mp3")
    provider = KokoroProvider(FakeTTSEngine())
    report = convert_epub(simple_epub3_path, tmp_path, settings, provider)

    # Output files
    mp3_files = sorted(tmp_path.glob("*.mp3"))
    assert len(mp3_files) == 2, (
        f"Expected 2 MP3 files, got {len(mp3_files)}: {[f.name for f in mp3_files]}"
    )

    # No pipeline errors
    assert report.errors == [], f"Unexpected errors: {report.errors}"

    # Each chapter has positive duration and an existing output file
    assert len(report.chapter_results) == 2
    for result in report.chapter_results:
        assert result.output_path is not None, f"Chapter {result.chapter_id}: output_path is None"
        assert Path(result.output_path).exists(), (
            f"Chapter {result.chapter_id}: {result.output_path!r} does not exist"
        )
        assert result.duration_seconds > 0, (
            f"Chapter {result.chapter_id}: duration is {result.duration_seconds}"
        )


@pytest.mark.integration
def test_provider_pipeline_director_routes_text_not_empty(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """The Director must produce at least one narration segment per chapter.

    Uses a counting engine so we can assert that synthesis was actually called
    (proving the Director produced segments that were sent to the provider).
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from tests.pipeline.conftest import CountingFakeTTSEngine

    engine = CountingFakeTTSEngine()
    provider = KokoroProvider(engine)
    settings = Settings(output_dir=tmp_path, output_format="mp3")
    convert_epub(simple_epub3_path, tmp_path, settings, provider)

    assert engine.call_count > 0, (
        "Expected at least one synthesize() call — Director produced no segments"
    )


@pytest.mark.integration
def test_provider_pipeline_request_text_no_ssml(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Every text string sent to the engine must be SSML-free (provider-neutral contract).

    Captures all synthesize() calls via CountingFakeTTSEngine and asserts none
    of the text arguments contain SSML tags.
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from tests.pipeline.conftest import CountingFakeTTSEngine

    engine = CountingFakeTTSEngine()
    provider = KokoroProvider(engine)
    settings = Settings(output_dir=tmp_path, output_format="mp3")
    convert_epub(simple_epub3_path, tmp_path, settings, provider)

    for call in engine.calls:
        text = call["text"]
        for tag in ("<speak", "<prosody", "<phoneme", "<emphasis"):
            assert tag not in text, f"SSML tag {tag!r} found in synthesized text: {text[:100]!r}"


@pytest.mark.integration
def test_provider_pipeline_report_metadata(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """ConversionReport carries correct book metadata through the provider pipeline."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path, output_format="mp3")
    report = convert_epub(simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()))

    assert report.book_metadata.title == "Test Book"
    assert report.book_metadata.author == "Test Author"
