"""Tests for audio.chapters_meta — FFmetadata chapter file generation.

Pure text-generation tests; no FFmpeg binary required.
"""

from __future__ import annotations

from pathlib import Path

from epub2audio.audio.chapters_meta import write_ffmetadata_chapters
from epub2audio.models import BookMetadata, ChapterMarker


def _book() -> BookMetadata:
    return BookMetadata(
        title="My Book",
        author="Jane Doe",
        language="en",
        identifier="urn:uuid:1234",
        publisher=None,
        date="2026",
        rights=None,
    )


def test_header_and_book_tags(tmp_path: Path) -> None:
    """The file starts with the FFMETADATA1 header and carries book tags."""
    out = tmp_path / "chapters.ffmeta"
    write_ffmetadata_chapters([], _book(), out)
    text = out.read_text(encoding="utf-8")

    assert text.startswith(";FFMETADATA1\n")
    assert "title=My Book" in text
    assert "album=My Book" in text
    assert "artist=Jane Doe" in text
    assert "genre=Audiobook" in text
    assert "date=2026" in text


def test_one_chapter_block_per_marker(tmp_path: Path) -> None:
    """Each marker becomes a [CHAPTER] block with correct timebase and bounds."""
    markers = [
        ChapterMarker(chapter_id="ch001", title="One", start_ms=0, end_ms=1500),
        ChapterMarker(chapter_id="ch002", title="Two", start_ms=1500, end_ms=4200),
    ]
    out = tmp_path / "chapters.ffmeta"
    write_ffmetadata_chapters(markers, _book(), out)
    text = out.read_text(encoding="utf-8")

    assert text.count("[CHAPTER]") == 2
    assert "TIMEBASE=1/1000" in text
    assert "START=0" in text
    assert "END=1500" in text
    assert "START=1500" in text
    assert "END=4200" in text
    assert "title=One" in text
    assert "title=Two" in text


def test_special_characters_escaped(tmp_path: Path) -> None:
    """`=`, `;`, `#`, and `\\` in a title are backslash-escaped."""
    markers = [
        ChapterMarker(
            chapter_id="ch001",
            title="A = B; C # D \\ E",
            start_ms=0,
            end_ms=100,
        )
    ]
    out = tmp_path / "chapters.ffmeta"
    write_ffmetadata_chapters(markers, _book(), out)
    text = out.read_text(encoding="utf-8")

    assert "title=A \\= B\\; C \\# D \\\\ E" in text
