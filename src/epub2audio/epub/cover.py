"""Cover image extraction from an EpubBook.

Tries multiple discovery strategies in order of reliability:

1. OPF ``<meta name="cover">`` attribute → item ID lookup
2. Item with id ``"cover-image"`` or ``"cover"``
3. First image item with ``epub:type="cover-image"`` in its properties
4. ``<img>`` element in the first spine document whose class/id contains "cover"
5. None — no cover found
"""

from __future__ import annotations

import warnings

import bs4
import ebooklib
import ebooklib.epub
from bs4 import XMLParsedAsHTMLWarning


def extract_cover(book: ebooklib.epub.EpubBook) -> bytes | None:
    """Return cover image bytes, or None if no cover found.

    Searches the EpubBook using four fallback strategies so that both
    EPUB2 and EPUB3 cover conventions are handled.

    Args:
        book: A fully parsed :class:`ebooklib.epub.EpubBook`.

    Returns:
        Raw image bytes (JPEG or PNG) of the cover, or ``None`` if no cover
        could be located.
    """
    # Strategy 1: OPF <meta name="cover"> → item id
    cover_meta = book.get_metadata("OPF", "cover")
    if cover_meta:
        cover_id, _attrs = cover_meta[0]
        item = book.get_item_with_id(str(cover_id))
        if item is not None and item.get_type() == ebooklib.ITEM_IMAGE:
            return bytes(item.get_content())

    # Strategy 2: item with well-known cover id
    for cover_id in ("cover-image", "cover"):
        item = book.get_item_with_id(cover_id)
        if item is not None and item.get_type() == ebooklib.ITEM_IMAGE:
            return bytes(item.get_content())

    # Strategy 3: image item whose properties contain "cover-image"
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        props: str = getattr(item, "properties", "") or ""
        if "cover-image" in props.split():
            return bytes(item.get_content())

    # Strategy 4: <img> in the first spine document with cover in class/id
    for idref, _linear in book.spine:
        spine_item = book.get_item_with_id(idref)
        if spine_item is None:
            continue

        try:
            content = spine_item.get_content()
        except Exception:
            continue

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = bs4.BeautifulSoup(content, "lxml")
        for img_tag in soup.find_all("img"):
            if not isinstance(img_tag, bs4.Tag):
                continue
            cls_list = img_tag.get("class", [])
            if isinstance(cls_list, str):
                cls_list = cls_list.split()
            img_id = str(img_tag.get("id", ""))
            combined = " ".join(cls_list) + " " + img_id
            if "cover" in combined.lower():
                src = img_tag.get("src", "")
                if src:
                    img_item = book.get_item_with_href(str(src))
                    if img_item is not None:
                        return bytes(img_item.get_content())
        # Only check the first spine item
        break

    return None
