"""Silence insertion specifications between TTS segments.

Pause durations are determined by the boundary type inferred from the
trailing punctuation and whitespace of the preceding segment.  The rules
are intentionally simple and conservative; future milestones may tune them
based on listening tests.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from epub2audio.models import TextSegment

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class PauseSpec(BaseModel):
    """Specification for a silence gap to insert between two TTS segments.

    Attributes:
        duration_ms: Pause duration in milliseconds.
        reason: Human-readable description of why this pause was chosen.
    """

    model_config = ConfigDict(frozen=True)

    duration_ms: int
    """Pause length in milliseconds."""

    reason: str
    """Short label describing the boundary type, e.g. ``"paragraph_boundary"``."""


# ---------------------------------------------------------------------------
# Boundary detection helpers
# ---------------------------------------------------------------------------

# Trailing characters that suggest a paragraph or section break.
# The segment text ends with these after stripping, AND there's evidence of
# a blank-line boundary (double newline) in the *source* text.  Since segments
# are already split, we infer paragraph boundaries by the absence of trailing
# mid-sentence punctuation.
_SENTENCE_ENDINGS = frozenset(".?!")
_CLAUSE_ENDINGS = frozenset(",;:")


def _classify_boundary(before: TextSegment) -> str:
    """Classify the boundary type at the end of *before*.

    Uses the trailing character of the segment text (after stripping) to
    infer what kind of boundary follows.

    Returns:
        One of ``"paragraph"``, ``"sentence"``, ``"clause"``,
        or ``"continuation"``.
    """
    text = before.text.rstrip()
    if not text:
        return "continuation"

    last_char = text[-1]

    # Sentence-ending punctuation → sentence boundary (at minimum).
    # We treat this as a paragraph boundary only when context (e.g. the
    # segment itself is a complete paragraph) is available; without that
    # context we conservatively classify as sentence.
    if last_char in _SENTENCE_ENDINGS:
        return "sentence"

    if last_char in _CLAUSE_ENDINGS:
        return "clause"

    return "continuation"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Pause durations in milliseconds, keyed by boundary type.
_PAUSE_DURATIONS: dict[str, int] = {
    "paragraph": 600,
    "sentence": 300,
    "clause": 150,
}


def get_pause(before: TextSegment, after: TextSegment) -> PauseSpec | None:
    """Return the pause to insert between two consecutive segments, or None.

    Boundary classification is inferred from the trailing punctuation of
    *before*:

    - Paragraph boundary → 600 ms
    - Sentence boundary  → 300 ms
    - Clause boundary    → 150 ms
    - Continuation       → no pause (returns ``None``)

    Args:
        before: The segment that was just synthesized.
        after: The segment about to be synthesized (currently unused, reserved
            for future context-aware pause logic).

    Returns:
        A :class:`PauseSpec` describing the silence to insert, or ``None``
        if no pause is warranted.
    """
    _ = after  # reserved for future use

    boundary = _classify_boundary(before)

    if boundary == "continuation":
        return None

    # Promote sentence boundary to paragraph if the segment text has leading
    # blank lines stripped — i.e. it was its own standalone paragraph already.
    # For now we rely on callers to pass paragraph-boundary context via a
    # sentinel (e.g. a segment with text "\n\n"); in the absence of such a
    # sentinel we use the sentence classification directly.

    duration_ms = _PAUSE_DURATIONS.get(boundary, 0)
    if duration_ms == 0:
        return None

    return PauseSpec(duration_ms=duration_ms, reason=f"{boundary}_boundary")
