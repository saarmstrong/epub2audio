"""Dialogue detection and speaker attribution for the Narration Director.

Deterministic, rule-based heuristics that classify a segment as narration or
dialogue and make a best-effort guess at the speaker.  These are intentionally
conservative: when attribution is uncertain we fall back to ``"unknown"``
rather than inventing a name, and we never alter the segment text.

See docs/decisions/003-narration-pipeline.md.
"""

from __future__ import annotations

import re

from epub2audio.models import SegmentType

# Characters that open/close spoken dialogue.
_QUOTE_CHARS = '"\u201c\u201d'
_QUOTED_RE = re.compile(r"[\"\u201c][^\"\u201c\u201d]+[\"\u201d]")

# "said Case", "asked the doctor", "whispered Molly" \u2014 verb then speaker.
_VERB_THEN_SPEAKER_RE = re.compile(
    r"\b(?:said|asked|replied|whispered|shouted|muttered|cried|called|answered)\s+"
    r"(?:the\s+)?([A-Z][a-zA-Z'-]+)",
)
# "Case said", "the doctor asked", "Molly whispered" \u2014 speaker then verb.
_SPEAKER_THEN_VERB_RE = re.compile(
    r"\b([A-Z][a-zA-Z'-]+)\s+"
    r"(?:said|asked|replied|whispered|shouted|muttered|cried|called|answered)\b",
)

# Attribution verbs preceded by a lowercase pronoun, e.g. "he said" / "she asked".
_PRONOUN_VERB_RE = re.compile(
    r"\b(he|she|they|i)\s+"
    r"(?:said|asked|replied|whispered|shouted|muttered|cried|called|answered)\b",
    re.IGNORECASE,
)

# Speaker labels that are pronouns should be normalised to lowercase.
_PRONOUNS = frozenset({"He", "She", "They", "I"})


def _quoted_char_ratio(text: str) -> float:
    """Return the fraction of characters inside double quotes in *text*."""
    if not text:
        return 0.0
    inside = False
    quoted = 0
    for ch in text:
        if ch in _QUOTE_CHARS:
            inside = not inside
            continue
        if inside:
            quoted += 1
    return quoted / len(text)


def is_dialogue(text: str) -> bool:
    """Return True if *text* is predominantly spoken dialogue.

    A segment counts as dialogue when it contains at least one quoted span and
    a meaningful share of its characters (\u2265 30%) sit inside quotes.  This keeps
    a narration paragraph that merely mentions a short quote classified as
    narration.

    Args:
        text: The segment text.

    Returns:
        True for dialogue-dominant segments, else False.
    """
    if not _QUOTED_RE.search(text):
        return False
    # A line that opens with a quote is a spoken line even if short.
    if text.lstrip()[:1] in _QUOTE_CHARS:
        return True
    return _quoted_char_ratio(text) >= 0.30


def guess_speaker(text: str) -> str:
    """Best-effort speaker attribution for a dialogue segment.

    Tries three deterministic patterns in order and returns the first match:
    ``<verb> <Name>``, ``<Name> <verb>``, then a pronoun subject
    (``he``/``she``/``they``/``i``).  Pronoun matches are normalised to
    lowercase; when nothing matches, returns ``"unknown"`` \u2014 the Director never
    fabricates a name.

    Args:
        text: The dialogue segment text.

    Returns:
        A speaker label, or ``"unknown"``.
    """
    for pattern in (_VERB_THEN_SPEAKER_RE, _SPEAKER_THEN_VERB_RE):
        match = pattern.search(text)
        if match:
            name = match.group(1)
            return name.lower() if name in _PRONOUNS else name

    pronoun = _PRONOUN_VERB_RE.search(text)
    if pronoun:
        return pronoun.group(1).lower()

    return "unknown"


def classify(text: str) -> tuple[SegmentType, str]:
    """Classify *text* and attribute a speaker.

    Args:
        text: The segment text.

    Returns:
        A ``(type, speaker)`` tuple.  Narration segments are always spoken by
        ``"narrator"``; dialogue segments carry the best-effort speaker guess.
    """
    if is_dialogue(text):
        return "dialogue", guess_speaker(text)
    return "narration", "narrator"
