"""Deterministic text-signal scoring for the Narration Director.

These helpers turn a block of narration text into provider-neutral delivery
numbers (intensity, pace) and a coarse mood label.  Everything here is a pure
function of the input text: the same text always yields the same numbers, which
keeps narration plans reproducible and unit-testable (see
docs/decisions/003-narration-pipeline.md).

No prose is rewritten and no engine-specific data is produced.
"""

from __future__ import annotations

import re

# Pace is clamped to a conservative band so a mis-scored scene can never make
# narration unlistenably fast or slow.
_PACE_MIN = 0.85
_PACE_MAX = 1.15

# A word is treated as shouted/emphatic ALL-CAPS only when it is at least this
# long, to avoid flagging short acronyms like "AI" or "TV".
_MIN_CAPS_LEN = 3

_WORD_RE = re.compile(r"[A-Za-z']+")
_CAPS_WORD_RE = re.compile(r"\b[A-Z]{" + str(_MIN_CAPS_LEN) + r",}\b")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")
# Straight and curly double quotes delimit spoken text.
_QUOTE_CHARS = '"\u201c\u201d'


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp *value* into the inclusive range ``[low, high]``."""
    return max(low, min(high, value))


def dialogue_ratio(text: str) -> float:
    """Return the fraction of characters that lie inside double quotes.

    A simple, deterministic proxy for "how much of this passage is spoken
    dialogue".  Handles both straight (``"``) and curly (``\u201c \u201d``) quotes by
    toggling an open/close state.

    Args:
        text: The passage to inspect.

    Returns:
        A ratio in ``[0.0, 1.0]``; ``0.0`` for empty text.
    """
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
    return _clamp(quoted / len(text), 0.0, 1.0)


def intensity(text: str) -> float:
    """Estimate emotional intensity of *text* in ``[0.0, 1.0]``.

    Combines three deterministic signals, each normalized and weighted:

    - density of exclamation marks (per word),
    - density of question marks (per word),
    - proportion of ALL-CAPS (shouted) words.

    Args:
        text: The passage to score.

    Returns:
        Intensity in ``[0.0, 1.0]``; ``0.0`` for text with no words.
    """
    words = _WORD_RE.findall(text)
    n = len(words)
    if n == 0:
        return 0.0

    exclaims = text.count("!")
    questions = text.count("?")
    caps = len(_CAPS_WORD_RE.findall(text))

    # Each term is a per-word density scaled so a handful of markers in a short
    # passage already pushes intensity up, then clamped by the final _clamp.
    exclaim_signal = (exclaims / n) * 4.0
    question_signal = (questions / n) * 2.0
    caps_signal = (caps / n) * 3.0

    score = 0.5 * exclaim_signal + 0.25 * question_signal + 0.25 * caps_signal
    return round(_clamp(score, 0.0, 1.0), 2)


def _avg_sentence_words(text: str) -> float:
    """Return the mean word count per sentence in *text* (0.0 if no words)."""
    words = _WORD_RE.findall(text)
    if not words:
        return 0.0
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    n_sentences = max(1, len(sentences))
    return len(words) / n_sentences


def pace(text: str, intensity_score: float) -> float:
    """Derive a speaking pace multiplier for *text*.

    Higher intensity nudges pace up; longer average sentences (denser, more
    descriptive prose) nudge it down.  The result is clamped to a conservative
    band and rounded to two decimals for stable, reproducible plans.

    Args:
        text: The passage the pace applies to.
        intensity_score: Precomputed :func:`intensity` for *text* (passed in to
            avoid recomputing it).

    Returns:
        A pace multiplier in ``[0.85, 1.15]``; ``1.0`` is neutral.
    """
    base = 1.0
    base += 0.15 * (intensity_score - 0.3)

    avg = _avg_sentence_words(text)
    if avg > 25:
        base -= 0.05
    elif 0 < avg < 12:
        base += 0.03

    return round(_clamp(base, _PACE_MIN, _PACE_MAX), 2)


def mood(text: str, intensity_score: float, dialogue_score: float) -> str:
    """Choose a coarse, deterministic mood label for a scene.

    The label is descriptive and provider-neutral; a provider adapter is free
    to ignore it or map it to instructions.  Selection is a fixed decision tree
    so the same signals always produce the same label.

    Args:
        text: The scene text (currently unused beyond the derived scores, kept
            for future signal expansion).
        intensity_score: Precomputed :func:`intensity`.
        dialogue_score: Precomputed :func:`dialogue_ratio`.

    Returns:
        One of a small fixed set of mood labels.
    """
    _ = text  # reserved for future lexical mood cues
    if intensity_score >= 0.6:
        return "tense and urgent"
    if dialogue_score >= 0.5:
        return "conversational"
    if intensity_score <= 0.2:
        return "calm and measured"
    return "neutral narration"
