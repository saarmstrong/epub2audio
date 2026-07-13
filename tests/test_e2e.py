"""End-to-end pipeline test using FakeTTSEngine — no Kokoro required.

This test exercises the full conversion pipeline from an EPUB file to MP3
output files.  It is marked ``@pytest.mark.integration`` and skipped
automatically when FFmpeg is not available.

The test does NOT require Kokoro or any network access.  It uses
``FakeTTSEngine`` from ``tts/fake.py``, which produces deterministic silence
proportional to word count.

Imports of implementation modules are done inside each test function so that:
  - Collection always succeeds, even when modules are still stubs.
  - Failures are isolated: if ``tts.fake`` is a stub but another module is
    implemented, only this test file errors — not others.

# TODO(pending-impl): this test requires real implementations of:
#   - tts/fake.py  (FakeTTSEngine)
#   - pipeline/converter.py  (convert_epub)
#   - audio/validate.py  (validate_mp3)
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module-level availability probe — checked inside each test
# ---------------------------------------------------------------------------

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_convert_epub_produces_two_mp3s(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Full pipeline: EPUB → 2 validated MP3 files with correct names.

    The test verifies:
    1. Exactly 2 MP3 files are produced.
    2. Filenames are '001 - Chapter One.mp3' and '002 - Chapter Two.mp3'.
    3. Each MP3 passes validate_mp3 (FFprobe structural check).
    4. The returned ConversionReport has 2 ChapterResult entries with output_path set.
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.audio.validate import validate_mp3
    from epub2audio.config import Settings
    from epub2audio.models import ChapterResult, ConversionReport
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path)
    engine = FakeTTSEngine()
    report = convert_epub(simple_epub3_path, tmp_path, settings, engine)

    # 1. Exactly 2 MP3 files in output directory
    mp3_files = sorted(tmp_path.glob("*.mp3"))
    assert len(mp3_files) == 2, (
        f"Expected 2 MP3 files, found {len(mp3_files)}: {[f.name for f in mp3_files]}"
    )

    # 2. Correct filenames
    names = [f.name for f in mp3_files]
    assert "001 - Chapter One.mp3" in names, f"'001 - Chapter One.mp3' not found in {names}"
    assert "002 - Chapter Two.mp3" in names, f"'002 - Chapter Two.mp3' not found in {names}"

    # 3. Each MP3 passes FFprobe validation
    for mp3 in mp3_files:
        validate_mp3(mp3, expected_sample_rate=settings.sample_rate)

    # 4. ConversionReport has 2 entries with output_path set
    assert isinstance(report, ConversionReport), (
        f"convert_epub must return a ConversionReport, got {type(report)}"
    )
    assert len(report.chapter_results) == 2, (
        f"Expected 2 ChapterResult entries, got {len(report.chapter_results)}"
    )
    for result in report.chapter_results:
        assert isinstance(result, ChapterResult)
        assert result.output_path is not None, (
            f"ChapterResult.output_path must be set; got None for {result.chapter_id}"
        )
        assert Path(result.output_path).exists(), (
            f"output_path '{result.output_path}' does not exist on disk"
        )


@pytest.mark.integration
def test_convert_epub_mp3s_are_in_reading_order(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """MP3 filenames reflect spine reading order, not filename alphabetical order.

    The simple_epub3 fixture intentionally has 'a_chapter_02.xhtml' alphabetically
    before 'b_chapter_01.xhtml', so this test proves spine order is respected.
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path)
    convert_epub(simple_epub3_path, tmp_path, settings, FakeTTSEngine())

    mp3_files = sorted(tmp_path.glob("*.mp3"))
    assert len(mp3_files) == 2

    track1 = tmp_path / "001 - Chapter One.mp3"
    track2 = tmp_path / "002 - Chapter Two.mp3"
    assert track1.exists(), f"Track 1 not found; files: {[f.name for f in mp3_files]}"
    assert track2.exists(), f"Track 2 not found; files: {[f.name for f in mp3_files]}"


@pytest.mark.integration
def test_convert_epub_report_metadata(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """ConversionReport.book_metadata contains expected title and author."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path)
    report = convert_epub(simple_epub3_path, tmp_path, settings, FakeTTSEngine())

    assert report.book_metadata.title == "Test Book"
    assert report.book_metadata.author == "Test Author"


@pytest.mark.integration
def test_convert_epub_no_errors_in_report(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """ConversionReport.errors is empty on a clean conversion."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path)
    report = convert_epub(simple_epub3_path, tmp_path, settings, FakeTTSEngine())

    assert report.errors == [], f"Expected no errors in report, got: {report.errors}"


@pytest.mark.integration
def test_convert_epub_chapter_duration_positive(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Each ChapterResult has a positive duration (real audio was produced)."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path)
    report = convert_epub(simple_epub3_path, tmp_path, settings, FakeTTSEngine())

    for result in report.chapter_results:
        assert result.duration_seconds > 0, (
            f"Chapter {result.chapter_id} has zero/negative duration"
        )
