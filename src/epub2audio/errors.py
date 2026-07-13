"""Domain exceptions for epub2audio.

This module is the base layer of the package.  It must never import from any
other epub2audio module.  All other modules may import from here.
"""

from __future__ import annotations


class Epub2AudioError(Exception):
    """Base class for all epub2audio domain errors.

    Catch this to handle any error raised by the epub2audio package without
    having to enumerate every subclass.
    """


class InvalidEpubError(Epub2AudioError):
    """Raised when an EPUB file is malformed, missing required OPF, or unreadable.

    This includes ZIP files that are corrupt, EPUBs that lack a valid
    ``container.xml``, and files that cannot be opened by ebooklib.
    """


class DrmProtectedEpubError(Epub2AudioError):
    """Raised when the EPUB file contains DRM encryption markers.

    Detected by the presence of a non-empty ``META-INF/encryption.xml`` entry
    inside the EPUB ZIP.  epub2audio will not attempt to decrypt or process
    DRM-protected content.
    """


class MissingDependencyError(Epub2AudioError):
    """Raised when a required external tool cannot be found on the system.

    Args:
        dependency: Name of the missing tool, e.g. ``"ffmpeg"`` or ``"espeak-ng"``.
        message: Optional human-readable description of what is needed.
    """

    dependency: str

    def __init__(self, dependency: str, message: str = "") -> None:
        self.dependency = dependency
        full_message = message or f"Required dependency not found: {dependency}"
        super().__init__(full_message)


class UnsupportedLanguageError(Epub2AudioError):
    """Raised when a language code is not supported by the configured TTS voice.

    Args:
        language: BCP-47 language tag that has no Kokoro ``lang_code`` mapping.
        message: Optional human-readable description.
    """

    language: str

    def __init__(self, language: str, message: str = "") -> None:
        self.language = language
        full_message = message or f"Unsupported language code: {language!r}"
        super().__init__(full_message)


class SegmentTooLongError(Epub2AudioError):
    """Raised when a text segment exceeds the TTS engine's maximum token length.

    Args:
        segment_length: Character length of the offending segment.
        message: Optional human-readable description.
    """

    segment_length: int

    def __init__(self, segment_length: int, message: str = "") -> None:
        self.segment_length = segment_length
        full_message = message or f"Text segment is too long for TTS engine: {segment_length} chars"
        super().__init__(full_message)


class FingerprintMismatchError(Epub2AudioError):
    """Raised when the resume fingerprint does not match the current EPUB.

    This indicates the EPUB file has changed since the manifest was written.
    The manifest must be discarded and a fresh conversion started.
    """


class ConfigChangedError(Epub2AudioError):
    """Raised when the config hash changed in ways that require re-synthesis.

    Args:
        changed_keys: List of configuration keys whose values differ from the
            manifest's ``config_snapshot``.
        message: Optional human-readable description.
    """

    changed_keys: list[str]

    def __init__(self, changed_keys: list[str], message: str = "") -> None:
        self.changed_keys = changed_keys
        full_message = (
            message
            or f"Configuration changed for keys: {', '.join(changed_keys)}; re-synthesis required"
        )
        super().__init__(full_message)
