"""Safe EPUB file opening with ZIP security guards.

All security checks are applied before ebooklib ever touches the file:

1. ZIP path traversal guard (``..`` components or absolute paths)
2. Zip-bomb guard (single entry > 100 MB; total uncompressed > 500 MB)
3. DRM detection via ``META-INF/encryption.xml``
4. General exception wrapping so callers only see :class:`InvalidEpubError`
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import ebooklib.epub

from epub2audio.errors import DrmProtectedEpubError, InvalidEpubError

# Thresholds for zip-bomb detection
_MAX_SINGLE_ENTRY_BYTES: int = 100 * 1024 * 1024  # 100 MB
_MAX_TOTAL_BYTES: int = 500 * 1024 * 1024  # 500 MB


def open_epub(path: Path) -> ebooklib.epub.EpubBook:
    """Open an EPUB file safely, guarding against common attacks and errors.

    The function inspects the raw ZIP archive before delegating to ebooklib
    so that malicious entries are caught before any content is decompressed.

    Args:
        path: Filesystem path to the ``.epub`` file.

    Returns:
        A fully parsed :class:`ebooklib.epub.EpubBook` ready for further
        processing.

    Raises:
        InvalidEpubError: The file is missing, not a valid ZIP/EPUB, contains
            path-traversal entries, or exceeds the zip-bomb size thresholds.
        DrmProtectedEpubError: The EPUB contains a non-empty
            ``META-INF/encryption.xml`` — DRM-protected content.
    """
    try:
        zf = zipfile.ZipFile(path, "r")
    except FileNotFoundError:
        raise InvalidEpubError(f"EPUB file not found: {path}") from None
    except zipfile.BadZipFile as exc:
        raise InvalidEpubError(f"Not a valid ZIP/EPUB file: {path} — {exc}") from exc

    with zf:
        _check_zip_entries(zf, path)
        _check_drm(zf, path)

    # All guards passed — hand off to ebooklib
    try:
        return ebooklib.epub.read_epub(str(path))
    except Exception as exc:
        raise InvalidEpubError(f"ebooklib could not parse EPUB: {exc}") from exc


def _check_zip_entries(zf: zipfile.ZipFile, path: Path) -> None:
    """Validate all ZIP entry names and sizes.

    Raises:
        InvalidEpubError: On path traversal attempt or zip-bomb.
    """
    total_bytes = 0

    for info in zf.infolist():
        name = info.filename

        # Path traversal guard
        if name.startswith("/") or ".." in name.split("/"):
            raise InvalidEpubError(f"ZIP path traversal detected in EPUB {path!r}: entry {name!r}")

        uncompressed = info.file_size

        # Single-entry bomb guard
        if uncompressed > _MAX_SINGLE_ENTRY_BYTES:
            raise InvalidEpubError(
                f"ZIP entry {name!r} is too large ({uncompressed} bytes) in {path!r}"
            )

        total_bytes += uncompressed

        # Aggregate bomb guard
        if total_bytes > _MAX_TOTAL_BYTES:
            raise InvalidEpubError(
                f"EPUB total uncompressed size exceeds limit ({total_bytes} bytes) in {path!r}"
            )


def _check_drm(zf: zipfile.ZipFile, path: Path) -> None:
    """Detect Adobe DRM via META-INF/encryption.xml.

    Raises:
        DrmProtectedEpubError: If ``META-INF/encryption.xml`` is present and
            non-empty.
    """
    try:
        data = zf.read("META-INF/encryption.xml")
    except KeyError:
        return  # No encryption.xml — not DRM protected

    if data.strip():
        raise DrmProtectedEpubError(
            f"EPUB is DRM-protected (META-INF/encryption.xml present): {path!r}"
        )
