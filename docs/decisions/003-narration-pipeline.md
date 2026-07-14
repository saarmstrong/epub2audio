# 003 — Narration Director + provider-adapter pipeline (additive, rule-based)

**Date:** 2026-07-12
**Status:** Accepted (plan) — implementation tracked as Milestones 8–12
**Author:** Architect / Orchestrator

---

## Context

`Feature.md` asks to evolve the shipped EPUB→MP3/M4B tool into a
*provider-agnostic, expressive-narration* pipeline with a **Narration
Director** stage, **provider adapters** (Kokoro, OpenAI, Gemini, Azure,
ElevenLabs), a **pronunciation subsystem**, and an optional **validation**
stage.

Reconciling the spec with the shipped code (M1–M7 complete):

- **Already done.** M4B is a first-class output (`--format m4b`, AAC, cover,
  chapter markers, book tags — see `002-m4b-output-format.md`). MP3 remains the
  default and is unchanged. `Feature.md` goal #1 is effectively satisfied.
- **Partial.** `tts/kokoro.py` is a working *raw engine* (`KokoroTTSEngine`
  satisfying the `TTSEngine` Protocol), but it is not a *plan-consuming
  adapter*.
- **Not started.** Narration Director, the provider-adapter abstraction,
  the pronunciation subsystem (`text/pronunciation.py` is a stub), and the
  validation stage.

The current flow is:

```
clean text → segment_text() → TextSegment[] → TTSEngine.synthesize(text, voice, language, speed) → AudioChunk[]
```

`Feature.md` wants a provider-neutral **NarrationPlan** in the middle, consumed
by provider adapters that translate it into provider-specific controls.

---

## Decision

### 1. Two chosen constraints (per Orchestrator direction)

- **Rule-based Director for v1.** The Director is deterministic (no LLM, no
  network, no API cost). This matches the project's deterministic-test culture
  and keeps the plan fully unit-testable. The `NarrationPlan` contract is
  identical whether produced by rules or by a future LLM, so the engine can be
  swapped later without touching providers or the pipeline.
