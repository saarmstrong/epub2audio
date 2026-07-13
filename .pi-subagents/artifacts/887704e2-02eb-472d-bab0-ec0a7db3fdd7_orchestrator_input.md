# Task for orchestrator

You are the Orchestrator for epub2audio. Begin Milestone 2 — Fake-TTS Audiobook Pipeline.

## Current state

- Milestone 1 is ✅ Complete (reviewer-approved 2026-07-12).
- 35 tests passing, all M1 modules implemented and clean.
- `tasks/active/` contains only `DEFECT-002-chapter-word-count-zero-for-long-docs.md` (deferred to M2, assigned to EPUB Engineer but will be resolved by the TTS Engineer since they are extending `epub/cleanup.py` and `epub/chapters.py` in M2-01).
- All M2 source files are still stubs under `src/epub2audio/text/`, `src/epub2audio/tts/`, `src/epub2audio/audio/`, `src/epub2audio/pipeline/`.

## What you must do

Create three task contract files in `tasks/active/` — one per agent. Then update `docs/status.md`.

Do NOT write feature code. Your job is task contracts only.

---

## Agent assignments for M2

### TTS Engineer → `tasks/active/M2-tts-engineer.md`

Tasks: DEFECT-002, M2-01 through M2-06.

**DEFECT-002 — Fix `Chapter.word_count` (epub/chapters.py)**
- Root cause: `select_chapters` calls `_extract_word_count_from_signals`, which returns 0 for chapters ≥ 200 words because the `short_document` signal only fires for short docs.
- Fix: in `score_candidates`, compute the true word count via `word_count(xhtml_to_text(content))` from `epub/cleanup.py` for every candidate (not only short ones). Store it on the candidate so `select_chapters` can assign it to `Chapter.word_count` directly.
- Acceptance: `uv run epub2audio inspect tests/fixtures/simple_epub3.epub --json` shows non-zero `word_count` for both chapters.
- Note: TTS Engineer is assigned this because they are extending `epub/cleanup.py` in M2-01; fixing the word count is a natural companion task.

**M2-01 — Extend `epub/cleanup.py`: full HTML → narration text**
- Add full cleanup: strip `<script>`, `<style>`, `<nav>`, footnote links (`<a epub:type="noteref">`), and decorative images (`<img>` with no alt or alt="").
- Convert `<li>` items to `• item` lines.
- Convert `<br>` to newlines.
- Preserve paragraph structure (each `<p>` → separate paragraph, separated by blank line).
- Handle `<table>` by extracting cell text in row order, cells joined with " | ".
- Image alt text: if `<img alt="...">` has meaningful alt text (non-empty, non-whitespace, not "image"), prepend `[Image: alt text]` to the paragraph.
- Footnote content (`<aside epub:type="footnote">`): skip entirely for Milestone 2; full handling deferred to M5.
- The existing `xhtml_to_text(content: bytes) -> str` and `word_count(text: str) -> int` signatures must be preserved.
- Acceptance: `uv run mypy src/epub2audio/epub/cleanup.py` → 0 errors.

**M2-02 — Write `text/normalize.py`**
- Conservative unicode/punctuation normalization. Preserve narration intent; do not alter meaning.
- Normalize: curly quotes → straight (`"` / `"` → `"`; `'` / `'` → `'`), em-dashes (` — ` or `—`) → ` - `, ellipsis `…` → `...`, non-breaking space → regular space, ligatures (ﬁ → fi, ﬂ → fl).
- Do NOT alter: numbers, proper nouns, abbreviations, initials, decimal points.
- Public API: `def normalize_text(text: str) -> str`
- Acceptance: `uv run mypy src/epub2audio/text/normalize.py` → 0 errors.

