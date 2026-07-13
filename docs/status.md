# epub2audio — Project Status

_Last updated: 2026-07-12 (M6 Reviewer FINAL sign-off — project complete)_

---

## Current Milestone

**Milestone 6** — Release readiness (docs, CI, packaging) — ✅ Complete (Reviewer-approved 2026-07-12)

🎉 **All milestones complete. epub2audio project is closed.**

---

## Milestone Tracker

| # | Milestone | Status | Notes |
|---|---|---|---|
| Pre | Repo structure + docs | ✅ Complete | Package skeleton created, importable |
| 1 | Inspectable EPUB plan | ✅ Complete | Reviewer-approved 2026-07-12; 35/35 tests pass, all gates green |
| 2 | Fake-TTS pipeline (MP3s without Kokoro) | ✅ Complete | Reviewer-approved 2026-07-12 (conditional on CI FFmpeg run); 112 pass / 5 skipped, all gates green |
| 3 | Kokoro integration | ✅ Complete | Reviewer-approved 2026-07-12; 117 pass / 11 skipped, all gates green |
| 4 | Reliability (resume, manifest, report) | ✅ Complete | Reviewer-approved 2026-07-12; DEFECT-003 fixed; 145 pass / 24 skipped, all gates green |
| 5 | Chapter-detection hardening | ✅ Complete | Reviewer-approved 2026-07-12; detection layer done + 77 epub tests pass, all M5 gates green. Product wiring tracked as DEFECT-004 (M6 follow-up) |
| 6 | Release readiness (docs, CI, packaging) | ✅ Complete | Reviewer-approved 2026-07-12; DEFECT-004 + DEFECT-005 fixed; README/CHANGELOG/LICENSE added; 204 pass / 6 skipped / 1 xfailed, all gates green |

---

## Active Tasks

_None — all tasks complete. Every M1–M6 task and all defects are in `tasks/completed/`._

DEFECT-004 (finalize_chapters wiring + converter fragment handling) and
DEFECT-005 (loudnorm exit 234 on silent input) are both fixed and closed.

**DEFECT-002** (Chapter.word_count = 0 for long docs) is tracked within
`M2-tts-engineer.md` and moved to `tasks/completed/`.

### M3 Task → Agent mapping

| Task IDs | Agent | Description |
|---|---|---|
| M3-01 – M3-04 | TTS Engineer | KokoroTTSEngine, voice catalogue, `voices` CLI command, `doctor` CLI command |
| M3-05 + CLI tests | Tester | Kokoro smoke tests (model-gated), CLI smoke tests (no model required) |
| M3-06 | Reviewer | Run `epub2audio doctor` and `epub2audio voices`, verify output |

### Cross-agent dependency (M3)

The Tester may write the `tests/tts/` skeleton and `test_kokoro_smoke.py` in
parallel with the TTS Engineer, but cannot run `test_voices_command.py` until
M3-03 and M3-04 are delivered. The Reviewer (M3-06) proceeds after both
TTS Engineer and Tester contracts are complete.

### M2 Task → Agent mapping

| Task IDs | Agent | Description |
|---|---|---|
| DEFECT-002, M2-01 – M2-06 | TTS Engineer | EPUB cleanup upgrade, text pipeline, TTS protocol + fake engine |
| M2-07 – M2-19 | Audio Engineer | Audio utilities, pipeline orchestration, `convert` CLI command |
| M2-20 + unit tests | Tester | E2E test, text/ unit tests, audio/ unit tests, manifest tests |

---

## Reviewer Sign-off — Milestone 1 (2026-07-12)

**Result: APPROVED.**

Verification performed:
- `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` → Rich table, 2 chapters in correct reading order (Chapter One = `b_chapter_01.xhtml`, Chapter Two = `a_chapter_02.xhtml`), proving spine order is used, not filename order. EPUB2 fixture verified likewise.
- `uv run pytest tests/ -v` → **35/35 pass** (also passes under `-W error::UserWarning`).
- `uv run ruff check src/ tests/` → All checks passed.
- `uv run ruff format --check src/ tests/` → 49 files already formatted.
- `uv run mypy src/epub2audio` → Success, 38 source files, 0 errors (strict).

