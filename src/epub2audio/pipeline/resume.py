"""Resume and fingerprint logic for epub2audio.

Detects whether a previous conversion run's manifest is still valid for the
current EPUB and settings, and determines which segments still need synthesis.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from epub2audio.config import Settings
from epub2audio.errors import FingerprintMismatchError
from epub2audio.models import ConversionManifest, TextSegment
from epub2audio.pipeline.manifest import config_hash, epub_fingerprint

log = logging.getLogger(__name__)

# Settings that affect TTS synthesis output — changing these invalidates segment WAVs.
_TTS_AFFECTING_KEYS: frozenset[str] = frozenset({"voice", "language", "speed"})

# Settings that affect encoding/normalization only — segment WAVs remain valid.
_ENCODE_AFFECTING_KEYS: frozenset[str] = frozenset({"normalize", "bitrate", "sample_rate"})


def check_resume(
    manifest: ConversionManifest,
    epub_path: Path,
    settings: Settings,
) -> list[str]:
    """Validate a saved manifest against the current EPUB and settings.

    Raises :class:`~epub2audio.errors.FingerprintMismatchError` if the EPUB
    file has changed since the manifest was written (different SHA-256 digest).
    If only the config changed, the differing setting keys are returned so the
    caller can decide whether to clear the affected artifacts.

    Args:
        manifest: The :class:`ConversionManifest` loaded from the previous run.
        epub_path: Path to the EPUB file being converted in the current run.
        settings: Effective settings for the current run.

    Returns:
        A list of setting keys whose values differ from the manifest's
        ``config_snapshot``.  An empty list means settings are unchanged.

    Raises:
        FingerprintMismatchError: If the EPUB SHA-256 digest has changed.
    """
    current_fingerprint = epub_fingerprint(epub_path)
    if current_fingerprint != manifest.epub_fingerprint:
        raise FingerprintMismatchError(
            f"EPUB file has changed since the last conversion run. "
            f"Stored fingerprint: {manifest.epub_fingerprint!r}, "
            f"current fingerprint: {current_fingerprint!r}. "
            f"Delete the manifest and restart the conversion."
        )

    current_hash = config_hash(settings)
    if current_hash == manifest.config_hash:
        return []

    # Config hash changed — we can't recover the old snapshot from the manifest
    # (manifest stores the hash, not the snapshot).  Return a sentinel key list
    # to indicate that config changed; the converter will handle invalidation.
    return ["config_hash"]


def tts_config_changed(changed_keys: list[str]) -> bool:
    """Return True if any changed key affects TTS synthesis output.

    TTS-affecting changes (voice, language, speed) require segment WAVs to be
    discarded and re-synthesized.  Encoding-only changes (bitrate, sample_rate,
    normalize) can reuse existing segment WAVs.

    Args:
        changed_keys: List returned by :func:`check_resume`.

    Returns:
        ``True`` if segment WAVs must be invalidated; ``False`` if they can be
        reused and only the final MP3 needs to be regenerated.
    """
    # When the config hash changes we cannot tell which specific keys changed
    # (the manifest stores the hash, not the snapshot).  We therefore treat any
    # config change as potentially TTS-affecting to be safe.
    return bool(changed_keys)


def clear_segment_cache(work_root: Path, chapter_id: str) -> None:
    """Delete cached segment WAVs for a single chapter.

    Called when a TTS-affecting config change is detected.  Removes the
    chapter's work directory so that all segments are re-synthesized.

    Args:
        work_root: The ``.epub2audio-work`` directory inside the output dir.
        chapter_id: The chapter whose segment cache should be cleared.
    """
    chapter_work = work_root / chapter_id
    if chapter_work.exists():
        log.info(
            "Config changed — clearing segment cache for chapter %r: %s",
            chapter_id,
            chapter_work,
        )
        shutil.rmtree(chapter_work, ignore_errors=True)


def segment_needs_synthesis(segment: TextSegment, output_dir: Path) -> bool:
    """Determine whether a segment's audio still needs to be synthesized.

    A segment can be skipped if:
    - Its ``audio_path`` is set (non-None).
    - The file at that path exists.
    - The file is non-empty (basic WAV validity proxy).

    Args:
        segment: The :class:`~epub2audio.models.TextSegment` to check.
        output_dir: Base output directory (used if ``audio_path`` is relative).

    Returns:
        ``True`` if the segment needs (re-)synthesis; ``False`` if it can be
        skipped.
    """
    if segment.audio_path is None:
        return True

    audio_path = Path(segment.audio_path)
    if not audio_path.is_absolute():
        audio_path = output_dir / audio_path

    if not audio_path.exists():
        return True

    if audio_path.stat().st_size == 0:
        return True

    return False
