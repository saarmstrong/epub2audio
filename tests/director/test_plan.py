"""End-to-end tests for :func:`epub2audio.director.build_narration_plan`.

These assert the provider-neutral contract of the Narration Director: correct
plan shape, deterministic output, scene-aware direction, and \u2014 critically \u2014
that the Director annotates without rewriting prose or inventing dialogue.
"""

from __future__ import annotations

import re

from epub2audio.director import build_narration_plan
from epub2audio.models import NarrationDirection, NarrationPlan, NarrationSegment
from epub2audio.text.normalize import normalize_text

# A small multi-scene chapter: calm narration, a heated dialogue exchange, then
# a quiet coda separated by an explicit scene break.
SAMPLE = """The rain fell on the neon street. Case walked slowly, thinking of nothing.

"You need to STOP," Molly said. "They will kill you if you go back there!"

* * *

Later, the room was quiet. He waited for the dawn.
"""


def _all_segments(plans: list[NarrationPlan]) -> list[NarrationSegment]:
    return [seg for plan in plans for seg in plan.segments]


def test_returns_narration_plans() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    assert plans
    assert all(isinstance(p, NarrationPlan) for p in plans)
    assert all(p.chapter == 4 for p in plans)


def test_empty_text_yields_no_plans() -> None:
    assert build_narration_plan("", 1) == []
    assert build_narration_plan("   \n\n  \t ", 1) == []


def test_scene_break_splits_scenes() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    # The "* * *" divider separates the dialogue scene from the quiet coda.
    assert len(plans) == 2
    assert [p.scene for p in plans] == [1, 2]


def test_scene_numbers_are_contiguous_from_one() -> None:
    plans = build_narration_plan(SAMPLE, 2)
    assert [p.scene for p in plans] == list(range(1, len(plans) + 1))


def test_default_direction_shape() -> None:
    plan = build_narration_plan(SAMPLE, 1)[0]
    d = plan.default_direction
    assert isinstance(d, NarrationDirection)
    assert 0.0 <= d.intensity <= 1.0
    assert 0.85 <= d.pace <= 1.15
    assert d.mood


def test_determinism() -> None:
    a = build_narration_plan(SAMPLE, 4)
    b = build_narration_plan(SAMPLE, 4)
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]


def test_dialogue_detected_with_speaker() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    dialogue = [s for s in _all_segments(plans) if s.type == "dialogue"]
    assert dialogue, "expected at least one dialogue segment"
    assert any(s.speaker == "Molly" for s in dialogue)


def test_narration_speaker_is_narrator() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    for seg in _all_segments(plans):
        if seg.type == "narration":
            assert seg.speaker == "narrator"


def test_emphasis_is_verbatim_substring() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    hits = [(s, e) for s in _all_segments(plans) for e in s.emphasis]
    assert any(e.phrase == "STOP" for _, e in hits), "expected STOP flagged"
    for seg, hint in hits:
        assert hint.phrase in seg.text
        assert hint.level in {"light", "moderate", "strong"}


def test_pause_after_ms_non_negative_and_scene_end_gap() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    for plan in plans:
        for seg in plan.segments:
            assert seg.pause_after_ms >= 0
        # Last segment of each scene carries at least the scene-gap pause.
        assert plan.segments[-1].pause_after_ms >= 700


def test_ids_are_unique_and_stable() -> None:
    plans = build_narration_plan(SAMPLE, 4)
    ids = [s.id for s in _all_segments(plans)]
    assert len(ids) == len(set(ids)), "segment ids must be unique"
    # Stable across a second run.
    again = [s.id for s in _all_segments(build_narration_plan(SAMPLE, 4))]
    assert ids == again


def test_text_is_preserved_never_rewritten() -> None:
    """Every segment's text must be a substring of the normalized chapter text.

    This is the core "preserve original text / never rewrite prose" guarantee:
    the Director may split and annotate, but the words themselves come straight
    from the source.
    """
    normalized = normalize_text(SAMPLE)
    # Collapse whitespace for a robust containment check (segmentation may drop
    # inter-paragraph newlines but never alters the words themselves).
    haystack = re.sub(r"\s+", " ", normalized)
    for seg in _all_segments(build_narration_plan(SAMPLE, 4)):
        needle = re.sub(r"\s+", " ", seg.text).strip()
        assert needle in haystack, f"segment text not found in source: {needle!r}"


def test_provider_neutral_no_markup() -> None:
    """Plans must not contain engine-specific markup (SSML, tags)."""
    for seg in _all_segments(build_narration_plan(SAMPLE, 4)):
        dumped = seg.model_dump_json()
        assert "<speak" not in dumped
        assert "<prosody" not in dumped
        assert "<phoneme" not in dumped
