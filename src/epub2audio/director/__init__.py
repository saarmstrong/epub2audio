"""Narration Director: provider-neutral narration planning.

The Director analyzes cleaned chapter text and produces
:class:`~epub2audio.models.NarrationPlan` objects (one per scene) describing how
the text should be delivered \u2014 mood, pace, intensity, dialogue/speaker,
emphasis, and pause timing \u2014 without any engine-specific data.  Provider
adapters (Milestone 9) translate these plans into provider-specific controls.

The v1 Director is fully deterministic and rule-based (no LLM); it annotates but
never rewrites prose and never invents dialogue.  See
docs/decisions/003-narration-pipeline.md.

Public API:
    build_narration_plan(chapter_text, chapter_index) -> list[NarrationPlan]
"""

from __future__ import annotations

from epub2audio.director.plan import build_narration_plan

__all__ = ["build_narration_plan"]
