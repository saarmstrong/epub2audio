"""Metadata shim — forward-looking alias over ``epub2audio.audio.metadata``
and ``epub2audio.epub.metadata``.

``Feature.md`` proposes a top-level ``metadata/`` module in the target project
layout.  This shim re-exports the metadata-related public API from its current
homes so that new code can import from ``epub2audio.metadata`` without a
disruptive restructure of the existing packages.

All real logic lives in ``epub2audio.audio.metadata`` (ID3 embedding) and
``epub2audio.epub.metadata`` (EPUB OPF extraction).  This module is intentionally
thin — no business logic, no duplicate implementations.

Example::

    from epub2audio.metadata import embed_metadata, extract_metadata, BookMetadata
"""

from __future__ import annotations

from epub2audio.audio.metadata import embed_metadata
from epub2audio.epub.metadata import extract_metadata
from epub2audio.models import BookMetadata

__all__ = [
    "BookMetadata",
    "embed_metadata",
    "extract_metadata",
]
