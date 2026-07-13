"""Programmatic EPUB factory for tests.

Builds self-contained EPUB files using ebooklib with only placeholder text.
No copyrighted content is included anywhere in this module.

Key design invariant for spine-order tests:
    Chapter 2's XHTML filename sorts alphabetically BEFORE Chapter 1's filename
    (e.g. ``a_chapter.xhtml`` holds Chapter Two, ``b_chapter.xhtml`` holds
    Chapter One).  This lets tests assert that reading order comes from the
    spine/nav, not from filename sort order.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from ebooklib import epub

# ---------------------------------------------------------------------------
# Default placeholder chapters (no copyrighted content)
# ---------------------------------------------------------------------------

DEFAULT_CHAPTERS: list[tuple[str, str]] = [
    (
        "Chapter One",
        "This is the first chapter of the test book. "
        "It contains placeholder text for testing purposes only. "
        "The quick brown fox jumps over the lazy dog. " * 20,
    ),
    (
        "Chapter Two",
        "This is the second chapter of the test book. "
        "More placeholder text follows here for testing. "
        "Pack my box with five dozen liquor jugs. " * 20,
    ),
]

# ---------------------------------------------------------------------------
# Minimal 1×1 white PNG (no external dependencies)
# ---------------------------------------------------------------------------


def _make_minimal_png() -> bytes:
    """Build a 1×1 white RGB PNG using only stdlib struct + zlib."""

    def _chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFF_FFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    # IHDR: width=1, height=1, bit_depth=8, color_type=2 (RGB), compress=0, filter=0, interlace=0
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    # Single scanline: filter byte 0x00, then R=255 G=255 B=255
    idat = _chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    iend = _chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


_MINIMAL_PNG: bytes = _make_minimal_png()

# ---------------------------------------------------------------------------
# XHTML template helpers
# ---------------------------------------------------------------------------


def _chapter_xhtml(title: str, body_text: str) -> str:
    """Return a valid XHTML5 document for a single chapter."""
    # Wrap each sentence-group as a paragraph for realistic structure
    paragraphs = "".join(
        f"<p>{para.strip()}</p>\n" for para in body_text.split(".") if para.strip()
    )
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>\n"
        f"  <head><title>{title}</title></head>\n"
        "  <body>\n"
        f"    <h1>{title}</h1>\n"
        f"    {paragraphs}\n"
        "  </body>\n"
        "</html>\n"
    )


def _multi_chapter_xhtml(chapters: list[tuple[str, str]]) -> str:
    """Return a valid XHTML5 document containing all chapters via <h1> + id anchors."""
    sections: list[str] = []
    for idx, (title, text) in enumerate(chapters, start=1):
        anchor = f"ch-{idx}"
        paragraphs = "".join(f"<p>{para.strip()}</p>\n" for para in text.split(".") if para.strip())
        sections.append(
            f"    <section id='{anchor}'>\n"
            f"      <h1>{title}</h1>\n"
            f"      {paragraphs}\n"
            f"    </section>\n"
        )
    body = "\n".join(sections)
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>\n"
        "  <head><title>Multi-Chapter Document</title></head>\n"
        "  <body>\n"
        f"{body}"
        "  </body>\n"
        "</html>\n"
    )


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_simple_epub3(
    output_path: Path,
    title: str = "Test Book",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
    include_cover: bool = True,
) -> Path:
    """Build a simple EPUB3 with nav document and optional cover.

    The XHTML filenames are intentionally assigned so that alphabetical
    filename order does NOT match reading order:

    * Chapter Two  → ``a_chapter.xhtml``  (sorts first alphabetically)
    * Chapter One  → ``b_chapter.xhtml``  (sorts second alphabetically)

    The spine and nav both declare Chapter One → Chapter Two, so any
    implementation that naively sorts by filename will produce the wrong order.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.
        chapters: List of ``(chapter_title, chapter_text)`` tuples.
                  Defaults to :data:`DEFAULT_CHAPTERS` (2 chapters).
        include_cover: If ``True``, embed a minimal 1×1 PNG cover image.

    Returns:
        *output_path* after writing.
    """
    if chapters is None:
        chapters = DEFAULT_CHAPTERS

    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-epub3-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Cover image
    if include_cover:
        cover_item = epub.EpubItem(
            uid="cover-image",
            file_name="images/cover.png",
            media_type="image/png",
            content=_MINIMAL_PNG,
        )
        book.add_item(cover_item)
        book.add_metadata("OPF", "cover", "cover-image", {})

    # Build chapter items with deliberately mismatched filenames.
    # Filename assignment (for 2+ chapters):
    #   chapters[0] (Chapter One)  → b_chapter_01.xhtml  (sorts AFTER a_chapter_02)
    #   chapters[1] (Chapter Two)  → a_chapter_02.xhtml  (sorts BEFORE b_chapter_01)
    # For 3+ chapters the pattern continues: c_chapter_03, etc.
    #
    # The spine and nav are set to reading order [ch1, ch2, …] so the correct
    # implementation ignores filename order and follows spine/nav.
    epub_items: list[epub.EpubHtml] = []
    for idx, (ch_title, ch_text) in enumerate(chapters, start=1):
        # Flip first two filenames so alpha != reading order.
        if idx == 1:
            fname = f"b_chapter_{idx:02d}.xhtml"
        elif idx == 2:
            fname = f"a_chapter_{idx:02d}.xhtml"
        else:
            fname = f"c_chapter_{idx:02d}.xhtml"

        item = epub.EpubHtml(
            title=ch_title,
            file_name=fname,
            lang="en",
        )
        item.content = _chapter_xhtml(ch_title, ch_text).encode("utf-8")
        book.add_item(item)
        epub_items.append(item)

    # TOC in reading order (Chapter One first)
    book.toc = [
        epub.Link(item.file_name, item.title, f"ch{i + 1}") for i, item in enumerate(epub_items)
    ]

    # NCX + Nav
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Spine in reading order
    book.spine = ["nav", *epub_items]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_simple_epub2(
    output_path: Path,
    title: str = "Test Book EPUB2",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
) -> Path:
    """Build a simple EPUB2 with NCX ``toc.ncx``.

    Like :func:`build_simple_epub3`, the XHTML filenames are intentionally
    mismatched with reading order so that spine-order tests are meaningful.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.
        chapters: List of ``(chapter_title, chapter_text)`` tuples.
                  Defaults to :data:`DEFAULT_CHAPTERS` (2 chapters).

    Returns:
        *output_path* after writing.
    """
    if chapters is None:
        chapters = DEFAULT_CHAPTERS

    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-epub2-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    epub_items: list[epub.EpubHtml] = []
    for idx, (ch_title, ch_text) in enumerate(chapters, start=1):
        # Same filename-flip as epub3 builder.
        if idx == 1:
            fname = f"b_chapter_{idx:02d}.xhtml"
        elif idx == 2:
            fname = f"a_chapter_{idx:02d}.xhtml"
        else:
            fname = f"c_chapter_{idx:02d}.xhtml"

        item = epub.EpubHtml(
            title=ch_title,
            file_name=fname,
            lang="en",
        )
        item.content = _chapter_xhtml(ch_title, ch_text).encode("utf-8")
        book.add_item(item)
        epub_items.append(item)

    # TOC / NCX in reading order
    book.toc = [
        epub.Link(item.file_name, item.title, f"ch{i + 1}") for i, item in enumerate(epub_items)
    ]
    book.add_item(epub.EpubNcx())

    # Spine in reading order (no nav item for EPUB2)
    book.spine = epub_items

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_multi_chapter_single_file(
    output_path: Path,
    title: str = "Multi-Chapter Single File",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
) -> Path:
    """Build an EPUB where multiple chapters live in a single XHTML file.

    Chapter headings use ``<h1>`` elements with ``id`` attributes (``ch-1``,
    ``ch-2``, …).  The nav document references fragment anchors so that a
    correct implementation resolves ``chapter1.xhtml#ch-2`` into
    ``doc_path="chapter1.xhtml"`` and ``fragment="ch-2"``.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.
        chapters: List of ``(chapter_title, chapter_text)`` tuples.
                  Defaults to :data:`DEFAULT_CHAPTERS` (2 chapters).

    Returns:
        *output_path* after writing.
    """
    if chapters is None:
        chapters = DEFAULT_CHAPTERS

    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-multi-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    fname = "chapter1.xhtml"
    single_item = epub.EpubHtml(
        title=title,
        file_name=fname,
        lang="en",
    )
    single_item.content = _multi_chapter_xhtml(chapters).encode("utf-8")
    book.add_item(single_item)

    # TOC uses fragment anchors: chapter1.xhtml#ch-1, chapter1.xhtml#ch-2, …
    book.toc = [
        epub.Link(f"{fname}#ch-{i + 1}", ch_title, f"ch{i + 1}")
        for i, (ch_title, _) in enumerate(chapters)
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", single_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_no_nav_epub(
    output_path: Path,
    title: str = "No Nav Test Book",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] | None = None,
) -> Path:
    """Build an EPUB with an empty NCX navMap and no EPUB3 nav document.

    Used to test the spine-fallback path in ``epub/navigation.py``.  The
    book includes a minimal NCX (required by ebooklib to load the file) but
    the navMap is empty, so there are no TOC entries.  A correct
    implementation falls back to one :class:`NavigationEntry` per spine item
    with an empty title.

    Note on ebooklib behaviour:
        When the NCX has an empty navMap, ebooklib may return ``book.toc`` as
        a single :class:`ebooklib.epub.Link` object rather than a list.  The
        ``extract_navigation`` implementation must guard against this
        (see DEFECT-001 if the fallback test fails).

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.
        chapters: List of ``(chapter_title, chapter_text)`` tuples.
                  Defaults to :data:`DEFAULT_CHAPTERS` (2 chapters).

    Returns:
        *output_path* after writing.
    """
    if chapters is None:
        chapters = DEFAULT_CHAPTERS

    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-nonav-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    epub_items: list[epub.EpubHtml] = []
    for idx, (ch_title, ch_text) in enumerate(chapters, start=1):
        item = epub.EpubHtml(
            title=ch_title,
            file_name=f"chapter_{idx:02d}.xhtml",
            lang="en",
        )
        item.content = _chapter_xhtml(ch_title, ch_text).encode("utf-8")
        book.add_item(item)
        epub_items.append(item)

    # Empty TOC — no TOC entries, so navigation should fall back to spine.
    book.toc = []
    # Do NOT add EpubNcx: if we add it, ebooklib writes a toc= attribute in
    # the spine element pointing to the NCX uid, and then fails to load the
    # NCX back (AttributeError on get_name).  Omitting EpubNcx means no toc
    # attribute in spine XML, so ebooklib loads cleanly.
    # Also add EpubNav so ebooklib has a valid EPUB3 structure to write.
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *epub_items]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_front_matter_epub(
    output_path: Path,
    title: str = "Front Matter Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB that includes front-matter pages (copyright, cover page).

    Used to test front-matter exclusion in the chapter scoring engine.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-frontmatter-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Front-matter: copyright page (very short, keyword in h1 title)
    # The <h1> heading ensures the scoring engine can detect the title via
    # _guess_title_from_content even without a TOC entry.
    copyright_item = epub.EpubHtml(
        title="copyright",
        file_name="copyright.xhtml",
        lang="en",
    )
    copyright_item.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>copyright</title></head>"
        b"<body><h1>copyright</h1><p>Copyright 2024 Test Author.</p></body>"
        b"</html>"
    )
    book.add_item(copyright_item)

    # Back-matter: index page (very short, keyword in h1 title)
    index_item = epub.EpubHtml(
        title="index",
        file_name="index_page.xhtml",
        lang="en",
    )
    index_item.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>index</title></head>"
        b"<body><h1>index</h1><p>A, B, C</p></body>"
        b"</html>"
    )
    book.add_item(index_item)

    # Real chapter
    chapter_item = epub.EpubHtml(
        title="Chapter One",
        file_name="chapter01.xhtml",
        lang="en",
    )
    chapter_item.content = _chapter_xhtml(
        "Chapter One",
        DEFAULT_CHAPTERS[0][1],
    ).encode("utf-8")
    book.add_item(chapter_item)

    book.toc = [epub.Link("chapter01.xhtml", "Chapter One", "ch1")]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", copyright_item, index_item, chapter_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_short_chapter_epub(
    output_path: Path,
    title: str = "Short Chapter Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB with one very short document (< 200 words) and one normal chapter.

    Used to test the −2 short-document penalty in the scoring engine.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-short-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Short item: ~10 words, no TOC entry
    short_item = epub.EpubHtml(
        title="Short Stub",
        file_name="short_stub.xhtml",
        lang="en",
    )
    short_item.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>Short Stub</title></head>"
        b"<body><p>This page is intentionally very short stub text only.</p></body>"
        b"</html>"
    )
    book.add_item(short_item)

    # Normal chapter
    chapter_item = epub.EpubHtml(
        title="Chapter One",
        file_name="chapter01.xhtml",
        lang="en",
    )
    chapter_item.content = _chapter_xhtml("Chapter One", DEFAULT_CHAPTERS[0][1]).encode("utf-8")
    book.add_item(chapter_item)

    book.toc = [epub.Link("chapter01.xhtml", "Chapter One", "ch1")]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", short_item, chapter_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_empty_doc_epub(
    output_path: Path,
    title: str = "Empty Doc Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB containing a document with no readable text content.

    Used to test the −10 ``no-text`` penalty (hard exclude) in the scoring engine.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-emptydoc-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    empty_item = epub.EpubHtml(
        title="Empty Page",
        file_name="empty.xhtml",
        lang="en",
    )
    # Body contains only an empty paragraph — BeautifulSoup returns zero words.
    # We cannot use a truly empty <body></body> because lxml's document_fromstring
    # raises ParserError.  An empty <p></p> satisfies lxml and gives word_count == 0.
    empty_item.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>Empty Page</title></head>"
        b"<body><p></p></body>"
        b"</html>"
    )
    book.add_item(empty_item)

    chapter_item = epub.EpubHtml(
        title="Chapter One",
        file_name="chapter01.xhtml",
        lang="en",
    )
    chapter_item.content = _chapter_xhtml("Chapter One", DEFAULT_CHAPTERS[0][1]).encode("utf-8")
    book.add_item(chapter_item)

    book.toc = [epub.Link("chapter01.xhtml", "Chapter One", "ch1")]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", empty_item, chapter_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_heading_epub(
    output_path: Path,
    title: str = "Heading Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB where a chapter has an ``<h1>`` matching a chapter-title pattern.

    No TOC entry is included so the +2 heading-match signal is isolated from the
    +4 TOC-entry signal.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-heading-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Chapter with <h1>Chapter 1</h1> — no TOC entry
    chapter_item = epub.EpubHtml(
        title="Chapter 1",
        file_name="chapter01.xhtml",
        lang="en",
    )
    chapter_item.content = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en'>\n"
        "<head><title>Chapter 1</title></head>\n"
        "<body>\n"
        "  <h1>Chapter 1</h1>\n"
        "  <p>" + ("placeholder text " * 50) + "</p>\n"
        "</body>\n"
        "</html>\n"
    ).encode("utf-8")
    book.add_item(chapter_item)

    # No TOC — spine fallback only
    book.toc = []
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_multi_file_chapter_epub(
    output_path: Path,
    title: str = "Multi-File Chapter Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB where one logical chapter spans multiple XHTML files.

    Structure::

        spine:  ch01_part1.xhtml → ch01_part2.xhtml → ch02.xhtml
        TOC:    "Chapter One"   → ch01_part1.xhtml
                "Chapter Two"   → ch02.xhtml

    ``ch01_part2.xhtml`` has no TOC entry and only a few words of content,
    so it scores below the inclusion threshold on its own.  A correct
    implementation of :func:`merge_consecutive_chapters` should fold it into
    ``Chapter One``.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-multifile-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Chapter One — Part 1 (has TOC entry, full content)
    part1 = epub.EpubHtml(
        title="Chapter One",
        file_name="ch01_part1.xhtml",
        lang="en",
    )
    part1.content = _chapter_xhtml("Chapter One", DEFAULT_CHAPTERS[0][1]).encode("utf-8")
    book.add_item(part1)

    # Chapter One — Part 2 (NO TOC entry, short content — continuation)
    part2 = epub.EpubHtml(
        title="Chapter One Continued",
        file_name="ch01_part2.xhtml",
        lang="en",
    )
    part2.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>Chapter One Continued</title></head>"
        b"<body><p>This is the continuation of chapter one with a few more sentences "
        b"to give it slightly more content than an empty stub.</p></body>"
        b"</html>"
    )
    book.add_item(part2)

    # Chapter Two (has TOC entry, full content)
    ch02 = epub.EpubHtml(
        title="Chapter Two",
        file_name="ch02.xhtml",
        lang="en",
    )
    ch02.content = _chapter_xhtml("Chapter Two", DEFAULT_CHAPTERS[1][1]).encode("utf-8")
    book.add_item(ch02)

    # TOC: only ch01_part1 and ch02 have entries; ch01_part2 is unlisted
    book.toc = [
        epub.Link("ch01_part1.xhtml", "Chapter One", "ch1"),
        epub.Link("ch02.xhtml", "Chapter Two", "ch2"),
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", part1, part2, ch02]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_multifile_chapter_epub(
    output_path: Path,
    title: str = "Multi-File Chapter (3-Part)",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB where one logical chapter spans THREE XHTML files.

    Structure::

        spine:  ch01_part1.xhtml → ch01_part2.xhtml → ch01_part3.xhtml → ch02.xhtml
        TOC:    "Chapter 1"   → ch01_part1.xhtml
                "Chapter 2"   → ch02.xhtml

    ``ch01_part2.xhtml`` and ``ch01_part3.xhtml`` have no TOC entries and
    very short content (< 200 words) so they each score −1 (spine +1 minus
    short −2) and are excluded from :func:`select_chapters`.  The merge pass
    then folds them into Chapter 1, giving it three ``source_docs``.

    Distinct from :func:`build_multi_file_chapter_epub` which only has two
    parts (``ch01_part1`` + ``ch01_part2``).

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-3part-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Chapter 1 — Part 1 (TOC entry, full content)
    part1 = epub.EpubHtml(
        title="Chapter 1",
        file_name="ch01_part1.xhtml",
        lang="en",
    )
    part1.content = _chapter_xhtml("Chapter 1", DEFAULT_CHAPTERS[0][1]).encode("utf-8")
    book.add_item(part1)

    # Chapter 1 — Part 2 (no TOC, short, no heading → score −1 → excluded → merged)
    part2 = epub.EpubHtml(
        title="Chapter 1 Continuation A",
        file_name="ch01_part2.xhtml",
        lang="en",
    )
    part2.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>Chapter 1 Continuation A</title></head>"
        b"<body>"
        b"<p>The story continues here with a few additional sentences "
        b"that flow on from the previous section without introducing "
        b"a new chapter heading.</p>"
        b"</body></html>"
    )
    book.add_item(part2)

    # Chapter 1 — Part 3 (no TOC, short, no heading → score −1 → excluded → merged)
    part3 = epub.EpubHtml(
        title="Chapter 1 Continuation B",
        file_name="ch01_part3.xhtml",
        lang="en",
    )
    part3.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>Chapter 1 Continuation B</title></head>"
        b"<body>"
        b"<p>A brief closing passage ends the chapter before the narrative "
        b"moves forward into the next part of the story.</p>"
        b"</body></html>"
    )
    book.add_item(part3)

    # Chapter 2 (TOC entry, full content, separate logical chapter)
    ch02 = epub.EpubHtml(
        title="Chapter 2",
        file_name="ch02.xhtml",
        lang="en",
    )
    ch02.content = _chapter_xhtml("Chapter 2", DEFAULT_CHAPTERS[1][1]).encode("utf-8")
    book.add_item(ch02)

    # TOC: only ch01_part1 and ch02 have entries
    book.toc = [
        epub.Link("ch01_part1.xhtml", "Chapter 1", "ch1"),
        epub.Link("ch02.xhtml", "Chapter 2", "ch2"),
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", part1, part2, part3, ch02]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_singlefile_multichapter_epub(
    output_path: Path,
    title: str = "Single File Multi-Chapter",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB where one document contains three chapters via fragment links.

    Structure::

        chapters.xhtml:
            <section id="prologue">Prologue + text</section>
            <section id="ch1">Chapter 1 + text</section>
            <section id="ch2">Chapter 2 + text</section>

        TOC:  "Prologue"   → chapters.xhtml#prologue
              "Chapter 1" → chapters.xhtml#ch1
              "Chapter 2" → chapters.xhtml#ch2

    Distinct from :func:`build_multi_chapter_single_file` (which uses
    ``ch-1`` / ``ch-2`` IDs and plain ``<h1>`` elements).  This builder
    uses ``<section id=...>`` containers which are self-contained block
    elements and influence how :func:`_extract_fragment` scopes the text.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-sfmc-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Build a single XHTML with three sections, each with its own id.
    sections_data = [
        ("prologue", "Prologue", DEFAULT_CHAPTERS[0][1]),
        ("ch1", "Chapter 1", DEFAULT_CHAPTERS[1][1]),
        ("ch2", "Chapter 2", DEFAULT_CHAPTERS[0][1]),
    ]
    sections_html = ""
    for frag_id, sec_title, sec_text in sections_data:
        paragraphs = "".join(
            f"<p>{para.strip()}</p>\n" for para in sec_text.split(".") if para.strip()
        )
        sections_html += (
            f"    <section id='{frag_id}'>\n"
            f"      <h1>{sec_title}</h1>\n"
            f"      {paragraphs}\n"
            f"    </section>\n"
        )

    xhtml_content = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>\n"
        "  <head><title>Single File Multi-Chapter</title></head>\n"
        "  <body>\n"
        f"{sections_html}"
        "  </body>\n"
        "</html>\n"
    )

    single_item = epub.EpubHtml(
        title="Single File Multi-Chapter",
        file_name="chapters.xhtml",
        lang="en",
    )
    single_item.content = xhtml_content.encode("utf-8")
    book.add_item(single_item)

    # TOC uses fragment links: chapters.xhtml#prologue, #ch1, #ch2
    book.toc = [
        epub.Link("chapters.xhtml#prologue", "Prologue", "prologue"),
        epub.Link("chapters.xhtml#ch1", "Chapter 1", "ch1"),
        epub.Link("chapters.xhtml#ch2", "Chapter 2", "ch2"),
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", single_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_fragment_toc_epub(
    output_path: Path,
    title: str = "Fragment TOC Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB with TOC entries using fragment links into one file.

    Structure::

        content.xhtml:
            <section id="part1">Part 1 + text</section>
            <section id="part2">Part 2 + text</section>

        TOC:  "Part 1" → content.xhtml#part1
              "Part 2" → content.xhtml#part2

    Tests that the navigation and chapter-split machinery correctly
    resolves fragment-only TOC links and creates two separate chapters.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-frag-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    part1_text = DEFAULT_CHAPTERS[0][1]
    part2_text = DEFAULT_CHAPTERS[1][1]

    def _make_section(frag_id: str, sec_title: str, sec_text: str) -> str:
        paragraphs = "".join(
            f"<p>{para.strip()}</p>\n" for para in sec_text.split(".") if para.strip()
        )
        return (
            f"    <section id='{frag_id}'>\n"
            f"      <h1>{sec_title}</h1>\n"
            f"      {paragraphs}\n"
            f"    </section>\n"
        )

    xhtml_content = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<!DOCTYPE html>\n"
        "<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>\n"
        "  <head><title>Fragment TOC Test</title></head>\n"
        "  <body>\n"
        + _make_section("part1", "Part 1", part1_text)
        + _make_section("part2", "Part 2", part2_text)
        + "  </body>\n"
        "</html>\n"
    )

    content_item = epub.EpubHtml(
        title="Fragment TOC Test",
        file_name="content.xhtml",
        lang="en",
    )
    content_item.content = xhtml_content.encode("utf-8")
    book.add_item(content_item)

    book.toc = [
        epub.Link("content.xhtml#part1", "Part 1", "part1"),
        epub.Link("content.xhtml#part2", "Part 2", "part2"),
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", content_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_titlepage_epub(
    output_path: Path,
    title: str = "Title Page Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB containing a document with ``epub:type='titlepage'``.

    Convenience wrapper around :func:`build_epub_with_epub_type` for the
    common case of testing titlepage strong-exclusion scoring.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    return build_epub_with_epub_type(output_path, "titlepage", title, author)


def build_continued_chapter_epub(
    output_path: Path,
    title: str = "Continued Chapter Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB with a 'Chapter 1 (continued)' continuation document.

    Structure::

        spine:  ch01.xhtml → ch01_cont.xhtml → ch02.xhtml
        TOC:    "Chapter 1" → ch01.xhtml
                "Chapter 2" → ch02.xhtml

    ``ch01_cont.xhtml`` carries the heading ``Chapter 1 (continued)`` which
    does **not** match the chapter heading regex (the parenthesised suffix
    prevents a match) and has very short content (< 200 words).  Scoring:
    ``+1`` (spine) ``−2`` (short) = ``−1`` → excluded from
    :func:`select_chapters`.  The merge pass then folds it into Chapter 1
    because it has no TOC entry and no front/back-matter signals.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-cont-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # ch01.xhtml — full chapter (TOC entry, matching heading, full content)
    ch01 = epub.EpubHtml(
        title="Chapter 1",
        file_name="ch01.xhtml",
        lang="en",
    )
    ch01.content = _chapter_xhtml("Chapter 1", DEFAULT_CHAPTERS[0][1]).encode("utf-8")
    book.add_item(ch01)

    # ch01_cont.xhtml — continuation (no TOC, heading won't match regex, < 200 words)
    # Heading "Chapter 1 (continued)" does NOT match _CHAPTER_HEADING_RE because
    # of the parenthesised suffix, so no +2 heading_match.  Scoring: +1 − 2 = −1.
    ch01_cont = epub.EpubHtml(
        title="Chapter 1 (continued)",
        file_name="ch01_cont.xhtml",
        lang="en",
    )
    ch01_cont.content = (
        b"<?xml version='1.0' encoding='utf-8'?>"
        b"<!DOCTYPE html>"
        b"<html xmlns='http://www.w3.org/1999/xhtml'>"
        b"<head><title>Chapter 1 (continued)</title></head>"
        b"<body>"
        b"<h2>Chapter 1 (continued)</h2>"
        b"<p>This short section concludes the narrative thread from the "
        b"previous document and leads directly into the next chapter.</p>"
        b"</body></html>"
    )
    book.add_item(ch01_cont)

    # ch02.xhtml — next chapter (TOC entry, matching heading, full content)
    ch02 = epub.EpubHtml(
        title="Chapter 2",
        file_name="ch02.xhtml",
        lang="en",
    )
    ch02.content = _chapter_xhtml("Chapter 2", DEFAULT_CHAPTERS[1][1]).encode("utf-8")
    book.add_item(ch02)

    # TOC: only ch01 and ch02 have entries; ch01_cont is unlisted
    book.toc = [
        epub.Link("ch01.xhtml", "Chapter 1", "ch1"),
        epub.Link("ch02.xhtml", "Chapter 2", "ch2"),
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", ch01, ch01_cont, ch02]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_roman_numeral_chapters_epub(
    output_path: Path,
    title: str = "Roman Numeral Chapters",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB with Roman numeral chapter headings (I, II, III, IV).

    All four chapters have TOC entries and ``<h1>`` headings that match the
    ``[IVXLCDM]+`` branch of the chapter-heading regex, exercising the Roman
    numeral detection path in the scoring engine.

    Args:
        output_path: Where to write the ``.epub`` file.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-roman-{title.replace(' ', '-').lower()}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    roman_chapters = [
        ("I", DEFAULT_CHAPTERS[0][1]),
        ("II", DEFAULT_CHAPTERS[1][1]),
        ("III", DEFAULT_CHAPTERS[0][1]),
        ("IV", DEFAULT_CHAPTERS[1][1]),
    ]

    epub_items: list[epub.EpubHtml] = []
    for idx, (numeral, text) in enumerate(roman_chapters, start=1):
        item = epub.EpubHtml(
            title=numeral,
            file_name=f"chapter_{idx:02d}.xhtml",
            lang="en",
        )
        item.content = _chapter_xhtml(numeral, text).encode("utf-8")
        book.add_item(item)
        epub_items.append(item)

    book.toc = [
        epub.Link(item.file_name, item.title, f"ch{i + 1}") for i, item in enumerate(epub_items)
    ]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *epub_items]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path


def build_epub_with_epub_type(
    output_path: Path,
    epub_type: str,
    title: str = "Epub Type Test",
    author: str = "Test Author",
) -> Path:
    """Build an EPUB with a single document that has a given ``epub:type`` attribute.

    Used to test strong-exclusion and front/back-matter epub:type scoring.

    Args:
        output_path: Where to write the ``.epub`` file.
        epub_type: The ``epub:type`` value to set on the ``<body>`` element.
        title: Book title metadata.
        author: Book author metadata.

    Returns:
        *output_path* after writing.
    """
    book = epub.EpubBook()
    book.set_identifier(f"epub2audio-test-epubtype-{epub_type}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Single page with the given epub:type on a section inside body.
    # Note: ebooklib strips epub:type from <body>; use <section> instead.
    typed_item = epub.EpubHtml(
        title=title,
        file_name="typed_page.xhtml",
        lang="en",
    )
    placeholder = "placeholder text " * 60
    typed_item.content = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<!DOCTYPE html>"
        "<html xmlns='http://www.w3.org/1999/xhtml'"
        "      xmlns:epub='http://www.idpf.org/2007/ops'>"
        f"<head><title>{title}</title></head>"
        "<body>"
        f"<section epub:type='{epub_type}'>"
        f"<h1>{title}</h1>"
        f"<p>{placeholder}</p>"
        "</section>"
        "</body>"
        "</html>"
    ).encode()
    book.add_item(typed_item)

    # Also add a normal chapter so the book is valid
    chapter_item = epub.EpubHtml(
        title="Chapter One",
        file_name="chapter01.xhtml",
        lang="en",
    )
    chapter_item.content = _chapter_xhtml("Chapter One", DEFAULT_CHAPTERS[0][1]).encode("utf-8")
    book.add_item(chapter_item)

    book.toc = [epub.Link("chapter01.xhtml", "Chapter One", "ch1")]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", typed_item, chapter_item]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return output_path
