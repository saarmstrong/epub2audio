"""Safe temporary file, atomic write, and disk-space utilities for epub2audio."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from epub2audio.errors import Epub2AudioError


def atomic_write(dest: Path, content: bytes) -> None:
    """Write *content* to *dest* atomically.

    Writes to a ``.tmp`` intermediate file in the same directory as *dest*,
    then calls :func:`os.replace` so the operation is atomic on POSIX systems.
    The intermediate file is cleaned up on failure.

    Args:
        dest: Destination path (will be created or overwritten).
        content: Raw bytes to write.

    Raises:
        OSError: If the write or replace operation fails.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(dest.suffix + ".tmp")
    try:
        tmp_path.write_bytes(content)
        os.replace(tmp_path, dest)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def temp_path(suffix: str = "") -> Path:
    """Return a :class:`~pathlib.Path` pointing to a new temporary file.

    The caller is responsible for deleting the file after use.  The file is
    created (zero-length) by :func:`tempfile.mkstemp` so that the path is
    reserved immediately.

    Args:
        suffix: Optional filename suffix, e.g. ``".wav"`` or ``".mp3"``.

    Returns:
        An absolute :class:`~pathlib.Path` to the newly created temp file.
    """
    fd, path_str = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return Path(path_str)


def check_disk_space(path: Path, required_bytes: int) -> None:
    """Raise :class:`~epub2audio.errors.Epub2AudioError` if free space is insufficient.

    Checks the free disk space on the filesystem that contains *path*.  If the
    available space is less than *required_bytes*, an error is raised before any
    work begins so that partial outputs are not written.

    Args:
        path: Any path on the target filesystem (the file does not need to
            exist; its parent directory is checked).
        required_bytes: Minimum required free bytes.

    Raises:
        Epub2AudioError: If free space < *required_bytes*.
        OSError: If the disk-usage query itself fails.
    """
    check_path = path if path.exists() else path.parent
    usage = shutil.disk_usage(check_path)
    if usage.free < required_bytes:
        required_mb = required_bytes / (1024 * 1024)
        free_mb = usage.free / (1024 * 1024)
        raise Epub2AudioError(
            f"Insufficient disk space: need {required_mb:.1f} MB, "
            f"only {free_mb:.1f} MB available on {check_path}."
        )
