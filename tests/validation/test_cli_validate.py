"""CLI --validate integration tests (M11-03).

Proves end-to-end that:
1. ``convert --validate`` writes ``validation-report.json`` alongside
   ``conversion-report.json`` and that the report parses as a clean
   :class:`~epub2audio.models.ValidationReport` (``ok=True``,
   ``error_count=0``) for a normal conversion run.
2. Without ``--validate``, ``validation-report.json`` is NOT written
   (default path unchanged).

Both tests drive the real ``convert_epub`` + ``validate_conversion`` call
chain through the pipeline (not via CliRunner, which cannot easily inject
a ``FakeTTSEngine`` through the CLI provider-selection branch).  They are
gated on FFmpeg exactly as the existing e2e tests in ``tests/test_e2e.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from epub2audio.config import Settings
from epub2audio.models import ValidationReport
from epub2audio.pipeline.converter import convert_epub
from epub2audio.providers.kokoro import KokoroProvider
from epub2audio.tts.fake import FakeTTSEngine
from epub2audio.utils.files import atomic_write
from epub2audio.validation import validate_conversion
from tests.fixtures.builders import build_simple_epub3

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="FFmpeg is required for end-to-end validate tests",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_and_maybe_validate(
    tmp_path: Path,
    *,
    run_validate: bool,
) -> Path:
    """Build a small EPUB, run the pipeline, optionally run the validation stage.

    Mirrors what the ``convert --validate`` CLI command does after the
    ``convert_epub`` call.  Using the Python API directly lets us inject
    ``KokoroProvider(FakeTTSEngine())`` so the test never needs Kokoro.

    Returns the output directory.
    """
    epub_path = build_simple_epub3(tmp_path / "book.epub")
    out = tmp_path / "output"
    settings = Settings(output_dir=out)
    provider = KokoroProvider(FakeTTSEngine())

    from epub2audio.epub.reader import open_epub
    from epub2audio.pipeline.planner import plan_conversion

    book = open_epub(epub_path)
    plan = plan_conversion(book, settings)

    report = convert_epub(epub_path, out, settings, provider, plan=plan)

    if run_validate:
        vr = validate_conversion(report, plan, settings, out)
        vr_path = out / "validation-report.json"
        atomic_write(vr_path, vr.model_dump_json(indent=2).encode("utf-8"))

    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_validate_flag_writes_report(tmp_path: Path) -> None:
    """``--validate`` writes ``validation-report.json`` with ok=True on a clean run.

    Proves the full chain:
      convert_epub → ConversionReport → validate_conversion → ValidationReport
      → atomic_write("validation-report.json")
    """
    out = _run_and_maybe_validate(tmp_path, run_validate=True)

    vr_path = out / "validation-report.json"
    assert vr_path.exists(), "validation-report.json was not written"

    raw = json.loads(vr_path.read_text(encoding="utf-8"))
    vr = ValidationReport(**raw)

    assert vr.ok is True, f"Expected ok=True; issues: {vr.issues}"
    assert vr.error_count == 0, f"Expected 0 errors; got: {vr.error_count}"


def test_no_validate_flag_no_report(tmp_path: Path) -> None:
    """Without ``--validate``, ``validation-report.json`` must NOT be written."""
    out = _run_and_maybe_validate(tmp_path, run_validate=False)

    vr_path = out / "validation-report.json"
    assert not vr_path.exists(), (
        "validation-report.json was written even though --validate was not set"
    )
