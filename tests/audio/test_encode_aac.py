"""Tests for audio.encode.encode_aac — FFmpeg AAC/MP4 encoding.

Mocks ``run_command`` so no real FFmpeg binary is required.  Verifies the
argument contract (native aac codec, mono, explicit mp4 format, atomic write).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from epub2audio.audio.encode import encode_aac

_RUN_COMMAND_PATH = "epub2audio.audio.encode.run_command"


def _make_wav(tmp_path: Path) -> Path:
    p = tmp_path / "chapter.wav"
    p.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    return p


def test_encode_aac_argument_contract(tmp_path: Path) -> None:
    """encode_aac uses native aac, mono, and explicit mp4 format."""
    wav = _make_wav(tmp_path)
    out = tmp_path / "chapter.m4a"

    def fake_run(args: list[str]) -> tuple[bytes, bytes]:
        # Simulate FFmpeg writing the .tmp sidecar.
        Path(args[-1]).write_bytes(b"fake-m4a")
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run) as mock_run:
        encode_aac(wav, out, bitrate="64k", sample_rate=24000)

    args = mock_run.call_args[0][0]
    assert args[0] == "ffmpeg"
    assert "-codec:a" in args
    assert args[args.index("-codec:a") + 1] == "aac"
    assert args[args.index("-ac") + 1] == "1"
    assert args[args.index("-b:a") + 1] == "64k"
    assert args[args.index("-ar") + 1] == "24000"
    assert args[args.index("-f") + 1] == "mp4"
    # Output is atomic: FFmpeg writes to a .tmp sidecar, not the final path.
    assert args[-1].endswith(".m4a.tmp")
    assert out.exists()
    assert not Path(str(out) + ".tmp").exists()


def test_encode_aac_cleans_up_tmp_on_failure(tmp_path: Path) -> None:
    """A failed FFmpeg run leaves no .tmp sidecar behind."""
    wav = _make_wav(tmp_path)
    out = tmp_path / "chapter.m4a"

    def boom(args: list[str]) -> tuple[bytes, bytes]:
        Path(args[-1]).write_bytes(b"partial")
        raise RuntimeError("ffmpeg failed")

    with patch(_RUN_COMMAND_PATH, side_effect=boom):
        try:
            encode_aac(wav, out)
        except RuntimeError:
            pass

    assert not out.exists()
    assert not Path(str(out) + ".tmp").exists()