**M2-03 — Write `text/segment.py`**
- Segment chapter text into `TextSegment` objects for TTS calls.
- Priority order: section boundary → paragraph boundary → sentence boundary → clause boundary → hard character limit (configurable, default 500 chars).
- Never split: mid-word, between opening quote and first word, inside decimal number (`3.14`), inside common abbreviations (`Dr.`, `Mr.`, `Mrs.`, `Ms.`, `Prof.`, `St.`, `vs.`, `etc.`), between initials (`J. R. R.`).
- Public API:
  ```python
  def segment_text(text: str, max_chars: int = 500) -> list[TextSegment]
  ```
  where each `TextSegment` has:
  - `text`: the segment string
  - `source_hash`: `hashlib.sha256(text.encode()).hexdigest()`
  - `normalized_hash`: `hashlib.sha256(normalize_text(text).encode()).hexdigest()`
  - `word_count`: `len(text.split())`
  - `status`: `"pending"`
  - `audio_path`: `None`
- Acceptance: `uv run mypy src/epub2audio/text/segment.py` → 0 errors.

**M2-04 — Write `text/pauses.py`**
- Silence insertion specifications between segments.
- Public API:
  ```python
  class PauseSpec(BaseModel):
      duration_ms: int
      reason: str

  def get_pause(before: TextSegment, after: TextSegment) -> PauseSpec | None:
      """Return a pause to insert between two segments, or None."""
  ```
- Rules: paragraph boundary → 600 ms; sentence boundary → 300 ms; clause boundary → 150 ms; no pause between continuation segments. Detect boundary type from trailing punctuation and whitespace in `before.text`.
- Acceptance: `uv run mypy src/epub2audio/text/pauses.py` → 0 errors.

**M2-05 — Write `tts/base.py`: TTSEngine Protocol**
- Implement the canonical Protocol from `docs/architecture.md`:
  ```python
  class TTSEngine(Protocol):
      def synthesize(self, text: str, *, voice: str, language: str, speed: float) -> list[AudioChunk]: ...
  ```
- Import `AudioChunk` from `epub2audio.models`. Import `Protocol` from `typing`.
- Add `runtime_checkable` decorator.
- Acceptance: `uv run mypy src/epub2audio/tts/base.py` → 0 errors.

**M2-06 — Write `tts/fake.py`: FakeTTSEngine**
- Deterministic fake TTS for tests: same input always produces same output.
- Generate a silent WAV (numpy zeros array) of `len(text.split()) * 150` milliseconds at 24000 Hz, mono, float32.
- Public API:
  ```python
  class FakeTTSEngine:
      def synthesize(self, text: str, *, voice: str, language: str, speed: float) -> list[AudioChunk]:
          """Return a single AudioChunk of deterministic silence proportional to word count."""
  ```
- Must satisfy `isinstance(FakeTTSEngine(), TTSEngine)` (i.e. implement the Protocol).
- Must be in `tts/fake.py`, not `tts/kokoro.py`.
- No `kokoro` imports anywhere in this file.
- Acceptance: `uv run mypy src/epub2audio/tts/fake.py` → 0 errors.

**Done criteria for TTS Engineer contract:**
- DEFECT-002 closed (word_count non-zero in inspect JSON)
- All 6 modules pass mypy strict
- All 6 modules pass ruff
- `uv run pytest tests/ -v` continues to pass (no regressions)
- Task moved to `tasks/completed/`

---

### Audio Engineer → `tasks/active/M2-audio-engineer.md`

Tasks: M2-07 through M2-19.

**M2-07 — Write `audio/chunks.py`**
- Helpers for `AudioChunk`: save to WAV file, load from WAV file, concatenate list of chunks.
- Public API:
  ```python
  def save_chunk(chunk: AudioChunk, path: Path) -> None
  def load_chunk(path: Path) -> AudioChunk
  def concat_chunks(chunks: list[AudioChunk]) -> AudioChunk
  ```
- Use `soundfile` for WAV I/O. numpy for concatenation.
- Acceptance: `uv run mypy src/epub2audio/audio/chunks.py` → 0 errors.

**M2-08 — Write `audio/concatenate.py`**
- Concatenate a list of WAV file paths into a single WAV file (lossless, no encoding yet).
- Public API:
  ```python
  def concatenate_wavs(input_paths: list[Path], output_path: Path) -> None
  ```
