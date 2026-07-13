"""Emphasis-hint extraction for the Narration Director.

Finds phrases within a segment worth stressing and returns provider-neutral
:class:`~epub2audio.models.EmphasisHint` objects.  Every hint's ``phrase`` is a
verbatim substring of the input text \u2014 the Director annotates but never
rewrites prose.  How the emphasis is realised (punctuation, SSML, etc.) is the
provider adapter's job.
"""

from __future__ import annotations

import re

from epub2audio.models import EmphasisHint

# ALL-CAPS run of \u2265 3 letters (optionally hyphenated), e.g. "STOP", "NO-ONE".
# Length \u2265 3 avoids flagging short acronyms like "AI"/"TV".
_CAPS_RE = re.compile(r"\b[A-Z][A-Z'-]{2,}\b")

# Text wrapped in single asterisks or underscores, e.g. *never* / _now_.
# Non-greedy inner match with no surrounding word char to avoid a*b*c noise.
_WRAPPED_RE = re.compile(r"(?<!\w)[*_]([^*_\n]{1,60}?)[*_](?!\w)")


def extract_emphasis(text: str) -> list[EmphasisHint]:
    """Extract emphasis hints from *text*.

    Two deterministic signals are used:

    - ALL-CAPS words (\u2265 3 letters) \u2192 ``"strong"`` emphasis.
    - Phrases wrapped in ``*asterisks*`` or ``_underscores_`` \u2192 ``"moderate"``.

    Hints are de-duplicated by phrase, preserving first-occurrence order, so a
    word shouted twice yields a single hint.

    Args:
        text: The segment text to scan.

    Returns:
        An ordered, de-duplicated list of :class:`EmphasisHint` (possibly empty).
    """
    hints: list[EmphasisHint] = []
    seen: set[str] = set()

    def _add(phrase: str, level: str) -> None:
        phrase = phrase.strip()
        if not phrase or phrase in seen:
            return
        seen.add(phrase)
        hints.append(EmphasisHint(phrase=phrase, level=level))  # type: ignore[arg-type]

    for match in _CAPS_RE.finditer(text):
        _add(match.group(0), "strong")

    for match in _WRAPPED_RE.finditer(text):
        _add(match.group(1), "moderate")

    return hints
