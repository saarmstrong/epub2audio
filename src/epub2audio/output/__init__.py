"""Output packaging shim — forward-looking alias over ``epub2audio.audio``.

``Feature.md`` proposes a top-level ``output/`` module in the target project
layout.  This shim re-exports the audio-packaging and encoding entry points
from their current homes in ``epub2audio.audio`` so that new code (and future
refactoring) can import from ``epub2audio.output`` without requiring a
disruptive rename of the existing ``audio/`` package.

All real logic lives in ``epub2audio.audio``.  This module is intentionally
thin — it only imports and re-exports.  It must never contain business logic
or duplicate implementations.

Example::

    from epub2audio.output import encode_mp3, build_m4b, normalize_loudness
"""

from __future__ import annotations

from epub2audio.audio.concatenate import concatenate_wavs
from epub2audio.audio.encode import encode_aac, encode_mp3
from epub2audio.audio.mux_m4b import build_m4b
from epub2audio.audio.normalize import normalize_loudness
from epub2audio.audio.validate import validate_audio, validate_mp3

__all__ = [
    "build_m4b",
    "concatenate_wavs",
    "encode_aac",
    "encode_mp3",
    "normalize_loudness",
    "validate_audio",
    "validate_mp3",
]