- Use `soundfile` to read and write. Validate all inputs share the same sample rate and channel count; raise `InvalidEpubError` (reuse from errors) or a new `AudioError` if mismatched.
- Write atomically: write to `.tmp` first, then `os.replace()`.
- Acceptance: `uv run mypy src/epub2audio/audio/concatenate.py` → 0 errors.

**M2-09 — Write `audio/encode.py`**
- FFmpeg MP3 encoding from a WAV file.
- Public API:
  ```python
  def encode_mp3(
      input_wav: Path,
      output_mp3: Path,
      *,
      bitrate: str = "96k",
      sample_rate: int = 24000,
  ) -> None
  ```
- Use `utils/subprocess.py` (safe runner). Build FFmpeg arg array — NEVER shell=True.
- Write atomically.
- Acceptance: `uv run mypy src/epub2audio/audio/encode.py` → 0 errors.

**M2-10 — Write `audio/normalize.py`**
- FFmpeg two-pass loudness normalization (EBU R128).
- Public API:
  ```python
  def normalize_loudness(
      input_wav: Path,
      output_wav: Path,
      *,
      target_lufs: float = -18.0,
      true_peak: float = -2.0,
      lra: float = 7.0,
  ) -> None
  ```
- Pass 1: run `ffmpeg -i input -af loudnorm=... -f null -` to get measured values (parse JSON from stderr).
- Pass 2: run `ffmpeg -i input -af loudnorm=...:<measured values> output_wav`.
- Write atomically.
- Acceptance: `uv run mypy src/epub2audio/audio/normalize.py` → 0 errors.

**M2-11 — Write `audio/metadata.py`**
- Embed ID3 tags and cover art into an MP3 using FFmpeg.
- Public API:
  ```python
  def embed_metadata(
      mp3_path: Path,
      metadata: BookMetadata,
      track_number: int,
      total_tracks: int,
      chapter_title: str,
      cover_bytes: bytes | None = None,
  ) -> None
  ```
- Tags to embed: title (chapter_title), album (book title), artist, album_artist, track (`N/total`), genre (`Audiobook`), date, comment (`Generated by epub2audio`).
- Cover art: if `cover_bytes` provided, pass as `-i cover_input -map 0 -map 1 -c copy`.
- Write to temp file then `os.replace()` atomically.
- Acceptance: `uv run mypy src/epub2audio/audio/metadata.py` → 0 errors.

**M2-12 — Write `audio/validate.py`**
- FFprobe validation of final MP3.
- Public API:
  ```python
  def validate_mp3(path: Path, *, expected_sample_rate: int = 24000) -> None
  ```
  Raises `Epub2AudioError` with a descriptive message if any check fails.
- Checks: file exists, size > 0, FFprobe parses without error, audio stream present, codec is `mp3`, duration > 0, sample rate matches, channel count == 1.
- Acceptance: `uv run mypy src/epub2audio/audio/validate.py` → 0 errors.

**M2-13 — Write `utils/subprocess.py`**
- Safe subprocess runner — arg arrays only, never shell strings.
- Public API:
  ```python
  def run_command(args: list[str], *, input_data: bytes | None = None, timeout: float | None = None) -> tuple[bytes, bytes]:
      """Run a subprocess. Returns (stdout, stderr). Raises MissingDependencyError if the executable is not found, subprocess.CalledProcessError on non-zero exit."""
  ```
- Wrap `subprocess.run(..., capture_output=True, check=True)`. Convert `FileNotFoundError` to `MissingDependencyError(args[0])`.
- Acceptance: `uv run mypy src/epub2audio/utils/subprocess.py` → 0 errors.

**M2-14 — Write `utils/files.py`**
- Safe temp files, atomic replace, disk space check.
- Public API:
  ```python
  def atomic_write(dest: Path, content: bytes) -> None
  def temp_path(suffix: str = "") -> Path
  def check_disk_space(path: Path, required_bytes: int) -> None
  ```
  `atomic_write`: write to `dest.with_suffix(dest.suffix + ".tmp")`, then `os.replace()`.
  `temp_path`: return `Path(tempfile.mkstemp(suffix=suffix)[1])`.
  `check_disk_space`: use `shutil.disk_usage`; raise `Epub2AudioError` if free < required.
