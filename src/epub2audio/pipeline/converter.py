"""Full pipeline orchestration for epub2audio.

:func:`convert_epub` is the central function of Milestone 2.  It drives the
complete EPUB → MP3 conversion for every chapter in reading order, handling
resume, per-segment TTS synthesis, WAV assembly, loudness normalization,
MP3 encoding, metadata embedding, validation, and intermediate file cleanup.

Design constraints:
- ``TTSEngine`` is injected — this module never imports ``KokoroTTSEngine``
  or ``FakeTTSEngine`` directly.
- Chapters are processed one at a time; the full audiobook is never held in
  memory simultaneously.
- All FFmpeg calls go through ``audio/`` helpers which enforce argument arrays
  and atomic writes.
- The manifest is written before synthesis begins and updated after each
  chapter so that interrupted runs can resume without losing completed work.
- Segment WAVs are written to a *persistent* work directory
  (``<output_dir>/.epub2audio-work/<chapter_id>/``) so they survive across
  runs and can be reused on resume.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from epub2audio.audio.chapters_meta import write_ffmetadata_chapters
from epub2audio.audio.chunks import concat_chunks, save_chunk
from epub2audio.audio.concatenate import concatenate_wavs
from epub2audio.audio.encode import encode_aac, encode_mp3
from epub2audio.audio.metadata import embed_metadata
from epub2audio.audio.mux_m4b import build_m4b
from epub2audio.audio.normalize import normalize_loudness
from epub2audio.audio.validate import probe_duration, validate_audio, validate_mp3
from epub2audio.config import Settings
from epub2audio.epub.cleanup import xhtml_to_text
from epub2audio.epub.cover import extract_cover
from epub2audio.epub.reader import open_epub
from epub2audio.models import (
    AudioChunk,
    Chapter,
    ChapterMarker,
    ChapterResult,
    ConversionManifest,
    ConversionPlan,
    ConversionReport,
    TextSegment,
)
from epub2audio.pipeline.manifest import (
    config_hash,
    epub_fingerprint,
    read_manifest,
    write_manifest,
)
from epub2audio.pipeline.resume import (
    check_resume,
    clear_segment_cache,
    segment_needs_synthesis,
    tts_config_changed,
)
from epub2audio.text.normalize import normalize_text
from epub2audio.text.segment import segment_text
from epub2audio.tts.base import TTSEngine
from epub2audio.utils.names import sanitize_book_filename, sanitize_filename

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MANIFEST_FILENAME = "manifest.json"
_WORK_DIR_NAME = ".epub2audio-work"


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _text_hash(text: str) -> str:
    """Return the SHA-256 hex digest of *text* encoded as UTF-8."""
    return hashlib.sha256(text.encode()).hexdigest()


def _get_end_fragment(source_docs: list[str], current: str) -> str | None:
    """Return the start fragment of the next source_doc if it shares the same file.

    When a single XHTML document is split into multiple chapters via fragment
    anchors, the end boundary for a given fragment entry is the start of the
    *next* fragment entry that references the same file.

    Args:
        source_docs: Full list of ``source_docs`` for the chapter.
        current: The current ``source_doc`` entry (may include a ``#fragment``).

    Returns:
        The fragment string of the immediately following source_doc if it has
        the same bare file path, otherwise ``None``.
    """
    bare_current = current.split("#", 1)[0]
    for i, doc in enumerate(source_docs):
        if doc == current and i + 1 < len(source_docs):
            next_doc = source_docs[i + 1]
            if "#" in next_doc:
                next_bare, next_frag = next_doc.split("#", 1)
                if next_bare == bare_current:
                    return next_frag
            break
    return None


def _load_chapter_text(
    book_path: Path,
    chapter: Chapter,
) -> str:
    """Extract and clean narration text for *chapter*.

    Opens the EPUB at *book_path*, reads the XHTML for each source document
    in the chapter, converts to plain text, and joins them.  Source documents
    may contain ``#fragment`` suffixes (e.g. ``chapter.xhtml#section2``)
    produced by :func:`~epub2audio.epub.chapters.split_multi_chapter_docs`.
    The bare path is used to look up the EPUB item and the fragment bounds
    are forwarded to :func:`~epub2audio.epub.cleanup.xhtml_to_text`.

    Args:
        book_path: Path to the EPUB file (opened fresh to avoid caching state).
        chapter: The chapter whose source documents to read.

    Returns:
        A single plain-text string for the chapter.
    """
    book = open_epub(book_path)
    texts: list[str] = []
    for doc_path in chapter.source_docs:
        # Strip optional #fragment suffix to get the bare EPUB item path.
        start_fragment: str | None
        if "#" in doc_path:
            bare_path, start_fragment = doc_path.split("#", 1)
        else:
            bare_path, start_fragment = doc_path, None

        item = book.get_item_with_href(bare_path)
        if item is None:
            log.warning(
                "Chapter %r: source doc %r not found in EPUB", chapter.chapter_id, bare_path
            )
            continue
        content: bytes = item.get_content()

        # When the same file is split into multiple chapters, derive the
        # exclusive end boundary from the next source_doc's fragment.
        end_fragment = _get_end_fragment(chapter.source_docs, doc_path)

        texts.append(
            xhtml_to_text(content, start_fragment=start_fragment, end_fragment=end_fragment)
        )
    return "\n\n".join(texts)


def _build_segments(text: str, settings: Settings) -> list[TextSegment]:
    """Normalize *text* and produce a list of :class:`TextSegment` objects.

    Args:
        text: Raw plain text from EPUB cleanup.
        settings: Effective settings (currently unused for segmentation tuning
            but included for forward compatibility).

    Returns:
        Ordered list of :class:`TextSegment` objects.
    """
    _ = settings  # reserved for future max_chars / segment tuning config
    normalized = normalize_text(text)
    return segment_text(normalized)


def _synthesize_segment(
    segment: TextSegment,
    tts_engine: TTSEngine,
    settings: Settings,
    seg_wav_path: Path,
) -> None:
    """Synthesize *segment* and write WAV output to *seg_wav_path*.

    Args:
        segment: The segment to synthesize.
        tts_engine: Injected TTS engine.
        settings: Effective settings (voice, language, speed).
        seg_wav_path: Destination WAV path for this segment.
    """
    chunks: list[AudioChunk] = tts_engine.synthesize(
        segment.text,
        voice=settings.voice,
        language=settings.language,
        speed=settings.speed,
    )
    combined = concat_chunks(chunks)
    save_chunk(combined, seg_wav_path)


def _process_chapter(
    chapter: Chapter,
    chapter_index: int,
    total_chapters: int,
    epub_path: Path,
    output_dir: Path,
    work_root: Path,
    settings: Settings,
    tts_engine: TTSEngine,
    manifest: ConversionManifest,
    cover_bytes: bytes | None,
) -> tuple[ChapterResult, list[TextSegment]]:
    """Convert a single chapter to a final MP3.

    Handles resume (skip already-synthesized segments), WAV concatenation,
    loudness normalization, MP3 encoding, metadata embedding, validation, and
    intermediate file cleanup.

    Args:
        chapter: The chapter to process.
        chapter_index: 1-based chapter index.
        total_chapters: Total chapter count (for track N/total tag).
        epub_path: Path to the source EPUB.
        output_dir: Final output directory for MP3s.
        work_root: Persistent root work directory (``.epub2audio-work/``).
        settings: Effective settings.
        tts_engine: Injected TTS engine.
        manifest: Current manifest (used for segment resume checking).
        cover_bytes: Optional cover art bytes to embed.

    Returns:
        A tuple of (:class:`ChapterResult`, list of completed
        :class:`TextSegment` objects with ``audio_path`` set).
    """
    chapter_work = work_root / chapter.chapter_id
    chapter_work.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    # ------------------------------------------------------------------ #
    # Text extraction and segmentation                                     #
    # ------------------------------------------------------------------ #
    raw_text = _load_chapter_text(epub_path, chapter)
    if not raw_text.strip():
        log.warning("Chapter %r has no narration text — skipping.", chapter.chapter_id)
        return (
            ChapterResult(
                chapter_id=chapter.chapter_id,
                duration_seconds=0.0,
                warnings=["Chapter has no narration text — skipped."],
                output_path=None,
            ),
            [],
        )

    segments = _build_segments(raw_text, settings)
    if not segments:
        log.warning("Chapter %r produced no segments — skipping.", chapter.chapter_id)
        return (
            ChapterResult(
                chapter_id=chapter.chapter_id,
                duration_seconds=0.0,
                warnings=["Chapter produced no segments after segmentation — skipped."],
                output_path=None,
            ),
            [],
        )

    # ------------------------------------------------------------------ #
    # Per-segment synthesis (with resume)                                  #
    # ------------------------------------------------------------------ #
    seg_wav_paths: list[Path] = []
    completed_segments: list[TextSegment] = []

    for seg_idx, segment in enumerate(segments):
        seg_wav = chapter_work / f"seg_{seg_idx:04d}.wav"

        # Resume: check if this segment's WAV already exists and is valid.
        # Match by normalized_hash against the manifest's segment list.
        existing_seg = _find_manifest_segment(manifest, segment.normalized_hash)
        if existing_seg is not None and not segment_needs_synthesis(existing_seg, output_dir):
            existing_path = Path(existing_seg.audio_path)  # type: ignore[arg-type]
            log.info(
                "Chapter %r segment %d: resumed from cached WAV",
                chapter.chapter_id,
                seg_idx,
            )
            seg_wav_paths.append(existing_path)
            completed_segments.append(existing_seg)
            continue

        log.debug(
            "Chapter %r segment %d: synthesizing %d words",
            chapter.chapter_id,
            seg_idx,
            segment.word_count,
        )
        _synthesize_segment(segment, tts_engine, settings, seg_wav)
        seg_wav_paths.append(seg_wav)

        # Record the completed segment with its audio_path set
        completed_segments.append(
            TextSegment(
                text=segment.text,
                source_hash=segment.source_hash,
                normalized_hash=segment.normalized_hash,
                word_count=segment.word_count,
                status="done",
                audio_path=str(seg_wav.resolve()),
            )
        )

    if not seg_wav_paths:
        return (
            ChapterResult(
                chapter_id=chapter.chapter_id,
                duration_seconds=0.0,
                warnings=["No segment WAVs produced — chapter skipped."],
                output_path=None,
            ),
            completed_segments,
        )

    # ------------------------------------------------------------------ #
    # WAV concatenation → normalization → MP3 encoding                    #
    # ------------------------------------------------------------------ #
    chapter_wav = chapter_work / "chapter.wav"
    chapter_wav_norm = chapter_work / "chapter_norm.wav"
    output_dir.mkdir(parents=True, exist_ok=True)

    concatenate_wavs(seg_wav_paths, chapter_wav)

    if settings.normalize:
        normalize_loudness(chapter_wav, chapter_wav_norm)
        encode_src = chapter_wav_norm
    else:
        encode_src = chapter_wav

    if settings.output_format == "m4b":
        # Per-chapter AAC segment persisted in the work dir; the single .m4b is
        # muxed after all chapters succeed.  No per-chapter metadata here.
        produced_path = chapter_work / "chapter.m4a"
        encode_aac(
            encode_src,
            produced_path,
            bitrate=settings.bitrate,
            sample_rate=settings.sample_rate,
        )
        validate_audio(
            produced_path,
            expected_codec="aac",
            expected_sample_rate=settings.sample_rate,
        )
    else:
        output_filename = sanitize_filename(chapter.title, chapter_index)
        produced_path = output_dir / output_filename
        encode_mp3(
            encode_src,
            produced_path,
            bitrate=settings.bitrate,
            sample_rate=settings.sample_rate,
        )
        validate_mp3(produced_path, expected_sample_rate=settings.sample_rate)

    # ------------------------------------------------------------------ #
    # Probe the produced file for its real duration                        #
    # ------------------------------------------------------------------ #
    try:
        duration_seconds = probe_duration(produced_path)
    except Exception as exc:
        log.warning("Chapter %r: duration probe failed: %s", chapter.chapter_id, exc)
        duration_seconds = 0.0
        warnings.append(f"Duration probe failed: {exc}")

    # ------------------------------------------------------------------ #
    # Cleanup intermediate files (only on success, unless keep_intermediates)
    # ------------------------------------------------------------------ #
    if not settings.keep_intermediates:
        # Remove just the non-segment intermediate files (chapter WAV, normalized WAV)
        # Segment WAVs are cleaned up at the top level after all chapters succeed.
        for tmp_file in [chapter_wav, chapter_wav_norm]:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

    return (
        ChapterResult(
            chapter_id=chapter.chapter_id,
            duration_seconds=duration_seconds,
            warnings=warnings,
            output_path=str(produced_path),
        ),
        completed_segments,
    )


def _find_manifest_segment(
    manifest: ConversionManifest,
    normalized_hash: str,
) -> TextSegment | None:
    """Find a segment in *manifest* by its normalized text hash.

    Args:
        manifest: The manifest to search.
        normalized_hash: SHA-256 hex digest of the normalized segment text.

    Returns:
        The matching :class:`TextSegment`, or ``None`` if not found.
    """
    for seg in manifest.segments:
        if seg.normalized_hash == normalized_hash:
            return seg
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert_epub(
    epub_path: Path,
    output_dir: Path,
    settings: Settings,
    tts_engine: TTSEngine,
    plan: ConversionPlan | None = None,
) -> ConversionReport:
    """Convert an EPUB to MP3 audiobook files.

    Orchestrates the full pipeline:

    1. Open EPUB and build (or reuse) the conversion plan.
    2. Write the manifest before synthesis begins.
    3. For each chapter (in reading order):
       a. Extract and clean text.
       b. Normalize and segment text.
       c. Synthesize each segment (skipping cached segments on resume).
       d. Concatenate segment WAVs.
       e. Optionally normalize loudness (EBU R128).
       f. Encode to MP3 (libmp3lame, mono, 24 kHz by default).
       g. Embed ID3 metadata and cover art.
       h. Validate via FFprobe.
       i. Clean up intermediate WAV files.
    4. Update manifest after each chapter.
    5. Return a :class:`ConversionReport`.

    Args:
        epub_path: Path to the source EPUB file.
        output_dir: Directory where MP3 files will be written.  Created if
            it does not exist.
        settings: Effective settings for this conversion run.
        tts_engine: The TTS engine to use for synthesis.  Must satisfy the
            :class:`~epub2audio.tts.base.TTSEngine` Protocol.  This module
            never imports a concrete engine class.
        plan: Optional pre-built :class:`ConversionPlan`.  If ``None``, the
            plan is built from the EPUB at *epub_path*.

    Returns:
        A :class:`ConversionReport` summarising the outcome of the conversion.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Persistent work directory for segment WAVs — survives across runs.
    work_root = output_dir / _WORK_DIR_NAME
    work_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Build or reuse the conversion plan                                   #
    # ------------------------------------------------------------------ #
    if plan is None:
        from epub2audio.pipeline.planner import plan_conversion

        book = open_epub(epub_path)
        plan = plan_conversion(book, settings)

    book_metadata = plan.book_metadata
    chapters = plan.chapters
    total_chapters = len(chapters)

    # Extract cover art once for all chapters
    book = open_epub(epub_path)
    cover_bytes = extract_cover(book)

    # ------------------------------------------------------------------ #
    # Manifest: load existing or create fresh                              #
    # ------------------------------------------------------------------ #
    manifest_path = output_dir / _MANIFEST_FILENAME
    now = _utc_now()

    if settings.resume and manifest_path.exists():
        try:
            manifest = read_manifest(manifest_path)
            changed_keys = check_resume(manifest, epub_path, settings)
            if changed_keys:
                log.info(
                    "Config changed (keys: %s) — clearing TTS segment cache.",
                    changed_keys,
                )
                if tts_config_changed(changed_keys):
                    # TTS-affecting change: discard all segment WAVs so they are
                    # re-synthesized with the new voice/language/speed.
                    for chapter in chapters:
                        clear_segment_cache(work_root, chapter.chapter_id)
                    cleared_segments: list[TextSegment] = []
                else:
                    # Encoding-only change: segment WAVs are still valid.
                    cleared_segments = list(manifest.segments)

                manifest = ConversionManifest(
                    epub_fingerprint=manifest.epub_fingerprint,
                    config_hash=config_hash(settings),
                    chapters=chapters,
                    segments=cleared_segments,
                    created_at=manifest.created_at,
                    updated_at=now,
                )
            else:
                # Settings unchanged — keep existing segment cache.
                manifest = ConversionManifest(
                    epub_fingerprint=manifest.epub_fingerprint,
                    config_hash=config_hash(settings),
                    chapters=chapters,
                    segments=manifest.segments,
                    created_at=manifest.created_at,
                    updated_at=now,
                )
        except Exception as exc:
            log.warning("Could not load manifest (%s) — starting fresh.", exc)
            manifest = _new_manifest(epub_path, settings, chapters, now)
    else:
        manifest = _new_manifest(epub_path, settings, chapters, now)

    write_manifest(manifest, manifest_path)

    # ------------------------------------------------------------------ #
    # Per-chapter conversion                                               #
    # ------------------------------------------------------------------ #
    chapter_results: list[ChapterResult] = []
    all_warnings: list[str] = []
    all_errors: list[str] = []
    all_new_segments: list[TextSegment] = []
    successful_chapter_ids: list[str] = []

    for idx, chapter in enumerate(chapters, start=1):
        log.info(
            "Converting chapter %d/%d: %r",
            idx,
            total_chapters,
            chapter.title,
        )

        try:
            result, chapter_segments = _process_chapter(
                chapter=chapter,
                chapter_index=idx,
                total_chapters=total_chapters,
                epub_path=epub_path,
                output_dir=output_dir,
                work_root=work_root,
                settings=settings,
                tts_engine=tts_engine,
                manifest=manifest,
                cover_bytes=cover_bytes,
            )

            # Accumulate newly completed segments from this chapter
            all_new_segments.extend(chapter_segments)

            # Metadata: MP3 gets per-file ID3 tags + cover embedded now.
            # For M4B the tags/chapters/cover are applied once in the final mux.
            if result.output_path is not None:
                if settings.output_format == "mp3":
                    mp3_path = Path(result.output_path)
                    try:
                        embed_metadata(
                            mp3_path=mp3_path,
                            metadata=book_metadata,
                            track_number=idx,
                            total_tracks=total_chapters,
                            chapter_title=chapter.title,
                            cover_bytes=cover_bytes,
                        )
                    except Exception as meta_exc:
                        log.warning(
                            "Chapter %r: metadata embedding failed: %s",
                            chapter.chapter_id,
                            meta_exc,
                        )
                        result = ChapterResult(
                            chapter_id=result.chapter_id,
                            duration_seconds=result.duration_seconds,
                            warnings=[*result.warnings, f"Metadata embedding failed: {meta_exc}"],
                            output_path=result.output_path,
                        )

                successful_chapter_ids.append(chapter.chapter_id)

        except Exception as exc:
            log.error("Chapter %r failed: %s", chapter.chapter_id, exc)
            result = ChapterResult(
                chapter_id=chapter.chapter_id,
                duration_seconds=0.0,
                warnings=[],
                output_path=None,
            )
            all_errors.append(f"Chapter {chapter.chapter_id!r}: {exc}")

        chapter_results.append(result)
        all_warnings.extend(result.warnings)

        # Update manifest after each chapter — merge new segments into existing
        # ones (keyed by normalized_hash so resume matches correctly).
        merged_segments = _merge_segments(manifest.segments, all_new_segments)
        manifest = ConversionManifest(
            epub_fingerprint=manifest.epub_fingerprint,
            config_hash=manifest.config_hash,
            chapters=chapters,
            segments=merged_segments,
            created_at=manifest.created_at,
            updated_at=_utc_now(),
        )
        write_manifest(manifest, manifest_path)

    # ------------------------------------------------------------------ #
    # M4B assembly: mux per-chapter AAC segments into one .m4b            #
    # (must run before work-dir cleanup, which removes the segments).      #
    # ------------------------------------------------------------------ #
    m4b_output_path: str | None = None
    m4b_markers: list[ChapterMarker] = []
    if settings.output_format == "m4b":
        chapter_audio: list[Path] = []
        cursor_ms = 0
        for chapter, result in zip(chapters, chapter_results, strict=True):
            if result.output_path is None:
                continue
            start_ms = cursor_ms
            end_ms = start_ms + round(result.duration_seconds * 1000)
            m4b_markers.append(
                ChapterMarker(
                    chapter_id=result.chapter_id,
                    title=chapter.title,
                    start_ms=start_ms,
                    end_ms=end_ms,
                )
            )
            chapter_audio.append(Path(result.output_path))
            cursor_ms = end_ms

        if chapter_audio:
            ffmeta_path = work_root / "chapters.ffmeta"
            write_ffmetadata_chapters(m4b_markers, book_metadata, ffmeta_path)
            m4b_path = output_dir / sanitize_book_filename(book_metadata.title, ".m4b")
            try:
                build_m4b(
                    chapter_audio=chapter_audio,
                    markers=m4b_markers,
                    metadata=book_metadata,
                    ffmeta_path=ffmeta_path,
                    output_m4b=m4b_path,
                    cover_bytes=cover_bytes,
                )
                validate_audio(
                    m4b_path,
                    expected_codec="aac",
                    expected_sample_rate=settings.sample_rate,
                    expected_chapters=len(m4b_markers),
                )
                m4b_output_path = str(m4b_path)
            except Exception as mux_exc:
                log.error("M4B assembly failed: %s", mux_exc)
                all_errors.append(f"M4B assembly failed: {mux_exc}")
                # Leave the work dir intact so --resume can retry the mux.
                successful_chapter_ids = []

        # Audio now lives inside the single .m4b; per-chapter files do not exist.
        chapter_results = [
            ChapterResult(
                chapter_id=r.chapter_id,
                duration_seconds=r.duration_seconds,
                warnings=r.warnings,
                output_path=None,
            )
            for r in chapter_results
        ]

    # ------------------------------------------------------------------ #
    # Post-run cleanup of persistent work dirs                             #
    # ------------------------------------------------------------------ #
    if not settings.keep_intermediates:
        # Only clean up chapters that fully succeeded — leave failed chapters'
        # segment WAVs in place so a subsequent --resume run can reuse them.
        for chapter_id in successful_chapter_ids:
            chapter_work = work_root / chapter_id
            if chapter_work.exists():
                shutil.rmtree(chapter_work, ignore_errors=True)

        # If all chapters succeeded, remove the work root entirely.
        if len(successful_chapter_ids) == total_chapters:
            try:
                shutil.rmtree(work_root, ignore_errors=True)
            except Exception as cleanup_exc:
                log.debug("Work root cleanup failed (non-fatal): %s", cleanup_exc)

    # ------------------------------------------------------------------ #
    # Assemble report                                                      #
    # ------------------------------------------------------------------ #
    total_duration = sum(r.duration_seconds for r in chapter_results)

    report = ConversionReport(
        book_metadata=book_metadata,
        chapter_results=chapter_results,
        total_duration_seconds=total_duration,
        warnings=all_warnings,
        errors=all_errors,
        output_path=m4b_output_path,
        chapter_markers=m4b_markers,
    )

    # Write report JSON
    report_path = output_dir / "conversion-report.json"
    from epub2audio.utils.files import atomic_write

    atomic_write(report_path, report.model_dump_json(indent=2).encode("utf-8"))

    return report


def _merge_segments(
    existing: list[TextSegment],
    new_segments: list[TextSegment],
) -> list[TextSegment]:
    """Merge *new_segments* into *existing*, deduplicating by ``normalized_hash``.

    New segments overwrite existing ones with the same hash so that updated
    ``audio_path`` and ``status`` values are reflected.  Segments present only
    in *existing* are retained to preserve resume state for future chapters.

    Args:
        existing: Segments already recorded in the manifest.
        new_segments: Segments produced in the current chapter processing run.

    Returns:
        Merged list with at most one entry per ``normalized_hash``.
    """
    by_hash: dict[str, TextSegment] = {seg.normalized_hash: seg for seg in existing}
    for seg in new_segments:
        by_hash[seg.normalized_hash] = seg
    return list(by_hash.values())


def _new_manifest(
    epub_path: Path,
    settings: Settings,
    chapters: list[Chapter],
    now: str,
) -> ConversionManifest:
    """Create a fresh :class:`ConversionManifest` for a new conversion run.

    Args:
        epub_path: Path to the source EPUB (fingerprinted).
        settings: Effective settings (hashed).
        chapters: Ordered chapter list from the plan.
        now: ISO-8601 UTC timestamp string for ``created_at`` / ``updated_at``.

    Returns:
        A new :class:`ConversionManifest` with empty segment list.
    """
    return ConversionManifest(
        epub_fingerprint=epub_fingerprint(epub_path),
        config_hash=config_hash(settings),
        chapters=chapters,
        segments=[],
        created_at=now,
        updated_at=now,
    )
