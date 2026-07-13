"""Tests for audio.encode — FFmpeg MP3 encoding.

These tests use ``unittest.mock.patch`` to mock ``run_command`` so no real
FFmpeg binary is required.  They verify the argument contract (no shell=True,
correct flags, atomic write) rather than actual audio output.

If ``encode_mp3`` is not yet importable (module is a stub), tests are skipped
with a clear message.

# TODO(pending-impl): tests require a real encode.py implementation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

try:
    from epub2audio.audio.encode import encode_mp3

    _IMPL_AVAILABLE = True
except (ImportError, AttributeError):
    _IMPL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _IMPL_AVAILABLE,
    reason="epub2audio.audio.encode is not yet implemented (stub)",
)

# The module path for run_command as used inside encode.py.
# The Audio Engineer contract specifies encode.py calls utils/subprocess.run_command.
_RUN_COMMAND_PATH = "epub2audio.audio.encode.run_command"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wav(tmp_path: Path) -> Path:
    """Create a dummy WAV file so Path.exists() checks pass."""
    p = tmp_path / "chapter.wav"
    p.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    return p


def _write_fake_mp3(mp3: Path) -> None:
    """Write a fake .tmp output file, simulating what FFmpeg would produce."""
    Path(str(mp3) + ".tmp").write_bytes(b"fake-mp3")


# ---------------------------------------------------------------------------
# No shell=True / arg-list shape
# ---------------------------------------------------------------------------


def test_encode_mp3_never_uses_shell_true(tmp_path: Path) -> None:
    """encode_mp3 must invoke run_command with a list argument, never a shell string."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    captured_args: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        captured_args.append(args)
        _write_fake_mp3(mp3)
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run_command):
        encode_mp3(wav, mp3)

    assert len(captured_args) >= 1
    assert isinstance(captured_args[0], list), (
        f"run_command must be called with a list of args, got {type(captured_args[0])}"
    )


def test_encode_mp3_arg_list_not_shell_string(tmp_path: Path) -> None:
    """FFmpeg is invoked as an argument list, not a single shell command string."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    with patch(_RUN_COMMAND_PATH) as mock_run:
        _write_fake_mp3(mp3)
        mock_run.return_value = (b"", b"")
        encode_mp3(wav, mp3)

    assert mock_run.called
    positional = mock_run.call_args[0]
    assert len(positional) >= 1
    cmd = positional[0]
    assert isinstance(cmd, list), f"First arg to run_command must be list, got: {type(cmd)}"
    assert all(isinstance(a, str) for a in cmd), "All arg-list elements must be strings"


def test_encode_mp3_ffmpeg_is_first_arg(tmp_path: Path) -> None:
    """The first element of the argument list is 'ffmpeg'."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    captured: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        _write_fake_mp3(mp3)
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run_command):
        encode_mp3(wav, mp3)

    assert captured[0][0] == "ffmpeg", f"Expected 'ffmpeg' as first arg, got: {captured[0][0]!r}"


# ---------------------------------------------------------------------------
# Correct flags
# ---------------------------------------------------------------------------


def test_encode_mp3_passes_default_bitrate_flag(tmp_path: Path) -> None:
    """The FFmpeg invocation includes the default bitrate flag '96k'."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    captured: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        _write_fake_mp3(mp3)
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run_command):
        encode_mp3(wav, mp3, bitrate="96k")

    flat = " ".join(captured[0])
    assert "96k" in flat, f"Bitrate '96k' not found in FFmpeg args: {captured[0]}"


def test_encode_mp3_passes_default_sample_rate_flag(tmp_path: Path) -> None:
    """The FFmpeg invocation includes the default sample rate flag '24000'."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    captured: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        _write_fake_mp3(mp3)
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run_command):
        encode_mp3(wav, mp3, sample_rate=24000)

    flat = " ".join(captured[0])
    assert "24000" in flat, f"Sample rate '24000' not found in FFmpeg args: {captured[0]}"


def test_custom_bitrate_128k(tmp_path: Path) -> None:
    """A custom bitrate of '128k' appears in the FFmpeg argument list."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    captured: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        _write_fake_mp3(mp3)
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run_command):
        encode_mp3(wav, mp3, bitrate="128k")

    assert "128k" in " ".join(captured[0])


def test_custom_sample_rate_22050(tmp_path: Path) -> None:
    """A custom sample rate of 22050 appears in the FFmpeg argument list."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    captured: list[list[str]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        captured.append(args)
        _write_fake_mp3(mp3)
        return b"", b""

    with patch(_RUN_COMMAND_PATH, side_effect=fake_run_command):
        encode_mp3(wav, mp3, sample_rate=22050)

    assert "22050" in " ".join(captured[0])


# ---------------------------------------------------------------------------
# Atomic write — failure leaves no partial file
# ---------------------------------------------------------------------------


def test_encode_mp3_no_partial_file_on_failure(tmp_path: Path) -> None:
    """If encoding fails, the output .mp3 file is not left on disk."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"

    def failing_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        raise subprocess.CalledProcessError(1, args, b"", b"ffmpeg error")

    with patch(_RUN_COMMAND_PATH, side_effect=failing_run_command):
        with pytest.raises((subprocess.CalledProcessError, Exception)):
            encode_mp3(wav, mp3)

    assert not mp3.exists(), "Partial .mp3 file must not exist after encoding failure"


def test_encode_mp3_no_tmp_file_left_on_failure(tmp_path: Path) -> None:
    """If encoding fails, no .tmp file is left on disk."""
    wav = _make_wav(tmp_path)
    mp3 = tmp_path / "chapter.mp3"
    tmp_mp3 = Path(str(mp3) + ".tmp")

    def failing_run_command(args: list[str], **kwargs: object) -> tuple[bytes, bytes]:
        raise subprocess.CalledProcessError(1, args, b"", b"error")

    with patch(_RUN_COMMAND_PATH, side_effect=failing_run_command):
        with pytest.raises((subprocess.CalledProcessError, Exception)):
            encode_mp3(wav, mp3)

    assert not tmp_mp3.exists(), ".tmp file must not remain after encoding failure"