- Acceptance: `uv run mypy src/epub2audio/utils/files.py` → 0 errors.

**M2-15 — Write `pipeline/planner.py`**
- Build a `ConversionPlan` from a parsed EPUB + config.
- Public API:
  ```python
  def plan_conversion(book: ebooklib.epub.EpubBook, settings: Settings) -> ConversionPlan
  ```
  Uses `extract_metadata`, `extract_navigation`, `score_candidates`, `select_chapters`, `extract_cover` from `epub/`. Returns a `ConversionPlan` with `book_metadata`, `chapters` (in spine order), and `config_snapshot = settings.model_dump()`.
- Acceptance: `uv run mypy src/epub2audio/pipeline/planner.py` → 0 errors.

**M2-16 — Write `pipeline/manifest.py`**
- Atomic write/read of `ConversionManifest`.
- Public API:
  ```python
  def write_manifest(manifest: ConversionManifest, path: Path) -> None
  def read_manifest(path: Path) -> ConversionManifest
  def epub_fingerprint(epub_path: Path) -> str
  def config_hash(settings: Settings) -> str
  ```
  `write_manifest`: serialise with `model.model_dump_json()`, write atomically via `utils/files.py`.
  `read_manifest`: parse with `ConversionManifest.model_validate_json(path.read_text())`.
  `epub_fingerprint`: SHA-256 of the EPUB file bytes (hex).
  `config_hash`: SHA-256 of the JSON-serialised settings (hex).
- Acceptance: `uv run mypy src/epub2audio/pipeline/manifest.py` → 0 errors.

**M2-17 — Write `pipeline/resume.py`**
- Fingerprint check and segment-skip logic.
- Public API:
  ```python
  def check_resume(
      manifest: ConversionManifest,
      epub_path: Path,
      settings: Settings,
  ) -> list[str]:
      """Return a list of changed_keys if config hash changed. Raises FingerprintMismatchError if EPUB changed."""

  def segment_needs_synthesis(segment: TextSegment, output_dir: Path) -> bool:
      """Return True if the segment's audio_path is missing or its WAV fails basic validation."""
  ```
- Acceptance: `uv run mypy src/epub2audio/pipeline/resume.py` → 0 errors.

**M2-18 — Write `pipeline/converter.py`**
- Full pipeline orchestration. This is the central piece of M2.
- Public API:
  ```python
  def convert_epub(
      epub_path: Path,
      output_dir: Path,
      settings: Settings,
      tts_engine: TTSEngine,
  ) -> ConversionReport
  ```
- Algorithm per chapter:
  1. `xhtml_to_text` + `normalize_text` + `segment_text` → `list[TextSegment]`
  2. Check resume; skip segments whose WAV already exists and matches hash.
  3. For each segment: `tts_engine.synthesize(...)` → `list[AudioChunk]`, `concat_chunks`, `save_chunk` to temp WAV.
  4. `concatenate_wavs` → chapter WAV.
  5. `normalize_loudness` → normalized WAV.
  6. `encode_mp3` → chapter MP3.
  7. `embed_metadata` (chapter title, track N/total, cover bytes).
  8. `validate_mp3` → raises on failure.
  9. Record `ChapterResult` (duration, output_path, warnings).
  10. Clean intermediate WAV files after MP3 validated.
- Write manifest before synthesis begins; update after each chapter.
- Writes output to: `output_dir / sanitize_filename(chapter.title, i)` (using `utils/names.py`).
- Returns `ConversionReport`.
- Import `TTSEngine` from `tts/base.py` — do NOT import `KokoroTTSEngine` or `FakeTTSEngine` here.
- Acceptance: `uv run mypy src/epub2audio/pipeline/converter.py` → 0 errors.

