"""Tests for the scene_analysis toggle in build_narration_plan (M12).

Critical regression guards:
- scene_analysis=False strips scene dividers (never read aloud).
- The word multiset across all segments is identical whether scene_analysis
  is True or False (same words, only grouping differs).
- scene_analysis=True produces multiple NarrationPlan objects for a chapter
  containing a scene break; False produces exactly one.
"""

from __future__ import annotations

import re
from collections import Counter

from epub2audio.director import build_narration_plan
from epub2audio.models import NarrationPlan

# A chapter with one explicit scene break and content on both sides.
CHAPTER_WITH_BREAK = """\
The rain fell on the neon street. Case walked slowly.

* * *

Later, the room was quiet. He waited for the dawn.
"""

# No scene break — both modes should agree on the word list.
CHAPTER_NO_BREAK = "Alpha beta gamma. Delta epsilon zeta."

# Multiple break styles
CHAPTER_TRIPLE_DASH = "Before.\n\n---\n\nAfter."


def _all_segments(plans: list[NarrationPlan]) -> list[str]:
    return [seg.text for plan in plans for seg in plan.segments]


def _words(texts: list[str]) -> Counter[str]:
    """Return a Counter of alphabetic tokens (case-insensitive)."""
    counter: Counter[str] = Counter()
    for t in texts:
        counter.update(w.lower() for w in re.findall(r"[a-zA-Z']+", t))
    return counter


# ---------------------------------------------------------------------------
# Scene splitting behaviour
# ---------------------------------------------------------------------------


class TestSceneAnalysisToggle:
    def test_true_splits_on_break(self) -> None:
        plans = build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=True)
        assert len(plans) > 1, "scene_analysis=True should produce >1 plan when a break exists"

    def test_false_gives_single_plan(self) -> None:
        plans = build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=False)
        assert len(plans) == 1, "scene_analysis=False must always yield exactly one plan"

    def test_false_single_plan_scene_number_is_one(self) -> None:
        plans = build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=False)
        assert plans[0].scene == 1

    def test_no_break_both_modes_give_one_plan(self) -> None:
        a = build_narration_plan(CHAPTER_NO_BREAK, 1, scene_analysis=True)
        b = build_narration_plan(CHAPTER_NO_BREAK, 1, scene_analysis=False)
        assert len(a) == 1
        assert len(b) == 1

    def test_triple_dash_break_false_gives_single_plan(self) -> None:
        plans = build_narration_plan(CHAPTER_TRIPLE_DASH, 1, scene_analysis=False)
        assert len(plans) == 1


# ---------------------------------------------------------------------------
# CRITICAL: scene dividers never appear in segment text (M12 bug regression)
# ---------------------------------------------------------------------------


class TestDividersNeverNarrated:
    """Verify the _collapse_scenes fix: scene-break divider characters are
    stripped and never passed to TTS, regardless of scene_analysis setting."""

    def test_true_no_divider_in_segments(self) -> None:
        segs = _all_segments(build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=True))
        for text in segs:
            assert "*" not in text, f"Divider character in segment: {text!r}"

    def test_false_no_divider_in_segments(self) -> None:
        """The _collapse_scenes path must not let '* * *' leak into TTS input."""
        segs = _all_segments(build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=False))
        for text in segs:
            assert "*" not in text, f"scene_analysis=False leaked divider into segment: {text!r}"

    def test_triple_dash_not_in_segments_false(self) -> None:
        segs = _all_segments(build_narration_plan(CHAPTER_TRIPLE_DASH, 1, scene_analysis=False))
        assert all("---" not in t for t in segs)

    def test_triple_dash_not_in_segments_true(self) -> None:
        segs = _all_segments(build_narration_plan(CHAPTER_TRIPLE_DASH, 1, scene_analysis=True))
        assert all("---" not in t for t in segs)


# ---------------------------------------------------------------------------
# Word multiset invariant: same words either way
# ---------------------------------------------------------------------------


class TestWordMultisetConsistency:
    """Assert Counter(words in scene_analysis=True) == Counter(words in False).

    This guards the invariant that the scene_analysis toggle only changes
    grouping, never drops or duplicates words.
    """

    def test_multiset_equal_with_break(self) -> None:
        plans_t = build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=True)
        plans_f = build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=False)
        words_t = _words(_all_segments(plans_t))
        words_f = _words(_all_segments(plans_f))
        assert words_t == words_f, (
            f"Word multiset differs between scene_analysis modes.\n"
            f"Only in True:  {words_t - words_f}\n"
            f"Only in False: {words_f - words_t}"
        )

    def test_multiset_equal_no_break(self) -> None:
        plans_t = build_narration_plan(CHAPTER_NO_BREAK, 1, scene_analysis=True)
        plans_f = build_narration_plan(CHAPTER_NO_BREAK, 1, scene_analysis=False)
        assert _words(_all_segments(plans_t)) == _words(_all_segments(plans_f))

    def test_multiset_equal_triple_dash(self) -> None:
        plans_t = build_narration_plan(CHAPTER_TRIPLE_DASH, 1, scene_analysis=True)
        plans_f = build_narration_plan(CHAPTER_TRIPLE_DASH, 1, scene_analysis=False)
        assert _words(_all_segments(plans_t)) == _words(_all_segments(plans_f))

    def test_multiset_equal_multi_break(self) -> None:
        chapter = "Part A.\n\n* * *\n\nPart B.\n\n---\n\nPart C."
        plans_t = build_narration_plan(chapter, 1, scene_analysis=True)
        plans_f = build_narration_plan(chapter, 1, scene_analysis=False)
        assert _words(_all_segments(plans_t)) == _words(_all_segments(plans_f))


# ---------------------------------------------------------------------------
# Default direction is present and meaningful in False mode
# ---------------------------------------------------------------------------


class TestSceneAnalysisFalseDirection:
    def test_single_plan_has_default_direction(self) -> None:
        plans = build_narration_plan(CHAPTER_WITH_BREAK, 1, scene_analysis=False)
        assert plans[0].default_direction is not None
        assert plans[0].default_direction.mood

    def test_chapter_index_propagated(self) -> None:
        plans = build_narration_plan(CHAPTER_WITH_BREAK, 7, scene_analysis=False)
        assert plans[0].chapter == 7
