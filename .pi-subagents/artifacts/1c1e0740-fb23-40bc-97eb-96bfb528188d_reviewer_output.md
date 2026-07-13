All gates green, nothing staged. Here is my Milestone 2 review summary.

## Milestone 2 Review Summary

**Fixes applied (I had edit access):**
1. **Issue 1 — `duration_seconds` always 0.0 (blocker):** Added `probe_duration()` to `audio/validate.py` (ffprobe `-show_format -show_streams`, parses container/stream duration, defensive float conversion) and wired it into `_process_chapter` in `pipeline/converter.py` after `validate_mp3`. Probe failures degrade to `0.0` + a warning. Since metadata embedding uses `-c copy` (duration-preserving), probing before embedding is correct. FakeTTS emits 150 ms/word of silence, so `test_convert_epub_chapter_duration_positive` will pass under FFmpeg.

**Investigated, no fix needed:**
2. **encode.py mock path:** `encode.py` uses `from epub2audio.utils.subprocess import run_command` → the test patch `epub2audio.audio.encode.run_command` resolves. `test_encode.py` passes (mocked).
3. **mypy 3.11→3.12:** documented inline; `requires-python >=3.11` and ruff `target-version = py311` still enforce 3.11 syntax; no 3.12-only syntax in `src/`. Masks nothing.
4. **5 skipped e2e tests:** structurally correct, skip cleanly; all ffmpeg/ffprobe call sites use argument arrays. **Conditional approval** — FFmpeg validation deferred to CI.
5. **cover `.jpg` temp extension:** cosmetic, acceptable (FFmpeg sniffs bytes).

**New defect filed:** `DEFECT-003` — segment-level resume is inert (manifest `segments` never populated; segment WAVs live in an OS temp dir deleted at run end). Manifest write/fingerprint/config-hash all work; only the segment-skip cache is unreachable. Deferred to M4 (where the resume acceptance criterion lives).

**Security/boundary:** no `shell=True`; all subprocess via `utils/subprocess.py`; no `kokoro` PyPI imports (cli imports the project's own adapter from `tts/kokoro.py`); no `epub/` imports in `tts/`/`audio/`; no book body text in logs.

**MILESTONE 2 SIGN-OFF: APPROVED** (conditional on CI running the FFmpeg-backed integration suite before release).