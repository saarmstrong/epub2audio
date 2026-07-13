# 006 — Validation data models (`ValidationIssue`, `ValidationReport`)

**Date:** 2026-07-13
**Status:** Accepted (amended M12-09 — see revision below)
**Author:** Architect
**Milestone:** M11 (optional validation stage); amended in M12
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
| `ok` | `bool` | — | `True` iff zero `"error"` issues. **Always recomputed (see M12-09 revision below).** |
| `issues` | `list[ValidationIssue]` | `[]` | All findings in discovery order. |
| `error_count` | `int` | — | Convenience count of errors. **Always recomputed (see M12-09 revision below).** |
| `warning_count` | `int` | — | Convenience count of warnings. **Always recomputed.** |
| `info_count` | `int` | — | Convenience count of info items. **Always recomputed.** |

`ValidationReport` is serialized to `validation-report.json` in the output
directory alongside `conversion-report.json`.  `ok` is the single gate a
caller checks.

---

## Scope boundary

These are **data-only** definitions.  The following are explicitly out of scope
for this record and for the Architect role:

- The `validation/` package and its check implementations (M11-01).
- CLI `--validate` flag and wiring (M11-02).

---

## Consequences

- Any module that needs to surface validation results imports
  `ValidationIssue` and `ValidationReport` from `models.py` — the base layer.
  No new cross-package dependencies are introduced.
- The count fields (`error_count`, `warning_count`, `info_count`) are
  intentionally redundant with `issues` — they exist so a caller or a log
  formatter can show a summary without iterating the full list.
- `ValidationSeverity` is a `Literal` type alias (not an `Enum`) for
  consistency with the rest of `models.py` (e.g. `SegmentType`).

---

## Alternatives Considered

1. **`Enum` for severity.** Would require callers to import the enum and use
   dot-access.  Rejected in favour of `Literal` for consistency with the
   rest of `models.py`.
2. **Compute `ok` / counts as `@model_validator`.** Would add logic to a
   frozen model and complicate construction in tests.  *Initially rejected; the
   Audio Engineer's factory sets all fields explicitly.  **Reversed in M12-09**
   — see revision below.*
3. **Inline `ValidationReport` as a field on `ConversionReport`.** Would
   couple the two reports and prevent the validation stage from being optional.
   Rejected in favour of a separate file (`validation-report.json`) and a
   separate model.

---

## Revision — M12-09 (2026-07-13): model_validator enforces count invariant

**Problem identified in M12:** JSON deserialization of `validation-report.json`
(`ValidationReport(**json_dict)` or `ValidationReport.model_validate(json_dict)`)
bypasses `validation.checks._assemble`, which means a stale, hand-edited, or
externally-generated report can carry `error_count` / `warning_count` /
`info_count` / `ok` values that are inconsistent with `issues`.  The CLI test
`test_validate_flag_writes_report` already exercises this path: it reads the
written JSON and calls `ValidationReport(**raw)` directly.

**Decision (reversal of Alternative 2 above):** a
`@model_validator(mode="after")` is added to `ValidationReport`.  It
unconditionally recomputes `ok`, `error_count`, `warning_count`, and
`info_count` from `issues` using `object.__setattr__` — the Pydantic
v2-documented method for mutating frozen model fields inside validators.

**Effect on `_assemble`:** `_assemble` already computes and passes correct
values; the model_validator recomputes them to the same values, so the
existing behaviour of all validation tests is unchanged.

**Effect on deserialization:** any `ValidationReport` constructed from JSON
(regardless of whether the JSON counts are stale) will always carry counts
that match its `issues` list.

Full rationale: `docs/decisions/007-output-both-and-config.md` §M12-09.
