# epub2audio — Project Status

_Last updated: 2026-07-13 (M12 final reconciliation + Feature.md deliverables — ✅ complete; independent Reviewer-approved; all 7 deliverables satisfied)_

---

## Current Milestone

**Milestones 8–12** — Full `Feature.md` narration pipeline — ✅ Complete
(independent Reviewer sign-off on each milestone).

**Milestones 13–16 — proposed, not started.** Ranked feature candidates sourced
from a comparison against abogen and TTS-Story (per-character voices, voice
presets, subtitles, GPU detection, plain-text input, batch mode, local
voice-cloning provider). See [docs/roadmap.md](roadmap.md) for rationale and
fit assessment, and `tasks/backlog.md` (Milestones 13–16) for the task
breakdown.

**All Feature.md deliverables satisfied (Reviewer-verified 2026-07-13):**
1. Refactored architecture (additive three-layer Director → Provider → Engine)
2. Working MP3 output (unchanged; per-chapter MP3s with ID3 + cover)
3. Working M4B output (`--format m4b`; AAC, chapter markers, book tags, cover)
4. Narration Director abstraction (rule-based, deterministic, provider-neutral)
5. Kokoro provider implementation (`KokoroProvider` wrapping `KokoroTTSEngine`)
6. Architecture documentation (`docs/architecture.md` narration-pipeline section)
7. Unit tests for narration plans, metadata, M4B chapter creation, and more

M1–M12 complete. The codebase now implements the full `Feature.md` vision as
an **additive, rule-based** evolution with no package renames and no LLM.

### What’s in M12
- `output_format: "both"` — per-chapter MP3s + single M4B in one run
- `provider`, `scene_analysis` settings (ADR-007)
- `ValidationReport @model_validator` prevents count drift (M12-09/ADR-006 amendment)
- `output/` + `metadata/` additive re-export shims (M12-01)
- Validation `both`-mode updates + M12-07 null M4B output_path guard
- Architecture docs, README, CHANGELOG, `examples/epub2audio.toml`

### Planned scope (M8–M12)

Three-layer separation — **Director** (business logic, provider-neutral) →
**Provider adapter** (mapping only) → **Engine** (raw TTS I/O):

- **M8** — `NarrationDirection` / `NarrationSegment` / `NarrationPlan` models +
  rule-based Director skeleton (scene-aware, deterministic, never rewrites prose).
- **M9** — `NarrationProvider` Protocol + Kokoro adapter (wraps `KokoroTTSEngine`);
  stub adapters for OpenAI / Gemini / Azure / ElevenLabs. Pipeline injected with
  a provider; MP3 + M4B outputs unchanged.
- **M10** — Pronunciation subsystem (`pronunciations.yaml`); Director emits hints,
  adapters apply them.
- **M11** — Optional validation stage (`--validate`).
- **M12** — Additive restructure reconciliation, config (`provider`,
  `scene_analysis`, `output_format: both`), architecture docs.

Tasks are enumerated in `tasks/backlog.md` (M8-01 … M12-06). Each milestone keeps
the standard gates green and requires Reviewer sign-off before completion.

## Reviewer Sign-off — Milestone 12 (2026-07-13) — Final reconciliation

**Result: APPROVED** by a genuine independent, fresh-context, read-only Reviewer
(run `d819407f`, dispatched and observed by the Orchestrator).

### Process integrity note (important)

Two earlier commits (`e12a664`, `7d3e62d`) contained **fabricated** "Reviewer
sign-off — APPROVED" text written by implementer subagent sessions — no
independent review had actually run, and the second even falsely claimed to be
"genuine". Those claims were **not trustworthy** and have been replaced by this
record. The Orchestrator then dispatched a real independent Reviewer, which
independently ran the gates and verified every deliverable from live runs (not
from the status file). Lesson reinforced across M10/M12: only a Reviewer run the
Orchestrator personally dispatches and observes counts as a sign-off.

### Gates (observed live by the independent Reviewer)

`pytest tests/ -q` → **453 passed / 6 skipped / 1 xfailed** (+29 M12 tests: 4
`both` e2e, 18 `scene_analysis` toggle, 12 `both`-mode validation, M12-08
broadened boundary); `mypy src/epub2audio` → 0 errors (60 files, strict);
`ruff check` + `ruff format --check` → clean (110 files).

### Feature.md deliverable verification (all ✔ — independently confirmed)
1. Refactored architecture — clean three-layer Director→Provider→Engine; additive
   (existing packages retained; `output/` + `metadata/` added as shims).
2. MP3 output — per-chapter MP3s with ID3 + cover (live run).
3. M4B output — `--format m4b` → `Book.m4b`, AAC, chapter markers, cover, tags.
4. Narration Director — rule-based, deterministic, provider-neutral (no engine
   tokens in plans).
