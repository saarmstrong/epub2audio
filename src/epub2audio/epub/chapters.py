"""Chapter scoring and selection engine for epub2audio.

Each EPUB spine item is scored against a set of weighted signals; items
that reach the inclusion threshold are promoted to :class:`~epub2audio.models.Chapter`
objects with stable identifiers.

Scoring table
-------------
+4  TOC / NCX entry points to this document
+3  ``epub:type="chapter"`` or ``"part"`` on the body/section element
+2  ``<h1>`` / ``<h2>`` matches a recognised chapter-title pattern
+1  Spine boundary (each distinct file gets this baseline)
+1  CSS class or id attribute contains the word "chapter"
-2  Short document (< 200 words)
-3  Title keyword is in the front/back-matter set
-3  ``epub:type`` is a front/back-matter semantic type
-10 No readable text content at all

Thresholds
----------
score >= 2   →  **include**
score 0–1    →  **warn**  (included, signal recorded)
score < 0    →  **exclude**
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import bs4
import ebooklib
import ebooklib.epub

from epub2audio.epub.cleanup import word_count, xhtml_to_text
from epub2audio.models import Chapter, ChapterCandidate, NavigationEntry

# Re-export for external callers that import from this module.
__all__ = [
    "finalize_chapters",
    "merge_consecutive_chapters",
    "score_candidates",
    "select_chapters",
    "split_multi_chapter_docs",
]

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

_FRONT_BACK_MATTER_KEYWORDS: frozenset[str] = frozenset(
    {
        "copyright",
        "index",
        "cover",
        "toc",
        "contents",
        "dedication",
        "preface",
        "foreword",
        "introduction",
        "acknowledgements",
        "about",
        "colophon",
        "half-title",
    }
)

# Titles that are, by convention, non-narrative front/back matter and should
# never be read aloud.  A match forces a hard exclusion regardless of any other
# positive signal (e.g. a TOC entry), because these pages are consistently NOT
# part of the narration.  Deliberately conservative: creative pages that are
# sometimes narrated (dedication, epigraph, prologue, preface, foreword,
# introduction) are NOT listed here.
_FRONT_MATTER_HARD_TITLES: frozenset[str] = frozenset(
    {
        "copyright",
        "contents",
        "table of contents",
        "acknowledgement",
        "acknowledgements",
        "acknowledgment",
        "acknowledgments",
        "colophon",
        "index",
        "cover",
        "title page",
        "half title",
        "half-title",
        "about the author",
        "about the publisher",
        "newsletter",
        "also by the author",
    }
)

# Title *prefixes* that mark non-narrative front/back matter, e.g. an "Also by
# William Gibson" / "Titles by …" page listing the author's other works, or a
# "Praise for …" blurbs page.  Matched against the lower-cased, stripped title.
_FRONT_MATTER_TITLE_PREFIXES: tuple[str, ...] = (
    "also by ",
    "titles by ",
    "books by ",
    "other books by ",
    "other titles by ",
    "by the same author",
    "praise for ",
    "more praise for ",
    "about the author",
)


def _is_hard_front_matter_title(title: str | None) -> bool:
    """Return True when *title* is a non-narrative front/back-matter page.

    Used to hard-exclude pages such as "Copyright", "Contents", or an "Also by
    …" author bibliography, which should never be narrated even when they
    appear in the table of contents.  Matching is case-insensitive on the
    stripped title: an exact match against :data:`_FRONT_MATTER_HARD_TITLES`
    or a prefix match against :data:`_FRONT_MATTER_TITLE_PREFIXES`.

    Args:
        title: The candidate title, or ``None``.

    Returns:
        True when the title is definitively non-narrative front/back matter.
    """
    if not title:
        return False
    t = title.strip().lower()
    if t in _FRONT_MATTER_HARD_TITLES:
        return True
    return any(t.startswith(prefix) for prefix in _FRONT_MATTER_TITLE_PREFIXES)


# epub:type values that receive a strong exclusion penalty (-5) because they
# are structural front-matter pages that can never be chapters.
_STRONG_EXCLUSION_EPUB_TYPES: frozenset[str] = frozenset(
    {
        "titlepage",
        "halftitlepage",
    }
)

_FRONT_BACK_MATTER_EPUB_TYPES: frozenset[str] = frozenset(
    {
        "cover",
        "frontmatter",
        "bodymatter",
        "backmatter",
        "toc",
        "landmarks",
        "loi",
        "lot",
        "preface",
        "copyright-page",
        "colophon",
        "index",
        "glossary",
        "bibliography",
        "acknowledgements",
        "dedication",
        "epigraph",
        # D3 additions
        "seriespage",
        "imprimatur",
        "errata",
    }
)

# Pattern for recognised chapter headings in h1/h2 text
_CHAPTER_HEADING_RE = re.compile(
    r"""
    ^\s*(
        chapter\s+[\divxlcdmIVXLCDM\w]+   # "Chapter 1", "Chapter One", "Chapter XII"
        | part\s+[\divxlcdmIVXLCDM\w]+     # "Part One", "Part I"
        | book\s+[\divxlcdmIVXLCDM\w]+     # "Book Two"
        | prologue | epilogue | interlude
        | afterword | appendix
        | \d+                               # bare number "1", "42"
        | [IVXLCDM]+                        # bare Roman numeral "I", "XIV"
    )\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _epub_types_from_item(content: bytes) -> set[str]:
    """Return all ``epub:type`` attribute values found in an XHTML document.

    Checks both the ``epub:type`` namespace-prefixed attribute and the
    unprefixed ``type`` attribute on any element.

    Args:
        content: Raw XHTML bytes of the spine document.

    Returns:
        A (possibly empty) set of epub:type value strings, each lower-cased
        and stripped.
    """
    soup = bs4.BeautifulSoup(content, features="xml")
    types: set[str] = set()

    for tag in soup.find_all(True):
        for attr_name in ("epub:type", "type"):
            val = tag.get(attr_name, "")
            if isinstance(val, list):
                val = " ".join(val)
            if val:
                for part in val.split():
                    # Strip namespace prefix if present (e.g. "epub:chapter")
                    bare = part.split(":")[-1].strip().lower()
                    if bare:
                        types.add(bare)
    return types


