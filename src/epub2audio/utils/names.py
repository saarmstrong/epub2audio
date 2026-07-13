"""Filename sanitisation utilities for epub2audio MP3 output files.

Produces safe, portable filenames in the format ``NNN - Title.mp3`` that
work on Windows, macOS, and Linux filesystems.
"""

from __future__ import annotations

import re

# Characters forbidden in filenames on Windows (and many Linux filesystems)
_FORBIDDEN_RE = re.compile(r'[/\\:*?"<>|\x00-\x1f]')

# Windows reserved device names (case-insensitive)
_WINDOWS_RESERVED: frozenset[str] = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)

_MAX_FILENAME_LENGTH = 200
_EXTENSION = ".mp3"
_PREFIX_TEMPLATE = "{:03d} - "


def sanitize_filename(title: str, index: int) -> str:
    """Return a sanitized filename in the format ``NNN - Title.mp3``.

    Handles Windows reserved names, forbidden characters, overly long names,
    and trailing dots / spaces.

    Args:
        title: Raw chapter title (may contain any characters).
        index: 1-based chapter number used for the numeric prefix.

    Returns:
        A safe filename string including the ``.mp3`` extension.
    """
    prefix = _PREFIX_TEMPLATE.format(index)  # e.g. "001 - "

    # Replace forbidden characters with underscores
    safe_title = _FORBIDDEN_RE.sub("_", title)

    # Strip trailing dots and spaces from the title portion (Windows restriction)
    safe_title = safe_title.rstrip(". ")

    # Ensure the title is non-empty after stripping
    if not safe_title:
        safe_title = f"Chapter_{index:03d}"

    # Assemble full filename
    full = prefix + safe_title + _EXTENSION

    # Truncate if over the length limit, preserving prefix and extension
    if len(full) > _MAX_FILENAME_LENGTH:
        max_title_len = _MAX_FILENAME_LENGTH - len(prefix) - len(_EXTENSION)
        safe_title = safe_title[:max_title_len].rstrip(". ")
        full = prefix + safe_title + _EXTENSION

    # Check for Windows reserved names on the full stem (prefix + title)
    stem = full[: -len(_EXTENSION)]  # everything before ".mp3"
    if stem.upper() in _WINDOWS_RESERVED:
        safe_title = safe_title + "_"
        full = prefix + safe_title + _EXTENSION

    return full


def make_unique(names: list[str]) -> list[str]:
    """Append ``-2``, ``-3``, … suffixes to deduplicate a list of filenames.

    The first occurrence of any duplicated name is left unchanged; subsequent
    occurrences receive a numeric suffix inserted before the ``.mp3`` extension.

    Deduplication is case-insensitive (as required by case-insensitive
    filesystems such as macOS HFS+ and Windows NTFS).

    Args:
        names: List of already-sanitized filenames (each ending with ``.mp3``).

    Returns:
        A new list of the same length with collisions resolved.
    """
    seen: dict[str, int] = {}  # lower-case name → next counter
    result: list[str] = []

    for name in names:
        key = name.lower()
        if key not in seen:
            seen[key] = 2  # next suffix if this name is seen again
            result.append(name)
        else:
            # Build a unique variant by inserting the counter before ".mp3"
            counter = seen[key]
            if name.lower().endswith(_EXTENSION):
                stem = name[: -len(_EXTENSION)]
                new_name = f"{stem}-{counter}{_EXTENSION}"
            else:
                new_name = f"{name}-{counter}"

            # Keep incrementing until we find a slot not already in use
            new_key = new_name.lower()
            while new_key in seen:
                counter += 1
                if name.lower().endswith(_EXTENSION):
                    stem = name[: -len(_EXTENSION)]
                    new_name = f"{stem}-{counter}{_EXTENSION}"
                else:
                    new_name = f"{name}-{counter}"
                new_key = new_name.lower()

            seen[key] = counter + 1
            seen[new_key] = 2
            result.append(new_name)

    return result
