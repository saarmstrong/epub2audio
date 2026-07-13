"""Tests for audio.validate.validate_audio — codec + chapter parameterization.

Mocks ``run_command`` so no real FFprobe binary is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from epub2audio.audio.validate import validate_audio
from epub2audio.errors import Epub2AudioError

_RUN_COMMAND_PATH = "epub2audio.audio.validate.run_command"


def _make_file(tmp_path: Path) -> Path:
    p = tmp_path / "book.m4b"
    p.write_bytes(b"\x00\x00\x00\x18ftypM4A ")
    return p


def _fake_probe(*, codec: str, sample_rate: int, channels: int, n_chapters: int):
    """Return a run_command side-effect that answers stream and chapter probes."""
    streams_payload = json.dumps(
        {
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": codec,
                    "sample_rate": str(sample_rate),
                    "channels": channels,
                    "duration": "12.5",
                }
            ],
            "format": {"duration": "12.5"},
        }
    ).encode()
    chapters_payload = json.dumps({"chapters": [{"id": i} for i in range(n_chapters)]}).encode()

    def run(args: list[str]) -> tuple[bytes, bytes]:
        if "-show_chapters" in args:
            return chapters_payload, b""
        return streams_payload, b""

    return run


def test_validate_audio_accepts_aac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A well-formed mono AAC file with the right chapter count passes."""
    path = _make_file(tmp_path)
    monkeypatch.setattr(
        _RUN_COMMAND_PATH,
        _fake_probe(codec="aac", sample_rate=24000, channels=1, n_chapters=2),
        raising=True,
    )
    validate_audio(
        path,
        expected_codec="aac",
        expected_sample_rate=24000,
        expected_chapters=2,
    )


def test_validate_audio_rejects_wrong_codec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A codec mismatch raises Epub2AudioError."""
    path = _make_file(tmp_path)
    monkeypatch.setattr(
        _RUN_COMMAND_PATH,
        _fake_probe(codec="mp3", sample_rate=24000, channels=1, n_chapters=2),
        raising=True,
    )
    with pytest.raises(Epub2AudioError, match="expected codec 'aac'"):
        validate_audio(path, expected_codec="aac", expected_sample_rate=24000)


def test_validate_audio_rejects_chapter_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A chapter-count mismatch raises Epub2AudioError."""
    path = _make_file(tmp_path)
    monkeypatch.setattr(
        _RUN_COMMAND_PATH,
        _fake_probe(codec="aac", sample_rate=24000, channels=1, n_chapters=1),
        raising=True,
    )
    with pytest.raises(Epub2AudioError, match="expected 3 chapter"):
        validate_audio(
            path,
            expected_codec="aac",
            expected_sample_rate=24000,
            expected_chapters=3,
        )