def _css_class_ids_from_item(content: bytes) -> set[str]:
    """Return all CSS class and id token values found in the document.

    Args:
        content: Raw XHTML bytes.

    Returns:
        Lower-cased set of all individual class tokens and id values.
    """
    soup = bs4.BeautifulSoup(content, features="xml")
    tokens: set[str] = set()

    for tag in soup.find_all(True):
        cls = tag.get("class", [])
        if isinstance(cls, str):
            cls = cls.split()
        for c in cls:
            tokens.add(c.lower())
        id_val = tag.get("id", "")
        if id_val:
            tokens.add(id_val.lower())
    return tokens


def _count_heading_elements(content: bytes, tag_name: str = "h1") -> int:
    """Count how many elements with *tag_name* appear in the document.

    Args:
        content: Raw XHTML bytes.
        tag_name: HTML tag to count (default ``"h1"``).

    Returns:
        Count of matching elements (0 if none or on parse error).
    """
    soup = bs4.BeautifulSoup(content, features="xml")
    return len(soup.find_all(tag_name))


def _first_heading_text(content: bytes) -> str | None:
    """Return the text of the first ``<h1>`` or ``<h2>`` element, or None.

    Args:
        content: Raw XHTML bytes.

    Returns:
        Stripped heading text or ``None`` if no h1/h2 is present.
    """
    soup = bs4.BeautifulSoup(content, features="xml")
    for tag_name in ("h1", "h2"):
        heading = soup.find(tag_name)
        if heading and isinstance(heading, bs4.Tag):
            text = heading.get_text(separator=" ").strip()
            if text:
                return text
    return None


