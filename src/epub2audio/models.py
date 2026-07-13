"""Shared Pydantic data models for epub2audio.

This module is the base layer of the package.  It must never import from any
other epub2audio module.  All other modules may import from here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Navigation / structural models
# ---------------------------------------------------------------------------


class NavigationEntry(BaseModel):
    """One entry in the EPUB Table-of-Contents (EPUB3 nav or EPUB2 NCX).

    Represents a single clickable heading in the reading order.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    """Human-readable title of the entry as it appears in the TOC."""

    doc_path: str
    """Relative path to the XHTML spine document this entry points at."""

    fragment: str | None
    """URL fragment (id attribute) within the document, or None for top-of-file."""

    depth: int
    """Nesting depth (0 = top-level chapter, 1 = sub-section, …)."""


class BookDocument(BaseModel):
    """One XHTML spine item from the EPUB manifest.

    Carries the content fingerprint so the pipeline can detect changes without
    re-reading the full document.
    """

    model_config = ConfigDict(frozen=True)

    path: str
    """Relative path to the XHTML document inside the EPUB ZIP."""

    content_hash: str
    """SHA-256 hex digest of the raw XHTML bytes (for change detection)."""

    nav_entries: list[NavigationEntry]
    """All NavigationEntry objects whose doc_path matches this document."""


# ---------------------------------------------------------------------------
# Book-level metadata
# ---------------------------------------------------------------------------


