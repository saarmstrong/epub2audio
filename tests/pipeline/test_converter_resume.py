"""Integration tests for the converter's segment-level resume behaviour.

All tests in this module require FFmpeg (``concatenate_wavs``, ``encode_mp3``,
``validate_mp3``) and are guarded with a ``pytest.skip`` when FFmpeg is absent.
Tests are also tagged ``@pytest.mark.integration`` so they can be selected or
excluded explicitly.

Scenario coverage
-----------------
1. A second ``convert_epub`` call with ``resume=True`` and unchanged settings
   skips synthesis for all cached segments (TTS call count == 0 on second run).
2. Segment WAV ``mtime`` values are unchanged on a resumed run, confirming the
   files were not re-written.
3. The persistent work directory is removed after a fully successful conversion
   (``keep_intermediates=False``, the default).
4. The work directory is preserved when ``keep_intermediates=True``.
5. A voice change between runs clears the segment cache and causes full
   re-synthesis (TTS call count on second run == first run count).
6. A speed change between runs causes full re-synthesis.
7. [xfail] A bitrate-only change should *not* invalidate segment WAVs.
   Currently fails because the conservative implementation clears the cache for
   any config change.  See ``_TTS_AFFECTING_KEYS`` / ``_ENCODE_AFFECTING_KEYS``
   in ``resume.py`` for the planned two-tier invalidation refinement.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from epub2audio.config import Settings
from epub2audio.pipeline.converter import convert_epub
from epub2audio.tts.fake import FakeTTSEngine

# CountingFakeTTSEngine is defined in tests/pipeline/conftest.py but we
# instantiate it directly here for tests that need two independent instances.
from tests.pipeline.conftest import CountingFakeTTSEngine

# ---------------------------------------------------------------------------
# Module-level skip guard
# ---------------------------------------------------------------------------

_FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))


def _skip_no_ffmpeg() -> None:
    """Call at the top of each test to skip when FFmpeg is not installed."""
    if not _FFMPEG_AVAILABLE:
        pytest.skip("FFmpeg not available — cannot run converter integration test")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _default_settings(tmp_path: Path, **overrides: object) -> Settings:
    """Return Settings with output_dir=tmp_path and any keyword overrides applied."""
    return Settings(output_dir=tmp_path, **overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Resume: skipping cached segments
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_resume_skips_completed_segments(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """A second ``convert_epub`` run with resume=True makes zero TTS calls.

    First run synthesizes all segments (call_count > 0).  Second run with the
    same settings and ``keep_intermediates=True`` (so WAVs are on disk) must
    not call ``synthesize()`` at all — every segment should be resumed from the
    cached WAV.
    """
    _skip_no_ffmpeg()

    # First run — synthesize everything, preserve WAVs
    engine1 = CountingFakeTTSEngine()
    settings = _default_settings(tmp_path, keep_intermediates=True, resume=True)
    report1 = convert_epub(simple_epub3_path, tmp_path, settings, engine1)
    assert report1.errors == [], f"First run had errors: {report1.errors}"
    assert engine1.call_count > 0, "First run should synthesize at least one segment"

    first_run_calls = engine1.call_count

    # Second run — everything cached, no synthesis expected
    engine2 = CountingFakeTTSEngine()
    report2 = convert_epub(simple_epub3_path, tmp_path, settings, engine2)
    assert report2.errors == [], f"Second run had errors: {report2.errors}"
    assert engine2.call_count == 0, (
        f"Second run (resume) should synthesize 0 segments, "
        f"but synthesized {engine2.call_count} "
        f"(first run had {first_run_calls})"
    )


@pytest.mark.integration
def test_resume_reuses_segment_wavs_without_modifying_them(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Segment WAV files are not modified on a resumed run.

    After the first run, we record the ``mtime`` of each segment WAV.  The
    second run must leave those files untouched (same mtime).
    """
    _skip_no_ffmpeg()

    settings = _default_settings(tmp_path, keep_intermediates=True, resume=True)
    engine = FakeTTSEngine()

    # First run
    report1 = convert_epub(simple_epub3_path, tmp_path, settings, engine)
    assert report1.errors == []

    work_root = tmp_path / ".epub2audio-work"
    seg_wavs = sorted(work_root.rglob("seg_*.wav"))
    assert seg_wavs, "Expected at least one segment WAV after first run"

    # Record mtimes
    mtimes_before = {p: p.stat().st_mtime for p in seg_wavs}

    # Second run
    report2 = convert_epub(simple_epub3_path, tmp_path, settings, engine)
    assert report2.errors == []

    for wav_path in seg_wavs:
        assert wav_path.exists(), f"Segment WAV disappeared on resume: {wav_path}"
        assert wav_path.stat().st_mtime == mtimes_before[wav_path], (
            f"Segment WAV was modified on resume: {wav_path}"
        )