def _score_item(
    item: Any,
    nav_doc_paths: set[str],
    content: bytes,
) -> tuple[int, list[str]]:
    """Compute the chapter score for one spine item.

    Args:
        item: An :class:`ebooklib.epub.EpubItem` (typically EpubHtml).
        nav_doc_paths: Set of doc_paths referenced in the TOC/NCX.
        content: Decompressed XHTML bytes for the item.

    Returns:
        ``(score, signals)`` where *signals* is a list of human-readable
        descriptions of which signals fired.
    """
    score = 0
    signals: list[str] = []
    item_path = item.get_name()

    # --- Baseline: spine boundary (every file gets +1) ---
    score += 1
    signals.append("spine_boundary +1")

    # --- Text content check ---
    plain_text = xhtml_to_text(content)
    wc = word_count(plain_text)

    if wc == 0:
        # Hard exclude: override any prior signals and return a fixed score
        # of −10 so the total is always ≤ −10 regardless of other signals.
        signals = ["no_text_content -10"]
        return -10, signals

    # Embed the true word count in a parseable signal so select_chapters can
    # assign Chapter.word_count without re-reading the document.
    signals.append(f"word_count({wc})")

    # --- TOC entry ---
    if item_path in nav_doc_paths:
        score += 4
        signals.append("toc_entry +4")

    # --- epub:type signals ---
    epub_types = _epub_types_from_item(content)

    chapter_types = {"chapter", "part"}
    if epub_types & chapter_types:
        score += 3
        signals.append("epub_type_chapter +3")

    # Strong exclusion types (-5) take precedence over general front/back matter (-3).
    strong_types = epub_types & _STRONG_EXCLUSION_EPUB_TYPES
    if strong_types:
        score -= 5
        signals.append(f"epub_type_strong_exclude({','.join(sorted(strong_types))}) -5")
    else:
        fm_types = epub_types & _FRONT_BACK_MATTER_EPUB_TYPES
        if fm_types:
            score -= 3
            signals.append(f"epub_type_frontback({','.join(sorted(fm_types))}) -3")

    # --- h1/h2 title pattern ---
    heading_text = _first_heading_text(content)
    if heading_text and _CHAPTER_HEADING_RE.match(heading_text):
        score += 2
        signals.append("heading_match +2")

    # --- CSS class/id contains "chapter" ---
    css_tokens = _css_class_ids_from_item(content)
    if any("chapter" in tok for tok in css_tokens):
        score += 1
        signals.append("css_chapter +1")

    # --- Multiple h1 elements signal this doc may need splitting ---
    h1_count = _count_heading_elements(content, "h1")
    if h1_count > 1:
        score -= 1
        signals.append(f"multiple_h1({h1_count}) -1")

    # --- Short document penalty ---
    if wc < 200:
        score -= 2
        signals.append(f"short_document({wc}_words) -2")

    return score, signals


def _guess_title_from_content(content: bytes) -> str | None:
    """Guess a chapter title from the first heading in the document.

    Args:
        content: Raw XHTML bytes.

    Returns:
        Heading text or ``None``.
    """
    return _first_heading_text(content)


def score_candidates(
    book: ebooklib.epub.EpubBook,
    nav_entries: list[NavigationEntry],
) -> list[ChapterCandidate]:
    """Score each spine item as a chapter candidate.

    Iterates the spine (reading order) and computes a weighted score for each
    document.  The spine — not the filename sort — defines iteration order.

    Args:
        book: A fully parsed EpubBook.
        nav_entries: Navigation entries from
            :func:`~epub2audio.epub.navigation.extract_navigation`.

    Returns:
        One :class:`~epub2audio.models.ChapterCandidate` per spine item,
        in reading (spine) order.
    """
    # Build a mapping from doc_path → title from the nav entries
    nav_title_by_path: dict[str, str] = {}
    nav_doc_paths: set[str] = set()

    for entry in nav_entries:
        if entry.doc_path:
            nav_doc_paths.add(entry.doc_path)
            if entry.title and entry.doc_path not in nav_title_by_path:
                nav_title_by_path[entry.doc_path] = entry.title

    # Also apply title-based front/back-matter keyword check
    candidates: list[ChapterCandidate] = []

    for idref, _linear in book.spine:
        item = book.get_item_with_id(idref)
        if item is None:
            continue

        item_path: str = item.get_name()

        try:
            content: bytes = item.get_content()
        except Exception:
            content = b""

        score, signals = _score_item(item, nav_doc_paths, content)

        # Determine best title for this candidate
        title: str | None = nav_title_by_path.get(item_path)
        if title is None:
            title = _guess_title_from_content(content)

        # Hard front/back-matter title check: definitive non-narrative pages
        # (Copyright, Contents, "Also by …", etc.) are excluded outright so a
        # TOC entry cannot pull them back in.  This overrides all other signals.
        if title and _is_hard_front_matter_title(title):
            score = -10
            signals = [f"front_matter_title({title.strip().lower()!r}) -10"]
        # Softer title-based front/back-matter keyword check for ambiguous pages.
        elif title:
            title_lower = title.strip().lower()
            if title_lower in _FRONT_BACK_MATTER_KEYWORDS:
                score -= 3
                signals.append(f"frontback_keyword({title_lower!r}) -3")

        candidates.append(
            ChapterCandidate(
                doc_path=item_path,
                title=title,
                score=score,
                signals=signals,
            )
        )

    return candidates


