"""Helpers for :class:`~epub2audio.models.AudioChunk` I/O and concatenation.

All WAV I/O uses :mod:`soundfile`; array operations use :mod:`numpy`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import soundfile as sf

from epub2audio.models import AudioChunk

if TYPE_CHECKING:
    pass


def save_chunk(chunk: AudioChunk, path: Path) -> None:
    """Write an :class:`AudioChunk` to a WAV file.

    Args:
        chunk: The audio chunk to persist.  ``chunk.data`` must be a NumPy
            array of float32 samples.
        path: Destination WAV file path.  Parent directories are created
            automatically.

    Raises:
        OSError: If the file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data: np.ndarray = np.asarray(chunk.data, dtype=np.float32)
    sf.write(str(path), data, chunk.sample_rate, subtype="FLOAT")


def load_chunk(path: Path) -> AudioChunk:
    """Load a WAV file into an :class:`AudioChunk`.

    Args:
        path: Path to an existing WAV file.

    Returns:
        An :class:`AudioChunk` whose ``data`` is a float32 NumPy array.

    Raises:
        FileNotFoundError: If *path* does not exist.
        OSError: If the file cannot be read by soundfile.
    """
    data, sample_rate = sf.read(str(path), dtype="float32", always_2d=False)
    return AudioChunk(sample_rate=sample_rate, data=data)


def concat_chunks(chunks: list[AudioChunk]) -> AudioChunk:
    """Concatenate a list of :class:`AudioChunk` objects into one.

    All chunks must share the same sample rate.  If *chunks* is empty an
    empty chunk at 24 000 Hz is returned.

    Args:
        chunks: Ordered list of audio chunks to concatenate.

    Returns:
        A single :class:`AudioChunk` containing all samples in order.

    Raises:
        ValueError: If chunks have mismatched sample rates.
    """
    if not chunks:
        return AudioChunk(sample_rate=24000, data=np.array([], dtype=np.float32))

    sample_rate = chunks[0].sample_rate
    for i, chunk in enumerate(chunks[1:], start=1):
        if chunk.sample_rate != sample_rate:
            raise ValueError(
                f"Cannot concatenate chunks with mismatched sample rates: "
                f"chunk 0 has {sample_rate} Hz, chunk {i} has {chunk.sample_rate} Hz."
            )

    arrays = [np.asarray(c.data, dtype=np.float32) for c in chunks]
    combined = np.concatenate(arrays, axis=0)
    return AudioChunk(sample_rate=sample_rate, data=combined)
