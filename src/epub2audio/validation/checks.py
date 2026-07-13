"""Post-conversion validation checks for epub2audio.

Each public ``check_*`` function inspects one aspect of the conversion result
and returns a (possibly empty) list of :class:`~epub2audio.models.ValidationIssue`
objects.  All checks are **pure** — they read their arguments and return issues;
they never mutate state, write files, or raise exceptions.

:func:`validate_conversion` is the orchestrator.  It calls every check, collects
all issues, and assembles the final :class:`~epub2audio.models.ValidationReport`
through the private :func:`_assemble` helper, which derives ``ok`` and the
severity counts from the issues list so the counts can never drift from reality.

Import policy
-------------
This module imports **only** from :mod:`epub2audio.models`,
:mod:`epub2audio.config`, and the Python standard library.  It must never
import from ``epub/``, ``director/``, ``providers/``, ``tts/``, ``audio/``,
or ``pipeline/``.
"""

from __future__ import annotations

from pathlib import Path

from epub2audio.config import Settings
from epub2audio.models import (
    ChapterMarker,
    ConversionPlan,
    ConversionReport,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _issue(
    code: str,
    severity: ValidationSeverity,
    message: str,
    chapter_id: str | None = None,
) -> ValidationIssue:
    """Construct a :class:`ValidationIssue` concisely."""
    return ValidationIssue(
        code=code,
        severity=severity,
        message=message,
        chapter_id=chapter_id,
    )


def _assemble(issues: list[ValidationIssue]) -> ValidationReport:
    """Build a :class:`ValidationReport` from *issues*, deriving all counts.

    This is the **only** place ``ValidationReport`` is constructed.  The
    ``ok`` flag and the three severity counts are derived from *issues* so
    they are guaranteed to be consistent.

    Args:
        issues: All findings collected by the orchestrator.

    Returns:
        A :class:`ValidationReport` whose ``ok``, ``error_count``,
        ``warning_count``, and ``info_count`` match *issues* exactly.
    """
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")
    return ValidationReport(
        ok=error_count == 0,
        issues=issues,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
    )


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_missing_chapters(
    report: ConversionReport,
    plan: ConversionPlan,
) -> list[ValidationIssue]:
    """Check that every chapter in the plan has a result in the report.

    A chapter present in the conversion plan but absent from
    ``report.chapter_results`` is flagged as a ``missing_chapter`` error.
    This can happen if the pipeline crashed mid-run before writing the chapter
    result, or if the plan and report are from different runs.

    Args:
        report: The conversion report produced by the pipeline.
        plan: The conversion plan that was passed to the pipeline.

    Returns:
        One :class:`ValidationIssue` per missing chapter (empty if all present).
    """
    result_ids = {r.chapter_id for r in report.chapter_results}
    issues: list[ValidationIssue] = []
    for chapter in plan.chapters:
        if chapter.chapter_id not in result_ids:
            issues.append(
                _issue(
                    code="missing_chapter",
                    severity="error",
                    message=(
                        f"Chapter {chapter.chapter_id!r} ({chapter.title!r}) is present in "
                        f"the conversion plan but has no result in the conversion report."
                    ),
                    chapter_id=chapter.chapter_id,
                )
            )
    return issues


def check_skipped_text(
    report: ConversionReport,
    plan: ConversionPlan,
    settings: Settings,
) -> list[ValidationIssue]:
    """Check for chapters with text that produced no audio.

    A chapter with ``word_count > 0`` in the plan whose result has zero
    (or negative) ``duration_seconds`` is flagged.  For MP3 mode, an
    ``output_path is None`` is also flagged, but for M4B mode
    ``output_path`` is intentionally ``None`` for per-chapter results
    (audio lives inside the container), so only ``duration_seconds`` is
    used for M4B.

    Args:
        report: The conversion report.
        plan: The conversion plan (for ``word_count`` per chapter).
        settings: Effective settings (for ``output_format``).

    Returns:
        One :class:`ValidationIssue` per chapter with skipped text.
    """
    word_counts = {c.chapter_id: c.word_count for c in plan.chapters}
    issues: list[ValidationIssue] = []

    for result in report.chapter_results:
        wc = word_counts.get(result.chapter_id, 0)
        if wc <= 0:
            continue  # genuinely empty chapter — not a problem

        skipped = False
        reason = ""

        if result.duration_seconds <= 0:
            skipped = True
            reason = "duration is zero or negative"
        elif settings.output_format == "mp3" and result.output_path is None:
            skipped = True
            reason = "output_path is None (no audio file produced)"

        if skipped:
            issues.append(
                _issue(
                    code="skipped_text",
                    severity="error",
                    message=(
                        f"Chapter {result.chapter_id!r} has {wc} word(s) in the plan "
                        f"but produced no audio ({reason})."
                    ),
                    chapter_id=result.chapter_id,
                )
            )
    return issues


def check_invalid_metadata(report: ConversionReport) -> list[ValidationIssue]:
    """Check that required book-level metadata fields are non-empty.

    Validates ``title``, ``author``, ``language``, and ``identifier`` on
    ``report.book_metadata``.  An empty or whitespace-only value in any of
    these fields is flagged as an ``invalid_metadata`` error because the
    field is required for usable ID3 tags and M4B container metadata.

    Args:
        report: The conversion report.

    Returns:
        One :class:`ValidationIssue` per empty/whitespace field (possibly empty).
    """
    meta = report.book_metadata
    issues: list[ValidationIssue] = []
    for field_name in ("title", "author", "language", "identifier"):
        value: object = getattr(meta, field_name, None)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                _issue(
                    code="invalid_metadata",
                    severity="error",
                    message=(
                        f"Book metadata field {field_name!r} is missing or empty (got {value!r})."
                    ),
                    chapter_id=None,
                )
            )
    return issues