def select_chapters(candidates: list[ChapterCandidate]) -> list[Chapter]:
    """Apply threshold rules and return confirmed chapters in reading order.

    Scoring thresholds:

    - score >= 2 → **include**
    - score 0–1  → **warn** (included, warning added to signals)
    - score < 0  → **exclude**

    Args:
        candidates: Ordered list from :func:`score_candidates`.

    Returns:
        Ordered list of :class:`~epub2audio.models.Chapter` objects for all
        included (and warned) candidates.
    """
    chapters: list[Chapter] = []
    chapter_index = 0

    for candidate in candidates:
        if candidate.score < 0:
            # Excluded — skip
            continue

        chapter_index += 1
        chapter_id = f"ch{chapter_index:03d}"
        title = candidate.title or f"Chapter {chapter_index}"

        # Compute stable_id: first 12 hex chars of SHA-256(chapter_id + title)
        raw = (chapter_id + title).encode("utf-8")
        stable_id = hashlib.sha256(raw).hexdigest()[:12]

        # For word_count we would need to re-read content; use 0 as placeholder
        # (the real count is set by the pipeline when it has the book open).
        # The scoring pass already has the content so we embed the word count
        # from the signals if available.
        wc = _extract_word_count_from_signals(candidate.signals)

        # Build updated signals for warned candidates
        signals = list(candidate.signals)
        if candidate.score <= 1:
            signals.append(f"warn: low_score({candidate.score})")

        chapters.append(
            Chapter(
                chapter_id=chapter_id,
                title=title,
                source_docs=[candidate.doc_path],
                word_count=wc,
                stable_id=stable_id,
            )
        )

    return chapters


def _extract_word_count_from_signals(signals: list[str]) -> int:
    """Extract the true word count embedded by :func:`_score_item`.

    Looks first for the explicit ``word_count(N)`` signal that is always
    appended by the scoring pass for any non-empty document, then falls back
    to the ``short_document(N_words)`` signal for backwards compatibility.

    Args:
        signals: Signal list from :func:`_score_item`.

    Returns:
        Word count, or 0 if not recoverable from signals (should not happen
        for valid documents scored by the current engine).
    """
    # Primary: explicit word_count signal added for every non-empty document.
    for sig in signals:
        m = re.match(r"word_count\((\d+)\)", sig)
        if m:
            return int(m.group(1))
    # Fallback: short_document signal (documents < 200 words).
    for sig in signals:
        m = re.match(r"short_document\((\d+)_words\)", sig)
        if m:
            return int(m.group(1))
    return 0


# ---------------------------------------------------------------------------
# Post-selection: merge and split passes
# ---------------------------------------------------------------------------


def _renumber_chapters(chapters: list[Chapter]) -> list[Chapter]:
    """Assign stable sequential chapter_id and recompute stable_id.

    Called after merge/split passes have changed the chapter list so that
    chapter IDs remain in the canonical ``ch001`` … ``chNNN`` form.

    Args:
        chapters: Chapter list in reading order (ids may be stale).

    Returns:
        New list with ``chapter_id`` = ``"ch001"``… and fresh ``stable_id``.
    """
    result: list[Chapter] = []
    for i, ch in enumerate(chapters, start=1):
        chapter_id = f"ch{i:03d}"
        raw = (chapter_id + ch.title).encode("utf-8")
        stable_id = hashlib.sha256(raw).hexdigest()[:12]
        result.append(ch.model_copy(update={"chapter_id": chapter_id, "stable_id": stable_id}))
    return result


