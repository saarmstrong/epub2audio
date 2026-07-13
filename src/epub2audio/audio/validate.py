"""FFprobe validation of final MP3 output files for epub2audio.

Every chapter MP3 produced by the pipeline must pass all checks here before
it is considered complete.  All FFprobe calls use argument arrays —
``shell=True`` is **never** used.
"""

from __future__ import annotations

import json
from pathlib import Path

from epub2audio.errors import Epub2AudioError
from epub2audio.utils.subprocess import run_command


def validate_mp3(path: Path, *, expected_sample_rate: int = 24000) -> None:
    """Validate a final MP3 file using FFprobe.

    Runs a set of checks on the file to ensure it is a well-formed mono MP3
    with audio content at the expected sample rate and a positive duration.

    Checklist:
    1. File exists and size > 0.
    2. FFprobe can parse the file without error.
    3. At least one audio stream is present.
    4. Audio codec is ``mp3``.
    5. Duration is > 0 seconds.
    6. Sample rate matches *expected_sample_rate*.
    7. Channel count is 1 (mono).

    Args:
        path: Path to the MP3 file to validate.
        expected_sample_rate: Expected sample rate in Hz (default ``24000``).

    Raises:
        Epub2AudioError: If any validation check fails, with a descriptive
            message identifying which check failed.
    """
    # Check 1: file exists and is non-empty
    if not path.exists():
        raise Epub2AudioError(f"Validation failed: file does not exist: {path}")
    if path.stat().st_size == 0:
        raise Epub2AudioError(f"Validation failed: file is empty: {path}")

    # Check 2: run FFprobe
    probe_args = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        stdout, _ = run_command(probe_args)
    except Exception as exc:
        raise Epub2AudioError(f"Validation failed: ffprobe could not parse {path}: {exc}") from exc

    try:
        probe_data: dict[str, object] = json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise Epub2AudioError(
            f"Validation failed: could not parse ffprobe JSON output for {path}: {exc}"
        ) from exc

    streams = probe_data.get("streams", [])
    if not isinstance(streams, list):
        streams = []

    # Check 3: at least one audio stream
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    if not audio_streams:
        raise Epub2AudioError(f"Validation failed: no audio stream found in {path}")

    audio = audio_streams[0]
    if not isinstance(audio, dict):
        raise Epub2AudioError(f"Validation failed: unexpected stream format in {path}")

    # Check 4: codec is mp3
    codec_name = audio.get("codec_name", "")
    if codec_name != "mp3":
        raise Epub2AudioError(
            f"Validation failed: expected codec 'mp3', got {codec_name!r} in {path}"
        )

    # Check 5: duration > 0
    # Duration may be on the stream or on the format container
    fmt = probe_data.get("format", {})
    if not isinstance(fmt, dict):
        fmt = {}

    duration_str = audio.get("duration") or fmt.get("duration", "0")
    try:
        duration = float(str(duration_str))
    except (ValueError, TypeError):
        duration = 0.0

    if duration <= 0.0:
        raise Epub2AudioError(f"Validation failed: duration is {duration} seconds in {path}")

    # Check 6: sample rate
    sr_str = audio.get("sample_rate", "0")
    try:
        sample_rate = int(str(sr_str))
    except (ValueError, TypeError):
        sample_rate = 0

    if sample_rate != expected_sample_rate:
        raise Epub2AudioError(
            f"Validation failed: expected sample rate {expected_sample_rate} Hz, "
            f"got {sample_rate} Hz in {path}"
        )

    # Check 7: mono (1 channel)
    channels_val = audio.get("channels", 0)
    try:
        channels = int(str(channels_val))
    except (ValueError, TypeError):
        channels = 0

    if channels != 1:
        raise Epub2AudioError(
            f"Validation failed: expected 1 channel (mono), got {channels} in {path}"
        )


def probe_duration(path: Path) -> float:
    """Return the duration of an audio file in seconds via FFprobe.

    Uses ``ffprobe`` to read the container/stream duration.  This is a
    lightweight probe intended to be called after :func:`validate_mp3` so the
    resulting :class:`~epub2audio.models.ChapterResult` records a real
    duration rather than a placeholder.

    Args:
        path: Path to the audio file to probe.

    Returns:
        The duration in seconds as a float.  Returns ``0.0`` if the duration
        cannot be determined.

    Raises:
        MissingDependencyError: If ``ffprobe`` is not on ``PATH``.
        Epub2AudioError: If FFprobe cannot parse the file.
    """
    probe_args = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        stdout, _ = run_command(probe_args)
    except Exception as exc:
        raise Epub2AudioError(
            f"Duration probe failed: ffprobe could not parse {path}: {exc}"
        ) from exc

    try:
        probe_data: dict[str, object] = json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise Epub2AudioError(
            f"Duration probe failed: could not parse ffprobe JSON output for {path}: {exc}"
        ) from exc

    fmt = probe_data.get("format", {})
    if not isinstance(fmt, dict):
        fmt = {}

    streams = probe_data.get("streams", [])
    if not isinstance(streams, list):
        streams = []
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    stream_duration = audio_streams[0].get("duration") if audio_streams else None

    duration_str = fmt.get("duration") or stream_duration or "0"
    try:
        return float(str(duration_str))
    except (ValueError, TypeError):
        return 0.0
