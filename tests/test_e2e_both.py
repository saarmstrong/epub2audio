"""End-to-end pipeline test for output_format='both' — no Kokoro required.

Exercises the full EPUB → MP3-per-chapter + single .m4b pass using
``FakeTTSEngine``.  Gated on FFmpeg/FFprobe.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.integration
def test_both_produces_mp3s_and_m4b(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """output_format='both' yields per-chapter MP3s AND a single .m4b in one run.

    Verifies:
    1. Both per-chapter .mp3 files exist with correct reading-order names.
    2. Exactly one .m4b file exists.
    3. ``ConversionReport.chapter_results[*].output_path`` each end in ``.mp3``.
    4. ``ConversionReport.output_path`` ends in ``.m4b``.
    5. ``ConversionReport.chapter_markers`` contains exactly 2 markers.
    6. No errors in the report.
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg/FFprobe not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_format="both")
    report = convert_epub(simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()))

    # 1. Per-chapter MP3s — correct names, correct count
    mp3_files = sorted(tmp_path.glob("*.mp3"))
    assert len(mp3_files) == 2, f"Expected 2 MP3s, got {[f.name for f in mp3_files]}"
    names = {f.name for f in mp3_files}
    assert "001 - Chapter One.mp3" in names
    assert "002 - Chapter Two.mp3" in names

    # 2. Exactly one .m4b
    m4b_files = list(tmp_path.glob("*.m4b"))
    assert len(m4b_files) == 1, f"Expected 1 M4B, got {[f.name for f in m4b_files]}"

    # 3. Per-chapter report output_paths point to .mp3 files that exist
    for result in report.chapter_results:
        assert result.output_path is not None, (
            f"{result.chapter_id}: output_path should not be None in 'both' mode"
        )
        assert result.output_path.endswith(".mp3"), (
            f"{result.chapter_id}: expected .mp3, got {result.output_path!r}"
        )
        assert Path(result.output_path).exists(), f"MP3 not on disk: {result.output_path!r}"

    # 4. Book-level output_path is the .m4b
    assert report.output_path is not None
    assert report.output_path.endswith(".m4b"), (
        f"report.output_path should be the .m4b, got {report.output_path!r}"
    )
    assert Path(report.output_path).exists()

    # 5. Two chapter markers
    assert len(report.chapter_markers) == 2
    markers = report.chapter_markers
    assert markers[0].start_ms == 0
    assert markers[0].end_ms == markers[1].start_ms  # contiguous
    assert [m.title for m in markers] == ["Chapter One", "Chapter Two"]

    # 6. No pipeline errors
    assert report.errors == [], f"Unexpected errors: {report.errors}"


@pytest.mark.integration
def test_both_audio_is_valid(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """All audio files produced in 'both' mode pass structural FFprobe validation."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg/FFprobe not available — skipping integration test")

    from epub2audio.audio.validate import validate_audio, validate_mp3
    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_format="both")
    report = convert_epub(simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()))

    # Each per-chapter MP3 passes mp3 validation
    for result in report.chapter_results:
        assert result.output_path is not None
        validate_mp3(Path(result.output_path), expected_sample_rate=settings.sample_rate)

    # The M4B passes AAC + chapter-count validation
    assert report.output_path is not None
    validate_audio(
        Path(report.output_path),
        expected_codec="aac",
        expected_sample_rate=settings.sample_rate,
        expected_chapters=2,
    )


@pytest.mark.integration
def test_both_validation_report_is_clean(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """validate_conversion on a 'both' run reports ok=True, error_count=0."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg/FFprobe not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.epub.reader import open_epub
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.pipeline.planner import plan_conversion
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine
    from epub2audio.validation import validate_conversion

    settings = Settings(output_format="both")
    plan = plan_conversion(open_epub(simple_epub3_path), settings)
    report = convert_epub(
        simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()), plan=plan
    )

    vr = validate_conversion(report, plan, settings, tmp_path)
    assert vr.ok is True, f"Expected ok=True; issues: {[(i.code, i.message) for i in vr.issues]}"
    assert vr.error_count == 0, f"Expected 0 errors; got: {vr.error_count}"


@pytest.mark.integration
def test_both_no_re_encoding_leaves_no_extra_work(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """A successful 'both' run cleans up the work directory."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg/FFprobe not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_format="both")
    convert_epub(simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()))

    assert not (tmp_path / ".epub2audio-work").exists(), (
        "Work directory should be cleaned up after a successful 'both' run"
    )