class BookMetadata(BaseModel):
    """Dublin Core metadata extracted from the EPUB OPF package document.

    Only ``title``, ``author``, ``language``, and ``identifier`` are
    mandatory; all other fields may be absent in the source EPUB.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    """Book title (dc:title)."""

    author: str
    """Primary creator/author (dc:creator)."""

    language: str
    """BCP-47 language tag, e.g. ``"en"``, ``"en-US"`` (dc:language)."""

    identifier: str
    """Unique identifier such as ISBN or UUID (dc:identifier)."""

    publisher: str | None
    """Publisher name (dc:publisher), or None if absent."""

    date: str | None
    """Publication date as a free-form string (dc:date), or None if absent."""

    rights: str | None
    """Copyright or license statement (dc:rights), or None if absent."""


# ---------------------------------------------------------------------------
# Chapter-detection models
# ---------------------------------------------------------------------------


class ChapterCandidate(BaseModel):
    """A document or section that has been evaluated for chapter inclusion.

    The scoring engine emits one ChapterCandidate per candidate; callers
    filter by score threshold (≥ 2 → include).
    """

    model_config = ConfigDict(frozen=True)

    doc_path: str
    """Relative path to the candidate XHTML document."""

    title: str | None
    """Best title guess from the TOC or heading element, or None if unknown."""

    score: int
    """Weighted sum of signals (positive = include, negative = exclude)."""

    signals: list[str]
    """Human-readable signal labels used to produce the score, e.g.
    ``["toc_entry +4", "short_document -2"]``."""


class Chapter(BaseModel):
    """A confirmed chapter ready for text extraction and synthesis.

    ``stable_id`` is derived from the chapter's content hashes so that
    segments can be matched across resume runs even if the chapter order
    changes.
    """

    model_config = ConfigDict(frozen=True)

    chapter_id: str
    """Positional identifier, e.g. ``"ch001"``."""

    title: str
    """Human-readable chapter title used in the output filename and ID3 tag."""

    source_docs: list[str]
    """Ordered list of XHTML document paths that make up this chapter."""

    word_count: int
    """Estimated word count of the cleaned narration text."""

    stable_id: str
    """Content-derived hash used to match chapters across resume runs."""


# ---------------------------------------------------------------------------
# Text / TTS segment models
# ---------------------------------------------------------------------------


class TextSegment(BaseModel):
    """One unit of text to be passed to the TTS engine in a single call.

    ``source_hash`` fingerprints the original extracted text; ``normalized_hash``
    fingerprints the text after normalization.  Both are used by the resume
    strategy to decide whether cached audio is still valid.
    """

    model_config = ConfigDict(frozen=True)

    text: str
    """The (possibly normalized) text to synthesize."""

    source_hash: str
    """SHA-256 hex digest of the original extracted text before normalization."""

    normalized_hash: str
    """SHA-256 hex digest of the text after normalization (fed to TTS)."""

    word_count: int
    """Approximate word count of this segment."""

    status: str
    """Synthesis status, one of: ``"pending"``, ``"done"``, ``"error"``."""

    audio_path: str | None
    """Absolute path to the synthesized WAV file for this segment, or None."""


class AudioChunk(BaseModel):
    """Raw audio returned by a single TTS call.

    This is the **one exception** to the project-wide ``frozen=True`` rule.
    NumPy arrays are not hashable and Pydantic cannot freeze them; we therefore
    use ``frozen=False, arbitrary_types_allowed=True``.  The model is treated as
    logically immutable by convention — callers must not mutate ``data`` after
    construction.
    """

    # AudioChunk is intentionally NOT frozen because numpy arrays are not
    # hashable and Pydantic raises a TypeError when it tries to compute the
    # hash during model construction with frozen=True.  See decision record
    # docs/decisions/001-audiochunk-frozen-exception.md.
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    sample_rate: int
    """Audio sample rate in Hz (e.g. 24000)."""

    data: Any
    """NumPy ndarray of float32 samples, shape (n_samples,) or (channels, n_samples).
    Typed as ``Any`` because mypy strict mode cannot verify numpy array shapes."""


# ---------------------------------------------------------------------------
# Narration Director models
# ---------------------------------------------------------------------------
#
# These models are the provider-neutral output of the Narration Director
# (see docs/decisions/003-narration-pipeline.md).  They must never contain
# engine-specific data (no SSML, no Kokoro tokens): a provider adapter is
# responsible for translating a plan into provider-specific controls.  The
# shape mirrors the illustrative JSON in Feature.md; field names use the
# project-wide snake_case convention (e.g. ``pause_after_ms`` for the doc's
# ``pauseAfterMs``) so serialized plans match every other model here.

SegmentType = Literal["narration", "dialogue"]
"""Kind of a narration segment: plain narration or attributed dialogue."""


class EmphasisHint(BaseModel):
    """A provider-neutral hint that a phrase should be emphasized.

    The Director locates phrases worth stressing; a provider adapter decides
    how to realize the emphasis (e.g. Kokoro punctuation, Azure SSML
    ``<emphasis>``).  ``phrase`` must be a verbatim substring of the owning
    segment's ``text`` — the Director never rewrites prose.
    """

    model_config = ConfigDict(frozen=True)

    phrase: str
    """Verbatim substring of the segment text to emphasize."""

    level: Literal["light", "moderate", "strong"]
    """Relative emphasis strength; mapped to provider controls by the adapter."""


class PronunciationHint(BaseModel):
    """A reference from a segment to a pronunciation-lexicon entry.

    The Director only *flags* which terms appear in a segment; the actual
    pronunciation (IPA / phonemes / substitution) lives in the pronunciation
    subsystem (Milestone 10) and is applied by the provider adapter.  Keeping
    the pronunciation itself out of the plan preserves provider neutrality.
    """

    model_config = ConfigDict(frozen=True)

    term: str
    """Verbatim substring of the segment text that has a lexicon entry."""


class NarrationDirection(BaseModel):
    """Provider-neutral delivery instruction for a scene or a single segment.

    Used both as a scene-level default (``NarrationPlan.default_direction``)
    and as an optional per-segment override when the emotion of a segment
    diverges significantly from its scene.
    """

    model_config = ConfigDict(frozen=True)

    mood: str
    """Free-form mood/tone label, e.g. ``"restrained cyberpunk noir"``."""

    pace: float
    """Relative speaking pace; ``1.0`` is neutral, < 1.0 slower, > 1.0 faster."""

    intensity: float
    """Emotional intensity in the range ``0.0`` (flat) to ``1.0`` (peak)."""


class NarrationSegment(BaseModel):
    """One directed unit of narration produced by the Director.

    Carries the original text plus provider-neutral delivery annotations.
    ``text`` is always derived from the source EPUB text (a normalized
    substring) — the Director annotates but never rewrites prose and never
    invents dialogue.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    """Stable identifier for the segment (content-derived; used for resume)."""

    type: SegmentType
    """Whether this segment is narration or attributed dialogue."""

    speaker: str
    """Likely speaker label; ``"narrator"`` for narration, a best-guess
    character label (or ``"unknown"``) for dialogue."""

    text: str
    """The narration text to be spoken (a normalized substring of the source)."""

    direction: NarrationDirection | None
    """Per-segment delivery override, or ``None`` to inherit the scene default."""

    pause_after_ms: int
    """Silence to insert after this segment, in milliseconds."""

    pace: float
    """Effective speaking pace for this segment (scene default unless overridden)."""

    emphasis: list[EmphasisHint]
    """Phrases within ``text`` to emphasize (possibly empty)."""

    pronunciation_hints: list[PronunciationHint]
    """Lexicon terms occurring in ``text`` (possibly empty)."""


