# 002 — M4B output format via an assembler strategy

**Date:** 2026-07-12  
**Status:** Accepted  
**Author:** Architect

---

## Context

The shipped pipeline produces **one MP3 file per logical chapter**
(`NNN - Title.mp3`).  `pipeline/converter._process_chapter()` runs the full
concat → normalize → encode → tag → validate cycle for each chapter, and
`audio/encode.py`, `audio/metadata.py`, and `audio/validate.py` all hardcode
MP3 (libmp3lame / ID3 / `codec_name == "mp3"`).

M4B is a different delivery model: a **single MP4/AAC container** (`.m4b`) for
the whole book, with **internal chapter markers** (timestamped metadata), a
single set of book-level tags, and one attached cover picture.  It is the
opposite of "one file per chapter": chapters become offsets inside one file,
not separate outputs.

We want to add M4B without regressing the MP3 path or breaking the
one-chapter-in-memory constraint.

---

## Decision

1. Add `output_format: Literal["mp3", "m4b"]` to `Settings` (default `"mp3"`;
   fully back-compatible). CLI exposes `--format`.

2. Keep **per-chapter synthesis, segmentation, resume, and loudness
   normalization exactly as they are today.** Only the *final assembly* forks.

3. Introduce a small assembler seam. `_process_chapter()` is refactored to
   return **chapter audio + measured duration** (not a finished MP3 in the
   M4B case). `convert_epub()` then dispatches on `output_format`:
   - `mp3` → today's behaviour (per-chapter MP3 files), unchanged.
   - `m4b` → collect all chapter audio, accumulate `(title, start_ms, end_ms)`
     offsets, then run a single mux step.

4. Chapter timestamps use the durations already computed via
   `probe_duration()`; no new timing infrastructure.

5. Native FFmpeg `aac` encoder is the baseline (always present, no new
   dependency). `libfdk_aac` is an optional quality upgrade documented but not
   required.

6. `.m4b` is muxed as MP4 (`-f mp4`) then named `.m4b`; cover embedded as an
   attached picture; book tags written once (`title`, `artist`/`album_artist`,
   `album`, `genre=Audiobook`, `date`).

---

## Consequences

- MP3 output is untouched; regression surface is the shared per-chapter code
  refactor, covered by existing e2e tests.
- `ConversionReport` for M4B has a single `output_path` plus chapter offsets,
  versus N MP3 paths. `ChapterResult.output_path` becomes `None` for the
  per-chapter entries in M4B mode (audio lives inside the single file); chapter
  offsets are recorded instead.
- Resume: the per-chapter WAV/AAC cache under `.epub2audio-work/` persists, so a
  failed final mux does **not** force re-synthesis.
- `audio/validate.py` is parameterized on expected codec and gains an M4B
  chapter-count check.

---

## Alternatives Considered

1. **A parallel `convert_m4b()` entry point** — duplicates orchestration,
   resume, and manifest logic; higher drift risk. Rejected.
2. **Post-process: build MP3s then remux to M4B** — wasteful double-encode
   (MP3 → AAC) and quality loss. Rejected.
3. **Full `AudioAssembler` Protocol with pluggable backends** — cleaner long
   term but over-engineered for two formats; the `if output_format` dispatch in
   one place is enough now. Revisit if a third format (e.g. Opus/OGG) lands.
