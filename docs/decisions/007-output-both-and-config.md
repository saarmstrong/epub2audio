# 007 — `output_format: both`, `provider`, `scene_analysis` config additions + M12-09 `ValidationReport` count invariant

**Date:** 2026-07-13
**Status:** Accepted
**Author:** Architect
**Milestone:** M12 (final reconciliation), branch `narrative`

---

## Context

`Feature.md` ("Configuration") specifies three settings that had not yet been
wired into `config.py` as of Milestone 11:

| Key | Values / type | Note |
|---|---|---|
| `output_format` | `mp3 \| m4b \| both` | `both` was absent |
| `provider` | `str` | Absent entirely |
| `scene_analysis` | `bool` | Absent entirely |

ADR-003 §9 listed all three as planned additions for M12.

Additionally, carried task M12-09 requires a decision about `ValidationReport`
count drift: the `error_count`, `warning_count`, `info_count`, and `ok` fields
on `ValidationReport` are redundant with `issues` but were previously trusted
as constructor inputs, with only `validation.checks._assemble` guaranteeing
consistency.  This ADR records the M12 decision to enforce consistency via a
`@model_validator`.

---

## Decision

### 1. `output_format: Literal["mp3", "m4b", "both"]`

`"both"` is added as a third accepted value for `output_format`.  The default
remains `"mp3"` (backward compatible).

**Semantics of `"both"`:**

- The pipeline synthesises and loudness-normalises audio per chapter exactly
  once (the same intermediate files are reused for both output paths).
- **MP3 output:** per-chapter MP3 files written with ID3 tags (title, author,
  cover art) — identical to `output_format="mp3"` behaviour.
- **M4B output:** a single M4B container (AAC, chapter markers, book-level
  tags, cover art) — identical to `output_format="m4b"` behaviour, assembled
  from the same per-chapter normalised audio.
- **`ConversionReport` for `"both"`:** carries both per-chapter
  `ChapterResult.output_path` entries (MP3 paths) AND a book-level
  `output_path` (M4B path) plus `chapter_markers`.  This differs from pure
  `"mp3"` (no `output_path` / `chapter_markers`) and pure `"m4b"`
  (no per-chapter `output_path`).

The `normalize_output_format` validator continues to lower-case and strip the
value before Pydantic checks the `Literal`; `"BOTH"`, `" both "`, etc. are
accepted.  No other change to the validator is needed — the `Literal` type
expansion handles the rest.

**Out of scope for this record (M12-03, Audio Engineer):** the converter
and assembler changes needed to actually produce both outputs in one run.
This ADR only widens the type and documents the semantics.

### 2. `provider: str` (default `"kokoro"`)

A new `provider` field is added to `Settings` with a `"before"`-mode
`field_validator` that:

1. Strips whitespace and lower-cases the value (so `"Kokoro"`, `"KOKORO"` are
   accepted).
2. Rejects any value not in `_SUPPORTED_PROVIDERS` (a module-level
   `frozenset`) with a `ValueError` that lists the supported providers.

**Supported providers in M12:** `{"kokoro"}` only.

OpenAI, Gemini, Azure, and ElevenLabs adapters exist as stubs in
`providers/`.  They are **not** added to `_SUPPORTED_PROVIDERS` until each
stub is promoted to a full implementation in a future milestone.  Advertising
them as valid would produce a confusing runtime failure deep in the pipeline
rather than a clear validation error at startup.

When a new provider is implemented, the change is: add its normalised name to
`_SUPPORTED_PROVIDERS` in `config.py` and create the corresponding ADR entry.

### 3. `scene_analysis: bool` (default `True`)

A new `scene_analysis` flag controls whether the Narration Director splits
chapters into scenes.

- **`True` (default):** the Director calls `director.scenes.split_scenes()`
  per chapter, produces one `NarrationPlan` per scene with its own
  `default_direction`, and applies local overrides only where
  emotion/intensity diverges significantly.  This is the full pipeline as
  specified in ADR-003 §5.