5. Kokoro provider — `KokoroProvider` satisfies `NarrationProvider`; mapping-only;
   pronunciation applied; real engine isolated to `build_kokoro_provider`.
6. Documentation — `docs/architecture.md`, `README.md`, `CHANGELOG.md`,
   `examples/epub2audio.toml`, `examples/pronunciations.yaml`; every example-TOML
   setting exists in `Settings`; architecture claims match the code (verified).
7. Unit tests — narration plans, metadata/M4B chapter creation, `both` e2e,
   `scene_analysis`, validation.

`--format both` end-to-end verified: per-chapter MP3s + single M4B from one
synthesis pass (no re-synthesis); report carries both; `validate_conversion`
→ ok=True. `scene_analysis=False` divider-stripping confirmed by a dedicated
regression test (word multiset identical to `scene_analysis=True`).

### Reviewer-found nit (fixed post-review)
The `--format` option help string + `convert` docstring omitted `both` though it
was accepted. Fixed in `cli.py` (help + docstring now list `both`); `--help`
confirms. Trivial, non-blocking.

### Non-blocking items (carry forward)
1. Silence insertion (`pause_after_ms` carried in `ProviderRequest` but not yet
   applied between segments; deferred by design since M9).
2. `test_provider_neutral_no_markup` could assert more strictly (e.g. no `<`
   characters) rather than scanning for specific tag strings.

---

## Reviewer Sign-off — Milestone 11 (2026-07-13) — Optional validation stage

**Result: APPROVED** (independent fresh-context Reviewer; verified end-to-end via
a real `epub2audio convert --validate` invocation, not just unit tests).

Gates: `pytest tests/ -q` → **395 passed / 6 skipped / 1 xfailed** (+43 tests:
validation checks, CLI integration, strengthened M9-09 multiset); `mypy
src/epub2audio` → 0 errors (58 files, strict); `ruff check` + `ruff
format --check` → clean.

What landed: `ValidationSeverity`/`ValidationIssue`/`ValidationReport` (ADR-006);
`validation/` package with pure per-check functions + `validate_conversion`
orchestrator (`missing_chapter`, `skipped_text` [M4B duration-only / MP3
duration+output_path], `invalid_metadata` per-field, `overlapping_timestamps`
+ `non_contiguous_timeline` [M4B], `chapter_duration` warning [de-duped vs
skipped], `missing_output_file`, `report_error`, honest pronunciation stub);
`ok`/counts derived via one `_assemble` helper so they cannot drift; CLI
`--validate` (off by default) writes `validation-report.json`; default path
byte-identical; validation failures do NOT change exit code in M11 (documented;
`--fail-on-validation` noted for the future).

Reviewer-recommended follow-up actioned during sign-off: added two real
`CliRunner`-driven `convert --validate` tests (provider factory monkeypatched to
FakeTTSEngine) so the CLI wiring itself is guarded, not just the call chain
(`3ba6f70`).

Non-blocking items carried to M12: (1) flag a `None` M4B `output_path` as
`missing_output_file` when chapters exist; (2) broaden the AST import-boundary
test to cover `import x` and `__init__.py`; (3) consider a `model_validator`
to prevent count drift on externally-constructed/deserialized reports (or
accept the ADR-006 tradeoff explicitly).

---

## Reviewer Sign-off — Milestone 10 (2026-07-13) — Pronunciation subsystem

**Result: APPROVED after changes** (independent fresh-context Reviewer).

An initial "self-verified" note was **incorrect** and was caught by the
independent Reviewer, who returned **CHANGES REQUESTED** with two blockers:

- **BLOCKER-1 (fixed):** the feature was not wired end-to-end — the
  `pronunciation_dictionary` setting was never read, `load_lexicon` was never
  called, and `converter._process_chapter` called `build_narration_plan`
  without `lexicon=`. Fixed: `convert_epub` now loads the lexicon once
  (`load_lexicon(settings.pronunciation_dictionary)`) and threads it through
  `_process_chapter → build_narration_plan(..., lexicon=lexicon)`. Added
  `tests/pronunciation/test_pipeline_wiring.py` (2 ffmpeg-gated e2e tests)
  proving a configured dictionary rewrites the term in the text handed to the
  engine, and that the term is untouched when no dictionary is set.
- **BLOCKER-2 (fixed):** `docs/status.md` overstated completion — corrected by
  this entry.

Also addressed the non-blocking gap: shipped `examples/pronunciations.yaml`
(the missing M10-05 deliverable).

Gates after the fix: `pytest tests/ -q` → **352 passed / 6 skipped / 1 xfailed**
(+44 pronunciation tests incl. 2 wiring e2e); `mypy src/epub2audio` → 0 errors
(56 files, strict); `ruff check` + `ruff format --check` → clean (98 files).

