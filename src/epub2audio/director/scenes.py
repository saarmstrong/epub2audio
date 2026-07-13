"""Scene segmentation for the Narration Director.

A chapter is divided into *scenes* so the Director can apply one default
direction per scene and only override individual segments when the emotion
changes significantly (see docs/decisions/003-narration-pipeline.md, "Scene
Segmentation").  Splitting is deterministic and text-only.

Scene boundaries are recognised from two sources:

1. Explicit *scene-break lines* — a paragraph whose visible content is only
   break punctuation such as ``* * *``, ``***``, ``---``, ``\u2022``, ``#``.
2. Nothing else: paragraphs between breaks (or the whole chapter, if there are
   no break lines) form a single scene.

The Director never inserts or invents text; a scene is always a contiguous
slice of the original paragraphs.
"""

from __future__ import annotations

import re

# A paragraph that, once stripped, consists solely of these characters (and
# whitespace) is treated as a scene divider rather than narration.
_BREAK_LINE_RE = re.compile(r"^[\s*#\u2022\u00b7.\-\u2014\u2013_=~]+$")


def _is_break_line(paragraph: str) -> bool:
    """Return True if *paragraph* is a scene-divider line, not narration.

    A divider is a short paragraph made up entirely of break punctuation
    (asterisks, dashes, bullets, hashes, etc.).  A length guard prevents a long
    run of dotted prose from being mistaken for a divider.

    Args:
        paragraph: A single paragraph (already stripped of surrounding space).

    Returns:
        True when the paragraph should be treated as a scene boundary.
    """
    if not paragraph or len(paragraph) > 12:
        return False
    return bool(_BREAK_LINE_RE.match(paragraph))


def split_scenes(text: str) -> list[str]:
    """Split chapter *text* into a list of scene texts.

    Paragraphs are delimited by blank lines (one or more).  Explicit
    scene-break lines start a new scene and are themselves discarded.  When a
    chapter contains no break lines, the entire chapter is returned as a single
    scene.

    Args:
        text: Cleaned, normalized chapter narration text.

    Returns:
        A list of non-empty scene strings in reading order.  Returns an empty
        list if *text* has no narration content.
    """
    if not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text)]

    scenes: list[str] = []
    current: list[str] = []
    for para in paragraphs:
        if not para:
            continue
        if _is_break_line(para):
            if current:
                scenes.append("\n\n".join(current))
                current = []
            continue
        current.append(para)

    if current:
        scenes.append("\n\n".join(current))

    return scenes