# ---------------------------------------------------------------------------
# Work-directory lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_full_conversion_cleans_work_dir(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """The persistent work directory is removed after a fully successful conversion.

    Default behaviour (``keep_intermediates=False``): once all chapters convert
    successfully, ``<output_dir>/.epub2audio-work/`` must be deleted.
    """
    _skip_no_ffmpeg()

    settings = _default_settings(tmp_path, keep_intermediates=False)
    engine = FakeTTSEngine()

    report = convert_epub(simple_epub3_path, tmp_path, settings, engine)
    assert report.errors == []

    work_root = tmp_path / ".epub2audio-work"
    assert not work_root.exists(), (
        f"Work root should be removed after full success, but {work_root} still exists"
    )


@pytest.mark.integration
def test_keep_intermediates_preserves_work_dir(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Work directory and segment WAVs are preserved when ``keep_intermediates=True``.

    The work root and per-chapter subdirectories must survive after a successful
    run so that the user can inspect or re-use the WAVs.
    """
    _skip_no_ffmpeg()

    settings = _default_settings(tmp_path, keep_intermediates=True)
    engine = FakeTTSEngine()

    report = convert_epub(simple_epub3_path, tmp_path, settings, engine)
    assert report.errors == []

    work_root = tmp_path / ".epub2audio-work"
    assert work_root.exists(), "Work root must be preserved with keep_intermediates=True"

    seg_wavs = list(work_root.rglob("seg_*.wav"))
    assert len(seg_wavs) > 0, (
        "Segment WAVs must be preserved with keep_intermediates=True, found none"
    )


