"""WAV file concatenation for epub2audio.

Concatenates multiple WAV files into one losslessly, without re-encoding.
All writes are atomic (write to ``.tmp``, then :func:`os.replace`).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from epub2audio.errors import Epub2AudioError


def concatenate_wavs(input_paths: list[Path], output_path: Path) -> None:
    """Concatenate WAV files into a single output WAV file.

    All input files must share the same sample rate and channel count.  The
    output is written atomically: data is first written to a ``.tmp`` sidecar
    file, then renamed into place via :func:`os.replace`.

    Args:
        input_paths: Ordered list of WAV files to concatenate.  Must be
            non-empty.
        output_path: Destination WAV file path.  Parent directories are
            created automatically.

    Raises:
        Epub2AudioError: If *input_paths* is empty, or if the input files
            have mismatched sample rates or channel counts.
        OSError: If any input file cannot be read or the output cannot be
            written.
    """
    if not input_paths:
        raise Epub2AudioError("concatenate_wavs requires at least one input file.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Use a proper .wav temp file so soundfile can detect the format
    fd, tmp_str = tempfile.mkstemp(suffix=".wav", dir=output_path.parent)
    os.close(fd)
    tmp_path = Path(tmp_str)

    # Read first file to establish reference format
    first_data, ref_sample_rate = sf.read(str(input_paths[0]), dtype="float32", always_2d=False)
    ref_channels = 1 if first_data.ndim == 1 else first_data.shape[1]

    all_arrays: list[np.ndarray] = [first_data]

    for idx, path in enumerate(input_paths[1:], start=1):
        data, sample_rate = sf.read(str(path), dtype="float32", always_2d=False)
        channels = 1 if data.ndim == 1 else data.shape[1]

        if sample_rate != ref_sample_rate:
            raise Epub2AudioError(
                f"WAV sample rate mismatch at index {idx}: "
                f"expected {ref_sample_rate} Hz, got {sample_rate} Hz "
                f"(file: {path})."
            )
        if channels != ref_channels:
            raise Epub2AudioError(
                f"WAV channel count mismatch at index {idx}: "
                f"expected {ref_channels} channel(s), got {channels} "
                f"(file: {path})."
            )
        all_arrays.append(data)

    combined: np.ndarray = np.concatenate(all_arrays, axis=0)

    try:
        sf.write(str(tmp_path), combined, ref_sample_rate, subtype="FLOAT")
        os.replace(tmp_path, output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