class NarrationPlan(BaseModel):
    """The Director's provider-neutral plan for one scene of one chapter.

    A chapter is analyzed into one or more scenes; each scene yields a
    :class:`NarrationPlan` with a single ``default_direction`` and its ordered
    segments.  Local overrides live on individual segments only when the
    emotion changes significantly, keeping narration consistent within a scene.
    """

    model_config = ConfigDict(frozen=True)

    chapter: int
    """1-based index of the chapter this plan belongs to."""

    scene: int
    """1-based index of the scene within the chapter."""

    default_direction: NarrationDirection
    """Scene-level delivery instruction applied to every segment by default."""

    segments: list[NarrationSegment]
    """Ordered narration segments for this scene."""


# ---------------------------------------------------------------------------
# Pipeline plan / manifest models
# ---------------------------------------------------------------------------


class ConversionPlan(BaseModel):
    """The ordered list of chapters to synthesize plus the effective configuration.

    Produced by the planner before any TTS work begins.  ``config_snapshot``
    captures all settings that affect synthesis so changes can be detected on
    resume.
    """

    model_config = ConfigDict(frozen=True)

    book_metadata: BookMetadata
    """Metadata for the source EPUB."""

    chapters: list[Chapter]
    """Chapters in reading order."""

    config_snapshot: dict[str, Any]
    """Serializable snapshot of all configuration values that affect output."""


class ConversionManifest(BaseModel):
    """Persistent run state written to disk to support interrupted-run resume.

    Written atomically (to ``.tmp`` then ``os.replace``) before and after each
    segment so a crash loses at most one segment of work.
    """

    model_config = ConfigDict(frozen=True)

    epub_fingerprint: str
    """SHA-256 hex digest of the EPUB file bytes used to detect source changes."""

    config_hash: str
    """SHA-256 hex digest of the serialized ``config_snapshot``."""

    chapters: list[Chapter]
    """Chapters as planned (used to detect plan changes on resume)."""

    segments: list[TextSegment]
    """All text segments across all chapters, in synthesis order."""

    created_at: str
    """ISO-8601 UTC timestamp when this manifest was first created."""

    updated_at: str
    """ISO-8601 UTC timestamp of the last write."""


# ---------------------------------------------------------------------------
# Result / reporting models
# ---------------------------------------------------------------------------


class ChapterResult(BaseModel):
    """Outcome record for one synthesized chapter.

    Written by the converter after each chapter finishes (or fails) so the
    final report can be assembled without re-reading audio files.
    """

    model_config = ConfigDict(frozen=True)

    chapter_id: str
    """Matches ``Chapter.chapter_id``."""

    duration_seconds: float
    """Duration of the output MP3 in seconds (0.0 if synthesis failed)."""

    warnings: list[str]
    """Non-fatal issues encountered during synthesis or encoding."""

    output_path: str | None
    """Absolute path to the final MP3 file, or None if synthesis failed."""


class ChapterMarker(BaseModel):
    """Start/end offsets of one chapter inside a single audiobook file.

    Used by the M4B output format, where every chapter lives inside one
    container as a timestamped marker rather than as a separate file.  Offsets
    are expressed in milliseconds against a ``1/1000`` timebase.
    """

    model_config = ConfigDict(frozen=True)

    chapter_id: str
    """Matches ``Chapter.chapter_id``."""

    title: str
    """Human-readable chapter title written into the container's chapter tag."""

    start_ms: int
    """Inclusive chapter start offset in milliseconds."""

    end_ms: int
    """Exclusive chapter end offset in milliseconds."""


class ConversionReport(BaseModel):
    """Final report written to the output directory after a conversion run.

    Serialized to JSON so users and tooling can inspect what happened without
    replaying the entire conversion.
    """

    model_config = ConfigDict(frozen=True)

    book_metadata: BookMetadata
    """Metadata of the converted book."""

    chapter_results: list[ChapterResult]
    """Per-chapter outcomes in reading order."""

    total_duration_seconds: float
    """Sum of all chapter durations."""

    warnings: list[str]
    """All non-fatal warnings from all chapters, aggregated."""

    errors: list[str]
    """All fatal or partial-failure error messages."""

    output_path: str | None = None
    """Path to the single M4B artifact, or None for per-chapter MP3 output."""

    chapter_markers: list[ChapterMarker] = []
    """Chapter offsets inside the single M4B file (empty for MP3 output)."""
