"""Rule-based Narration Director: build provider-neutral narration plans.

:func:`build_narration_plan` is the public entry point of the Director.  It
turns a chapter's cleaned text into one :class:`~epub2audio.models.NarrationPlan`
per scene, applying a single scene-level default direction and only overriding
individual segments when their emotional intensity diverges significantly from
the scene.

The Director is fully deterministic (no LLM, no network): identical input text
always produces an identical plan.  It annotates but never rewrites prose and
never invents dialogue \u2014 every segment's ``text`` comes straight from
:func:`~epub2audio.text.segment.segment_text`.

See docs/decisions/003-narration-pipeline.md.
"""

from __future__ import annotations

from epub2audio.director import dialogue, emphasis, scenes, scoring
from epub2audio.models import (
    NarrationDirection,
    NarrationPlan,
    NarrationSegment,
    TextSegment,
)
from epub2audio.pronunciation.lexicon import PronunciationLexicon
from epub2audio.text.normalize import normalize_text
from epub2audio.text.pauses import get_pause
from epub2audio.text.segment import segment_text

# A segment whose own intensity differs from its scene's default by more than
# this threshold gets a local direction override; otherwise it inherits the
# scene default.  Keeps narration consistent within a scene.
_OVERRIDE_THRESHOLD = 0.25

# Minimum silence after the final segment of a scene, to mark the scene change.
_SCENE_GAP_MS = 700


def _segment_id(chapter: int, scene: int, index: int, normalized_hash: str) -> str:
    """Build a stable, unique segment id.

    Combines positional coordinates with a slice of the segment's normalized
    content hash so ids are stable across runs (for resume) yet unique within a
    chapter even if two segments share identical text.

    Args:
        chapter: 1-based chapter index.
        scene: 1-based scene index.
        index: 0-based segment index within the scene.
        normalized_hash: The segment's normalized-text SHA-256 hex digest.

    Returns:
        An identifier such as ``"ch004-sc02-seg0007-1a2b3c4d"``.
    """
    return f"ch{chapter:03d}-sc{scene:02d}-seg{index:04d}-{normalized_hash[:8]}"


def _pause_after_ms(current_text: str, is_last_in_scene: bool) -> int:
    """Compute the silence to insert after a segment, in milliseconds.

    Reuses the shared boundary-classification rules in
    :func:`~epub2audio.text.pauses.get_pause` (via the segment's trailing
    punctuation).  A minimal :class:`~epub2audio.models.TextSegment` is
    constructed directly from *current_text* — the text is already a
    segment, so there is no need to re-run :func:`~epub2audio.text.segment
    .segment_text`.  The final segment of a scene is given at least a
    scene-gap pause so scene changes are audible.

    Args:
        current_text: The text of the segment the pause follows.
        is_last_in_scene: Whether this is the last segment of its scene.

    Returns:
        Pause duration in milliseconds (≥ 0).
    """
    # Build a minimal TextSegment so get_pause can classify the trailing
    # punctuation.  Hashes and word_count are not used by get_pause.
    stub = TextSegment(
        text=current_text,
        source_hash="",
        normalized_hash="",
        word_count=0,
        status="pending",
        audio_path=None,
    )
    spec = get_pause(stub, stub)
    base = spec.duration_ms if spec is not None else 0
    if is_last_in_scene:
        return max(base, _SCENE_GAP_MS)
    return base


def _build_segment(
    text: str,
    chapter: int,
    scene: int,
    index: int,
    normalized_hash: str,
    scene_direction: NarrationDirection,
    scene_intensity: float,
    is_last_in_scene: bool,
    lexicon: PronunciationLexicon | None = None,
) -> NarrationSegment:
    """Assemble a single :class:`NarrationSegment` from a chunk of text."""
    seg_type, speaker = dialogue.classify(text)

    seg_intensity = scoring.intensity(text)
    override: NarrationDirection | None = None
    effective_pace = scene_direction.pace
    if abs(seg_intensity - scene_intensity) > _OVERRIDE_THRESHOLD:
        effective_pace = scoring.pace(text, seg_intensity)
        override = NarrationDirection(
            mood=scene_direction.mood,
            pace=effective_pace,
            intensity=seg_intensity,
        )

    return NarrationSegment(
        id=_segment_id(chapter, scene, index, normalized_hash),
        type=seg_type,
        speaker=speaker,
        text=text,
        direction=override,
        pause_after_ms=_pause_after_ms(text, is_last_in_scene),
        pace=effective_pace,
        emphasis=emphasis.extract_emphasis(text),
        pronunciation_hints=(
            [e.to_hint() for e in lexicon.find_terms(text)] if lexicon is not None else []
        ),
    )


