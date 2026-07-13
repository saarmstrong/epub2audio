# M2 — Tester Task Contract

**Milestone:** 2 — Fake-TTS Audiobook Pipeline
**Agent:** Tester
**Date opened:** 2026-07-12
**Depends on:** M1 complete ✅; implementations from TTS Engineer and Audio Engineer
(tests may be written and import-checked before implementations are complete, but
full execution awaits the other agents).

---

## Scope

Tasks: M2-20, plus unit tests for `text/` and `audio/` modules.

---

## M2-20 — Write `tests/test_e2e.py`: end-to-end test

Full pipeline test using `FakeTTSEngine` — no Kokoro required.

**The test must:**
1. Open `tests/fixtures/simple_epub3.epub`.
2. Call `convert_epub(epub_path, tmp_path, settings, FakeTTSEngine())`.
3. Assert the output directory contains **exactly 2 MP3 files**.
4. Assert MP3 filenames are in the correct format:
   - `001 - Chapter One.mp3`
   - `002 - Chapter Two.mp3`
5. Assert each MP3 passes `validate_mp3`.
6. Assert the `ConversionReport` has 2 `ChapterResult` entries with `output_path` set.

**Test structure:**
- Use `pytest.fixture` with `tmp_path` for the output directory.
- Mark as `@pytest.mark.integration` (requires FFmpeg).
- Skip automatically if FFmpeg is not found:
  ```python
  ffmpeg = shutil.which("ffmpeg")
  if ffmpeg is None:
      pytest.skip("FFmpeg not available")
  ```

**Acceptance:** `uv run pytest tests/test_e2e.py -v -m integration` passes when
FFmpeg is available.

---

## Unit tests for `text/` modules

### `tests/text/test_normalize.py`

Test `normalize_text` from `text/normalize.py`.

**Required tests:**
- Curly double quotes (`"` / `"`) are replaced with straight double quotes (`"`).
- Curly single quotes (`'` / `'`) are replaced with straight single quotes (`'`).
- Em-dash surrounded by spaces (` — `) is replaced with ` - `.
- Em-dash without spaces (`—`) is replaced with ` - `.
- Ellipsis character (`…`) is replaced with `...`.
- Non-breaking space (`\u00a0`) is replaced with regular space.
- Ligature `ﬁ` is replaced with `fi`.
- Ligature `ﬂ` is replaced with `fl`.
- **No alteration:** integer numbers (e.g., `42`) are unchanged.
- **No alteration:** decimal numbers (e.g., `3.14`) are unchanged.
- **No alteration:** initials (e.g., `J. R. R. Tolkien`) are unchanged.
- **No alteration:** abbreviations (e.g., `Dr.`, `Mr.`, `etc.`) are unchanged.

### `tests/text/test_segment.py`

Test `segment_text` from `text/segment.py`.

**Required tests:**
- Paragraph boundaries split text into separate segments.
- Sentence boundaries split long paragraphs at sentence ends.
- Hard character limit splits text that exceeds `max_chars`.
- **Never split mid-word** (no segment ends in the middle of a word).
- **Never split inside a decimal number** (e.g., `3.14` stays together).
- **Never split inside common abbreviations** (`Dr.`, `Mr.`, `Mrs.`, `Ms.`, `Prof.`,
  `St.`, `vs.`, `etc.`).
- **Never split between initials** (e.g., `J. R. R. Tolkien` stays together).
- `TextSegment.source_hash` is deterministic: same text → same hash.
- `TextSegment.normalized_hash` is deterministic: same normalized text → same hash.
- `TextSegment.status` defaults to `"pending"`.
- `TextSegment.audio_path` defaults to `None`.

---

## Unit tests for `audio/` and `pipeline/` modules

### `tests/audio/test_encode.py`

Test `encode_mp3` from `audio/encode.py`.

**Required tests:**
- `encode_mp3` calls `run_command` with an argument list (not a shell string).
- The FFmpeg invocation never uses `shell=True`.
- Atomic write: if encoding fails, the output `.mp3` file is not left as a partial file
  (mock `run_command` to raise `CalledProcessError` and assert output does not exist).
- The FFmpeg argument list contains the correct bitrate flag (e.g., `-b:a 96k`).
- The FFmpeg argument list contains the correct sample rate flag (e.g., `-ar 24000`).

Use `unittest.mock.patch` to mock `run_command` so no real FFmpeg is required.

### `tests/pipeline/test_manifest.py`

Test manifest round-trip and fingerprinting from `pipeline/manifest.py`.

**Required tests:**
- `write_manifest` → `read_manifest` round-trip: the deserialized object equals
  the original `ConversionManifest`.
- `epub_fingerprint` returns a hex string of exactly 64 characters (SHA-256).
- `epub_fingerprint` returns the same value for the same file on repeated calls.
- `epub_fingerprint` returns different values for different files.
- `config_hash` returns a hex string of exactly 64 characters.
- Changing any synthesis-relevant config field (e.g., `voice`, `speed`, `bitrate`)
  changes the `config_hash`.
- `write_manifest` writes atomically (file is complete or absent, never partial).

---

## Dependency Note

The Tester should write all test files and ensure they parse and import cleanly
(mypy + ruff). If implementations are still stubs when you run them:
- Write the tests against the expected public API.
- Use `pytest.importorskip` or a `try/except ImportError` to skip gracefully
  if a module is still a stub.
- Note clearly in a `# TODO(pending-impl)` comment which tests need live
  implementations to pass.

Do NOT suppress test failures by wrapping in blanket try/except. Use pytest's
skip mechanism.

---

## Done Criteria

All of the following must be true before this contract is moved to `tasks/completed/`:

- [ ] `tests/test_e2e.py` written.
- [ ] `tests/text/test_normalize.py` written.
- [ ] `tests/text/test_segment.py` written.
- [ ] `tests/audio/test_encode.py` written.
- [ ] `tests/pipeline/test_manifest.py` written.
- [ ] All 5 test files pass `uv run mypy tests/` (0 errors).
- [ ] All 5 test files pass `uv run ruff check tests/` (0 issues).
- [ ] `uv run ruff format --check tests/` passes.
- [ ] `uv run pytest tests/ -v` passes with ≥ 35 existing tests, 0 failures.
- [ ] New tests pass if implementations are available, or are cleanly skipped/noted
      as pending if not.

---

## Files to Create

| File | Action |
|---|---|
| `tests/test_e2e.py` | Create |
| `tests/text/__init__.py` | Create (empty, if not present) |
| `tests/text/test_normalize.py` | Create |
| `tests/text/test_segment.py` | Create |
| `tests/audio/__init__.py` | Create (empty, if not present) |
| `tests/audio/test_encode.py` | Create |
| `tests/pipeline/__init__.py` | Create (empty, if not present) |
| `tests/pipeline/test_manifest.py` | Create |

Do NOT modify any existing tests. Do NOT implement feature code.
