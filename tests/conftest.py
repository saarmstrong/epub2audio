"""Shared pytest fixtures for the epub2audio test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Auto-skip opt-in marks unless explicitly selected
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip slow/requires_model tests unless those marks are explicitly requested."""
    expr = config.option.markexpr if hasattr(config.option, "markexpr") else ""
    slow_requested = "slow" in expr
    model_requested = "requires_model" in expr

    skip_slow = pytest.mark.skip(reason="opt-in only: run with -m 'slow'")
    skip_model = pytest.mark.skip(reason="opt-in only: run with -m 'requires_model'")

    for item in items:
        marks = {m.name for m in item.iter_markers()}
        if "slow" in marks and not slow_requested:
            item.add_marker(skip_slow)
        elif "requires_model" in marks and not model_requested:
            item.add_marker(skip_model)


# ---------------------------------------------------------------------------
# Fixture directory helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the absolute path to ``tests/fixtures/``."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def simple_epub3_path(fixtures_dir: Path) -> Path:
    """Path to the pre-generated simple EPUB3 fixture."""
    p = fixtures_dir / "simple_epub3.epub"
    if not p.exists():
        from tests.fixtures.builders import build_simple_epub3

        build_simple_epub3(p)
    return p


@pytest.fixture(scope="session")
def simple_epub2_path(fixtures_dir: Path) -> Path:
    """Path to the pre-generated simple EPUB2 fixture."""
    p = fixtures_dir / "simple_epub2.epub"
    if not p.exists():
        from tests.fixtures.builders import build_simple_epub2

        build_simple_epub2(p)
    return p
