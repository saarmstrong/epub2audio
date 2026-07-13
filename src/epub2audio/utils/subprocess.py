"""Safe subprocess runner for epub2audio.

All external tool invocations (FFmpeg, FFprobe) must go through
:func:`run_command`.  This module enforces the project-wide rule that
subprocess calls **never** use ``shell=True`` or string interpolation.
"""

from __future__ import annotations

import subprocess

from epub2audio.errors import MissingDependencyError


def run_command(
    args: list[str],
    *,
    input_data: bytes | None = None,
    timeout: float | None = None,
) -> tuple[bytes, bytes]:
    """Run a subprocess defined by an argument array.

    Args:
        args: Full command as a list, e.g. ``["ffmpeg", "-i", "input.wav"]``.
            The first element is the executable name.  Shell expansion is
            **never** applied.
        input_data: Optional bytes to feed to the process via stdin.
        timeout: Optional wall-clock timeout in seconds.  If the process does
            not finish within this time a :class:`subprocess.TimeoutExpired`
            exception is raised.

    Returns:
        A ``(stdout, stderr)`` tuple of raw bytes.

    Raises:
        MissingDependencyError: If the executable (``args[0]``) is not found
            on ``PATH``.
        subprocess.CalledProcessError: If the process exits with a non-zero
            return code.  ``returncode``, ``stdout``, and ``stderr`` are all
            populated on the exception.
        subprocess.TimeoutExpired: If the process exceeds *timeout*.
    """
    if not args:
        raise ValueError("args must be a non-empty list")

    try:
        result = subprocess.run(
            args,
            input=input_data,
            capture_output=True,
            check=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        executable = args[0]
        raise MissingDependencyError(
            executable,
            f"Required executable not found: {executable!r}. "
            f"Please install it and ensure it is on your PATH.",
        ) from None

    return result.stdout, result.stderr


def run_command_unchecked(
    args: list[str],
    *,
    input_data: bytes | None = None,
    timeout: float | None = None,
) -> tuple[int, bytes, bytes]:
    """Run a subprocess and return exit code without raising on failure.

    Useful for FFmpeg loudnorm pass-1 which writes measurement JSON to stderr
    regardless of exit code, and for FFprobe probes.

    Args:
        args: Full command as a list.  Shell expansion is **never** applied.
        input_data: Optional bytes to feed via stdin.
        timeout: Optional wall-clock timeout in seconds.

    Returns:
        A ``(returncode, stdout, stderr)`` tuple.

    Raises:
        MissingDependencyError: If the executable is not found on ``PATH``.
        subprocess.TimeoutExpired: If the process exceeds *timeout*.
    """
    if not args:
        raise ValueError("args must be a non-empty list")

    try:
        result = subprocess.run(
            args,
            input=input_data,
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        executable = args[0]
        raise MissingDependencyError(
            executable,
            f"Required executable not found: {executable!r}. "
            f"Please install it and ensure it is on your PATH.",
        ) from None

    return result.returncode, result.stdout, result.stderr
