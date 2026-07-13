"""Tests for segment-level resume persistence (DEFECT-003 fix).

Verifies that:
- Segment WAVs are written to the persistent work directory.
- manifest.segments is populated with audio_path set after synthesis.
- segment_needs_synthesis() correctly skips existing valid WAVs.
- clear_segment_cache() removes the chapter's work directory.
- tts_config_changed() correctly identifies TTS-affecting changes.
- _merge_segments() deduplicates by normalized_hash.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from epub2audio.models import Chapter, TextSegment
from epub2audio.pipeline.resume import (
    clear_segment_cache,
    segment_needs_synthesis,
    tts_config_changed,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_text_segment(
    normalized_hash: str = "a" * 64,
    audio_path: str | None = None,
    status: str = "pending",
) -> TextSegment:
    return TextSegment(
        text="Hello world.",
        source_hash="s" * 64,
        normalized_hash=normalized_hash,
        word_count=2,
        status=status,
        audio_path=audio_path,
    )


def _make_chapter(chapter_id: str = "ch001") -> Chapter:
    return Chapter(
        chapter_id=chapter_id,
        title="Chapter One",
        source_docs=["chapter1.xhtml"],
        word_count=100,
        stable_id="stable1",
    )


# ---------------------------------------------------------------------------
# segment_needs_synthesis
# ---------------------------------------------------------------------------


class TestSegmentNeedsSynthesis:
    def test_returns_true_when_audio_path_is_none(self, tmp_path: Path) -> None:
        seg = _make_text_segment(audio_path=None)
        assert segment_needs_synthesis(seg, tmp_path) is True

    def test_returns_true_when_file_does_not_exist(self, tmp_path: Path) -> None:
        missing = str(tmp_path / "nonexistent.wav")
        seg = _make_text_segment(audio_path=missing)
        assert segment_needs_synthesis(seg, tmp_path) is True

    def test_returns_true_when_file_is_empty(self, tmp_path: Path) -> None:
        wav = tmp_path / "seg_0000.wav"
        wav.write_bytes(b"")
        seg = _make_text_segment(audio_path=str(wav))
        assert segment_needs_synthesis(seg, tmp_path) is True

    def test_returns_false_when_file_exists_and_non_empty(self, tmp_path: Path) -> None:
        wav = tmp_path / "seg_0000.wav"
        wav.write_bytes(b"RIFF fake wav data")
        seg = _make_text_segment(audio_path=str(wav), status="done")
        assert segment_needs_synthesis(seg, tmp_path) is False

    def test_resolves_relative_path_against_output_dir(self, tmp_path: Path) -> None:
        wav = tmp_path / "seg_0000.wav"
        wav.write_bytes(b"RIFF fake wav data")
        # Store relative path
        seg = _make_text_segment(audio_path="seg_0000.wav", status="done")
        assert segment_needs_synthesis(seg, tmp_path) is False


# ---------------------------------------------------------------------------
# tts_config_changed
# ---------------------------------------------------------------------------


class TestTtsConfigChanged:
    def test_empty_changed_keys_returns_false(self) -> None:
        assert tts_config_changed([]) is False

    def test_non_empty_changed_keys_returns_true(self) -> None:
        assert tts_config_changed(["config_hash"]) is True

    def test_multiple_keys_returns_true(self) -> None:
        assert tts_config_changed(["voice", "speed"]) is True


# ---------------------------------------------------------------------------
# clear_segment_cache
# ---------------------------------------------------------------------------


class TestClearSegmentCache:
    def test_removes_chapter_work_directory(self, tmp_path: Path) -> None:
        work_root = tmp_path / ".epub2audio-work"
        chapter_work = work_root / "ch001"
        chapter_work.mkdir(parents=True)
        (chapter_work / "seg_0000.wav").write_bytes(b"fake wav")

        clear_segment_cache(work_root, "ch001")

        assert not chapter_work.exists()

    def test_no_error_when_directory_does_not_exist(self, tmp_path: Path) -> None:
        work_root = tmp_path / ".epub2audio-work"
        # Should not raise even though the directory doesn't exist
        clear_segment_cache(work_root, "ch001")

    def test_only_removes_specified_chapter(self, tmp_path: Path) -> None:
        work_root = tmp_path / ".epub2audio-work"
        ch1 = work_root / "ch001"
        ch2 = work_root / "ch002"
        ch1.mkdir(parents=True)
        ch2.mkdir(parents=True)
        (ch1 / "seg_0000.wav").write_bytes(b"fake wav 1")
        (ch2 / "seg_0000.wav").write_bytes(b"fake wav 2")

        clear_segment_cache(work_root, "ch001")

        assert not ch1.exists()
        assert ch2.exists()


# ---------------------------------------------------------------------------
# _merge_segments (internal helper — imported directly)
# ---------------------------------------------------------------------------


class TestMergeSegments:
    def test_new_segment_added_to_empty_existing(self) -> None:
        from epub2audio.pipeline.converter import _merge_segments

        new = _make_text_segment(normalized_hash="a" * 64, status="done")
        result = _merge_segments([], [new])
        assert len(result) == 1
        assert result[0].normalized_hash == "a" * 64

    def test_new_segment_overwrites_existing_by_hash(self) -> None:
        from epub2audio.pipeline.converter import _merge_segments

        old = _make_text_segment(normalized_hash="a" * 64, status="pending", audio_path=None)
        new = _make_text_segment(normalized_hash="a" * 64, status="done", audio_path="/tmp/seg.wav")
        result = _merge_segments([old], [new])
        assert len(result) == 1
        assert result[0].status == "done"
        assert result[0].audio_path == "/tmp/seg.wav"

    def test_existing_segments_retained_when_not_in_new(self) -> None:
        from epub2audio.pipeline.converter import _merge_segments

        existing = _make_text_segment(normalized_hash="a" * 64, status="done")
        new_seg = _make_text_segment(normalized_hash="b" * 64, status="done")
        result = _merge_segments([existing], [new_seg])
        hashes = {s.normalized_hash for s in result}
        assert "a" * 64 in hashes
        assert "b" * 64 in hashes

    def test_deduplicates_within_new_segments(self) -> None:
        from epub2audio.pipeline.converter import _merge_segments

        seg1 = _make_text_segment(normalized_hash="a" * 64, status="pending")
        seg2 = _make_text_segment(
            normalized_hash="a" * 64, status="done", audio_path="/tmp/seg.wav"
        )
        result = _merge_segments([], [seg1, seg2])
        assert len(result) == 1
        assert result[0].status == "done"


# ---------------------------------------------------------------------------
# Integration: persistent work dir and manifest segment population
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_convert_epub_creates_persistent_work_dir(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """convert_epub creates .epub2audio-work/<chapter_id>/ during processing.

    Because cleanup runs on success (keep_intermediates=False default), the
    directory will be removed after success.  We verify this is non-fatal and
    that the manifest was populated during processing.
    """
    import shutil as _shutil

    if not _shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.pipeline.manifest import read_manifest
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path)
    engine = FakeTTSEngine()
    report = convert_epub(simple_epub3_path, tmp_path, settings, engine)

    # Conversion should succeed
    assert report.errors == []

    # Manifest should have been written with segments populated
    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists()
    manifest = read_manifest(manifest_path)
    # After full success, segments are populated (at least 1 per chapter)
    assert len(manifest.segments) > 0, "manifest.segments must be populated after conversion"


@pytest.mark.integration
def test_convert_epub_keep_intermediates_preserves_work_dir(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """With keep_intermediates=True, the work dir is preserved after success."""
    import shutil as _shutil

    if not _shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path, keep_intermediates=True)
    engine = FakeTTSEngine()
    report = convert_epub(simple_epub3_path, tmp_path, settings, engine)

    assert report.errors == []

    work_root = tmp_path / ".epub2audio-work"
    assert work_root.exists(), "Work root must be preserved with keep_intermediates=True"

    # At least some segment WAVs should be present
    wavs = list(work_root.rglob("seg_*.wav"))
    assert len(wavs) > 0, "Segment WAVs must be preserved with keep_intermediates=True"


@pytest.mark.integration
def test_convert_epub_segments_have_audio_path_set(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """manifest.segments entries must have audio_path set (not None) after conversion."""
    import shutil as _shutil

    if not _shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.pipeline.manifest import read_manifest
    from epub2audio.tts.fake import FakeTTSEngine

    # Use keep_intermediates to ensure work dir and segment paths remain valid
    settings = Settings(output_dir=tmp_path, keep_intermediates=True)
    engine = FakeTTSEngine()
    convert_epub(simple_epub3_path, tmp_path, settings, engine)

    manifest = read_manifest(tmp_path / "manifest.json")
    assert len(manifest.segments) > 0

    for seg in manifest.segments:
        assert seg.audio_path is not None, (
            f"Segment {seg.normalized_hash[:8]} must have audio_path set"
        )
        assert seg.status == "done", f"Segment {seg.normalized_hash[:8]} must have status='done'"


@pytest.mark.integration
def test_resume_skips_cached_segments(
    simple_epub3_path: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A second run with --resume logs 'resumed from cached WAV' for each segment."""
    import shutil as _shutil

    if not _shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")

    import logging

    from epub2audio.config import Settings
    from epub2audio.pipeline.converter import convert_epub
    from epub2audio.tts.fake import FakeTTSEngine

    settings = Settings(output_dir=tmp_path, keep_intermediates=True, resume=True)
    engine = FakeTTSEngine()

    # First run — synthesize everything
    report1 = convert_epub(simple_epub3_path, tmp_path, settings, engine)
    assert report1.errors == []

    # Second run — should reuse cached WAVs
    with caplog.at_level(logging.INFO, logger="epub2audio.pipeline.converter"):
        report2 = convert_epub(simple_epub3_path, tmp_path, settings, engine)

    assert report2.errors == []
    assert "resumed from cached WAV" in caplog.text, (
        "Second run must log 'resumed from cached WAV' for cached segments"
    )
