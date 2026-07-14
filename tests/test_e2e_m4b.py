"""End-to-end M4B pipeline test using FakeTTSEngine — no Kokoro required.

Exercises the full EPUB -> single .m4b conversion.  Marked
``@pytest.mark.integration`` and skipped automatically when FFmpeg/FFprobe is
not available.  Uses ``FakeTTSEngine`` (deterministic silence), no network.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.integration
def test_convert_epub_produces_single_m4b(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Full pipeline with output_format='m4b' yields one validated .m4b.

    Verifies:
    1. Exactly one .m4b file and zero .mp3 files are produced.
    2. The report carries the m4b output_path and two chapter markers.
    3. Chapter markers are contiguous and in reading order.
    4. The .m4b passes AAC + chapter-count validation via FFprobe.
    """
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg/FFprobe not available — skipping integration test")

    from epub2audio.audio.validate import validate_audio
    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path, output_format="m4b")
    report = convert_epub(simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()))

    # 1. One .m4b, no per-chapter .mp3
    m4b_files = sorted(tmp_path.glob("*.m4b"))
    assert len(m4b_files) == 1, f"Expected one .m4b, found {[f.name for f in m4b_files]}"
    assert list(tmp_path.glob("*.mp3")) == []

    # 2. Report references the single artifact + two markers
    assert report.output_path is not None
    assert Path(report.output_path).exists()
    assert Path(report.output_path) == m4b_files[0]
    assert len(report.chapter_markers) == 2
    # Per-chapter output_path is None in M4B mode (audio lives in the one file).
    assert all(r.output_path is None for r in report.chapter_results)
    assert report.errors == []

    # 3. Markers are contiguous, ordered, and reflect reading order
    m = report.chapter_markers
    assert m[0].start_ms == 0
    assert m[0].end_ms == m[1].start_ms
    assert m[1].end_ms > m[1].start_ms
    assert [marker.title for marker in m] == ["Chapter One", "Chapter Two"]

    # 4. Structural validation of the container
    validate_audio(
        m4b_files[0],
        expected_codec="aac",
        expected_sample_rate=settings.sample_rate,
        expected_chapters=2,
    )


@pytest.mark.integration
def test_m4b_run_leaves_no_work_dir(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """A successful M4B run cleans up the per-chapter work directory."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg/FFprobe not available — skipping integration test")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.providers.kokoro import KokoroProvider
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path, output_format="m4b")
    convert_epub(simple_epub3_path, tmp_path, settings, KokoroProvider(FakeTTSEngine()))

    assert not (tmp_path / ".epub2audio-work").exists()
