"""Unit tests for individual validation check functions (M11-01)."""

from __future__ import annotations

from pathlib import Path

import pytest

from epub2audio.config import Settings
from epub2audio.models import (
    BookMetadata,
    Chapter,
    ChapterMarker,
    ConversionPlan,
    ConversionReport,
)
from epub2audio.validation.checks import (
    _assemble,
    check_chapter_duration,
    check_invalid_metadata,
    check_missing_chapters,
    check_missing_output_files,
    check_pronunciation,
    check_report_errors,
    check_skipped_text,
    check_timestamps,
)
from tests.validation.conftest import make_report, make_result

# ---------------------------------------------------------------------------
# _assemble
# ---------------------------------------------------------------------------


class TestAssemble:
    def test_empty_issues_is_ok(self) -> None:
        r = _assemble([])
        assert r.ok is True
        assert r.error_count == 0
        assert r.warning_count == 0
        assert r.info_count == 0
        assert r.issues == []

    def test_one_error_flips_ok(self) -> None:
        from epub2audio.models import ValidationIssue

        issues = [ValidationIssue(code="x", severity="error", message="m")]
        r = _assemble(issues)
        assert r.ok is False
        assert r.error_count == 1
        assert r.warning_count == 0

    def test_warning_only_stays_ok(self) -> None:
        from epub2audio.models import ValidationIssue

        issues = [ValidationIssue(code="x", severity="warning", message="m")]
        r = _assemble(issues)
        assert r.ok is True
        assert r.warning_count == 1
        assert r.error_count == 0

    def test_counts_match_issues(self) -> None:
        from epub2audio.models import ValidationIssue

        issues = [
            ValidationIssue(code="a", severity="error", message="e1"),
            ValidationIssue(code="b", severity="error", message="e2"),
            ValidationIssue(code="c", severity="warning", message="w"),
            ValidationIssue(code="d", severity="info", message="i"),
        ]
        r = _assemble(issues)
        assert r.error_count == 2
        assert r.warning_count == 1
        assert r.info_count == 1
        assert r.ok is False


# ---------------------------------------------------------------------------
# check_missing_chapters
# ---------------------------------------------------------------------------


class TestMissingChapters:
    def test_no_missing(self, good_plan: ConversionPlan, good_meta: BookMetadata) -> None:
        results = [make_result("ch001"), make_result("ch002")]
        report = make_report(good_meta, results)
        assert check_missing_chapters(report, good_plan) == []

    def test_one_missing(self, good_plan: ConversionPlan, good_meta: BookMetadata) -> None:
        results = [make_result("ch001")]  # ch002 missing
        report = make_report(good_meta, results)
        issues = check_missing_chapters(report, good_plan)
        assert len(issues) == 1
        assert issues[0].code == "missing_chapter"
        assert issues[0].severity == "error"
        assert issues[0].chapter_id == "ch002"

    def test_both_missing(self, good_plan: ConversionPlan, good_meta: BookMetadata) -> None:
        report = make_report(good_meta, [])
        issues = check_missing_chapters(report, good_plan)
        assert len(issues) == 2
        assert all(i.code == "missing_chapter" for i in issues)


# ---------------------------------------------------------------------------
# check_skipped_text
# ---------------------------------------------------------------------------


