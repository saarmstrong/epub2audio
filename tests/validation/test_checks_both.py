"""Validation checks for output_format='both' mode (M12).

Covers:
- skipped_text in both mode (MP3 output_path=None or duration=0)
- missing_output_file in both mode (per-chapter MP3 missing, M4B missing)
- M12-07: null M4B output_path with chapters present → missing_output_file error
"""

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
    check_missing_output_files,
    check_skipped_text,
)
from tests.validation.conftest import make_report, make_result

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def meta() -> BookMetadata:
    return BookMetadata(
        title="Test Book",
        author="Test Author",
        language="en",
        identifier="both-test-001",
        publisher=None,
        date=None,
        rights=None,
    )


@pytest.fixture
def plan(meta: BookMetadata) -> ConversionPlan:
    chapters = [
        Chapter(
            chapter_id="ch001",
            title="Chapter One",
            source_docs=["ch01.xhtml"],
            word_count=200,
            stable_id="aaa",
        ),
    ]
    return ConversionPlan(book_metadata=meta, chapters=chapters, config_snapshot={})


@pytest.fixture
def both_settings() -> Settings:
    return Settings(output_format="both")


# ---------------------------------------------------------------------------
# check_skipped_text — both mode
# ---------------------------------------------------------------------------


class TestSkippedTextBothMode:
    def test_zero_duration_flags_error(
        self,
        meta: BookMetadata,
        plan: ConversionPlan,
        both_settings: Settings,
    ) -> None:
        """A chapter with duration=0 is flagged as skipped_text in both mode."""
        result = make_result("ch001", duration=0.0, output_path="/tmp/ch001.mp3")
        report = make_report(meta, [result])
        issues = check_skipped_text(report, plan, both_settings)
        codes = [i.code for i in issues]
        assert "skipped_text" in codes

    def test_none_output_path_flags_error(
        self,
        meta: BookMetadata,
        plan: ConversionPlan,
        both_settings: Settings,
    ) -> None:
        """A chapter with output_path=None is flagged as skipped_text in both mode
        (because both mode expects per-chapter MP3 paths)."""
        result = make_result("ch001", duration=30.0, output_path=None)
        report = make_report(meta, [result])
        issues = check_skipped_text(report, plan, both_settings)
        codes = [i.code for i in issues]
        assert "skipped_text" in codes

    def test_good_chapter_no_error(
        self,
        meta: BookMetadata,
        plan: ConversionPlan,
        both_settings: Settings,
    ) -> None:
        """A chapter with positive duration and an mp3 output_path is not flagged."""
        result = make_result("ch001", duration=30.0, output_path="/tmp/ch001.mp3")
        report = make_report(meta, [result])
        issues = check_skipped_text(report, plan, both_settings)
        assert issues == []


# ---------------------------------------------------------------------------
# check_missing_output_files — both mode
# ---------------------------------------------------------------------------


class TestMissingOutputFilesBothMode:
    def test_missing_per_chapter_mp3_flagged(
        self, meta: BookMetadata, both_settings: Settings, tmp_path: Path
    ) -> None:
        """Per-chapter MP3 path that doesn't exist on disk → missing_output_file."""
        ghost_mp3 = str(tmp_path / "ghost.mp3")  # does not exist
        m4b_path = tmp_path / "book.m4b"
        m4b_path.write_bytes(b"x")  # exists

        result = make_result("ch001", duration=30.0, output_path=ghost_mp3)
        report = make_report(meta, [result], output_path=str(m4b_path))
        issues = check_missing_output_files(report, both_settings)
        codes = [i.code for i in issues]
        assert "missing_output_file" in codes
        # Should flag the specific chapter
        assert any(i.chapter_id == "ch001" for i in issues)

    def test_missing_m4b_flagged(
        self, meta: BookMetadata, both_settings: Settings, tmp_path: Path
    ) -> None:
        """M4B path that doesn't exist on disk → missing_output_file."""
        mp3_path = tmp_path / "001 - Chapter One.mp3"
        mp3_path.write_bytes(b"x")  # exists
        ghost_m4b = str(tmp_path / "ghost.m4b")  # does not exist

        result = make_result("ch001", duration=30.0, output_path=str(mp3_path))
        report = make_report(meta, [result], output_path=ghost_m4b)
        issues = check_missing_output_files(report, both_settings)
        codes = [i.code for i in issues]
        assert "missing_output_file" in codes
        # Book-level issue, no chapter_id
        assert any(i.chapter_id is None for i in issues)

    def test_both_exist_no_issues(
        self, meta: BookMetadata, both_settings: Settings, tmp_path: Path
    ) -> None:
        """When both the MP3 and M4B files exist, no issues are produced."""
        mp3_path = tmp_path / "001 - Chapter One.mp3"
        mp3_path.write_bytes(b"x")
        m4b_path = tmp_path / "book.m4b"
        m4b_path.write_bytes(b"x")

        result = make_result("ch001", duration=30.0, output_path=str(mp3_path))
        report = make_report(meta, [result], output_path=str(m4b_path))
        issues = check_missing_output_files(report, both_settings)
        assert issues == []

    # M12-07: null M4B output_path with chapters present
    def test_m12_07_null_m4b_output_path_with_chapters(
        self, meta: BookMetadata, both_settings: Settings, tmp_path: Path
    ) -> None:
        """M12-07: output_path=None in both/m4b mode with chapters → missing_output_file."""
        result = make_result("ch001", duration=30.0, output_path="/tmp/ch001.mp3")
        report = make_report(meta, [result], output_path=None)  # M4B assembly failed
        issues = check_missing_output_files(report, both_settings)
        codes = [i.code for i in issues]
        assert "missing_output_file" in codes
        assert any(i.chapter_id is None for i in issues)

    def test_m12_07_null_m4b_m4b_mode(self, meta: BookMetadata, tmp_path: Path) -> None:
        """M12-07: also applies in pure m4b mode when output_path is None."""
        m4b_settings = Settings(output_format="m4b")
        result = make_result("ch001", duration=30.0, output_path=None)
        report = make_report(meta, [result], output_path=None)
        issues = check_missing_output_files(report, m4b_settings)
        codes = [i.code for i in issues]
        assert "missing_output_file" in codes

    def test_m4b_none_output_path_no_chapters_not_flagged(
        self, meta: BookMetadata, both_settings: Settings
    ) -> None:
        """output_path=None with zero chapters is not flagged (nothing to assemble)."""
        report = make_report(meta, [], output_path=None)
        issues = check_missing_output_files(report, both_settings)
        assert issues == []


# ---------------------------------------------------------------------------
# M4B chapter-marker validation also fires in both mode
# ---------------------------------------------------------------------------


class TestTimestampsBothMode:
    def test_overlapping_markers_flagged_in_both_mode(
        self, meta: BookMetadata, tmp_path: Path
    ) -> None:
        """Overlapping chapter markers are an error in both mode (same as m4b)."""
        from epub2audio.validation.checks import check_timestamps

        markers = [
            ChapterMarker(chapter_id="ch001", title="Ch 1", start_ms=0, end_ms=1000),
            ChapterMarker(chapter_id="ch002", title="Ch 2", start_ms=900, end_ms=2000),
        ]
        report = ConversionReport(
            book_metadata=meta,
            chapter_results=[],
            total_duration_seconds=2.0,
            warnings=[],
            errors=[],
            output_path="/tmp/book.m4b",
            chapter_markers=markers,
        )
        both_settings = Settings(output_format="both")
        issues = check_timestamps(report, both_settings)
        codes = [i.code for i in issues]
        assert "overlapping_timestamps" in codes
