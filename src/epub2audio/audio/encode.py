"""FFmpeg MP3 encoding for epub2audio.

All FFmpeg invocations use argument arrays via :func:`~epub2audio.utils.subprocess.run_command`.
``shell=True`` is **never** used.

Writes are atomic: the MP3 is first written to a ``.tmp`` sidecar, then
renamed into place via :func:`os.replace`.
"""

from __future__ import annotations

import os
from pathlib import Path

from epub2audio.utils.subprocess import run_command


def encode_mp3(
    input_wav: Path,
    output_mp3: Path,
    *,
    bitrate: str = "96k",
    sample_rate: int = 24000,
) -> None:
    """Encode a WAV file to MP3 using FFmpeg.

    The output is written atomically: FFmpeg writes to a ``.tmp`` sidecar
    file first, which is then renamed into *output_mp3* via
    :func:`os.replace`.

    Args:
        input_wav: Path to the source WAV file.
        output_mp3: Destination MP3 file path.  Parent directories are
            created automatically.
        bitrate: MP3 bitrate string, e.g. ``"96k"`` or ``"128k"``.
        sample_rate: Output sample rate in Hz.  The audio is resampled if
            the input differs.

    Raises:
        MissingDependencyError: If ``ffmpeg`` is not on ``PATH``.
        subprocess.CalledProcessError: If FFmpeg exits with a non-zero code.
        OSError: If the output directory cannot be created or the rename fails.
    """
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_mp3.with_suffix(output_mp3.suffix + ".tmp")

    args = [
        "ffmpeg",
        "-y",  # overwrite tmp file without prompting
        "-i",
        str(input_wav),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ar",
        str(sample_rate),
        "-ac",
        "1",  # mono
        "-f",
        "mp3",  # explicit format: FFmpeg ≥ 8 can't infer from .tmp extension
        str(tmp_path),
    ]

    try:
        run_command(args)
        os.replace(tmp_path, output_mp3)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