def _collapse_scenes(scene_parts: list[str]) -> list[str]:
    """Collapse divider-stripped scene parts into a single scene.

    Used when scene analysis is disabled: the scene-divider lines have already
    been removed by :func:`~epub2audio.director.scenes.split_scenes`, and the
    remaining paragraphs are rejoined into one scene string so the whole
    chapter receives a single default direction.

    Args:
        scene_parts: The divider-stripped scene strings from ``split_scenes``.

    Returns:
        A single-element list (or empty list when there is no narration text).
    """
    if not scene_parts:
        return []
    return ["\n\n".join(scene_parts)]


def build_narration_plan(
    chapter_text: str,
    chapter_index: int,
    *,
    lexicon: PronunciationLexicon | None = None,
    scene_analysis: bool = True,
) -> list[NarrationPlan]:
    """Build one narration plan per scene for a chapter.

    Pipeline:

    1. Normalize the chapter text.
    2. Optionally split it into scenes (:func:`~epub2audio.director.scenes.split_scenes`).
    3. For each scene, derive a scene-level :class:`NarrationDirection` from
       deterministic text signals, then segment the scene and direct each
       segment (dialogue/speaker, emphasis, pause, optional intensity override,
       pronunciation hints resolved from *lexicon*).

    Args:
        chapter_text: Cleaned narration text for the chapter (the output of
            :func:`~epub2audio.epub.cleanup.xhtml_to_text`).
        chapter_index: 1-based index of the chapter within the book.
        lexicon: Optional :class:`~epub2audio.pronunciation.lexicon.PronunciationLexicon`
            used to resolve pronunciation hints for each segment.  When
            ``None`` (the default), ``pronunciation_hints`` is always empty
            and all existing callers are unaffected.
        scene_analysis: When ``True`` (the default), the chapter is split into
            scenes via :func:`~epub2audio.director.scenes.split_scenes` and
            one :class:`~epub2audio.models.NarrationPlan` is emitted per
            non-empty scene.  When ``False``, the entire normalised chapter is
            treated as a single scene (one plan, ``scene=1``) with one
            ``default_direction`` computed over the whole chapter.  All other
            annotation — dialogue detection, emphasis hints, pause timing, and
            pronunciation hints — still applies.  Only scene-splitting is
            skipped.  Per ADR-007.

    Returns:
        An ordered list of :class:`NarrationPlan`, one per non-empty scene
        (always exactly one plan when *scene_analysis* is ``False``).
        Empty or whitespace-only input yields an empty list.
    """
    normalized = normalize_text(chapter_text)
    # `split_scenes` also strips scene-divider lines (e.g. "* * *"), which are
    # never narration.  When scene analysis is disabled we still remove those
    # dividers, then collapse everything into a single scene so the chapter
    # gets one default direction.
    scene_parts = scenes.split_scenes(normalized)
    scene_texts = scene_parts if scene_analysis else _collapse_scenes(scene_parts)

    plans: list[NarrationPlan] = []
    scene_number = 0

    for scene_text in scene_texts:
        text_segments = segment_text(scene_text)
        if not text_segments:
            continue

        scene_number += 1

        scene_intensity = scoring.intensity(scene_text)
        scene_dialogue = scoring.dialogue_ratio(scene_text)
        scene_direction = NarrationDirection(
            mood=scoring.mood(scene_text, scene_intensity, scene_dialogue),
            pace=scoring.pace(scene_text, scene_intensity),
            intensity=scene_intensity,
        )

        last_idx = len(text_segments) - 1
        segments = [
            _build_segment(
                text=ts.text,
                chapter=chapter_index,
                scene=scene_number,
                index=i,
                normalized_hash=ts.normalized_hash,
                scene_direction=scene_direction,
                scene_intensity=scene_intensity,
                is_last_in_scene=(i == last_idx),
                lexicon=lexicon,
            )
            for i, ts in enumerate(text_segments)
        ]

        plans.append(
            NarrationPlan(
                chapter=chapter_index,
                scene=scene_number,
                default_direction=scene_direction,
                segments=segments,
            )
        )

    return plans