def _is_continuation_candidate(
    cand: ChapterCandidate,
    nav_doc_paths: set[str],
) -> bool:
    """Return True if *cand* looks like a continuation of the preceding chapter.

    A continuation document is one that:

    * Has **no** TOC / NCX entry (it was not independently identified).
    * Has **no** front/back-matter or strong-exclusion signals (so it is not
      a copyright page, title page, etc. that happens to fall between chapters).

    Args:
        cand: A :class:`~epub2audio.models.ChapterCandidate` from the spine.
        nav_doc_paths: Set of doc_paths referenced in the TOC / NCX.

    Returns:
        ``True`` if this candidate should be merged into the preceding chapter.
    """
    if cand.doc_path in nav_doc_paths:
        return False
    for sig in cand.signals:
        if "frontback" in sig or "strong_exclude" in sig:
            return False
    return True


def merge_consecutive_chapters(
    chapters: list[Chapter],
    candidates: list[ChapterCandidate],
    nav_entries: list[NavigationEntry],
) -> list[Chapter]:
    """Merge continuation spine documents into the preceding chapter.

    Some EPUBs split one logical chapter across multiple XHTML files (e.g.
    for reader pagination).  Only the *first* file receives a TOC entry;
    subsequent files have no TOC pointer and low scores.

    **Merge heuristic**: for every gap in the spine between two consecutive
    chapters, any intervening candidates that have *no TOC entry* and *no
    front/back-matter exclusion signals* are merged into the preceding
    chapter by appending their ``doc_path`` to ``source_docs`` and summing
    their word counts.

    This function does **not** renumber chapters; call
    :func:`_renumber_chapters` afterwards if you need sequential IDs.

    Args:
        chapters: Selected chapters in reading order (output of
            :func:`select_chapters`).
        candidates: All spine candidates in reading order (output of
            :func:`score_candidates`).
        nav_entries: TOC entries used to build the "no TOC entry" check.

    Returns:
        Chapter list with continuation docs appended to their predecessors.
    """
    if not chapters:
        return chapters

    # Build nav_doc_paths for quick membership testing.
    nav_doc_paths: set[str] = {e.doc_path for e in nav_entries if e.doc_path}

    cand_by_path: dict[str, ChapterCandidate] = {c.doc_path: c for c in candidates}
    spine_paths: list[str] = [c.doc_path for c in candidates]

    result: list[Chapter] = []

    for ch_idx, chapter in enumerate(chapters):
        # Find the spine position of this chapter's *last* source document.
        last_doc = chapter.source_docs[-1].split("#")[0]
        try:
            pos = spine_paths.index(last_doc)
        except ValueError:
            result.append(chapter)
            continue

        # Determine where the *next* chapter starts in the spine.
        if ch_idx + 1 < len(chapters):
            next_first = chapters[ch_idx + 1].source_docs[0].split("#")[0]
            try:
                next_pos = spine_paths.index(next_first)
            except ValueError:
                next_pos = len(spine_paths)
        else:
            next_pos = len(spine_paths)

        # Collect any intervening spine items as continuation documents.
        extra_docs: list[str] = []
        extra_wc = 0
        for j in range(pos + 1, next_pos):
            cand = cand_by_path.get(spine_paths[j])
            if cand is not None and _is_continuation_candidate(cand, nav_doc_paths):
                extra_docs.append(cand.doc_path)
                extra_wc += _extract_word_count_from_signals(cand.signals)

        if extra_docs:
            result.append(
                chapter.model_copy(
                    update={
                        "source_docs": list(chapter.source_docs) + extra_docs,
                        "word_count": chapter.word_count + extra_wc,
                    }
                )
            )
        else:
            result.append(chapter)

    return result


