"""FFmpeg two-pass EBU R128 loudness normalization for epub2audio.

Pass 1 measures the loudness of the input; pass 2 applies corrective
normalization using the measured values.  All FFmpeg calls use argument
arrays — ``shell=True`` is **never** used.

Output files are written atomically via a ``.tmp`` sidecar.

Silence handling: if the first-pass measurement yields ``measured_I=-inf``
or any non-finite value (e.g. pure-silence input from FakeTTSEngine), the
two-pass normalization is skipped and the file is copied through unchanged.
This avoids FFmpeg exit 234 errors on degenerate input.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from pathlib import Path

from epub2audio.errors import Epub2AudioError
from epub2audio.utils.subprocess import run_command, run_command_unchecked

log = logging.getLogger(__name__)


def normalize_loudness(
    input_wav: Path,
    output_wav: Path,
    *,
    target_lufs: float = -18.0,
    true_peak: float = -2.0,
    lra: float = 7.0,
) -> None:
    """Apply two-pass EBU R128 loudness normalization to a WAV file.

    Pass 1 runs FFmpeg with ``-f null -`` to measure the actual loudness of
    *input_wav* and parse the JSON measurement block from stderr.  Pass 2
    applies corrective gain using those measured values so the output matches
    the targets precisely.

    The output is written atomically: pass-2 writes to a ``.tmp`` sidecar
    which is then renamed into *output_wav* via :func:`os.replace`.

    Args:
        input_wav: Path to the source WAV file.
        output_wav: Destination WAV file path.  Parent directories are
            created automatically.
        target_lufs: Integrated loudness target in LUFS (default ``-18.0``).
        true_peak: Maximum true peak in dBTP (default ``-2.0``).
        lra: Loudness range target in LU (default ``7.0``).

    Raises:
        Epub2AudioError: If the pass-1 JSON measurement block cannot be
            parsed from FFmpeg's stderr.
        MissingDependencyError: If ``ffmpeg`` is not on ``PATH``.
        subprocess.CalledProcessError: If FFmpeg pass 2 exits non-zero.
        OSError: If the output cannot be written.
    """
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_wav.with_suffix(output_wav.suffix + ".tmp")

    # ------------------------------------------------------------------
    # Pass 1: measure loudness
    # ------------------------------------------------------------------
    loudnorm_filter = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=json"
    pass1_args = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_wav),
        "-af",
        loudnorm_filter,
        "-f",
        "null",
        "-",
    ]
    # FFmpeg writes loudnorm JSON to stderr; exit code may be 0 or non-zero
    # depending on version — use unchecked variant.
    _, _, stderr_bytes = run_command_unchecked(pass1_args)
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")

    measured = _parse_loudnorm_json(stderr_text)

    # ------------------------------------------------------------------
    # Silence guard: skip normalization if input is silent / degenerate
    # ------------------------------------------------------------------
    if _is_degenerate(measured):
        log.warning(
            "normalize_loudness: input appears to be silence "
            "(measured_I=%s) — skipping normalization, copying through.",
            measured.get("input_i", "?"),
        )
        shutil.copy(str(input_wav), str(output_wav))
        return

    # ------------------------------------------------------------------
    # Pass 2: apply normalization
    # ------------------------------------------------------------------
    pass2_filter = (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
        f":measured_I={measured['input_i']}"
        f":measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}"
        f":measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}"
        f":linear=true:print_format=none"
    )
    pass2_args = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_wav),
        "-af",
        pass2_filter,
        "-f",
        "wav",  # explicit format: FFmpeg ≥ 8 can't infer from .tmp extension
        str(tmp_path),
    ]

    try:
        run_command(pass2_args)
        os.replace(tmp_path, output_wav)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _is_degenerate(measured: dict[str, str]) -> bool:
    """Return ``True`` if any loudnorm measurement is non-finite.

    FFmpeg's loudnorm filter emits ``"-inf"`` (or ``"inf"``) for the
    integrated loudness when the input is completely silent or otherwise
    degenerate.  Passing these values to pass 2 causes FFmpeg to exit with
    code 234; this function detects that condition so the caller can copy
    through instead.

    Args:
        measured: Parsed loudnorm JSON dict from :func:`_parse_loudnorm_json`.

    Returns:
        ``True`` if *input_i*, *input_tp*, *input_lra*, or *input_thresh*
        contains a non-finite string value (``"-inf"``, ``"inf"``, ``"nan"``).
    """
    non_finite = {"-inf", "inf", "+inf", "nan"}
    check_keys = ("input_i", "input_tp", "input_lra", "input_thresh")
    for key in check_keys:
        val = measured.get(key, "").strip().lower()
        if val in non_finite:
            return True
        # Also guard against Python float conversion failures
        try:
            parsed = float(val)
            import math

            if not math.isfinite(parsed):
                return True
        except ValueError:
            pass
    return False


def _parse_loudnorm_json(stderr_text: str) -> dict[str, str]:
    """Extract the loudnorm JSON block from FFmpeg stderr.

    FFmpeg embeds a JSON object between ``{`` and ``}`` delimiters somewhere
    in the loudnorm filter output on stderr.  This function locates and
    parses that block.

    Args:
        stderr_text: Full stderr output from the FFmpeg pass-1 command.

    Returns:
        A dict with keys ``input_i``, ``input_tp``, ``input_lra``,
        ``input_thresh``, and ``target_offset``.

    Raises:
        Epub2AudioError: If no valid JSON block can be located or parsed.
    """
    # Find the last JSON object in stderr (loudnorm appends it after its log lines)
    match = None
    for m in re.finditer(r"\{[^{}]+\}", stderr_text, re.DOTALL):
        match = m

    if match is None:
        raise Epub2AudioError(
            "Could not parse loudnorm measurement from FFmpeg stderr. "
            "Ensure ffmpeg is compiled with the loudnorm filter."
        )

    try:
        data: dict[str, str] = json.loads(match.group())
    except json.JSONDecodeError as exc:
        raise Epub2AudioError(f"Malformed loudnorm JSON from FFmpeg: {exc}") from exc

    required_keys = {"input_i", "input_tp", "input_lra", "input_thresh", "target_offset"}
    missing = required_keys - data.keys()
    if missing:
        raise Epub2AudioError(f"Loudnorm JSON missing expected keys: {', '.join(sorted(missing))}")

    return data
