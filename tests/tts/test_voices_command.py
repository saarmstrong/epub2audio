"""CLI smoke tests for the voices and doctor commands.

These tests do not require the kokoro model or package.
They test the CLI entry-points added in M3-03 and M3-04.
"""

from __future__ import annotations

import subprocess
import sys


def test_voices_command_exits_zero() -> None:
    """epub2audio voices exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "epub2audio.cli", "voices"],
        capture_output=True,
        text=True,
    )
    # Also accept invocation via uv
    if result.returncode not in (0, 1):
        result2 = subprocess.run(
            ["uv", "run", "epub2audio", "voices"],
            capture_output=True,
            text=True,
        )
        assert result2.returncode == 0, result2.stderr
    else:
        assert result.returncode == 0, result.stderr


def test_voices_command_output_contains_af_heart() -> None:
    """voices output mentions af_heart (the default voice)."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "voices"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "af_heart" in result.stdout, (
        f"Expected 'af_heart' in voices output.\nstdout: {result.stdout}"
    )


def test_voices_command_output_contains_count() -> None:
    """voices output contains the voice count footer line."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "voices"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "voices available" in result.stdout, (
        f"Expected 'voices available' in output.\nstdout: {result.stdout}"
    )


def test_doctor_command_exits() -> None:
    """epub2audio doctor exits 0 or 1 (not crashes or other exit codes)."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "doctor"],
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}.\nstderr: {result.stderr}"
    )


def test_doctor_shows_python_version() -> None:
    """doctor output contains 'Python' and a version string."""
    result = subprocess.run(
        ["uv", "run", "epub2audio", "doctor"],
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    assert "Python" in combined, (
        f"Expected 'Python' in doctor output.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert any(char.isdigit() for char in combined), "No version digits found in doctor output."