def check_timestamps(
    report: ConversionReport,
    settings: Settings,
) -> list[ValidationIssue]:
    """Check M4B chapter-marker timestamps for overlaps and gaps.

    Only runs when ``settings.output_format == "m4b"`` and
    ``report.chapter_markers`` is non-empty.  Two checks are performed:

    - **overlapping_timestamps** (error): any marker where
      ``start_ms >= end_ms``, or any pair of consecutive markers where
      ``marker[i].end_ms > marker[i+1].start_ms``.
    - **non_contiguous_timeline** (warning): any pair of consecutive markers
      where ``marker[i].end_ms != marker[i+1].start_ms`` (a gap in the
      timeline).

    Args:
        report: The conversion report (``chapter_markers`` used).
        settings: Effective settings (checks skipped unless M4B).

    Returns:
        A (possibly empty) list of :class:`ValidationIssue` objects.
    """
    if settings.output_format != "m4b":
        return []
    markers: list[ChapterMarker] = report.chapter_markers
    if not markers:
        return []

    issues: list[ValidationIssue] = []

    for marker in markers:
        if marker.start_ms >= marker.end_ms:
            issues.append(
                _issue(
                    code="overlapping_timestamps",
                    severity="error",
                    message=(
                        f"Chapter {marker.chapter_id!r} ({marker.title!r}) has "
                        f"start_ms={marker.start_ms} >= end_ms={marker.end_ms}."
                    ),
                    chapter_id=marker.chapter_id,
                )
            )

    for i in range(len(markers) - 1):
        a, b = markers[i], markers[i + 1]
        if a.end_ms > b.start_ms:
            issues.append(
                _issue(
                    code="overlapping_timestamps",
                    severity="error",
                    message=(
                        f"Chapter markers overlap: {a.chapter_id!r} ends at "
                        f"{a.end_ms} ms but {b.chapter_id!r} starts at {b.start_ms} ms."
                    ),
                    chapter_id=b.chapter_id,
                )
            )
        elif a.end_ms != b.start_ms:
            issues.append(
                _issue(
                    code="non_contiguous_timeline",
                    severity="warning",
                    message=(
                        f"Timeline gap between chapters: {a.chapter_id!r} ends at "
                        f"{a.end_ms} ms but {b.chapter_id!r} starts at {b.start_ms} ms "
                        f"(gap of {b.start_ms - a.end_ms} ms)."
                    ),
                    chapter_id=b.chapter_id,
                )
            )

    return issues


def check_chapter_duration(
    report: ConversionReport,
    plan: ConversionPlan,
    skipped_ids: set[str],
) -> list[ValidationIssue]:
    """Flag chapters with suspiciously zero duration (warning only).

    A chapter with ``word_count > 0`` in the plan and ``duration_seconds <= 0``
    in the report gets a ``chapter_duration`` warning — unless it was already
    flagged by :func:`check_skipped_text` (to avoid duplicate noise).

    Args:
        report: The conversion report.
        plan: The conversion plan (for ``word_count``).
        skipped_ids: Set of ``chapter_id`` values already flagged by
            :func:`check_skipped_text`; these are excluded to avoid
            redundant issues.

    Returns:
        One warning per zero-duration chapter not already covered by
        ``skipped_text``.
    """
    word_counts = {c.chapter_id: c.word_count for c in plan.chapters}
    issues: list[ValidationIssue] = []
    for result in report.chapter_results:
        if result.chapter_id in skipped_ids:
            continue
        wc = word_counts.get(result.chapter_id, 0)
        if wc > 0 and result.duration_seconds <= 0:
            issues.append(
                _issue(
                    code="chapter_duration",
                    severity="warning",
                    message=(
                        f"Chapter {result.chapter_id!r} has {wc} word(s) but "
                        f"duration_seconds={result.duration_seconds:.3f} is zero or negative."
                    ),
                    chapter_id=result.chapter_id,
                )
            )
    return issues