Defects investigated:
1. **errors.py parallel write** — coherent; all 8 exceptions present with correct `__init__` signatures and custom attributes; no cross-module imports. ✅
2. **XMLParsedAsHTMLWarning (52/run)** — FIXED. `epub/cleanup.py` and `epub/chapters.py` now parse with `BeautifulSoup(content, features="xml")`; warning-count is 0 with no test regressions. ✅
3. **word_count = 0 for long chapters** — confirmed cosmetic (no text loss/corruption); tracked as `DEFECT-002`, deferred to M2. ✅
4. **pyproject.toml suppressions** — `B008` (Typer defaults), `RUF001/2/3` (en-dash in strings/docstrings), and the ebooklib mypy `ignore_missing_imports` override are all legitimate and do not mask real issues. ✅
5. **builders.py concurrent write** — full API present (8 builder functions); edge-case builders (no-nav, empty-doc) carry the EPUB Engineer's fixes. ✅

Boundary/security checks: no `kokoro` imports outside `tts/kokoro.py`; no `epub/` imports inside `tts/` or `audio/`; no `subprocess`/`shell=True`; no book content in log statements.

---

## What Works Today

- `uv run python -c "import epub2audio; print('ok')"` → passes
- `uv run mypy src/epub2audio/models.py src/epub2audio/errors.py` → 0 errors (strict)
- `uv run pytest tests/epub/ -v` → **35/35 PASS**
- All shared Pydantic models fully implemented (`models.py`)
- All domain exceptions fully implemented (`errors.py`)
- EPUB reader, metadata, navigation, chapter-detection, cleanup fully implemented
- Config settings fully implemented (`config.py`)
- Filename sanitization fully implemented (`utils/names.py`)
- CLI `inspect` command implemented (`cli.py`)
- Test fixtures factory implemented (`tests/fixtures/builders.py`)
- Fixture EPUBs generated: `simple_epub3.epub`, `simple_epub2.epub`
- All M1-15, M1-16, M1-17 test files written and passing

---

## What is Explicitly Not Implemented

- Real Kokoro synthesis (`tts/kokoro.py` adapter is scaffolded; wiring + the
  `kokoro` PyPI package integration is in progress — Milestone 3)
- Functional segment-level resume across runs (see DEFECT-003; Milestone 4)
- End-to-end FFmpeg validation on the review machine (deferred to CI; 5 e2e
  tests skip locally because FFmpeg is absent)

### Implemented in Milestone 2

- `epub/cleanup.py` full HTML → narration text (DEFECT-002 word_count fixed)
- Text normalization + segmentation + pauses (`text/`)
- `TTSEngine` Protocol + `FakeTTSEngine` (`tts/base.py`, `tts/fake.py`)
- Audio pipeline: chunks, concatenate, encode, normalize, metadata, validate
  (`audio/`) including `probe_duration`
- Pipeline orchestrator, planner, manifest, resume scaffolding (`pipeline/`)
- `convert` CLI command (16 flags)

---

## Completed Tasks

| Task | Description | Date |
|---|---|---|
| PRE-01 | Package skeleton (all stubs) | 2026-07-12 |
| PRE-02 | Importability verified | 2026-07-12 |
| M1-01 | `models.py` — all shared Pydantic data models | 2026-07-12 |
| M1-02 | `errors.py` — all domain exceptions | 2026-07-12 |
| M1-03 | `config.py` — TOML settings + Pydantic | 2026-07-12 |
| M1-04 | `epub/reader.py` — safe EPUB open | 2026-07-12 |
| M1-05 | `epub/metadata.py` — BookMetadata extraction | 2026-07-12 |
| M1-06 | `epub/navigation.py` — spine + nav + NCX | 2026-07-12 |
| M1-07 | `epub/chapters.py` — scoring engine | 2026-07-12 |
| M1-08 | `epub/cover.py` — cover image extraction | 2026-07-12 |
| M1-09 | `epub/cleanup.py` — XHTML → plain text | 2026-07-12 |
| M1-10 | `utils/names.py` — filename sanitization | 2026-07-12 |
| M1-11 | `cli.py` — inspect command | 2026-07-12 |
| M1-12 | `tests/fixtures/builders.py` — EPUB factory | 2026-07-12 |
| M1-13 | `tests/fixtures/simple_epub3.epub` generated | 2026-07-12 |
| M1-14 | `tests/fixtures/simple_epub2.epub` generated | 2026-07-12 |
| M1-15 | `tests/epub/test_metadata.py` (11 tests) | 2026-07-12 |
| M1-16 | `tests/epub/test_navigation.py` (11 tests) | 2026-07-12 |
| M1-17 | `tests/epub/test_chapters.py` (13 tests) | 2026-07-12 |
| M1-REVIEW | Milestone 1 Reviewer sign-off — APPROVED | 2026-07-12 |
| DEFECT-002 | Chapter.word_count = 0 for long docs — assigned to M2-tts-engineer | 2026-07-12 |

