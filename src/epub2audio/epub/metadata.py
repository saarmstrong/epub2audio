"""OPF metadata extraction for epub2audio.

Extracts Dublin Core metadata from an :class:`ebooklib.epub.EpubBook` and
returns a :class:`~epub2audio.models.BookMetadata` instance.  All fields
have safe fallbacks so callers never receive ``None`` for required fields.
"""

from __future__ import annotations

from typing import Any

import ebooklib.epub

from epub2audio.models import BookMetadata


def _first_dc(book: ebooklib.epub.EpubBook, key: str) -> str | None:
    """Return the first Dublin Core value for *key*, or ``None``.

    :func:`ebooklib.epub.EpubBook.get_metadata` returns a list of
    ``(value, attributes)`` tuples.  We want only the string value of the
    first entry.

    Args:
        book: Opened EpubBook instance.
        key: Dublin Core element name (e.g. ``"creator"``, ``"language"``).

    Returns:
        The first string value, or ``None`` if the metadata is absent or empty.
    """
    entries: list[tuple[Any, Any]] = book.get_metadata("DC", key)
    if not entries:
        return None
    value, _attrs = entries[0]
    if not value or not str(value).strip():
        return None
    return str(value).strip()


def extract_metadata(book: ebooklib.epub.EpubBook) -> BookMetadata:
    """Extract book metadata from an opened EpubBook.

    All fields that are absent or empty in the OPF fall back to safe defaults
    so downstream code can always treat required fields as non-None strings.

    Args:
        book: A fully parsed EpubBook (e.g. from
            :func:`~epub2audio.epub.reader.open_epub`).

    Returns:
        A :class:`~epub2audio.models.BookMetadata` populated from the OPF
        ``<metadata>`` section.
    """
    # title: ebooklib exposes this directly on the book object
    raw_title: str | None = book.title if book.title and str(book.title).strip() else None
    title = raw_title or "Unknown Title"

    author = _first_dc(book, "creator") or "Unknown Author"
    language = _first_dc(book, "language") or "en"
    identifier = _first_dc(book, "identifier") or ""
    publisher = _first_dc(book, "publisher")
    date = _first_dc(book, "date")
    rights = _first_dc(book, "rights")

    return BookMetadata(
        title=title,
        author=author,
        language=language,
        identifier=identifier,
        publisher=publisher,
        date=date,
        rights=rights,
    )
