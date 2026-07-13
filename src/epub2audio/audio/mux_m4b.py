"""Single-file M4B assembly for epub2audio.

Concatenates the per-chapter AAC/MP4 segments losslessly (stream copy, no
re-encode), then muxes in the FFmetadata chapter file and optional cover art
to produce one ``.m4b`` audiobook.

All FFmpeg calls use argument arrays via
:func:`~epub2audio.utils.subprocess.run_command`; ``shell=True`` is **never**
used.  The final file is written atomically via a ``.tmp`` sidecar renamed
with :func:`os.replace`.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from epub2audio.errors import Epub2AudioError
from epub2audio.models import BookMetadata, ChapterMarker
from epub2audio.utils.subprocess import run_command


def _write_concat_list(chapter_audio: list[Path], dest: Path) -> None:
    """Write an FFmpeg concat-demuxer list file for *chapter_audio*.

    Each line is ``file '<absolute-path>'`` with single quotes in the path
    escaped per the concat demuxer's quoting rules.

    Args:
        chapter_audio: Ordered list of per-chapter MP4/AAC files.
        dest: Destination path for the concat list file.
    """
    lines: list[str] = []
    for path in chapter_audio:
        abs_path = str(path.resolve())
        escaped = abs_path.replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_m4b(
    chapter_audio: list[Path],
    markers: list[ChapterMarker],
    metadata: BookMetadata,
    ffmeta_path: Path,
    output_m4b: Path,
    cover_bytes: bytes | None = None,
) -> None:
    """Assemble a single ``.m4b`` audiobook from per-chapter AAC segments.

    Concatenates *chapter_audio* with the concat demuxer (stream copy), then
    attaches the chapter metadata from *ffmeta_path* and, if provided, an
    attached-picture cover.  The output is written atomically.

    Args:
        chapter_audio: Ordered per-chapter MP4/AAC files.  Must be non-empty.
        markers: Chapter markers (used only for validation of a non-empty
            book; the actual chapter data comes from *ffmeta_path*).
        metadata: Book metadata (reserved; tags are carried by *ffmeta_path*).
        ffmeta_path: Path to the FFmetadata file produced by
            :func:`~epub2audio.audio.chapters_meta.write_ffmetadata_chapters`.
        output_m4b: Destination ``.m4b`` path.  Parent dirs are created.
        cover_bytes: Optional cover image bytes (JPEG/PNG) to attach.

    Raises:
        Epub2AudioError: If *chapter_audio* is empty.
        MissingDependencyError: If ``ffmpeg`` is not on ``PATH``.
        subprocess.CalledProcessError: If FFmpeg exits non-zero.
        OSError: If temp files cannot be created or the rename fails.
    """
    _ = (markers, metadata)  # carried via ffmeta_path; kept for a clear signature
    if not chapter_audio:
        raise Epub2AudioError("build_m4b requires at least one chapter audio file.")

    output_m4b.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_m4b.with_suffix(output_m4b.suffix + ".tmp")

    # concat list + optional cover temp live beside the output for atomicity.
    fd, concat_str = tempfile.mkstemp(suffix=".txt", dir=output_m4b.parent)
    os.close(fd)
    concat_list = Path(concat_str)
    cover_tmp: str | None = None

    try:
        _write_concat_list(chapter_audio, concat_list)

        args: list[str] = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-i",
            str(ffmeta_path),
        ]

        if cover_bytes is not None:
            fd, cover_tmp = tempfile.mkstemp(suffix=".jpg")
            try:
                os.write(fd, cover_bytes)
            finally:
                os.close(fd)
            args += ["-i", cover_tmp]

        # Explicit stream selection so the output contains exactly the audio
        # (+ optional cover) we intend and nothing carried over from inputs:
        #   -map 0:a       audio from the concatenated chapters (input 0)
        #   -map_metadata 1 global tags from the ffmetadata file (input 1)
        #   -map_chapters 1 pin chapters to the ffmetadata input (deterministic;
        #                   avoids FFmpeg's implicit "input with most chapters"
        #                   heuristic).  FFmpeg materializes these as a QuickTime
        #                   chapter track (a `bin_data` stream) — that track *is*
        #                   how MP4/M4B chapters are stored and is required for
        #                   chapter navigation in players; it is not spurious.
        args += [
            "-map",
            "0:a",
            "-c:a",
            "copy",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
        ]

        if cover_bytes is not None:
            args += [
                "-map",
                "2:v",
                "-c:v",
                "copy",
                "-disposition:v:0",
                "attached_pic",
            ]

        args += ["-f", "mp4", str(tmp_path)]

        run_command(args)
        os.replace(tmp_path, output_m4b)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    finally:
        concat_list.unlink(missing_ok=True)
        if cover_tmp is not None:
            try:
                os.unlink(cover_tmp)
            except OSError:
                pass