def check_missing_output_files(
    report: ConversionReport,
    settings: Settings,
) -> list[ValidationIssue]:
    """Check that output files recorded in the report exist on disk.

    For MP3 mode: every ``ChapterResult.output_path`` that is not ``None``
    must point to an existing file.
    For M4B mode: ``report.output_path`` (when not ``None``) must exist.

    Args:
        report: The conversion report.
        settings: Effective settings (for ``output_format``).

    Returns:
        One :class:`ValidationIssue` per missing file.
    """
    issues: list[ValidationIssue] = []

    if settings.output_format == "m4b":
        if report.output_path is not None and not Path(report.output_path).exists():
            issues.append(
                _issue(
                    code="missing_output_file",
                    severity="error",
                    message=(
                        f"M4B output file recorded in report does not exist on disk: "
                        f"{report.output_path!r}."
                    ),
                    chapter_id=None,
                )
            )
    else:
        for result in report.chapter_results:
            if result.output_path is not None and not Path(result.output_path).exists():
                issues.append(
                    _issue(
                        code="missing_output_file",
                        severity="error",
                        message=(
                            f"Chapter {result.chapter_id!r}: output file recorded in report "
                            f"does not exist on disk: {result.output_path!r}."
                        ),
                        chapter_id=result.chapter_id,
                    )
                )
    return issues


def check_report_errors(report: ConversionReport) -> list[ValidationIssue]:
    """Surface any pipeline errors recorded in the conversion report.

    Errors already captured in ``report.errors`` are surfaced as
    ``report_error`` issues so they appear in the validation report alongside
    the structural checks.

    Args:
        report: The conversion report.

    Returns:
        One :class:`ValidationIssue` per entry in ``report.errors``.
    """
    return [
        _issue(
            code="report_error",
            severity="error",
            message=f"Pipeline error recorded in conversion report: {err}",
            chapter_id=None,
        )
        for err in report.errors
    ]


def check_pronunciation(
    report: ConversionReport,
    plan: ConversionPlan,
) -> list[ValidationIssue]:
    """Placeholder for pronunciation-failure detection.

    Feature.md lists pronunciation failures as a validation check.  However,
    the current pipeline does not record per-segment synthesis outcomes at the
    granularity needed to detect which terms failed to be applied — the
    conversion report only carries chapter-level results.

    Per-segment pronunciation tracking is deferred to a future milestone
    (requires the pipeline to record which ``PronunciationHint`` entries were
    applied, which terms could not be matched, and any synthesis-time errors
    from the provider adapter).  When that infrastructure exists, this function
    will be replaced by a real implementation.

    Args:
        report: The conversion report (unused — no per-segment data available).
        plan: The conversion plan (unused for the same reason).

    Returns:
        Always an empty list.  This is intentional: do not fabricate hollow
        checks that produce false positives.
    """
    return []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_conversion(
    report: ConversionReport,
    plan: ConversionPlan,
    settings: Settings,
    output_dir: Path,
) -> ValidationReport:
    """Run all post-conversion validation checks and return a summary report.

    This is the single public entry point of the validation stage.  It calls
    every ``check_*`` function in order, aggregates their issues, and returns
    a :class:`~epub2audio.models.ValidationReport` built through
    :func:`_assemble` (which guarantees ``ok`` and the severity counts are
    always consistent with the issue list).

    The checks run are:

    1. :func:`check_missing_chapters` — plan chapters without a report result.
    2. :func:`check_skipped_text` — chapters with text but no audio.
    3. :func:`check_invalid_metadata` — empty/whitespace required metadata fields.
    4. :func:`check_timestamps` — M4B marker overlaps and timeline gaps.
    5. :func:`check_chapter_duration` — zero-duration chapters (warning).
    6. :func:`check_missing_output_files` — output files not found on disk.
    7. :func:`check_report_errors` — pipeline errors in the conversion report.
    8. :func:`check_pronunciation` — pronunciation failure detection (stub).

    The ``output_dir`` argument is accepted for forward-compatibility (future
    checks may scan the directory) but is not used by any current check.

    Args:
        report: The :class:`~epub2audio.models.ConversionReport` returned by
            :func:`~epub2audio.pipeline.converter.convert_epub`.
        plan: The :class:`~epub2audio.models.ConversionPlan` that was passed to
            the pipeline (used by checks that compare planned vs. actual).
        settings: Effective :class:`~epub2audio.config.Settings` for this run.
        output_dir: The directory where output files were written.  Currently
            accepted for forward-compatibility; not used by existing checks.

    Returns:
        A :class:`~epub2audio.models.ValidationReport` describing all findings.
        ``report.ok`` is ``True`` iff there are no ``"error"``-severity issues.
    """
    all_issues: list[ValidationIssue] = []

    all_issues.extend(check_missing_chapters(report, plan))

    skipped_issues = check_skipped_text(report, plan, settings)
    all_issues.extend(skipped_issues)
    skipped_ids = {i.chapter_id for i in skipped_issues if i.chapter_id is not None}

    all_issues.extend(check_invalid_metadata(report))
    all_issues.extend(check_timestamps(report, settings))
    all_issues.extend(check_chapter_duration(report, plan, skipped_ids))
    all_issues.extend(check_missing_output_files(report, settings))
    all_issues.extend(check_report_errors(report))
    all_issues.extend(check_pronunciation(report, plan))

    return _assemble(all_issues)
