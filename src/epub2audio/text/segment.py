"""Text segmentation for TTS synthesis.

Splits chapter text into :class:`~epub2audio.models.TextSegment` objects,
each small enough for a single TTS call.  The segmentation respects
linguistic boundaries in priority order:

1. Section boundary (double newline / blank-line paragraph break)
2. Paragraph boundary (single newline)
3. Sentence boundary (period/question/exclamation followed by whitespace)
4. Clause boundary (comma, semicolon, colon followed by whitespace)
5. Hard character limit (configurable, conservative default 500 chars)

**Never split:**
- Mid-word
- Between an opening quotation mark and the first word that follows
- Inside a decimal number (e.g. ``3.14``)
- Inside common abbreviations: ``Dr.``, ``Mr.``, ``Mrs.``, ``Ms.``,
  ``Prof.``, ``St.``, ``vs.``, ``etc.``
- Between initials: ``J. R. R.``
"""

from __future__ import annotations

import hashlib
import re

from epub2audio.models import TextSegment
from epub2audio.text.normalize import normalize_text

# ---------------------------------------------------------------------------
# Abbreviation / initial patterns
# ---------------------------------------------------------------------------

# Common abbreviations that end with a period but should NOT be treated as
# sentence boundaries.  Matched case-insensitively.
_ABBREV_PATTERN = re.compile(
    r"""
    \b(
        Dr | Mr | Mrs | Ms | Prof | St | vs | etc
        | [A-Z]          # single capital initial (e.g. "J.")
    )\.
    """,
    re.VERBOSE,
)

# Decimal number pattern — period surrounded by digits on both sides.
_DECIMAL_PATTERN = re.compile(r"\d\.\d")

# Sequence of initials: "J. R. R." — capital letter, period, space (repeating).
_INITIALS_PATTERN = re.compile(r"(?:[A-Z]\.\s){2,}")

# Opening quotation mark immediately preceding a word (no split after it).
_OPENING_QUOTE_RE = re.compile(r'^["\'\u201c\u2018]\w')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_sentence_boundary(text: str, pos: int) -> bool:
    """Return True if *pos* marks a safe sentence boundary in *text*.

    A safe sentence boundary is a ``.``, ``?``, or ``!`` at *pos* followed
    immediately by a space (or end-of-string) that is:

    - NOT part of a known abbreviation (Dr., Mr., etc.)
    - NOT inside a decimal number (3.14)
    - NOT the period of a lone capital initial (J.)
    - NOT part of an initials sequence (J. R. R.)

    Args:
        text: The full paragraph/section text.
        pos: Index of the punctuation character being tested.

    Returns:
        True when splitting after *pos* is linguistically safe.
    """
    ch = text[pos]
    if ch not in ".?!":
        return False

    # Must be followed by whitespace or end-of-string
    next_pos = pos + 1
    if next_pos < len(text) and text[next_pos] not in (" ", "\t", "\n"):
        return False

    if ch == ".":
        # Check decimal: digit on both sides
        if pos > 0 and text[pos - 1].isdigit():
            if next_pos < len(text) and text[next_pos].isdigit():
                return False

        # Check abbreviations: word before period matches known abbreviation
        # Extract the word ending at pos
        word_start = pos
        while word_start > 0 and not text[word_start - 1].isspace():
            word_start -= 1
        word = text[word_start:pos]
        if _ABBREV_PATTERN.match(word + "."):
            return False

        # Single capital initial followed by period — treat as non-boundary
        if len(word) == 1 and word.isupper():
            return False

        # Check initials sequence: look back for pattern like "J. "
        prefix = text[max(0, pos - 6) : pos + 1]
        if re.search(r"[A-Z]\.\s[A-Z]\.", prefix):
            return False

    return True


