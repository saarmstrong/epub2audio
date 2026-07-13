# M7 — Audio Engineer Task: M4B assembly (encode, chapters, mux, validate)

**Milestone:** 7 — M4B output format  
**Agent:** Audio Engineer  
**Depends on:** M7-architect (Settings.output_format, ChapterMarker)  
**Blocks:** M7-tester, M7-reviewer

---

## Overview

Implement the M4B *final assembly* path. Per-chapter synthesis, segmentation,
resume, and loudness normalization are **unchanged** — only how finished chapter
audio is turned into a deliverable forks on `settings.output_format`.

See `docs/decisions/002-m4b-output-format.md`.

---

## Deliverables

### D1: AAC encoder — `audio/encode.py`

Add alongside `encode_mp3()`:

```python
def encode_aac(input_wav: Path, output_m4a: Path, *, bitrate: str = "64k",
               sample_rate: int = 24000) -> None:
    # ffmpeg -y -i in.wav -c:a aac -b:a <bitrate> -ar <sr> -ac 1 -f mp4 out.tmp
```

- Native `aac` (no new dependency). Atomic `.tmp` + `os.replace`, argument
  arrays only, `-f mp4` explicit. Mirror the docstring/style of `encode_mp3`.

### D2: Chapter metadata file — new `audio/chapters_meta.py`

```python
def write_ffmetadata_chapters(markers: list[ChapterMarker],
                              book: BookMetadata, out_path: Path) -> None:
    # ;FFMETADATA1 header + book tags + one [CHAPTER] block per marker
    # TIMEBASE=1/1000, START=<start_ms>, END=<end_ms>, title=<title>
```

- Escape `=`, `;`, `#`, `\`, newlines in tag/title values per FFmetadata rules.

### D3: M4B mux — new `audio/mux_m4b.py`

```python
def build_m4b(chapter_audio: list[Path], markers: list[ChapterMarker],
              metadata: BookMetadata, ffmeta_path: Path, output_m4b: Path,
              cover_bytes: bytes | None) -> None:
    # 1. concat demuxer over chapter AAC/m4a (concat list file, -c copy)
    # 2. mux: ffmpeg -i concat.m4a -i ffmeta.txt -map_metadata 1
    #         [-i cover.jpg -map 0:a -map 2:v -disposition:v attached_pic]
    #         -c copy -f mp4 out.tmp  → rename .m4b
```

- Atomic write; temp files cleaned in `finally`. No `shell=True`.

### D4: Validation — `audio/validate.py`

- Parameterize expected codec: `validate_audio(path, *, expected_codec, expected_sample_rate)`
  (keep `validate_mp3` as a thin wrapper for back-compat).
- For M4B add checks: container parses, exactly one AAC audio stream, positive
  duration, and **chapter count == len(markers)** (parse `-show_chapters`).

### D5: Orchestration — `pipeline/converter.py`

- Refactor `_process_chapter()` so it returns the **chapter audio path + measured
  duration** (do not encode to MP3 when `output_format == "m4b"`; encode AAC or
  keep the normalized WAV for the concat step).
- In `convert_epub()`, after the chapter loop, dispatch:
  - `mp3`: current behaviour (per-chapter MP3 + per-file `embed_metadata`).
  - `m4b`: accumulate `ChapterMarker` offsets from durations, call
    `write_ffmetadata_chapters` → `build_m4b` → `validate_audio` once; set the
    report's single `output_path` + `chapter_markers`.
- Keep the `.epub2audio-work/` cache so a failed mux does not re-synthesize.
- Output filename: `sanitize_filename(book.title)` + `.m4b`.

---

## Files to Modify / Add

- `src/epub2audio/audio/encode.py` (add `encode_aac`)
- `src/epub2audio/audio/chapters_meta.py` (new)
- `src/epub2audio/audio/mux_m4b.py` (new)
- `src/epub2audio/audio/metadata.py` (MP4 book-level tag path if not fully handled by mux)
- `src/epub2audio/audio/validate.py` (parameterize codec + chapter check)
- `src/epub2audio/pipeline/converter.py` (assembly dispatch)

---

## Constraints (project rules)

- No `epub/` imports inside `audio/`. No `shell=True`. All FFmpeg via
  `utils/subprocess.run_command` argument arrays. Atomic writes everywhere.
- No narration/body text in logs (chapter IDs, titles, offsets, word counts only).
- MP3 path must remain byte-for-byte behaviourally unchanged.

---

## Exit Criteria

- [ ] `encode_aac`, `write_ffmetadata_chapters`, `build_m4b`, `validate_audio` implemented
- [ ] `convert --format m4b` produces a single `.m4b` with correct chapters + cover
- [ ] MP3 path unchanged; existing e2e tests still pass
- [ ] Resume reuses per-chapter cache across a failed mux
- [ ] `uv run mypy src/epub2audio` passes (strict); `ruff check`/`format` clean
