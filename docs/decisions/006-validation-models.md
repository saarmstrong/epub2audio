# 006 — Validation data models (`ValidationIssue`, `ValidationReport`)

**Date:** 2026-07-13
**Status:** Accepted
**Author:** Architect
**Milestone:** M11 (optional validation stage)
**Branch:** `narrative`

---

## Context

`Feature.md` (§ "Quality Assurance") and ADR-003 §7 specify an optional
post-conversion validation stage that checks: skipped text, pronunciation
failures, missing chapters, invalid metadata, overlapping timestamps, and
chapter-duration consistency.  The validation stage emits a structured report
that the CLI surfaces (via `--validate`) and external tools can parse.

The Audio Engineer owns the `validation/` package, checks, and CLI wiring
(tasks M11-01, M11-02).  The Architect owns the shared data types that the
validation package produces and the pipeline consumes.

---

## Decision

Add three definitions to `models.py` in a new clearly-commented
"Validation models" section placed after `ConversionReport`:

### `ValidationSeverity`

A module-level `Literal["error", "warning", "info"]` type alias.

- **`"error"`** — output is likely incorrect or unusable; causes `ok = False`.
- **`"warning"`** — suspicious condition; does not affect `ok`.
- **`"info"`** — diagnostic observation; does not affect `ok`.

### `ValidationIssue(BaseModel, frozen=True)`

One finding from the validation stage.

| Field | Type | Notes |
|---|---|---|
| `code` | `str` | Stable machine-readable identifier.  Never renamed once in use. |
| `severity` | `ValidationSeverity` | Error / warning / info. |
| `message` | `str` | Human-readable description. |
| `chapter_id` | `str \| None` | Affected chapter, or `None` for book-level. |

Known initial codes (non-exhaustive; codes are stable — tests and tools
may match on them):

| Code | Meaning |
|---|---|
| `"missing_chapter"` | Chapter expected from the plan has no output file. |
| `"skipped_text"` | EPUB text not synthesised. |
| `"invalid_metadata"` | Required metadata field absent or malformed. |
| `"overlapping_timestamps"` | Two chapter markers overlap in the M4B timeline. |
| `"chapter_duration"` | Chapter audio duration outside expected range. |
| `"missing_output_file"` | Output path in conversion report does not exist on disk. |

Codes must **never be renamed** without a decision record and a migration note;
new codes are introduced additively.

### `ValidationReport(BaseModel, frozen=True)`

Aggregated result of the validation stage.

| Field | Type | Default | Notes |
|---|---|---|---|
| `ok` | `bool` | — | `True` iff zero `"error"` issues. |
| `issues` | `list[ValidationIssue]` | `[]` | All findings in discovery order. |
| `error_count` | `int` | — | Convenience count of errors. |
| `warning_count` | `int` | — | Convenience count of warnings. |
| `info_count` | `int` | — | Convenience count of info items. |

`ValidationReport` is serialized to `validation-report.json` in the output
directory alongside `conversion-report.json`.  `ok` is the single gate a
caller checks.

---

## Scope boundary

These are **data-only** definitions.  The following are explicitly out of scope
for this record and for the Architect role:

- The `validation/` package and its check implementations (M11-01).
- CLI `--validate` flag and wiring (M11-02).
- Any logic to compute `ok`, `error_count`, `warning_count`, `info_count` —
  the Audio Engineer's factory/builder is responsible for constructing a
  `ValidationReport` with correct values.

---

## Consequences

- Any module that needs to surface validation results imports
  `ValidationIssue` and `ValidationReport` from `models.py` — the base layer.
  No new cross-package dependencies are introduced.
- The count fields (`error_count`, `warning_count`, `info_count`) are
  intentionally redundant with `issues` — they exist so a caller or a log
  formatter can show a summary without iterating the full list.  The Audio
  Engineer's factory is responsible for keeping them consistent.
- `ValidationSeverity` is a `Literal` type alias (not an `Enum`) for
  consistency with the rest of `models.py` (e.g. `SegmentType`).

---

## Alternatives Considered

1. **`Enum` for severity.** Would require callers to import the enum and use
   dot-access.  Rejected in favour of `Literal` for consistency with the
   rest of `models.py`.
2. **Compute `ok` / counts as `@model_validator`.** Would add logic to a
   frozen model and complicate construction in tests.  Rejected; the
   Audio Engineer's factory sets all fields explicitly.
3. **Inline `ValidationReport` as a field on `ConversionReport`.** Would
   couple the two reports and prevent the validation stage from being optional.
   Rejected in favour of a separate file (`validation-report.json`) and a
   separate model.
