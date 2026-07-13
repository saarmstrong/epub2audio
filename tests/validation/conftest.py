"""Shared fixtures for validation tests."""

from __future__ import annotations

import pytest

from epub2audio.models import (
    BookMetadata,
    Chapter,
    ChapterResult,
    ConversionPlan,
    ConversionReport,
)


@pytest.fixture
def good_meta() -> BookMetadata:
    return BookMetadata(
        title="Test Book",
        author="Test Author",
        language="en",
        identifier="test-id-001",
        publisher=None,
        date=None,
        rights=None,
    )


@pytest.fixture
def chapter_a() -> Chapter:
    return Chapter(
        chapter_id="ch001",
        title="Chapter One",
        source_docs=["ch01.xhtml"],
        word_count=200,
        stable_id="aaa",
    )


@pytest.fixture
def chapter_b() -> Chapter:
    return Chapter(
        chapter_id="ch002",
        title="Chapter Two",
        source_docs=["ch02.xhtml"],
        word_count=150,
        stable_id="bbb",
    )


@pytest.fixture
def good_plan(good_meta: BookMetadata, chapter_a: Chapter, chapter_b: Chapter) -> ConversionPlan:
    return ConversionPlan(
        book_metadata=good_meta,
        chapters=[chapter_a, chapter_b],
        config_snapshot={},
    )


def make_result(
    chapter_id: str,
    duration: float = 60.0,
    output_path: str | None = None,
) -> ChapterResult:
    return ChapterResult(
        chapter_id=chapter_id,
        duration_seconds=duration,
        warnings=[],
        output_path=output_path,
    )


def make_report(
    meta: BookMetadata,
    results: list[ChapterResult],
    errors: list[str] | None = None,
    output_path: str | None = None,
) -> ConversionReport:
    return ConversionReport(
        book_metadata=meta,
        chapter_results=results,
        total_duration_seconds=sum(r.duration_seconds for r in results),
        warnings=[],
        errors=errors or [],
        output_path=output_path,
        chapter_markers=[],
    )