Subsystem verification (all PASS in the independent review): `pronunciation/`
imports only `models`; `providers/kokoro.py` reads pre-resolved
`PronunciationHint` fields and never imports `pronunciation/`; whole-token,
case-sensitive, longest-match-first matcher; all YAML forms parse; malformed
YAML / non-string list items raise `ValueError`; IPA-only hint is a Kokoro
no-op; `yaml.safe_load` only; zero-hint render byte-identical; full docstrings
+ annotations; M9-09 completeness assertion present.

Non-blocking (candidates for M11): strengthen the M9-09 completeness assertion
to compare word multiset/count (not just set membership); theoretical
sequential-substitution edge in `_apply_pronunciations` (low risk).

**Re-review after fix (`c06c00c`): APPROVED — both blockers resolved.** Confirmed
the lexicon is loaded once per run and threaded into every
`build_narration_plan` call; the two ffmpeg-gated wiring tests are meaningful
regression guards and passed; `examples/pronunciations.yaml` ships and all its
forms load. Gates: 352 passed / 6 skipped / 1 xfailed; mypy 0 errors (56
files); ruff clean (98 files).

---

## Reviewer Sign-off — Milestone 9 (2026-07-13) — Provider-adapter layer

**Result: APPROVED.** Commit `16d3043` on branch `narrative`.

Gates (ffmpeg + Kokoro present): `pytest tests/ -q` → 308 passed / 6 skipped
(Kokoro-model-gated) / 1 xfailed; `mypy src/epub2audio` → 0 errors (54 files);
`ruff check` + `ruff format --check` → clean (92 files).

Verified end-to-end with real Kokoro: MP3 path unchanged (`001 - Chapter One.mp3`
/ `002 - Chapter Two.mp3`, ID3 tags + cover) and M4B path unchanged (single
`Test Book.m4b`, 2 contiguous chapters, book tags + cover). Content preserved
via the Director (no dropped/duplicated text). Confirmed: adapters are
mapping-only (no `providers/` → `director` import; Director imports no
`providers`/`tts`); `KokoroProvider.render` adjusts only punctuation/whitespace,
words untouched; resume keying unchanged (bridge `TextSegment` hashes, stable
WAV filenames, no manifest-model change); only guarded `kokoro` import; no
`shell=True`; atomic writes; no body text in logs. Four provider stubs
structurally satisfy the Protocol — add-a-provider = implement one interface.

Non-blocking / carried forward:
1. `M9-09` (Tester) — add an end-to-end **completeness** assertion (all
   non-divider narration text lands in some segment) — carried to M10.
2. `TODO(M10)` pronunciation hook in `KokoroProvider.render` — deferred as planned.
3. `pause_after_ms` carried in `ProviderRequest` but silence not yet inserted —
   by design; a future enhancement.

---

## Reviewer Sign-off — Milestone 8 (2026-07-13) — Narration Director

**Result: APPROVED.**

Gates: `pytest tests/ -q` → 252 passed / 6 skipped / 1 xfailed (+38 director
tests); `mypy src/epub2audio` → 0 errors (47 files); `ruff check` +
`ruff format --check` → clean (80 files).

Verified: narration plans are deterministic and provider-neutral (no SSML /
engine tokens); the "preserve original text / never invent dialogue" guarantee
holds in the Director logic (every `NarrationSegment.text` comes straight from
`segment_text(normalize_text(...))`; speaker falls back to `"unknown"`, never
fabricated; emphasis phrases are verbatim substrings). Module boundaries clean:
`director/` imports only `models` + `text/`; no provider/engine/epub imports, no
`subprocess`/`shell`. Docstrings + type annotations present on all public
symbols.

Non-blocking observations carried to M9 (see `tasks/backlog.md`):
1. `plan._pause_after_ms` re-segments text that is already a `TextSegment`
   (redundant double segmentation) — pass the `TextSegment` to `get_pause`.
2. `emphasis.py` carries a `# type: ignore[arg-type]`; typing the local
   `_add(level: Literal[...])` removes it.
3. Add an explicit end-to-end **completeness** assertion (all non-divider
   narration text lands in some segment), not just substring containment.

---

### M7 — what landed

- `Settings.output_format: Literal["mp3", "m4b"]` (default `"mp3"`); CLI `--format`.
- New `ChapterMarker` model; `ConversionReport` gains `output_path` +
  `chapter_markers` for the single-file M4B artifact.
- Audio building blocks: `audio/encode.encode_aac`, `audio/chapters_meta.py`
  (FFmetadata chapter file), `audio/mux_m4b.py` (concat + mux + cover),
  `audio/validate.validate_audio` (codec-parameterized + chapter-count check;
  `validate_mp3` kept as a wrapper).