def split_multi_chapter_docs(
    chapters: list[Chapter],
    nav_entries: list[NavigationEntry],
    book: ebooklib.epub.EpubBook,
) -> list[Chapter]:
    """Split single-file multi-chapter documents into separate Chapter objects.

    Detects chapters whose single source document is referenced by multiple
    TOC entries with different **fragment** anchors (e.g.
    ``chapter1.xhtml#ch-1``, ``chapter1.xhtml#ch-2``).  Each TOC entry
    becomes its own :class:`~epub2audio.models.Chapter` with a
    ``source_docs`` entry using the ``"path#fragment"`` format.

    The word count for each split chapter is estimated by calling
    :func:`~epub2audio.epub.cleanup.xhtml_to_text` with the appropriate
    fragment bounds.

    This function does **not** renumber chapters; call
    :func:`_renumber_chapters` afterwards.

    Args:
        chapters: Selected chapters in reading order.
        nav_entries: TOC entries (may include fragment anchors).
        book: The opened :class:`ebooklib.epub.EpubBook` (needed to read
            content for word-count estimation).

    Returns:
        Chapter list with multi-chapter docs expanded to multiple entries.
    """
    # Group nav entries by doc_path, preserving TOC order.
    nav_by_doc: dict[str, list[NavigationEntry]] = {}
    for entry in nav_entries:
        if entry.doc_path:
            nav_by_doc.setdefault(entry.doc_path, []).append(entry)

    result: list[Chapter] = []

    for chapter in chapters:
        # Only process chapters with a single, non-fragmented source doc.
        if len(chapter.source_docs) != 1 or "#" in chapter.source_docs[0]:
            result.append(chapter)
            continue

        doc_path = chapter.source_docs[0]
        entries_for_doc = nav_by_doc.get(doc_path, [])

        # Split if the same document has multiple TOC entries with distinct fragments.
        fragment_entries = [e for e in entries_for_doc if e.fragment is not None]
        if len(fragment_entries) < 2:
            result.append(chapter)
            continue

        # Fetch document content once for word-count estimation.
        item = book.get_item_with_href(doc_path)
        content: bytes = item.get_content() if item is not None else b""

        for i, entry in enumerate(fragment_entries):
            end_frag = fragment_entries[i + 1].fragment if i + 1 < len(fragment_entries) else None
            frag_source = f"{doc_path}#{entry.fragment}"

            # Estimate word count for this fragment.
            if content:
                frag_text = xhtml_to_text(
                    content,
                    start_fragment=entry.fragment,
                    end_fragment=end_frag,
                )
                frag_wc = word_count(frag_text)
            else:
                frag_wc = 0

            # Preserve chapter_id/stable_id as placeholders; renumber later.
            result.append(
                Chapter(
                    chapter_id=chapter.chapter_id,
                    title=entry.title or chapter.title,
                    source_docs=[frag_source],
                    word_count=frag_wc,
                    stable_id=chapter.stable_id,
                )
            )

    return result


def finalize_chapters(
    chapters: list[Chapter],
    candidates: list[ChapterCandidate],
    nav_entries: list[NavigationEntry],
    book: ebooklib.epub.EpubBook,
) -> list[Chapter]:
    """Apply merge and split passes and return the final chapter list.

    Runs the two post-selection refinement passes in order:

    1. :func:`merge_consecutive_chapters` — fold continuation spine docs
       into the preceding chapter.
    2. :func:`split_multi_chapter_docs` — expand single-file docs with
       multiple TOC fragment entries into separate chapters.

    After both passes the chapter list is renumbered with fresh
    ``chapter_id`` and ``stable_id`` values.

    Args:
        chapters: Output of :func:`select_chapters`.
        candidates: Output of :func:`score_candidates` (all spine items).
        nav_entries: TOC entries from
            :func:`~epub2audio.epub.navigation.extract_navigation`.
        book: The opened :class:`ebooklib.epub.EpubBook`.

    Returns:
        Final ordered list of :class:`~epub2audio.models.Chapter` objects.
    """
    merged = merge_consecutive_chapters(chapters, candidates, nav_entries)
    split = split_multi_chapter_docs(merged, nav_entries, book)
    return _renumber_chapters(split)