class TestSkippedText:
    def test_no_issue_when_duration_positive(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        # MP3 mode: output_path must be set for a successful chapter
        results = [
            make_result("ch001", duration=60.0, output_path="/fake/ch1.mp3"),
            make_result("ch002", duration=30.0, output_path="/fake/ch2.mp3"),
        ]
        report = make_report(good_meta, results)
        assert check_skipped_text(report, good_plan, Settings()) == []

    def test_zero_duration_flags_error(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        results = [
            make_result("ch001", duration=0.0, output_path=None),
            make_result("ch002", duration=30.0, output_path="/fake/ch2.mp3"),
        ]
        report = make_report(good_meta, results)
        issues = check_skipped_text(report, good_plan, Settings())
        assert len(issues) == 1
        assert issues[0].code == "skipped_text"
        assert issues[0].chapter_id == "ch001"

    def test_mp3_none_output_path_flags_error(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        # MP3 mode: output_path=None with positive duration still flags error
        results = [
            make_result("ch001", duration=60.0, output_path=None),
            make_result("ch002", duration=30.0),
        ]
        report = make_report(good_meta, results)
        settings = Settings(output_format="mp3")
        issues = check_skipped_text(report, good_plan, settings)
        assert any(i.code == "skipped_text" and i.chapter_id == "ch001" for i in issues)

    def test_m4b_none_output_path_not_flagged(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        # M4B mode: per-chapter output_path=None is expected; only duration matters
        results = [
            make_result("ch001", duration=60.0, output_path=None),
            make_result("ch002", duration=30.0, output_path=None),
        ]
        report = make_report(good_meta, results)
        settings = Settings(output_format="m4b")
        issues = check_skipped_text(report, good_plan, settings)
        assert issues == []

    def test_empty_chapter_not_flagged(self, good_meta: BookMetadata) -> None:
        # word_count=0 chapters are exempt
        empty_chapter = Chapter(
            chapter_id="ch001",
            title="Empty",
            source_docs=["a.xhtml"],
            word_count=0,
            stable_id="zzz",
        )
        plan = ConversionPlan(book_metadata=good_meta, chapters=[empty_chapter], config_snapshot={})
        results = [make_result("ch001", duration=0.0)]
        report = make_report(good_meta, results)
        assert check_skipped_text(report, plan, Settings()) == []


# ---------------------------------------------------------------------------
# check_invalid_metadata
# ---------------------------------------------------------------------------


class TestInvalidMetadata:
    def test_valid_metadata_no_issues(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        report = make_report(good_meta, [make_result("ch001")])
        assert check_invalid_metadata(report) == []

    @pytest.mark.parametrize("field", ["title", "author", "language", "identifier"])
    def test_empty_field_flagged(self, field: str) -> None:
        kwargs: dict[str, str | None] = {
            "title": "T",
            "author": "A",
            "language": "en",
            "identifier": "id",
            "publisher": None,
            "date": None,
            "rights": None,
        }
        kwargs[field] = ""
        meta = BookMetadata(**kwargs)  # type: ignore[arg-type]
        report = make_report(meta, [make_result("ch001")])
        issues = check_invalid_metadata(report)
        assert len(issues) == 1
        assert issues[0].code == "invalid_metadata"
        assert issues[0].chapter_id is None

    def test_whitespace_only_flagged(self) -> None:
        meta = BookMetadata(
            title="   ",
            author="Author",
            language="en",
            identifier="id",
            publisher=None,
            date=None,
            rights=None,
        )
        report = make_report(meta, [])
        issues = check_invalid_metadata(report)
        assert any(i.code == "invalid_metadata" for i in issues)


# ---------------------------------------------------------------------------
# check_timestamps
# ---------------------------------------------------------------------------


class TestTimestamps:
    def _m4b_settings(self) -> Settings:
        return Settings(output_format="m4b")

    def _markers(self, *spans: tuple[int, int]) -> list[ChapterMarker]:
        return [
            ChapterMarker(
                chapter_id=f"ch{i:03d}",
                title=f"Ch {i}",
                start_ms=s,
                end_ms=e,
            )
            for i, (s, e) in enumerate(spans, 1)
        ]

    def test_skipped_for_mp3(self, good_meta: BookMetadata) -> None:
        report = make_report(good_meta, [])
        issues = check_timestamps(report, Settings(output_format="mp3"))
        assert issues == []

    def test_contiguous_no_issues(self, good_meta: BookMetadata) -> None:
        report = ConversionReport(
            book_metadata=good_meta,
            chapter_results=[],
            total_duration_seconds=0.0,
            warnings=[],
            errors=[],
            output_path=None,
            chapter_markers=self._markers((0, 1000), (1000, 2000)),
        )
        assert check_timestamps(report, self._m4b_settings()) == []

    def test_invalid_marker_start_ge_end(self, good_meta: BookMetadata) -> None:
        report = ConversionReport(
            book_metadata=good_meta,
            chapter_results=[],
            total_duration_seconds=0.0,
            warnings=[],
            errors=[],
            output_path=None,
            chapter_markers=self._markers((500, 500)),  # start == end
        )
        issues = check_timestamps(report, self._m4b_settings())
        assert any(i.code == "overlapping_timestamps" and i.severity == "error" for i in issues)

    def test_overlapping_consecutive(self, good_meta: BookMetadata) -> None:
        report = ConversionReport(
            book_metadata=good_meta,
            chapter_results=[],
            total_duration_seconds=0.0,
            warnings=[],
            errors=[],
            output_path=None,
            chapter_markers=self._markers((0, 1500), (1000, 2000)),  # overlap
        )
        issues = check_timestamps(report, self._m4b_settings())
        assert any(i.code == "overlapping_timestamps" and i.severity == "error" for i in issues)

    def test_gap_between_markers_is_warning(self, good_meta: BookMetadata) -> None:
        report = ConversionReport(
            book_metadata=good_meta,
            chapter_results=[],
            total_duration_seconds=0.0,
            warnings=[],
            errors=[],
            output_path=None,
            chapter_markers=self._markers((0, 1000), (1100, 2000)),  # 100 ms gap
        )
        issues = check_timestamps(report, self._m4b_settings())
        assert any(i.code == "non_contiguous_timeline" and i.severity == "warning" for i in issues)


# ---------------------------------------------------------------------------
# check_chapter_duration
# ---------------------------------------------------------------------------


class TestChapterDuration:
    def test_positive_duration_no_issue(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        results = [make_result("ch001", duration=60.0), make_result("ch002", duration=30.0)]
        report = make_report(good_meta, results)
        assert check_chapter_duration(report, good_plan, set()) == []

    def test_zero_duration_is_warning(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        results = [make_result("ch001", duration=0.0), make_result("ch002", duration=30.0)]
        report = make_report(good_meta, results)
        issues = check_chapter_duration(report, good_plan, set())
        assert any(i.code == "chapter_duration" and i.severity == "warning" for i in issues)

    def test_skipped_id_not_duplicated(
        self, good_plan: ConversionPlan, good_meta: BookMetadata
    ) -> None:
        # If ch001 was already flagged by check_skipped_text, don't duplicate
        results = [make_result("ch001", duration=0.0)]
        report = make_report(good_meta, results)
        issues = check_chapter_duration(report, good_plan, {"ch001"})
        assert all(i.chapter_id != "ch001" for i in issues)


# ---------------------------------------------------------------------------
# check_missing_output_files
# ---------------------------------------------------------------------------


class TestMissingOutputFiles:
    def test_existing_mp3_no_issue(self, good_meta: BookMetadata, tmp_path: Path) -> None:
        mp3 = tmp_path / "ch1.mp3"
        mp3.write_bytes(b"x")
        results = [make_result("ch001", output_path=str(mp3))]
        report = make_report(good_meta, results)
        assert check_missing_output_files(report, Settings(output_format="mp3")) == []

    def test_missing_mp3_flagged(self, good_meta: BookMetadata, tmp_path: Path) -> None:
        results = [make_result("ch001", output_path=str(tmp_path / "nonexistent.mp3"))]
        report = make_report(good_meta, results)
        issues = check_missing_output_files(report, Settings(output_format="mp3"))
        assert any(i.code == "missing_output_file" for i in issues)

    def test_none_output_path_not_flagged(self, good_meta: BookMetadata) -> None:
        results = [make_result("ch001", output_path=None)]
        report = make_report(good_meta, results)
        assert check_missing_output_files(report, Settings(output_format="mp3")) == []

    def test_m4b_existing_file_no_issue(self, good_meta: BookMetadata, tmp_path: Path) -> None:
        m4b = tmp_path / "book.m4b"
        m4b.write_bytes(b"x")
        report = make_report(good_meta, [], output_path=str(m4b))
        assert check_missing_output_files(report, Settings(output_format="m4b")) == []

    def test_m4b_missing_file_flagged(self, good_meta: BookMetadata, tmp_path: Path) -> None:
        report = make_report(good_meta, [], output_path=str(tmp_path / "nonexistent.m4b"))
        issues = check_missing_output_files(report, Settings(output_format="m4b"))
        assert any(i.code == "missing_output_file" for i in issues)


# ---------------------------------------------------------------------------
# check_report_errors
# ---------------------------------------------------------------------------


class TestReportErrors:
    def test_no_errors(self, good_meta: BookMetadata) -> None:
        report = make_report(good_meta, [], errors=[])
        assert check_report_errors(report) == []

    def test_one_error(self, good_meta: BookMetadata) -> None:
        report = make_report(good_meta, [], errors=["something exploded"])
        issues = check_report_errors(report)
        assert len(issues) == 1
        assert issues[0].code == "report_error"
        assert issues[0].severity == "error"

    def test_multiple_errors(self, good_meta: BookMetadata) -> None:
        report = make_report(good_meta, [], errors=["e1", "e2", "e3"])
        assert len(check_report_errors(report)) == 3


# ---------------------------------------------------------------------------
# check_pronunciation (stub)
# ---------------------------------------------------------------------------


class TestPronunciationStub:
    def test_always_empty(self, good_plan: ConversionPlan, good_meta: BookMetadata) -> None:
        report = make_report(good_meta, [])
        assert check_pronunciation(report, good_plan) == []


# ---------------------------------------------------------------------------
# validate_conversion orchestrator
# ---------------------------------------------------------------------------


class TestValidateConversion:
    from epub2audio.validation.checks import validate_conversion as _vc

    def test_fully_clean_run(
        self, good_plan: ConversionPlan, good_meta: BookMetadata, tmp_path: Path
    ) -> None:
        from epub2audio.validation.checks import validate_conversion

        mp3_a = tmp_path / "ch1.mp3"
        mp3_b = tmp_path / "ch2.mp3"
        mp3_a.write_bytes(b"x")
        mp3_b.write_bytes(b"x")
        results = [
            make_result("ch001", duration=60.0, output_path=str(mp3_a)),
            make_result("ch002", duration=30.0, output_path=str(mp3_b)),
        ]
        report = make_report(good_meta, results)
        vr = validate_conversion(report, good_plan, Settings(), tmp_path)
        assert vr.ok is True
        assert vr.issues == []

    def test_skipped_chapter_sets_not_ok(
        self, good_plan: ConversionPlan, good_meta: BookMetadata, tmp_path: Path
    ) -> None:
        from epub2audio.validation.checks import validate_conversion

        results = [
            make_result("ch001", duration=0.0, output_path=None),
            make_result("ch002", duration=30.0, output_path=None),
        ]
        report = make_report(good_meta, results)
        vr = validate_conversion(report, good_plan, Settings(), tmp_path)
        assert vr.ok is False
        assert any(i.code == "skipped_text" for i in vr.issues)

    def test_chapter_duration_no_duplicate(
        self, good_plan: ConversionPlan, good_meta: BookMetadata, tmp_path: Path
    ) -> None:
        """A zero-duration chapter should fire skipped_text but NOT chapter_duration."""
        from epub2audio.validation.checks import validate_conversion

        results = [
            make_result("ch001", duration=0.0, output_path=None),
            make_result("ch002", duration=30.0, output_path=None),
        ]
        report = make_report(good_meta, results)
        vr = validate_conversion(report, good_plan, Settings(), tmp_path)
        codes = [i.code for i in vr.issues]
        assert "skipped_text" in codes
        # chapter_duration should NOT appear for ch001 since skipped_text already covers it
        duration_issues = [i for i in vr.issues if i.code == "chapter_duration"]
        assert all(i.chapter_id != "ch001" for i in duration_issues)

    def test_counts_consistent(
        self, good_plan: ConversionPlan, good_meta: BookMetadata, tmp_path: Path
    ) -> None:
        from epub2audio.validation.checks import validate_conversion

        results = [make_result("ch001", duration=0.0)]
        report = make_report(good_meta, results, errors=["pipeline blew up"])
        vr = validate_conversion(report, good_plan, Settings(), tmp_path)
        assert vr.error_count == sum(1 for i in vr.issues if i.severity == "error")
        assert vr.warning_count == sum(1 for i in vr.issues if i.severity == "warning")
        assert vr.info_count == sum(1 for i in vr.issues if i.severity == "info")

    def test_import_boundary(self) -> None:
        """All .py files in validation/ must not import forbidden domains.

        M12-08: broadened from checks.py-only + ImportFrom-only to cover every
        .py file in the package (including __init__.py) and BOTH ``import x``
        (ast.Import) and ``from x import y`` (ast.ImportFrom) node forms.
        """
        import ast
        import pathlib

        forbidden = {
            "epub2audio.epub",
            "epub2audio.director",
            "epub2audio.providers",
            "epub2audio.tts",
            "epub2audio.audio",
            "epub2audio.pipeline",
        }

        validation_dir = pathlib.Path("src/epub2audio/validation")
        py_files = sorted(validation_dir.glob("*.py"))
        assert py_files, f"No .py files found under {validation_dir}"

        for py_file in py_files:
            src = py_file.read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for prefix in forbidden:
                        assert not node.module.startswith(prefix), (
                            f"{py_file.name}: must not `from {prefix}...` import, "
                            f"found: {node.module}"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        for prefix in forbidden:
                            assert not alias.name.startswith(prefix), (
                                f"{py_file.name}: must not `import {prefix}...`, "
                                f"found: {alias.name}"
                            )


# ---------------------------------------------------------------------------
# ValidationReport model_validator (M12-09)
# ---------------------------------------------------------------------------


class TestValidationReportModelValidator:
    """Verify that the @model_validator on ValidationReport enforces count invariants.

    The model_validator unconditionally recomputes ok, error_count, warning_count,
    and info_count from the issues list, regardless of what values were supplied at
    construction time (ADR-006 M12-09 revision, ADR-007 §M12-09).
    """

    def test_correct_inputs_unchanged(self) -> None:
        """When correct values are passed, the model_validator is a no-op."""
        from epub2audio.models import ValidationIssue, ValidationReport

        issues = [ValidationIssue(code="x", severity="error", message="m")]
        r = ValidationReport(ok=False, issues=issues, error_count=1, warning_count=0, info_count=0)
        assert r.ok is False
        assert r.error_count == 1
        assert r.warning_count == 0
        assert r.info_count == 0

    def test_wrong_ok_is_corrected(self) -> None:
        """ok=True with error issues is corrected to False by the model_validator."""
        from epub2audio.models import ValidationIssue, ValidationReport

        issues = [ValidationIssue(code="x", severity="error", message="e")]
        # Deliberately supply wrong ok and wrong counts
        r = ValidationReport(ok=True, issues=issues, error_count=99, warning_count=0, info_count=0)
        assert r.ok is False  # corrected
        assert r.error_count == 1  # corrected

    def test_wrong_counts_are_corrected(self) -> None:
        """Supplying wrong counts with mixed-severity issues is always corrected."""
        from epub2audio.models import ValidationIssue, ValidationReport

        issues = [
            ValidationIssue(code="a", severity="error", message="e1"),
            ValidationIssue(code="b", severity="error", message="e2"),
            ValidationIssue(code="c", severity="warning", message="w"),
            ValidationIssue(code="d", severity="info", message="i"),
        ]
        # Supply all-wrong counts
        r = ValidationReport(ok=True, issues=issues, error_count=0, warning_count=0, info_count=0)
        assert r.ok is False
        assert r.error_count == 2
        assert r.warning_count == 1
        assert r.info_count == 1

    def test_empty_issues_always_ok(self) -> None:
        """An empty issues list always produces ok=True and zero counts."""
        from epub2audio.models import ValidationReport

        # Supply wrong ok
        r = ValidationReport(ok=False, issues=[], error_count=5, warning_count=3, info_count=1)
        assert r.ok is True
        assert r.error_count == 0
        assert r.warning_count == 0
        assert r.info_count == 0

    def test_json_roundtrip_corrects_stale_counts(self) -> None:
        """Deserializing a JSON blob with wrong counts yields a corrected report."""
        import json

        from epub2audio.models import ValidationReport

        # Simulate a stale or hand-edited JSON report
        stale_json = json.dumps(
            {
                "ok": True,
                "issues": [{"code": "e", "severity": "error", "message": "bad"}],
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            }
        )
        r = ValidationReport.model_validate_json(stale_json)
        assert r.ok is False
        assert r.error_count == 1

    def test_frozen_after_construction(self) -> None:
        """ValidationReport remains frozen after the model_validator runs."""
        from pydantic import ValidationError as PydanticValidationError

        from epub2audio.models import ValidationReport

        r = ValidationReport(ok=True, issues=[], error_count=0, warning_count=0, info_count=0)
        with pytest.raises((AttributeError, PydanticValidationError, TypeError)):
            r.ok = False  # type: ignore[misc]