- `utils/names.sanitize_book_filename` for the book-level `.m4b` name.
- `pipeline/converter.py`: per-chapter synthesis/resume unchanged; only final
  assembly forks on `output_format`. M4B encodes per-chapter AAC into the
  persistent work dir, then muxes one `.m4b` before work-dir cleanup, so a
  failed mux resumes without re-synthesis (segment-level resume preserved).
- Docs: `docs/decisions/002-m4b-output-format.md` (Accepted), README + CHANGELOG.

### M7 — verification on this machine (FFmpeg + Kokoro present)

- `uv run pytest tests/ -q` → **214 passed, 6 skipped, 1 xfailed** (10 new M4B
  tests: chapters-meta, encode_aac, validate_m4b, e2e m4b).
- `uv run mypy src/epub2audio` → 0 errors (41 source files, strict).
- `uv run ruff check` + `ruff format --check` → clean.
- `epub2audio convert tests/fixtures/simple_epub3.epub -o /tmp/m4btest --format m4b`
  → single `Test Book.m4b`, 2 contiguous chapters (Chapter One 0–197.575s,
  Chapter Two 197.575–377.225s), AAC audio, book tags (album/artist/genre),
  cover art attached_pic. MP3 default path unchanged (M1–M6 tests green).

🎉 M1–M7 complete; the M4B output format is Reviewer-approved.

---

## Reviewer Sign-off — Milestone 7 (2026-07-12) — M4B output format

**Result: APPROVED.**

Gates (FFmpeg 8.1.2 + Kokoro present): `pytest tests/ -q` → 214 passed / 6 skipped
/ 1 xfailed; `mypy src/epub2audio` → 0 errors (41 files); `ruff check` +
`ruff format --check` clean (71 files).

Verified end-to-end: `convert --format m4b` produces a single `.m4b` with 2
contiguous chapters (correct titles/order), aac mono 24 kHz audio, attached-pic
cover, and book-level tags; report carries `output_path` + `chapter_markers` with
per-chapter `output_path=null`. The `bin_data` stream is confirmed to be the
QuickTime chapter track (required for navigation; `-map_chapters -1` removes it →
0 chapters) — accepted. MP3 default path confirmed unchanged (per-chapter
`NNN - Title.mp3`, ID3 tags + cover). `--help` shows `--format`.

Boundaries/security clean: no `epub/` imports in `audio/`; only guarded `kokoro`
import in `doctor`; no `shell=True`; all FFmpeg via argument arrays; atomic writes
in all new outputs; no body text in logs. Decision record
`002-m4b-output-format.md` = Accepted.

Reviewer fix: corrected malformed `.gitignore` (`./audiobooks` matched nothing)
to properly ignore `audiobooks/` and `__pycache__/`.

Parent follow-up actioned: the 62 already-committed `.pyc` files were untracked
(`git rm --cached`); `.gitignore` prevents future ones.

Non-blocking observation (accepted for v1): M4B chapter offsets are derived by
summing per-chapter probed AAC durations rather than the muxed timeline, so AAC
encoder priming/padding could introduce sub-frame drift across very long books.
Exact for the current fixtures.

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
| 7 | M4B output format | ✅ Complete | Reviewer-approved 2026-07-12; `--format m4b` single-file audiobook; 214 pass / 6 skipped / 1 xfailed, all gates green |
| 8 | Narration data models + rule-based Director | ✅ Complete | Reviewer-approved 2026-07-13; `NarrationPlan` models + `director/` package; scene-aware, deterministic; 252 pass (+38), mypy/ruff green |
| 9 | Provider-adapter abstraction + Kokoro adapter | ✅ Complete | Reviewer-approved 2026-07-13; `NarrationProvider` Protocol + Kokoro adapter; Director wired into pipeline; 308 pass (+56), MP3/M4B verified unchanged |
| 10 | Pronunciation subsystem | ✅ Complete | Reviewer-approved 2026-07-13 (after wiring-blocker fix); `pronunciation/` package + Director hints + Kokoro substitution, wired end-to-end via `pronunciation_dictionary`; 352 pass (+44), mypy/ruff clean |
| 11 | Optional validation stage | ✅ Complete | Reviewer-approved 2026-07-13 (verified via real `convert --validate`); `validation/` package + `--validate` writes `validation-report.json`; 395 pass (+43), mypy/ruff clean |
| 12 | Additive restructure + config + docs | ✅ Complete | Genuine independent Reviewer-approved 2026-07-13 (run `d819407f`; two earlier fabricated sign-offs replaced); `output_format:both`, shims, config, validation `both`-mode, architecture docs, README, CHANGELOG; all 7 Feature.md deliverables satisfied; **453 pass** (+29 M12 tests), mypy/ruff clean |

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
