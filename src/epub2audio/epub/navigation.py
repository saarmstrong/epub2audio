"""Spine and TOC navigation extraction for epub2audio.

Builds a reading-order list of :class:`~epub2audio.models.NavigationEntry`
objects by examining the EPUB's Table of Contents.  The extraction order
of preference is:

1. ``book.toc`` populated from EPUB3 nav or EPUB2 NCX by ebooklib
2. Spine fallback (one entry per spine item, no titles)

**Critical constraint**: spine order (``book.spine``) defines reading order.
Filename / alphabetical order is never assumed to match reading order.
"""

from __future__ import annotations

import ebooklib
import ebooklib.epub

from epub2audio.models import NavigationEntry


def _split_href(href: str) -> tuple[str, str | None]:
    """Split an href into (doc_path, fragment).

    Args:
        href: A relative URL such as ``"chapter1.xhtml#section-2"``.

    Returns:
        A tuple of ``(doc_path, fragment)`` where *fragment* is ``None``
        if no ``#`` was present.
    """
    if "#" in href:
        doc_path, fragment = href.split("#", 1)
        return doc_path, fragment or None
    return href, None


def _flatten_toc(
    toc: list[object],
    depth: int = 0,
) -> list[NavigationEntry]:
    """Recursively flatten a nested ebooklib TOC into a list of NavigationEntry.

    ebooklib represents the TOC as a list whose elements are either:
    - :class:`ebooklib.epub.Link` — a leaf entry
    - A 2-tuple of ``(Section, [children])`` — a nested section

    Args:
        toc: ebooklib TOC list (may be nested).
        depth: Current nesting depth (0 = top-level).

    Returns:
        Flat list of :class:`~epub2audio.models.NavigationEntry` in TOC order.
    """
    entries: list[NavigationEntry] = []

    for item in toc:
        if isinstance(item, ebooklib.epub.Link):
            doc_path, fragment = _split_href(item.href)
            entries.append(
                NavigationEntry(
                    title=item.title or "",
                    doc_path=doc_path,
                    fragment=fragment,
                    depth=depth,
                )
            )
        elif isinstance(item, tuple) and len(item) == 2:
            section, children = item
            # Section itself may have an href (points to the first child's file)
            if isinstance(section, ebooklib.epub.Section) and section.href:
                doc_path, fragment = _split_href(section.href)
                entries.append(
                    NavigationEntry(
                        title=section.title or "",
                        doc_path=doc_path,
                        fragment=fragment,
                        depth=depth,
                    )
                )
            elif isinstance(section, ebooklib.epub.Section):
                entries.append(
                    NavigationEntry(
                        title=section.title or "",
                        doc_path="",
                        fragment=None,
                        depth=depth,
                    )
                )
            if isinstance(children, list):
                entries.extend(_flatten_toc(children, depth=depth + 1))

    return entries


def _spine_fallback(book: ebooklib.epub.EpubBook) -> list[NavigationEntry]:
    """Produce one NavigationEntry per spine item as a last resort.

    Args:
        book: An opened EpubBook whose spine defines reading order.

    Returns:
        One :class:`~epub2audio.models.NavigationEntry` per spine document,
        with empty title and no fragment.
    """
    entries: list[NavigationEntry] = []
    for idref, _linear in book.spine:
        item = book.get_item_with_id(idref)
        if item is None:
            continue
        entries.append(
            NavigationEntry(
                title="",
                doc_path=item.get_name(),
                fragment=None,
                depth=0,
            )
        )
    return entries


def extract_navigation(book: ebooklib.epub.EpubBook) -> list[NavigationEntry]:
    """Extract navigation entries in spine reading order.

    Tries the TOC populated by ebooklib (from EPUB3 nav or EPUB2 NCX) first,
    then falls back to bare spine order.

    **Never assumes filename order equals reading order.**  The EPUB spine
    defines order; the TOC/NCX provides human-readable titles.

    Args:
        book: A fully parsed EpubBook (e.g. from
            :func:`~epub2audio.epub.reader.open_epub`).

    Returns:
        A flat list of :class:`~epub2audio.models.NavigationEntry` objects
        ordered according to the book's TOC / NCX / spine.
    """
    toc: list[object] = list(book.toc) if book.toc else []

    if toc:
        entries = _flatten_toc(toc, depth=0)
        if entries:
            return entries

    # Neither nav nor NCX produced entries — use bare spine
    return _spine_fallback(book)
