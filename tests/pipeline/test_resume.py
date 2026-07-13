"""Unit tests for :func:`~epub2audio.pipeline.resume.check_resume`.

Verifies that:
- An unchanged EPUB + unchanged config returns an empty changed-keys list.
- A changed config (voice, speed, bitrate, language) returns ``["config_hash"]``.
- A changed EPUB file raises :exc:`~epub2audio.errors.FingerprintMismatchError`.

These tests do **not** require FFmpeg; they only use the manifest/fingerprint
helpers and the Settings model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from epub2audio.config import Settings
from epub2audio.errors import FingerprintMismatchError
from epub2audio.models import ConversionManifest
from epub2audio.pipeline.manifest import config_hash, epub_fingerprint
from epub2audio.pipeline.resume import check_resume

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_manifest(epub_path: Path, settings: Settings) -> ConversionManifest:
    """Build a minimal :class:`ConversionManifest` that matches *epub_path* and *settings*."""
    now = datetime.now(UTC).isoformat()
    return ConversionManifest(
        epub_fingerprint=epub_fingerprint(epub_path),
        config_hash=config_hash(settings),
        chapters=[],
        segments=[],
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# EPUB fingerprint validation
# ---------------------------------------------------------------------------


class TestCheckResumeFingerprint:
    """check_resume detects EPUB file changes via SHA-256 digest."""

    def test_matching_epub_does_not_raise(self, simple_epub3_path: Path) -> None:
        """check_resume does not raise when the EPUB matches the stored fingerprint."""
        settings = Settings()
        manifest = _make_manifest(simple_epub3_path, settings)
        # Must not raise — returns empty list (config unchanged)
        result = check_resume(manifest, simple_epub3_path, settings)
        assert result == []

    def test_different_epub_raises_fingerprint_mismatch(
        self, simple_epub3_path: Path, simple_epub2_path: Path
    ) -> None:
        """check_resume raises FingerprintMismatchError when a different EPUB is passed.

        The manifest was created for *simple_epub3_path*; passing *simple_epub2_path*
        must be detected as an EPUB change.
        """
        settings = Settings()
        # Manifest recorded fingerprint of EPUB3 file
        manifest = _make_manifest(simple_epub3_path, settings)

        # Run against the *different* EPUB2 file
        with pytest.raises(FingerprintMismatchError):
            check_resume(manifest, simple_epub2_path, settings)

    def test_stale_fingerprint_raises(self, simple_epub3_path: Path) -> None:
        """check_resume raises FingerprintMismatchError when the stored fingerprint is stale."""
        settings = Settings()
        now = datetime.now(UTC).isoformat()
        # Manifest has a made-up fingerprint that will never match a real file
        manifest = ConversionManifest(
            epub_fingerprint="0" * 64,
            config_hash=config_hash(settings),
            chapters=[],
            segments=[],
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(FingerprintMismatchError):
            check_resume(manifest, simple_epub3_path, settings)

    def test_manually_altered_file_raises(self, tmp_path: Path) -> None:
        """check_resume raises when the EPUB bytes have been modified since the last run."""
        epub_path = tmp_path / "book.epub"
        epub_path.write_bytes(b"fake epub content version A")

        settings = Settings()
        manifest = _make_manifest(epub_path, settings)

        # Simulate the file being modified between runs
        epub_path.write_bytes(b"fake epub content version B - different bytes!")

        with pytest.raises(FingerprintMismatchError):
            check_resume(manifest, epub_path, settings)


# ---------------------------------------------------------------------------
# Config change detection
# ---------------------------------------------------------------------------


class TestCheckResumeConfigChange:
    """check_resume detects settings changes via config_hash comparison."""

    def test_unchanged_config_returns_empty_list(self, simple_epub3_path: Path) -> None:
        """check_resume returns [] when the config matches the manifest exactly."""
        settings = Settings()
        manifest = _make_manifest(simple_epub3_path, settings)
        changed = check_resume(manifest, simple_epub3_path, settings)
        assert changed == []

    def test_voice_change_returns_config_hash_key(self, simple_epub3_path: Path) -> None:
        """check_resume returns ['config_hash'] when the voice setting changes.

        Voice is a TTS-affecting setting; a change requires segment re-synthesis.
        """
        old_settings = Settings(voice="af_heart")
        manifest = _make_manifest(simple_epub3_path, old_settings)

        new_settings = Settings(voice="af_bella")
        changed = check_resume(manifest, simple_epub3_path, new_settings)
        assert changed == ["config_hash"]

    def test_speed_change_returns_config_hash_key(self, simple_epub3_path: Path) -> None:
        """check_resume returns ['config_hash'] when the speed setting changes.

        Speed is a TTS-affecting setting; a change requires segment re-synthesis.
        """
        old_settings = Settings(speed=1.0)
        manifest = _make_manifest(simple_epub3_path, old_settings)

        new_settings = Settings(speed=1.5)
        changed = check_resume(manifest, simple_epub3_path, new_settings)
        assert changed == ["config_hash"]

    def test_bitrate_change_returns_config_hash_key(self, simple_epub3_path: Path) -> None:
        """check_resume returns ['config_hash'] when the bitrate setting changes.

        Note: The current implementation is conservative — it cannot distinguish
        a TTS-affecting change (voice, speed) from an encoding-only change (bitrate)
        because the manifest stores only the config *hash*, not the full snapshot.
        The ``_TTS_AFFECTING_KEYS`` / ``_ENCODE_AFFECTING_KEYS`` constants in
        ``resume.py`` document the planned two-tier invalidation refinement.
        """
        old_settings = Settings(bitrate="96k")
        manifest = _make_manifest(simple_epub3_path, old_settings)

        new_settings = Settings(bitrate="128k")
        changed = check_resume(manifest, simple_epub3_path, new_settings)
        assert changed == ["config_hash"]

    def test_language_change_returns_config_hash_key(self, simple_epub3_path: Path) -> None:
        """check_resume returns ['config_hash'] when the language setting changes."""
        old_settings = Settings(language="en-us")
        manifest = _make_manifest(simple_epub3_path, old_settings)

        new_settings = Settings(language="en-gb")
        changed = check_resume(manifest, simple_epub3_path, new_settings)
        assert changed == ["config_hash"]

    def test_sample_rate_change_returns_config_hash_key(self, simple_epub3_path: Path) -> None:
        """check_resume returns ['config_hash'] when the sample_rate setting changes."""
        old_settings = Settings(sample_rate=24000)
        manifest = _make_manifest(simple_epub3_path, old_settings)

        new_settings = Settings(sample_rate=22050)
        changed = check_resume(manifest, simple_epub3_path, new_settings)
        assert changed == ["config_hash"]

    def test_all_defaults_unchanged(self, simple_epub3_path: Path) -> None:
        """Two independently constructed Settings() with all defaults are equal.

        This verifies that config_hash is deterministic across objects.
        """
        s1 = Settings()
        s2 = Settings()
        manifest = _make_manifest(simple_epub3_path, s1)
        changed = check_resume(manifest, simple_epub3_path, s2)
        assert changed == []


# ---------------------------------------------------------------------------
# Changed-keys semantics
# ---------------------------------------------------------------------------


class TestCheckResumeReturnValue:
    """Verify the structure of the changed-keys list returned by check_resume."""

    def test_config_changed_result_is_a_list(self, simple_epub3_path: Path) -> None:
        """check_resume returns a list object, not some other sequence type."""
        settings = Settings()
        manifest = _make_manifest(simple_epub3_path, settings)
        result = check_resume(manifest, simple_epub3_path, settings)
        assert isinstance(result, list)

    def test_config_changed_returns_single_sentinel_key(self, simple_epub3_path: Path) -> None:
        """When config changes, exactly one sentinel key ('config_hash') is returned.

        The manifest stores a hash rather than a snapshot, so only a single sentinel
        key is available; callers use :func:`tts_config_changed` to decide how to
        handle it.
        """
        old_settings = Settings(voice="af_heart")
        manifest = _make_manifest(simple_epub3_path, old_settings)
        new_settings = Settings(voice="af_bella")
        result = check_resume(manifest, simple_epub3_path, new_settings)
        assert len(result) == 1
        assert result[0] == "config_hash"