- **Additive restructure.** We do **not** rename existing packages. New
  packages (`director/`, `providers/`, `pronunciation/`, `validation/`) are
  added alongside the current layout; `Feature.md`'s `output/` / `metadata/`
  targets are satisfied with thin re-export shims where useful. `src/` stays
  importable at every milestone boundary (AGENTS.md rule #5), and M1–M7 code
  paths are preserved.

### 2. Three-layer separation ("no business logic in providers")

```
EPUB → clean text
        ↓
[Layer 1] Narration Director  ── business logic, provider-neutral
        ↓  NarrationPlan
[Layer 2] Provider Adapter    ── mapping only (plan → provider controls)
        ↓  provider request
[Layer 3] TTS Engine          ── raw model I/O (existing KokoroTTSEngine)
        ↓  AudioChunk[]
Audio assembly → MP3 / M4B
```

- **Layer 1 — Director** (`director/`): scene analysis, dialogue detection,
  likely-speaker labelling, pacing/intensity, emphasis hints, pause timing, and
  pronunciation *hints* (references into the lexicon). Emits `NarrationPlan`.
  Knows nothing about any TTS engine. **Never rewrites prose, never invents
  dialogue** — it only annotates.
- **Layer 2 — Provider adapter** (`providers/`): converts a plan segment into
  provider-specific controls. Kokoro: punctuation optimization, pause
  insertion, long-segment splitting, pronunciation-dictionary application,
  speed mapping. OpenAI/Gemini: natural-language narration instructions. Azure:
  SSML. ElevenLabs: provider settings + prompting. **Contains no analysis
  logic** — pure translation of an already-computed plan.
- **Layer 3 — Engine** (`tts/`): the existing `KokoroTTSEngine.synthesize()`
  raw call. Unchanged in shape.

### 3. Contracts

- The existing `TTSEngine` Protocol stays as the **Layer-3** contract.
- A new `NarrationProvider` Protocol becomes the **Layer-2** contract that the
  pipeline depends on:

  ```python
  class NarrationProvider(Protocol):
      def render(self, segment: NarrationSegment,
                 defaults: NarrationDirection,
                 settings: Settings) -> ProviderRequest: ...
      def synthesize(self, request: ProviderRequest) -> list[AudioChunk]: ...
  ```

  A provider is added by implementing this single interface — no changes to the
  Director, pipeline, or audio assembly. The Kokoro provider wraps the existing
  `KokoroTTSEngine`; other providers ship as interface stubs first.

### 4. Data models (added to `models.py`, all frozen Pydantic)

Mirrors the `Feature.md` JSON shape:

- `NarrationDirection` — `mood: str`, `pace: float`, `intensity: float`.
- `NarrationSegment` — `id`, `type` (`"narration" | "dialogue"`), `speaker`,
  `text`, `direction: str`, `pause_after_ms: int`, `pace: float`,
  `emphasis: list[...]`, `pronunciation_hints: list[...]`.
- `NarrationPlan` — `chapter: int`, `scene: int`,
  `default_direction: NarrationDirection`, `segments: list[NarrationSegment]`.

The plan is **provider-neutral**: no SSML, no Kokoro tokens, no engine-specific
fields ever appear in it.

### 5. Scene-aware segmentation (per `Feature.md` "Scene Segmentation")

The Director directs **scenes, not sentences**: it groups segments into scenes,
applies one `default_direction` per scene, and emits **local overrides only
when emotion/intensity changes significantly**. This preserves narration
consistency and keeps plans small.

### 6. Pronunciation subsystem (`pronunciation/`)

- Load `pronunciations.yaml` into a provider-neutral lexicon.
- Director emits pronunciation *hints* (which lexicon entries apply to a
  segment); the **provider adapter applies** them (Kokoro: substitution / phone
  hints; a future Azure adapter: SSML `<phoneme>`).
- New `pronunciation_dictionary` config path. Adds a YAML dependency (currently
  only `tomllib` is used) — recorded as a consequence below.

### 7. Validation stage (`validation/`, optional)

CLI `--validate` runs post-conversion checks: skipped text, pronunciation
failures, missing chapters, invalid metadata, overlapping timestamps, and
chapter-duration consistency. Reuses `audio/validate.py` probes. Emits a
validation report next to `conversion-report.json`. Off by default.

### 8. Pipeline wiring

`pipeline/converter.py` is injected with a `NarrationProvider` instead of a
`TTSEngine`. `_process_chapter()` calls the Director to produce a
`NarrationPlan`, then drives `provider.render()` + `provider.synthesize()` per
segment. Per-segment resume is re-keyed on plan-segment hashes. Loudness
normalization, encoding, tagging, M4B assembly, and MP3 output are unchanged.

### 9. Config additions (`config.py`)

`provider`, `scene_analysis` (bool), `pronunciation_dictionary` (path), and
`output_format: both` (emit MP3 **and** M4B) join the existing keys.

---

## Milestones

| M | Title | Primary owners |
|---|---|---|
| 8 | Narration data models + rule-based Director skeleton | Architect, TTS Engineer, Tester |
| 9 | `NarrationProvider` abstraction + Kokoro adapter (+ stub adapters) | Architect, TTS Engineer |
| 10 | Pronunciation subsystem (`pronunciations.yaml`) | TTS Engineer |
| 11 | Optional validation stage + `--validate` | Audio Engineer, Tester |
| 12 | Additive restructure reconciliation, config, architecture docs | Orchestrator, all |

Each milestone follows the established gate: `pytest` + `mypy --strict` +
`ruff check`/`format --check` green, `src/` importable, tests added with every
behaviour change, and **Reviewer sign-off before the milestone is marked
complete**.

---

## Consequences

- **MP3 and M4B outputs are untouched.** The Director/provider layers sit
  above audio assembly; the M4B assembler and per-chapter MP3 path are reused
  as-is.
- **Adding a provider = implementing one Protocol.** No edits to Director,
  pipeline, or audio code — the core `Feature.md` extensibility requirement.
- **Original text is preserved.** Director and adapters annotate, never
  rewrite. A test asserts each `NarrationSegment.text` is derived from (a
  substring/normalization of) the source, and that no dialogue is invented.
- **Deterministic and testable.** Rule-based v1 means narration plans are
  reproducible byte-for-byte, satisfying deliverable #7 (unit tests for
  narration plans) without mocking an LLM.
- **New dependency: a YAML parser** for `pronunciations.yaml` (M10). Recorded
  here; a dedicated decision record accompanies the M10 implementation if the
  choice is non-trivial.
- **Resume key change.** Segment identity moves from `TextSegment.normalized_hash`
  to a `NarrationSegment`-derived hash; the manifest/resume logic is updated
  once in M9. Old manifests are treated as a cache miss (safe re-synthesis).

---

## Alternatives Considered

1. **LLM-backed Director for v1.** More expressive but non-deterministic,
   costly, and hard to unit-test; blocks offline/CI runs. Rejected for v1; the
   `NarrationPlan` contract is designed so an LLM engine can be dropped in later
   without touching providers or the pipeline.
2. **Full rename to `Feature.md`'s `src/` layout in one step.** Large diff,
   breaks import paths, and risks regressing M1–M7. Rejected in favour of the
   additive approach; the target layout is approached incrementally with
   re-export shims.
3. **Fold Director logic into provider adapters.** Violates "no business logic
   in providers" and would force every new provider to re-implement scene
   analysis. Rejected — the whole point is that providers are thin mappers.
4. **Put narration controls inside `TextSegment`.** Couples the provider-neutral
   text model to narration/provider concerns and bloats the resume key.
   Rejected in favour of a distinct `NarrationPlan`/`NarrationSegment`.
