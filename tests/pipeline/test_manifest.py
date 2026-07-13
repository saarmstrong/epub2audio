"""Tests for pipeline.manifest — serialization round-trip, fingerprinting,
config hashing, and atomic write behaviour.

If the module is still a stub when collected, tests are skipped with a message.

# TODO(pending-impl): tests require a real manifest.py implementation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from epub2audio.config import Settings
    from epub2audio.models import ConversionManifest

# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

try:
    from epub2audio.pipeline.manifest import (
        config_hash,
        epub_fingerprint,
        read_manifest,
        write_manifest,
    )

    _IMPL_AVAILABLE = True
except (ImportError, AttributeError):
    _IMPL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _IMPL_AVAILABLE,
    reason="epub2audio.pipeline.manifest is not yet implemented (stub)",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_manifest() -> ConversionManifest:
    """Build a minimal but valid ConversionManifest for testing."""
    from epub2audio.models import (
        Chapter,
        ConversionManifest,
        TextSegment,
    )

    chapter = Chapter(
        chapter_id="ch001",
        title="Chapter One",
        source_docs=["chapter1.xhtml"],
        word_count=42,
        stable_id="abc123def456",
    )
    segment = TextSegment(
        text="Hello world.",
        source_hash="a" * 64,
        normalized_hash="b" * 64,
        word_count=2,
        status="pending",
        audio_path=None,
    )
    now = datetime.now(tz=UTC).isoformat()
    return ConversionManifest(
        epub_fingerprint="f" * 64,
        config_hash="e" * 64,
        chapters=[chapter],
        segments=[segment],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def manifest() -> ConversionManifest:
    """A minimal ConversionManifest for use in tests."""
    return _make_manifest()


@pytest.fixture
def settings() -> Settings:
    """Default Settings for hashing tests."""
    from epub2audio.config import Settings

    return Settings()


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------


def test_write_then_read_round_trip(tmp_path: Path, manifest: ConversionManifest) -> None:
    """write_manifest followed by read_manifest returns an equal object."""
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    loaded = read_manifest(path)
    assert loaded == manifest


def test_round_trip_preserves_epub_fingerprint(
    tmp_path: Path, manifest: ConversionManifest
) -> None:
    """epub_fingerprint field survives serialization round-trip."""
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    loaded = read_manifest(path)
    assert loaded.epub_fingerprint == manifest.epub_fingerprint


def test_round_trip_preserves_chapters(tmp_path: Path, manifest: ConversionManifest) -> None:
    """Chapter list survives serialization round-trip."""
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    loaded = read_manifest(path)
    assert loaded.chapters == manifest.chapters


def test_round_trip_preserves_segments(tmp_path: Path, manifest: ConversionManifest) -> None:
    """TextSegment list survives serialization round-trip."""
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    loaded = read_manifest(path)
    assert loaded.segments == manifest.segments


def test_manifest_file_is_valid_json(tmp_path: Path, manifest: ConversionManifest) -> None:
    """The file written by write_manifest is valid JSON."""
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    with path.open() as fh:
        parsed: dict[str, Any] = json.load(fh)
    assert isinstance(parsed, dict)
    assert "epub_fingerprint" in parsed


# ---------------------------------------------------------------------------
# epub_fingerprint
# ---------------------------------------------------------------------------


def test_epub_fingerprint_returns_64_char_hex(simple_epub3_path: Path) -> None:
    """epub_fingerprint returns a 64-character hex string (SHA-256)."""
    fp = epub_fingerprint(simple_epub3_path)
    assert isinstance(fp, str)
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_epub_fingerprint_is_deterministic(simple_epub3_path: Path) -> None:
    """epub_fingerprint returns the same value on repeated calls."""
    assert epub_fingerprint(simple_epub3_path) == epub_fingerprint(simple_epub3_path)


def test_epub_fingerprint_differs_for_different_files(
    simple_epub3_path: Path, simple_epub2_path: Path
) -> None:
    """epub_fingerprint returns different values for different EPUB files."""
    assert epub_fingerprint(simple_epub3_path) != epub_fingerprint(simple_epub2_path)


def test_epub_fingerprint_differs_for_modified_file(tmp_path: Path) -> None:
    """epub_fingerprint changes if the file content changes."""
    epub_a = tmp_path / "a.epub"
    epub_b = tmp_path / "b.epub"
    epub_a.write_bytes(b"fake epub content version A")
    epub_b.write_bytes(b"fake epub content version B")
    assert epub_fingerprint(epub_a) != epub_fingerprint(epub_b)


# ---------------------------------------------------------------------------
# config_hash
# ---------------------------------------------------------------------------


def test_config_hash_returns_64_char_hex(settings: Settings) -> None:
    """config_hash returns a 64-character hex string (SHA-256)."""
    h = config_hash(settings)
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_config_hash_is_deterministic(settings: Settings) -> None:
    """config_hash returns the same value for the same settings object."""
    assert config_hash(settings) == config_hash(settings)


def test_config_hash_changes_on_voice_change() -> None:
    """Changing the voice field produces a different config_hash."""
    from epub2audio.config import Settings

    s1 = Settings(voice="af_heart")
    s2 = Settings(voice="af_sky")
    assert config_hash(s1) != config_hash(s2)


def test_config_hash_changes_on_speed_change() -> None:
    """Changing the speed field produces a different config_hash."""
    from epub2audio.config import Settings

    s1 = Settings(speed=1.0)
    s2 = Settings(speed=1.5)
    assert config_hash(s1) != config_hash(s2)


def test_config_hash_changes_on_bitrate_change() -> None:
    """Changing the bitrate field produces a different config_hash."""
    from epub2audio.config import Settings

    s1 = Settings(bitrate="96k")
    s2 = Settings(bitrate="128k")
    assert config_hash(s1) != config_hash(s2)


def test_config_hash_changes_on_sample_rate_change() -> None:
    """Changing the sample_rate field produces a different config_hash."""
    from epub2audio.config import Settings

    s1 = Settings(sample_rate=24000)
    s2 = Settings(sample_rate=22050)
    assert config_hash(s1) != config_hash(s2)


def test_config_hash_changes_on_language_change() -> None:
    """Changing the language field produces a different config_hash."""
    from epub2audio.config import Settings

    s1 = Settings(language="en-us")
    s2 = Settings(language="en-gb")
    assert config_hash(s1) != config_hash(s2)


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def test_write_manifest_creates_file(tmp_path: Path, manifest: ConversionManifest) -> None:
    """write_manifest creates the target file."""
    path = tmp_path / "manifest.json"
    assert not path.exists()
    write_manifest(manifest, path)
    assert path.exists()


def test_write_manifest_no_tmp_file_left_on_success(
    tmp_path: Path, manifest: ConversionManifest
) -> None:
    """After a successful write, no .tmp file remains on disk."""
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    tmp_candidates = list(tmp_path.glob("*.tmp"))
    assert tmp_candidates == [], f"Unexpected .tmp files left after write: {tmp_candidates}"


def test_write_manifest_overwrites_existing(tmp_path: Path, manifest: ConversionManifest) -> None:
    """write_manifest overwrites an existing manifest file cleanly."""
    from epub2audio.models import ConversionManifest

    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    first_text = path.read_text()

    manifest2 = ConversionManifest(**{**manifest.model_dump(), "epub_fingerprint": "0" * 64})
    write_manifest(manifest2, path)
    second_text = path.read_text()

    assert first_text != second_text
    assert "0" * 64 in second_text


def test_read_manifest_raises_on_missing_file(tmp_path: Path) -> None:
    """read_manifest raises FileNotFoundError when the file does not exist."""
    missing = tmp_path / "no_such_manifest.json"
    with pytest.raises((FileNotFoundError, OSError)):
        read_manifest(missing)
