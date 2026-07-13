"""XHTML to plain-text conversion for epub2audio.

Converts EPUB XHTML spine documents to clean narration text suitable for
TTS synthesis.  The cleanup rules are intentionally conservative: they remove
non-narrated markup (scripts, navigation, footnote refs) and convert
structural elements (lists, tables, paragraphs) to text equivalents, but they
never alter the wording of prose content.

Full footnote handling (skip / inline / end-of-chapter modes) is deferred to
Milestone 5; for M2 footnote ``<aside>`` elements are stripped entirely.
"""

from __future__ import annotations

import re

import bs4

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _epub_type_value(tag: bs4.Tag) -> str:
    """Return the normalised epub:type string for a tag, or empty string."""
    val = tag.get("epub:type", tag.get("type", ""))
    if isinstance(val, list):
        return " ".join(val).lower()
    return str(val).lower()


def _extract_fragment(
    body: bs4.Tag,
    start_fragment: str,
    end_fragment: str | None,
) -> bs4.Tag:
    """Limit a body element to the subtree rooted at *start_fragment*.

    Searches *body* for an element whose ``id`` attribute equals
    *start_fragment*.  Two cases:

    * **Block container** (``section``, ``div``, ``article``, ``main``): the
      element itself is returned directly as the new scope.  *end_fragment*
      is ignored because the container boundary already delimits the section.
    * **Other element** (e.g. ``h1``, ``span``): all siblings *before* the
      start element are removed from *body*.  If *end_fragment* is given,
      all siblings at or after the element with that id are also removed.
      The modified *body* is returned.

    If *start_fragment* is not found, *body* is returned unchanged (graceful
    degradation to full-document extraction).

    Args:
        body: The ``<body>`` element (or soup root) to search within.
        start_fragment: ``id`` attribute value of the start element.
        end_fragment: ``id`` attribute value of the exclusive end element,
            or ``None`` to extract to end of document.

    Returns:
        A :class:`bs4.Tag` representing the fragment scope.
    """
    start_el = body.find(id=start_fragment)
    if start_el is None or not isinstance(start_el, bs4.Tag):
        # Fragment not found; fall back to full-document extraction.
        return body

    # Self-contained block containers are returned directly.
    if start_el.name in ("section", "div", "article", "main"):
        return start_el

    # Heading/inline element: carve out the relevant range in-place.
    # Remove all preceding siblings of start_el.
    for sibling in list(start_el.previous_siblings):
        sibling.extract()

    # If end_fragment is given, remove everything from that element onward.
    if end_fragment is not None:
        end_el = body.find(id=end_fragment)
        if end_el is not None and isinstance(end_el, bs4.Tag):
            for sibling in list(end_el.next_siblings):
                sibling.extract()
            end_el.extract()

    return body


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def xhtml_to_text(
    content: bytes,
    *,
    start_fragment: str | None = None,
    end_fragment: str | None = None,
) -> str:
    """Convert XHTML bytes to clean plain text suitable for TTS narration.

    Applies the following rules in order:

    1. Strip ``<script>``, ``<style>``, ``<nav>`` elements entirely.
    2. Strip footnote references: ``<a epub:type="noteref">``.
    3. Strip footnote content: ``<aside epub:type="footnote">`` (M5 deferred).
    4. Convert ``<li>`` items to ``• item`` lines.
    5. Convert ``<br>`` to newlines.
    6. Handle ``<table>``: extract cell text in row order, cells joined with
       `` | ``.
    7. Preserve paragraph structure: each ``<p>`` becomes its own paragraph
       separated by a blank line.
    8. Emit image alt text for meaningful ``<img alt="...">`` values as
       ``[Image: alt text]``.
    9. Collapse resulting whitespace to a single clean string.

    When *start_fragment* is provided, only the portion of the document
    starting at the element whose ``id`` equals *start_fragment* is
    extracted.  *end_fragment* (if given) marks the exclusive end boundary.
    See :func:`_extract_fragment` for details.

    Args:
        content: Raw XHTML document bytes.
        start_fragment: ``id`` attribute of the element where extraction
            begins, or ``None`` to extract the whole document.
        end_fragment: ``id`` attribute of the exclusive end element, or
            ``None`` to extract to end of document.  Ignored when
            *start_fragment* is ``None``.

    Returns:
        A single string of plain text with normalised internal whitespace and
        paragraph breaks represented as double newlines.
    """
    # Parse as XML (XHTML is XML): avoids XMLParsedAsHTMLWarning and preserves
    # namespaced attributes such as ``epub:type``.
    soup = bs4.BeautifulSoup(content, features="xml")

    # Work on <body> only — the <head> title is not narrated.
    # soup.find() can return Tag | NavigableString | None; we need a Tag to
    # call find_all().  Fall back to the soup root (also a Tag subclass) when
    # no <body> is present.
    _body = soup.find("body")
    body: bs4.Tag = _body if isinstance(_body, bs4.Tag) else soup

    # Optionally restrict extraction to a named fragment within the document.
    if start_fragment is not None:
        body = _extract_fragment(body, start_fragment, end_fragment)

    # 1. Strip non-narrated block elements entirely.
    for tag in body.find_all(["script", "style", "nav"]):
        tag.decompose()

    # 2. Strip footnote references (inline anchors pointing to footnotes).
    for tag in body.find_all("a"):
        epub_type = _epub_type_value(tag)
        if "noteref" in epub_type:
            tag.decompose()

    # 3. Strip footnote content asides (deferred to M5 for inline/end modes).
    for tag in body.find_all("aside"):
        epub_type = _epub_type_value(tag)
        if "footnote" in epub_type:
            tag.decompose()

    # 4. Replace <br> with newline placeholder before text extraction.
    for br in body.find_all("br"):
        br.replace_with("\n")

    # 5. Convert <li> items — prepend bullet.
    for li in body.find_all("li"):
        # Get direct text of the li element
        li_text = li.get_text(separator=" ").strip()
        li.replace_with(f"\n• {li_text}\n")

    # 6. Handle tables: extract cell text in row order.
    for table in body.find_all("table"):
        rows: list[str] = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(separator=" ").strip() for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(" | ".join(cells))
        table.replace_with("\n" + "\n".join(rows) + "\n")

    # 7. Convert <p> elements to paragraphs separated by blank lines.
    for p in body.find_all("p"):
        p_text = p.get_text(separator=" ").strip()
        if p_text:
            p.replace_with(f"\n\n{p_text}\n\n")
        else:
            p.decompose()

    # 8. Handle image alt text — meaningful alt only.
    for img in body.find_all("img"):
        alt = img.get("alt", "").strip()
        if alt and alt.lower() not in ("", "image"):
            img.replace_with(f"[Image: {alt}]")
        else:
            img.decompose()

    # Extract remaining text from the processed tree.
    raw = body.get_text(separator=" ")

    # Normalize: collapse runs of blank lines to at most one blank line,
    # and collapse inline whitespace within each line.
    lines = [" ".join(line.split()) for line in raw.splitlines()]
    # Re-join and collapse multiple blank lines.
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text


def word_count(text: str) -> int:
    """Return the word count of a plain-text string.

    Args:
        text: Plain text (whitespace-normalised or not).

    Returns:
        Number of whitespace-separated tokens in *text*.
    """
    return len(text.split())