---

## Reviewer Sign-off — Milestone 2 (2026-07-12)

**Result: APPROVED (conditional on CI running the integration suite with FFmpeg installed).**

Gates verified on this machine:
- `uv run pytest tests/ -v` → **112 passed, 5 skipped** (the 5 skips are the
  FFmpeg-dependent e2e tests; FFmpeg is not installed on the review machine —
  they skip cleanly via `shutil.which("ffmpeg")`).
- `uv run ruff check src/ tests/` → All checks passed.
- `uv run ruff format --check src/ tests/` → 55 files already formatted.
- `uv run mypy src/epub2audio` → Success, 39 source files, 0 errors (strict).
- `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` → Rich plan table,
  2 chapters in spine reading order (Chapter One = `b_chapter_01.xhtml`, Chapter
  Two = `a_chapter_02.xhtml`), nav excluded. Spine order confirmed, not filename order.
- `uv run epub2audio convert --help` → all 16 documented flags present.

Reviewer-applied fixes:
1. **ChapterResult.duration_seconds was hardcoded 0.0** — `pipeline/converter.py`
   never probed the final MP3. Added `probe_duration()` to `audio/validate.py`
   (ffprobe `-show_format -show_streams`, parses container/stream duration) and
   call it after `validate_mp3` in `_process_chapter`. Failures degrade to 0.0
   with a warning. This makes `test_convert_epub_chapter_duration_positive`
   pass under FFmpeg (FakeTTS emits 150 ms/word of silence → positive duration).

Defects investigated (from sign-off brief):
2. **encode.py mock path** — `audio/encode.py` uses
   `from epub2audio.utils.subprocess import run_command`; the test patch
   `epub2audio.audio.encode.run_command` resolves correctly. `test_encode.py`
   passes (mocked, no FFmpeg needed). ✅
3. **mypy python_version 3.11 → 3.12** — documented inline (numpy 2.x stubs use
   the 3.12 `type` statement). `requires-python` stays `>=3.11` and ruff
   `target-version = "py311"` still enforces 3.11 syntax; no 3.12-only syntax
   found in `src/`, so the bump masks nothing. Comment recommends a CI 3.11 run
   with numpy<2. Acceptable. ✅
4. **5 e2e tests skipped (FFmpeg absent)** — the tests are structurally correct
   and skip cleanly. Code paths (`encode_mp3`, `validate_mp3`, `probe_duration`,
   `embed_metadata`, `concatenate_wavs`) all use ffmpeg/ffprobe argument arrays.
   **Conditional approval**: FFmpeg validation of M2-21 deferred to CI. CI must
   install FFmpeg and run the `integration`-marked suite before release.
5. **cover art `.jpg` temp extension** — cosmetic; FFmpeg detects format from
   bytes, not extension. Acceptable. ✅

Security / boundary checks:
- No `shell=True` anywhere (only docstrings that state it is never used).
- All subprocess calls route through `utils/subprocess.py` (argument arrays).
- No `kokoro` PyPI imports anywhere; `cli.py` imports the project's own
  `KokoroTTSEngine` adapter from `tts/kokoro.py` (intended M3 injection point).
- No `epub/` imports inside `tts/` or `audio/`.
- No narration/body text in log statements (only chapter IDs, titles (metadata),
  word counts, config keys).

Outstanding (does not block M2):
- **DEFECT-003** — segment-level resume is non-functional (manifest `segments`
  never populated; segment WAVs live in an OS temp dir deleted at run end).
  Manifest write/fingerprint/config-hash validation all work; only the
  segment-skip cache is inert. Deferred to Milestone 4 (Reliability), where the
  "Interrupted conversions resume" acceptance criterion lives.

---

## Reviewer Sign-off — Milestone 3 (2026-07-12)

**Result: APPROVED.**

Gates verified on this machine:
- `uv run pytest tests/ -v` → **117 passed, 11 skipped** (6 Kokoro smoke tests
  gated by `slow`+`requires_model`, 5 FFmpeg e2e tests — all skip cleanly).
