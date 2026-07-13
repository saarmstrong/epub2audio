"""Atomic read/write of :class:`~epub2audio.models.ConversionManifest` for epub2audio.

Manifests capture full run state so interrupted conversions can be resumed
without re-synthesizing already-completed segments.  All writes are atomic:
JSON is written to a ``.tmp`` sidecar then renamed with :func:`os.replace`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from epub2audio.config import Settings
from epub2audio.models import ConversionManifest
from epub2audio.utils.files import atomic_write


def write_manifest(manifest: ConversionManifest, path: Path) -> None:
    """Serialize and atomically write a :class:`ConversionManifest` to disk.

    The manifest is serialized to JSON using Pydantic's
    :meth:`~pydantic.BaseModel.model_dump_json`, then written atomically via
    :func:`~epub2audio.utils.files.atomic_write` (write to ``.tmp`` sidecar,
    then :func:`os.replace`).

    Args:
        manifest: The manifest to persist.
        path: Destination file path (typically ``<output_dir>/manifest.json``).

    Raises:
        OSError: If the directory cannot be created or the file cannot be written.
    """
    content = manifest.model_dump_json(indent=2).encode("utf-8")
    atomic_write(path, content)


def read_manifest(path: Path) -> ConversionManifest:
    """Deserialize a :class:`ConversionManifest` from a JSON file.

    Args:
        path: Path to the manifest JSON file written by :func:`write_manifest`.

    Returns:
        The deserialized :class:`ConversionManifest`.

    Raises:
        FileNotFoundError: If *path* does not exist.
        pydantic.ValidationError: If the JSON does not match the manifest schema.
    """
    return ConversionManifest.model_validate_json(path.read_text(encoding="utf-8"))


def epub_fingerprint(epub_path: Path) -> str:
    """Return a SHA-256 hex digest of the EPUB file bytes.

    Used to detect whether the source EPUB has changed between runs so that
    the resume logic can reject a stale manifest.

    Args:
        epub_path: Path to the EPUB file.

    Returns:
        A 64-character lowercase hex string (SHA-256 of the raw file bytes).

    Raises:
        FileNotFoundError: If *epub_path* does not exist.
        OSError: If the file cannot be read.
    """
    digest = hashlib.sha256(epub_path.read_bytes()).hexdigest()
    return digest


def config_hash(settings: Settings) -> str:
    """Return a SHA-256 hex digest of the JSON-serialized settings.

    Used to detect configuration changes that would invalidate cached
    synthesis artifacts.

    Args:
        settings: The effective :class:`~epub2audio.config.Settings` for
            this conversion run.

    Returns:
        A 64-character lowercase hex string (SHA-256 of the settings JSON).
    """
    serialized = settings.model_dump_json().encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