# ---------------------------------------------------------------------------
# Config change invalidation
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_voice_change_invalidates_segments(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Changing the voice between runs causes full re-synthesis of all segments.

    Voice is a TTS-affecting setting.  Any cached segment WAVs from the first
    run must be discarded so the new voice is used for every segment.
    """
    _skip_no_ffmpeg()

    # First run with voice=af_heart
    engine1 = CountingFakeTTSEngine()
    s1 = _default_settings(tmp_path, voice="af_heart", keep_intermediates=True, resume=True)
    report1 = convert_epub(simple_epub3_path, tmp_path, s1, engine1)
    assert report1.errors == []
    first_run_calls = engine1.call_count
    assert first_run_calls > 0, "First run must synthesize at least one segment"

    # Second run with voice=af_bella (different voice — TTS-affecting change)
    engine2 = CountingFakeTTSEngine()
    s2 = _default_settings(tmp_path, voice="af_bella", keep_intermediates=True, resume=True)
    report2 = convert_epub(simple_epub3_path, tmp_path, s2, engine2)
    assert report2.errors == []

    assert engine2.call_count == first_run_calls, (
        f"Voice change must cause full re-synthesis: "
        f"expected {first_run_calls} calls but got {engine2.call_count}"
    )


@pytest.mark.integration
def test_speed_change_invalidates_segments(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """Changing the speed between runs causes full re-synthesis of all segments.

    Speed is a TTS-affecting setting.  Cached WAVs from the first run must be
    discarded so all segments are re-synthesized at the new speed.
    """
    _skip_no_ffmpeg()

    # First run at speed=1.0
    engine1 = CountingFakeTTSEngine()
    s1 = _default_settings(tmp_path, speed=1.0, keep_intermediates=True, resume=True)
    report1 = convert_epub(simple_epub3_path, tmp_path, s1, engine1)
    assert report1.errors == []
    first_run_calls = engine1.call_count
    assert first_run_calls > 0

    # Second run at speed=1.25 (TTS-affecting change)
    engine2 = CountingFakeTTSEngine()
    s2 = _default_settings(tmp_path, speed=1.25, keep_intermediates=True, resume=True)
    report2 = convert_epub(simple_epub3_path, tmp_path, s2, engine2)
    assert report2.errors == []

    assert engine2.call_count == first_run_calls, (
        f"Speed change must cause full re-synthesis: "
        f"expected {first_run_calls} calls but got {engine2.call_count}"
    )


@pytest.mark.integration
@pytest.mark.xfail(
    reason=(
        "Two-tier invalidation not yet implemented. "
        "The manifest stores a config hash, not a snapshot, so check_resume() "
        "cannot distinguish a TTS-affecting change (voice, speed) from an "
        "encoding-only change (bitrate, sample_rate). "
        "Any config change currently clears ALL segment WAVs. "
        "See _TTS_AFFECTING_KEYS / _ENCODE_AFFECTING_KEYS in resume.py "
        "for the planned refinement."
    ),
    strict=False,
)
def test_bitrate_change_keeps_segments(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """DESIRED (not yet implemented): Bitrate changes must NOT invalidate segment WAVs.

    Bitrate is an encoding-only setting — it affects only the final MP3 encode
    step, not TTS synthesis.  When this is properly implemented, a bitrate
    change should leave segment WAVs intact and re-run only the encode step.
    """
    _skip_no_ffmpeg()

    # First run at bitrate=96k
    engine1 = CountingFakeTTSEngine()
    s1 = _default_settings(tmp_path, bitrate="96k", keep_intermediates=True, resume=True)
    report1 = convert_epub(simple_epub3_path, tmp_path, s1, engine1)
    assert report1.errors == []
    first_run_calls = engine1.call_count
    assert first_run_calls > 0

    # Second run at bitrate=128k — only MP3 encoding should re-run, not TTS
    engine2 = CountingFakeTTSEngine()
    s2 = _default_settings(tmp_path, bitrate="128k", keep_intermediates=True, resume=True)
    report2 = convert_epub(simple_epub3_path, tmp_path, s2, engine2)
    assert report2.errors == []

    # Once two-tier invalidation is implemented, TTS call count should be 0
    assert engine2.call_count == 0, (
        f"Bitrate-only change must NOT cause TTS re-synthesis, "
        f"but {engine2.call_count} segments were re-synthesized"
    )


# ---------------------------------------------------------------------------
# Segment population in the manifest
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_manifest_segments_populated_with_audio_path(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """After conversion, every manifest segment has ``audio_path`` set and ``status='done'``.

    Verifies D2 (manifest segment population) from the DEFECT-003 fix.
    """
    _skip_no_ffmpeg()

    from epub2audio.pipeline.manifest import read_manifest

    settings = _default_settings(tmp_path, keep_intermediates=True)
    engine = FakeTTSEngine()

    report = convert_epub(simple_epub3_path, tmp_path, settings, engine)
    assert report.errors == []

    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists(), "manifest.json must be written after conversion"
    manifest = read_manifest(manifest_path)

    assert len(manifest.segments) > 0, "manifest.segments must be non-empty after conversion"
    for seg in manifest.segments:
        assert seg.audio_path is not None, (
            f"Segment {seg.normalized_hash[:8]}… has audio_path=None after conversion"
        )
        assert seg.status == "done", (
            f"Segment {seg.normalized_hash[:8]}… has status={seg.status!r}, expected 'done'"
        )


@pytest.mark.integration
def test_manifest_cleared_segment_cache_on_config_change(
    simple_epub3_path: Path,
    tmp_path: Path,
) -> None:
    """After a config change, manifest.segments is reset to [] before re-synthesis.

    The converter must clear the segment list when a TTS-affecting config
    change is detected, then re-populate it after synthesis.
    """
    _skip_no_ffmpeg()

    from epub2audio.pipeline.manifest import read_manifest

    # First run
    settings1 = _default_settings(tmp_path, voice="af_heart", keep_intermediates=True, resume=True)
    engine1 = FakeTTSEngine()
    report1 = convert_epub(simple_epub3_path, tmp_path, settings1, engine1)
    assert report1.errors == []
    manifest_after_run1 = read_manifest(tmp_path / "manifest.json")
    seg_hashes_run1 = {s.normalized_hash for s in manifest_after_run1.segments}
    assert len(seg_hashes_run1) > 0

    # Second run with different voice (config change)
    settings2 = _default_settings(tmp_path, voice="af_bella", keep_intermediates=True, resume=True)
    engine2 = FakeTTSEngine()
    report2 = convert_epub(simple_epub3_path, tmp_path, settings2, engine2)
    assert report2.errors == []
    manifest_after_run2 = read_manifest(tmp_path / "manifest.json")

    # After re-synthesis, all segments should still be present (re-synthesized)
    assert len(manifest_after_run2.segments) == len(manifest_after_run1.segments), (
        "Same number of segments should be present after re-synthesis"
    )
    # All segments should be 'done' (re-synthesized)
    for seg in manifest_after_run2.segments:
        assert seg.status == "done", f"Segment {seg.normalized_hash[:8]}… has status={seg.status!r}"