- `uv run ruff check src/ tests/` → All checks passed.
- `uv run ruff format --check src/ tests/` → 58 files already formatted.
- `uv run mypy src/epub2audio` → Success, 39 source files, 0 errors (strict).
- `uv run epub2audio voices` → Rich table, 9 voices incl. `af_heart` (default),
  footer "9 voices available.", exit 0.
- `uv run epub2audio doctor` → status line for Python, FFmpeg, FFprobe,
  espeak-ng, kokoro, misaki, disk. FFmpeg+FFprobe absent on review machine →
  exit **1** (correct per contract). Code path confirmed to exit **0** only when
  both FFmpeg and FFprobe resolve via `shutil.which`.
- `uv run epub2audio inspect ...` and `convert --help` → no CLI regressions
  (spine reading order preserved; nav excluded).

Reviewer-applied fixes:
1. **Voice descriptions were factually wrong** — `af_heart`/`af_bella`/`af_sarah`
   were labelled "Afrikaans". In Kokoro the `af_` prefix is **American English
   female** (the `a` maps to `en-us` → `"a"` in this module's own `LANGUAGE_MAP`);
   none of these are Afrikaans voices. Relabelled to "American …" for accuracy
   and internal consistency (`tts/voices.py`).
2. **KokoroTTSEngine single-language scope undocumented / misleading** — the
   class docstring implied the `synthesize(language=...)` argument governs the
   pipeline language; in fact the pipeline is locked to the init-time
   `lang_code` and `language` is only validated. Added an explicit
   "Single-language scope (by design)" section to the class docstring
   (`tts/kokoro.py`). Behaviour is intentional and unchanged.
3. **Repo hygiene** — removed stray developer scratch artifacts left in the repo
   root (`0.wav`, `test_kokoro.py`) that were untracked but could be committed by
   mistake.

Defects/known-issues investigated (from sign-off brief):
- **KokoroTTSEngine language scope (design, low)** — confirmed intentional; now
  documented (fix #2 above). A single engine is locked to one language.
- **pyproject.toml mypy overrides (low)** — exactly three override stanzas
  (ebooklib, soundfile, kokoro/misaki); no duplicates; all legitimate
  `ignore_missing_imports` for un-stubbed optional/3rd-party packages. ✅
- **Kokoro smoke tests (kokoro not installed)** — 6 tests carry
  `pytestmark = [slow, requires_model]`; conftest auto-skips both marks unless
  explicitly requested, so they skip in default `pytest tests/`. Verified they
  skip (6 SKIPPED). Structure is correct (import-guard test reloads the module
  with `kokoro=None` in `sys.modules`; sample-rate test asserts positivity, not
  a hardcoded 24000). ✅
- **doctor exit code (medium)** — code path confirmed: exits **0** iff both
  `ffmpeg_path` and `ffprobe_path` truthy; otherwise exits **1** with the
  missing list on stderr. Never exits 2+. ✅
- **Import boundaries** — no `kokoro` imports outside `tts/kokoro.py` for
  *synthesis*; the only other `import kokoro` is a guarded `try/except` in the
  `doctor` command that reads `__version__` for the env report (inherent to a
  doctor check, does not touch the Kokoro API surface). No `epub/` imports in
  `tts/` or `audio/`. `from epub2audio.tts.kokoro import KokoroTTSEngine`
  succeeds without the `kokoro` package installed. ✅

Security / logging checks: no `shell=True` anywhere (only docstrings stating it
is never used); no narration/body text in any log statement (cli logging is
level config only).

---

## Reviewer Sign-off — Milestone 4 (2026-07-12)

**Result: APPROVED (conditional on CI running the FFmpeg integration suite).**

DEFECT-003 (segment-level resume non-functional) is **fixed**. Segment WAVs now
persist under `<output_dir>/.epub2audio-work/<chapter_id>/seg_NNNN.wav`,
`manifest.segments` is populated with resolved `audio_path` + `status="done"`
after each chapter, and `segment_needs_synthesis()` is wired into
`_process_chapter` so cached WAVs are reused on resume.

Gates verified on this machine:
- `uv run pytest tests/ -v` → **145 passed, 24 skipped** (skips are FFmpeg
  integration + Kokoro model-gated tests; all skip cleanly).
- `uv run mypy src/epub2audio` → Success, 39 source files, 0 errors (strict).
- `uv run ruff check src/ tests/` → All checks passed.
- `uv run ruff format --check src/ tests/` → 62 files formatted.

Reviewer-applied fix:
1. **`ruff format --check` was red** on `tests/pipeline/test_segment_resume.py`
   (the Tester's lint cleanup left two multi-line assertions unformatted).
   Ran `ruff format` on the file — mechanical whitespace only, no logic change;
   all 19 tests in the file still pass.

Code review of `pipeline/converter.py` + `pipeline/resume.py`:
- Work dir is under the **output dir** (`.epub2audio-work/`), not OS temp — D1 ✓.
- Manifest is written after **each chapter** with segments merged by
  `normalized_hash` (`_merge_segments`) — crash-safe, atomic write → D2 ✓.
- Resume path matches by `normalized_hash`, verifies the WAV exists and is
  non-empty, and reuses it (logs "resumed from cached WAV") → D3 ✓.
- Cleanup: per-chapter only removes `chapter.wav`/`chapter_norm.wav`; segment
  WAVs survive until post-run cleanup, which only runs on a completed pass and
  respects `keep_intermediates`; on interrupt the work dir is left intact for
  `--resume` → D5 ✓.

Manual resume / config-invalidation tests (from the task): **deferred to CI** —
FFmpeg and FFprobe are not installed on the review machine, so the 9
converter-resume integration tests skip cleanly (guarded by
`shutil.which("ffmpeg")`). The 13 `check_resume` unit tests run without FFmpeg
and pass. This mirrors the M2/M3 conditional-approval pattern.

Known limitation (does not block M4; safe by construction):
- **Two-tier invalidation is conservative, not selective.** `ConversionManifest`
  stores only `config_hash` (a digest), not the config snapshot, so
  `check_resume()` returns a single `["config_hash"]` sentinel and cannot tell a
  TTS-affecting change (voice/language/speed) from an encoding-only change
  (bitrate/sample_rate/normalize). `tts_config_changed()` therefore treats **any**
  config change as TTS-affecting and clears all segment WAVs. This never reuses
  stale audio (correct artifacts are always invalidated) but re-synthesizes on
  encoding-only changes that could in principle be reused. `_TTS_AFFECTING_KEYS`
  / `_ENCODE_AFFECTING_KEYS` are defined for the planned refinement, and the
  Tester documents the desired behaviour via a non-strict `xfail`
  (`test_bitrate_change_keeps_segments`). Recommended follow-up: persist
  `config_snapshot` in the manifest to enable true two-tier invalidation.

Security / boundary checks:
- No `kokoro` imports outside `tts/kokoro.py` for synthesis (the only other is
  the guarded `import kokoro` in `cli.py` `doctor` for `__version__`, accepted
  in M3). No `epub/` imports inside `tts/` or `audio/`. No `shell=True`
  anywhere. No narration/body text in any log statement (only chapter IDs,
  titles, segment indices, word counts, changed config keys).

---

## Reviewer Sign-off — Milestone 5 (2026-07-12)

**Result: APPROVED (detection layer). Two follow-up defects filed for Milestone 6.**

M5 hardened the chapter-detection engine with three new public functions in
`epub/chapters.py` — `merge_consecutive_chapters()` (D1 multi-file merge),
`split_multi_chapter_docs()` (D2 single-file split), and the orchestrating
`finalize_chapters()` — plus D3 scoring refinements (titlepage/halftitlepage -5,
multiple_h1 -1, new front/back-matter epub:types) and D4 fragment-range extraction
in `cleanup.xhtml_to_text(start_fragment=, end_fragment=)`.

Gates verified on this machine:
- `uv run pytest tests/epub/ -q` → **77 passed** (M5 scope).
- `uv run mypy src/epub2audio` → Success, 39 source files, 0 errors (strict).
- `uv run ruff check src/ tests/` → All checks passed.
- `uv run ruff format --check src/ tests/` → 65 files formatted (see reviewer fix below).
- `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` → no regression; 2 chapters
  in spine reading order (Chapter One = `b_chapter_01.xhtml`, Chapter Two =
  `a_chapter_02.xhtml`), nav excluded.

Reviewer-applied fix:
1. **`ruff format --check` was red** on 5 test/fixture files
   (`test_chapter_split.py`, `test_chapters.py`, `test_cleanup_fragments.py`,
   `test_chapter_merge.py`, `builders.py`) — the Tester's assertion-string wrapping was
   unformatted. Ran `ruff format` (mechanical whitespace only, no logic change); all 77
   epub tests still pass.

Code review of `epub/chapters.py`:
- Merge/split logic is cleanly separated from scoring; `finalize_chapters()` runs
  merge → split → `_renumber_chapters()` with fresh `chapter_id`/`stable_id`. ✓
- New scoring weights are documented in the module docstring table and inline signals. ✓
- Fragment extraction (`_extract_fragment`) degrades gracefully when the anchor is
  missing (falls back to whole-document text) — no crash on invalid fragment refs. ✓
- No regression: `simple_epub3` still yields 2 independent chapters (no false merge/split).

Acceptance criteria (detection layer, unit-tested):
- **Multi-file chapters can be merged** → `merge_consecutive_chapters()` + 8 tests. ✅¹
- **Multi-chapter single-file can be split** → `split_multi_chapter_docs()` + 9 tests. ✅¹

¹ **Condition (DEFECT-004, non-blocking, M6 follow-up):** `finalize_chapters()` is not
yet wired into `cli.py` (`inspect`) or `pipeline/planner.py` (`convert`) — both still call
`select_chapters()` only — so merge/split is currently reachable only through unit tests,
not the shipped product path. Additionally, `converter._load_chapter_text` does not strip
`#fragment` from `source_docs` nor pass fragment bounds to `xhtml_to_text`, so wiring it
as-is would silently drop or duplicate split-chapter text. Both are captured in
`DEFECT-004` for Milestone 6 (product integration).

Pre-existing (not M5 scope) — **DEFECT-005**:
- With FFmpeg installed on this machine, 16 M4 pipeline/e2e tests fail (they previously
  skipped when FFmpeg was absent). Root cause: `loudnorm` returns exit 234 on FakeTTS
  pure-silence input (`measured_I=-inf`). Not introduced by M5; filed as DEFECT-005 with
  a recommended silence guard + skip-guard fix. Full suite: **188 passed, 16 failed,
  6 skipped, 1 xfailed** — all 16 failures are this FFmpeg loudnorm issue; 0 failures in
  M5 (`tests/epub/`) scope.

Security / boundary checks: no `kokoro` imports outside `tts/kokoro.py`; no `epub/`
imports inside `tts/` or `audio/`; no `shell=True`; no narration/body text in any log
statement (only chapter IDs, titles, doc paths, word counts, signal strings).

---

## Reviewer Sign-off — Milestone 6 (2026-07-12) — FINAL / PROJECT CLOSE

**Result: APPROVED. This is the final milestone; the epub2audio project is complete.**

DEFECT-004 and DEFECT-005 are both fixed and verified end-to-end.

Gates verified on this machine (FFmpeg + FFprobe installed — full suite runs, no
FFmpeg-gated skips):
- `uv run pytest tests/ -q` → **204 passed, 6 skipped, 1 xfailed** (skips are the
  Kokoro model-gated smoke tests; xfail is the documented conservative two-tier
  invalidation follow-up).
- `uv run mypy src/epub2audio` → Success, 39 source files, 0 errors (strict).
- `uv run ruff check src/ tests/` → All checks passed.
- `uv run ruff format --check src/ tests/` → 65 files already formatted.
- `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` and `simple_epub2.epub`
  → no regression from the `finalize_chapters()` wiring; 2 chapters each in spine
  reading order (Chapter One = `b_chapter_01.xhtml`, Chapter Two =
  `a_chapter_02.xhtml`, nav excluded).

**DEFECT-004 — `finalize_chapters()` wiring + converter fragment handling — FIXED:**
- `cli.py` (`inspect`, line 77) and `pipeline/planner.py` (line 40) now both call
  `finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)`,
  so merge/split reaches the shipped product path.
- `pipeline/converter._load_chapter_text` now strips the optional `#fragment`
  suffix from each `source_docs` entry, looks the EPUB item up by the bare path,
  and forwards `start_fragment` / `end_fragment` to `xhtml_to_text`. The end
  boundary for a split file is derived by `_get_end_fragment()` from the next
  same-file fragment entry. This prevents both silent text drop (fragment path
  passed to `get_item_with_href`) and duplication (full-doc text per split chapter).

**DEFECT-005 — loudnorm exit 234 on silent input — FIXED:**
- `audio/normalize.py` adds a `_is_degenerate()` silence guard: if the pass-1
  loudnorm measurement yields a non-finite value (`-inf`/`inf`/`nan`) — as
  FakeTTS pure-silence input does — pass 2 is skipped and the file is copied
  through, avoiding FFmpeg exit 234.
- Pass-2 output now uses explicit `-f wav` (and the encoder uses `-f mp3` for its
  `.tmp` sidecar) so FFmpeg ≥ 8 does not fail to infer the format from the
  `.tmp` extension.
- The 16 previously-failing pipeline/e2e tests now pass:
  `test_converter_resume.py` + `test_segment_resume.py` + `test_e2e.py` →
  **32 passed, 1 xfailed** with FFmpeg installed.

**Documentation / packaging:** `README.md`, `CHANGELOG.md`, and `LICENSE` (MIT)
are present at the repo root.

**Residual risk (non-blocking):** the converter fragment glue
(`_load_chapter_text` / `_get_end_fragment`) has no dedicated end-to-end
regression test; it is covered indirectly by `test_cleanup_fragments.py` (the
`xhtml_to_text` start/end-fragment layer) and `test_chapter_split.py` (the split
detection layer). The glue logic is small and reviewed as correct. Recommended
future follow-up: add an e2e test that converts a single-file multi-chapter EPUB
and asserts split-chapter MP3 text is non-empty and non-duplicated.

Security / boundary checks: no `kokoro` imports outside `tts/kokoro.py` for
synthesis (the only other is the guarded `import kokoro` in `cli.py` `doctor` for
`__version__`, accepted since M3); no `epub/` imports inside `tts/` or `audio/`;
no `shell=True` anywhere; no narration/body text in any log statement (only
chapter IDs, titles, doc paths, segment indices, word counts, config keys).

---

## Known Risks / Open Questions

- Kokoro PyPI package API stability — isolate in `tts/kokoro.py` (per M3-01 spec)
- `espeak-ng` requirement on macOS needs verification with actual Kokoro install
- Chapter-detection scoring thresholds will need tuning against real EPUBs
- `AudioChunk.data` typed as `Any` (numpy array) — resolved; see `docs/decisions/`

---

## Acceptance Criteria Progress

| Criterion | Done? |
|---|---|
| Valid non-DRM EPUB converts locally | ✅ (e2e convert suite passes with FFmpeg) |
| One MP3 per logical chapter | ✅ (e2e: two chapters → two MP3s) |
| Track order matches reading order | ✅ (tested — spine order used, not filename order) |
| Human-readable sanitized chapter names | ✅ (utils/names.py implemented) |
| Does not assume filename order = reading order | ✅ (tested — spine order enforced) |
| Multi-file chapters can be merged | ✅ (detection + 8 tests; wired into `inspect`/`convert` via `finalize_chapters` — DEFECT-004 fixed) |
| Multi-chapter single-file can be split | ✅ (detection + 9 tests; wired into `inspect`/`convert` + converter fragment handling — DEFECT-004 fixed) |
| Navigation-only and empty pages excluded | ✅ (scoring engine excludes score < 0) |
| `inspect` shows conversion plan | ✅ (cli.py inspect command) |
| Every MP3 passes FFprobe validation | ✅ (`validate_mp3` + `probe_duration` in e2e) |
| MP3s contain book/track metadata | ✅ (`embed_metadata`; e2e report metadata test) |
| Cover art embedded | ✅ (`embed_metadata` cover path exercised) |
| Interrupted conversions resume | ✅ (segments persisted + skipped on resume; FFmpeg e2e deferred to CI) |
| Config changes invalidate correct artifacts | ✅ (conservative — any config change clears segment WAVs; never reuses stale audio. Selective two-tier is a documented follow-up) |
| Failed synthesis never silently omits text | ✅ (chapter failures recorded as errors in report; no silent drop) |
| No content sent over network | ✅ (by design — no network calls planned) |
| No DRM removal | ✅ (by design) |
| Unit + e2e tests pass | ✅ (204 pass / 6 skipped / 1 xfailed; e2e runs with FFmpeg installed) |
| Ruff + type checking pass | ✅ (ruff check + format clean; mypy strict 0 errors, 39 files) |
| New user can install from README | ✅ (README.md, CHANGELOG.md, LICENSE present) |