**M2-19 — Extend `cli.py`: add `convert` command**
- Add a `convert` command to the existing Typer app. Do NOT remove or break `inspect`.
- Signature matches `docs/product-spec.md` convert options (voice, language, speed, bitrate, sample-rate, normalize, resume, overwrite, dry-run, workers, config, verbose, quiet, chapter-start, chapter-end).
- Default behaviour: open EPUB, plan conversion, print summary, call `convert_epub` with `FakeTTSEngine` if no Kokoro available (detect with `try: import kokoro` — use Kokoro if available, FakeTTS otherwise), write MP3s to output dir, print completion summary.
- `epub2audio BOOK.epub` must work as an alias for `convert`.
- Error handling: `InvalidEpubError` / `DrmProtectedEpubError` / `FileNotFoundError` → stderr + exit 1; `MissingDependencyError` → stderr + friendly install hint + exit 1.
- Acceptance: `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` still works (no regression). `uv run epub2audio convert --help` shows all flags.

**Done criteria for Audio Engineer contract:**
- All 13 modules pass mypy strict
- All 13 modules pass ruff
- `convert --help` works
- `inspect` still works (no regression)
- `uv run pytest tests/ -v` continues to pass (no regressions in existing 35 tests)
- Task moved to `tasks/completed/`

---

### Tester → `tasks/active/M2-tester.md`

Tasks: M2-20, plus unit tests for text/ and audio/ modules.

**M2-20 — Write `tests/test_e2e.py`: end-to-end test**
- Full pipeline test using `FakeTTSEngine` — no Kokoro required.
- The test must:
  1. Open `tests/fixtures/simple_epub3.epub`.
  2. Run `convert_epub(epub_path, tmp_path, settings, FakeTTSEngine())`.
  3. Assert output directory contains exactly 2 MP3 files.
  4. Assert MP3 filenames are in the correct format (`001 - Chapter One.mp3`, `002 - Chapter Two.mp3`).
  5. Assert each MP3 passes `validate_mp3`.
  6. Assert the `ConversionReport` has 2 `ChapterResult` entries with `output_path` set.
- Use `pytest.fixture` with `tmp_path` for output dir.
- Mark as `@pytest.mark.integration` (requires FFmpeg; skip automatically if FFmpeg not found using `pytest.importorskip` pattern or `shutil.which`).
- Acceptance: `uv run pytest tests/test_e2e.py -v -m integration` passes when FFmpeg is available.

**Unit tests for text/ modules:**
- `tests/text/test_normalize.py`: test curly quotes, em-dash, ellipsis, NBSP, ligature normalization. Test that numbers, initials, abbreviations are NOT altered.
- `tests/text/test_segment.py`: test paragraph boundary splitting, sentence splitting, hard-limit splitting. Test the "never split" rules (mid-word, decimal, abbreviation, initials). Test that `TextSegment` hash fields are deterministic.

**Unit tests for audio/ modules:**
- `tests/audio/test_encode.py`: test that `encode_mp3` calls FFmpeg with an argument array (mock `run_command`); test that no `shell=True` is used; test atomic write behaviour.
- `tests/pipeline/test_manifest.py`: test round-trip serialization of `ConversionManifest`; test that `epub_fingerprint` returns a hex string; test that changing any synthesis-relevant config field changes `config_hash`.

**Dependency note:** The Tester should write test files and stub them if the implementations are not yet present. If `FakeTTSEngine` and the audio modules are complete when tests are run, run the full suite. If implementations are still stubs, write and import-check the tests but note that full execution awaits the other agents.

**Done criteria for Tester contract:**
- `tests/test_e2e.py` written
- `tests/text/test_normalize.py` and `tests/text/test_segment.py` written
- `tests/audio/test_encode.py` and `tests/pipeline/test_manifest.py` written
- All test files pass mypy and ruff
- `uv run pytest tests/ -v` still passes existing 35 tests (no regressions)
- New tests pass if implementations are available, or are cleanly noted as pending if not
- Task moved to `tasks/completed/`

---

## After creating the three contracts

1. Move `tasks/active/DEFECT-002-chapter-word-count-zero-for-long-docs.md` to `tasks/completed/DEFECT-002-...md` — it is now assigned and tracked within `M2-tts-engineer.md`.
2. Update `docs/status.md`: Milestone 2 is now In Progress; list the three active task contracts.
3. Do NOT write any feature code.

## Acceptance Contract
Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```