- **`False`:** the Director treats the entire chapter as a single scene
  (one `NarrationPlan` with one `default_direction`).  All other annotation
  — dialogue detection, emphasis hints, pause timing, and pronunciation hints
  resolved from the lexicon — **still applies**.  Only scene-splitting is
  skipped.

The `scene_analysis` flag is a hint to the Director; enforcing it is the
Director's responsibility (owned by the TTS Engineer).  The Architect only
defines the field and documents its semantics here.

### 4. M12-09 — `ValidationReport` count invariant via `@model_validator`

**Problem:** `ValidationReport` carries `ok`, `error_count`, `warning_count`,
and `info_count` as explicit fields that are redundant with `issues`.
Previously, ADR-006 (Alternative 2) explicitly *rejected* adding a
`@model_validator`, delegating consistency to `validation.checks._assemble`.

This was safe as long as `_assemble` was the only construction path.  However,
JSON deserialization (`ValidationReport.model_validate(json_dict)` or
`ValidationReport(**json_dict)`) bypasses `_assemble`, which means a stale or
hand-edited report could carry incorrect counts.

**Decision (reversal of ADR-006 Alternative 2):** add a
`@model_validator(mode="after")` to `ValidationReport` that unconditionally
recomputes `ok`, `error_count`, `warning_count`, and `info_count` from
`issues` using `object.__setattr__` (the Pydantic v2-documented pattern for
mutating frozen models inside validators).

Consequences:
- `_assemble` continues to compute and pass correct values; the recompute
  is a no-op for that path but costs negligible time.
- Any externally-constructed or deserialized `ValidationReport` with
  mismatched counts is silently corrected.
- Tests that construct `ValidationReport` directly with wrong counts and then
  read the count fields will see the corrected values.
- ADR-006 is amended with a revision note; this record cross-references it.

---

## Consequences

- `output_format="both"` is accepted by the validator from M12; the Audio
  Engineer (M12-03) implements the converter branch that produces both outputs.
- `provider` validation fails fast at `Settings` construction with a clear
  message listing supported providers, rather than a deep pipeline error.
- `scene_analysis=False` disables scene splitting while preserving all other
  annotation; Director wiring is the TTS Engineer's responsibility.
- `ValidationReport` count fields are now always authoritative, whether the
  instance was created by `_assemble`, deserialized from JSON, or constructed
  directly in a test.
- `check_timestamps` and `check_missing_output_files` in
  `validation/checks.py` currently branch on `output_format in {"mp3", "m4b"}`
  and do not handle `"both"`.  Updating those checks for `"both"` mode is
  deferred to M12-03 (Audio Engineer) as part of the converter wiring.

---

## Alternatives Considered

### `output_format: both` — post-process approach (MP3 → M4B re-encode)

Build both outputs by running the full MP3 path, then re-encoding to M4B.
**Rejected.** Double-encode degrades quality (MP3 lossy → AAC lossy).
ADR-002 already rejected this; `"both"` reuses the same normalised PCM
intermediates.

### `provider` — `Literal` type instead of `str` + validator

Using `Literal["kokoro"]` would require a type change every time a provider
is added.  **Rejected.** `str` + `_SUPPORTED_PROVIDERS` set allows updating
the supported set without changing the field type annotation; it also produces
a better error message that lists the known providers.

### `scene_analysis` — `scenes_per_chapter: int` limit instead of bool

Allowing `scenes_per_chapter=1` as a numeric cap would be more flexible.
**Rejected.** Feature.md uses a boolean flag; the bool is simpler to
document, test, and configure.  A future ADR can introduce a numeric limit if
needed.

### M12-09 — document trusted-input in ADR-006, no validator

Leave counts as trusted-input; document in ADR-006 that `_assemble` is the
sole construction path and callers must not construct `ValidationReport`
directly.  **Rejected.**  JSON deserialization (`model_validate`) is a
legitimate second construction path already exercised by the CLI test that
reads `validation-report.json` from disk.  A model_validator is the safer
choice because it is enforced automatically without callers needing to know
about `_assemble`.