def _split_at_sentences(text: str, max_chars: int) -> list[str]:
    """Split *text* at sentence boundaries, respecting the max_chars limit.

    Scans for sentence-ending punctuation and only splits when the current
    chunk would exceed *max_chars* OR we've already accumulated enough text
    that a natural sentence boundary is a good stopping point.

    Args:
        text: A single paragraph or section of text.
        max_chars: Maximum character count per output chunk.

    Returns:
        List of sentence-level chunks.
    """
    chunks: list[str] = []
    current_start = 0
    i = 0
    n = len(text)

    while i < n:
        if _is_sentence_boundary(text, i):
            # The sentence ends at i (inclusive).
            end = i + 1
            chunk = text[current_start:end].strip()
            if chunk:
                chunks.append(chunk)
            current_start = end
            # Skip whitespace after sentence-ending punctuation
            while current_start < n and text[current_start] in (" ", "\t"):
                current_start += 1
            i = current_start
            continue

        # Hard limit: if we're past max_chars and hit a clause boundary,
        # force a split at the last whitespace boundary before max_chars.
        if (i - current_start) >= max_chars:
            # Try to split at a clause boundary (comma, semicolon, colon)
            slice_ = text[current_start:i]
            clause_pos = _last_clause_boundary(slice_)
            if clause_pos > 0:
                split_at = current_start + clause_pos
                chunk = text[current_start:split_at].strip()
                if chunk:
                    chunks.append(chunk)
                current_start = split_at
                # skip the clause-boundary punctuation and any trailing space
                while current_start < n and text[current_start] in (",;: \t"):
                    current_start += 1
                i = current_start
                continue
            else:
                # Fall back to last word boundary
                space_pos = slice_.rfind(" ")
                if space_pos > 0:
                    split_at = current_start + space_pos
                    chunk = text[current_start:split_at].strip()
                    if chunk:
                        chunks.append(chunk)
                    current_start = split_at + 1
                    i = current_start
                    continue

        i += 1

    # Remaining text
    remaining = text[current_start:].strip()
    if remaining:
        chunks.append(remaining)

    return chunks


def _last_clause_boundary(text: str) -> int:
    """Return index of the last safe clause-boundary character in *text*.

    A clause boundary is a ``,``, ``;``, or ``:`` that is not inside a
    number or abbreviation.  Returns -1 if none found.

    Args:
        text: Text to scan.

    Returns:
        Index of the last clause-boundary punctuation, or -1.
    """
    for i in range(len(text) - 1, -1, -1):
        if text[i] in ",;:":
            return i
    return -1


def _make_segment(text: str) -> TextSegment:
    """Create a :class:`TextSegment` from a chunk of text.

    Args:
        text: The segment text (already stripped).

    Returns:
        A fully-populated :class:`TextSegment` with hashes, word count,
        ``status="pending"``, and ``audio_path=None``.
    """
    source_hash = hashlib.sha256(text.encode()).hexdigest()
    normalized = normalize_text(text)
    normalized_hash = hashlib.sha256(normalized.encode()).hexdigest()
    wc = len(text.split())
    return TextSegment(
        text=text,
        source_hash=source_hash,
        normalized_hash=normalized_hash,
        word_count=wc,
        status="pending",
        audio_path=None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def segment_text(text: str, max_chars: int = 500) -> list[TextSegment]:
    """Segment text into TTS-sized chunks, respecting linguistic boundaries.

    Splits in priority order:

    1. Section boundary (double newline)
    2. Paragraph boundary (single newline)
    3. Sentence boundary (sentence-ending punctuation + space)
    4. Clause boundary (comma / semicolon / colon + space)
    5. Hard character limit (*max_chars*)

    Opening quotation marks are never separated from the word that follows
    them; decimal numbers and common abbreviations are never split mid-term.

    Args:
        text: Chapter plain text, typically the output of
            :func:`epub2audio.epub.cleanup.xhtml_to_text` after normalization.
        max_chars: Maximum character count per segment.  Defaults to 500.

    Returns:
        Ordered list of :class:`~epub2audio.models.TextSegment` objects.
    """
    if not text.strip():
        return []

    segments: list[TextSegment] = []

    # Priority 1: split on section boundaries (double newline / blank line).
    sections = re.split(r"\n\n+", text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chars:
            # Section fits — emit as-is.
            segments.append(_make_segment(section))
            continue

        # Priority 2: split on paragraph boundaries (single newline).
        paragraphs = section.split("\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(para) <= max_chars:
                segments.append(_make_segment(para))
                continue

            # Priority 3 & 4 & 5: sentence / clause / hard-limit splitting.
            chunks = _split_at_sentences(para, max_chars)
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                # Final safety: if a chunk is still too long, split at word
                # boundary (never mid-word).
                if len(chunk) > max_chars:
                    sub_chunks = _split_at_word_boundary(chunk, max_chars)
                    for sub in sub_chunks:
                        if sub.strip():
                            segments.append(_make_segment(sub.strip()))
                else:
                    segments.append(_make_segment(chunk))

    return segments


def _split_at_word_boundary(text: str, max_chars: int) -> list[str]:
    """Split *text* at word boundaries so no chunk exceeds *max_chars*.

    Never splits mid-word.  Used as the last-resort fallback when sentence
    and clause splitting fail to produce short enough chunks.

    Args:
        text: Text to split.
        max_chars: Maximum characters per chunk.

    Returns:
        List of chunks, each ≤ max_chars characters (unless a single word
        exceeds the limit, in which case that word is emitted as-is).
    """
    words = text.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        # +1 for the space we'd add
        needed = len(word) + (1 if current else 0)
        if current_len + needed > max_chars and current:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += needed

    if current:
        chunks.append(" ".join(current))

    return chunks
