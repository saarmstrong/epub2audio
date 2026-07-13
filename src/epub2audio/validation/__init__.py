"""Optional post-conversion validation stage for epub2audio.

The validation stage checks the output of a conversion run against the
conversion plan and settings, producing a :class:`~epub2audio.models.ValidationReport`
that is written to ``validation-report.json`` in the output directory.

Validation is **off by default** and enabled with ``--validate`` on the CLI.
It never modifies output files — it is a read-only quality-assurance pass.

Public API::

    validate_conversion(
        report: ConversionReport,
        plan: ConversionPlan,
        settings: Settings,
        output_dir: Path,
    ) -> ValidationReport

See ``validation/checks.py`` for the individual check functions.
See ``docs/decisions/003-narration-pipeline.md`` §7 for design rationale.
"""

from __future__ import annotations

from epub2audio.validation.checks import validate_conversion

__all__ = ["validate_conversion"]
