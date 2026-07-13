# Task for orchestrator

You are the Orchestrator for epub2audio. Begin Milestone 1.

Context already read for you:
- docs/status.md: Pre-work in progress, M1 not started, no src/ code exists yet
- tasks/backlog.md: PRE-01, PRE-02 pending; M1-01 through M1-18 queued
- docs/architecture.md: full module map, data models, TTSEngine Protocol
- pyproject.toml: hatchling build, src layout at src/epub2audio/

## Your tasks in order

### 1. Complete PRE-01 — Create package skeleton

Create every `__init__.py` stub needed so `src/epub2audio` is a valid importable package. All stubs should be empty files (or contain a single `"""Module stub."""` docstring). Create stubs for:

```
src/epub2audio/__init__.py
src/epub2audio/cli.py           (stub only — "# CLI stub")
src/epub2audio/config.py        (stub only)
src/epub2audio/models.py        (stub only)
src/epub2audio/errors.py        (stub only)
src/epub2audio/logging.py       (stub only)
src/epub2audio/epub/__init__.py
src/epub2audio/epub/reader.py   (stub only)
src/epub2audio/epub/metadata.py (stub only)
src/epub2audio/epub/navigation.py (stub only)
src/epub2audio/epub/chapters.py (stub only)
src/epub2audio/epub/cleanup.py  (stub only)
src/epub2audio/epub/cover.py    (stub only)
src/epub2audio/text/__init__.py
src/epub2audio/text/normalize.py (stub only)
src/epub2audio/text/segment.py  (stub only)
src/epub2audio/text/pronunciation.py (stub only)
src/epub2audio/text/pauses.py   (stub only)
src/epub2audio/tts/__init__.py
src/epub2audio/tts/base.py      (stub only)
src/epub2audio/tts/kokoro.py    (stub only)
src/epub2audio/tts/voices.py    (stub only)
src/epub2audio/audio/__init__.py
src/epub2audio/audio/chunks.py  (stub only)
src/epub2audio/audio/concatenate.py (stub only)
src/epub2audio/audio/encode.py  (stub only)
src/epub2audio/audio/normalize.py (stub only)
src/epub2audio/audio/metadata.py (stub only)
src/epub2audio/audio/validate.py (stub only)
src/epub2audio/pipeline/__init__.py
src/epub2audio/pipeline/planner.py (stub only)
src/epub2audio/pipeline/converter.py (stub only)
src/epub2audio/pipeline/manifest.py (stub only)
src/epub2audio/pipeline/resume.py (stub only)
src/epub2audio/utils/__init__.py
src/epub2audio/utils/files.py   (stub only)
src/epub2audio/utils/names.py   (stub only)
src/epub2audio/utils/subprocess.py (stub only)
tests/__init__.py               (empty)
tests/fixtures/__init__.py      (empty)
tests/epub/__init__.py          (empty)
tests/text/__init__.py          (empty)
tests/audio/__init__.py         (empty)
tests/pipeline/__init__.py      (empty)
```

### 2. Complete PRE-02 — Verify importable

Run: `uv run python -c "import epub2audio; print('ok')"` 
If it fails, fix the issue before continuing.

### 3. Create M1 task contracts

Create these three files in `tasks/active/`:

#### tasks/active/M1-architect.md
Task contract for the Architect covering M1-01 and M1-02:
- M1-01: Write `src/epub2audio/models.py` — all Pydantic models as specified in docs/architecture.md. All models must use `model_config = ConfigDict(frozen=True)`. Include: BookMetadata, BookDocument, NavigationEntry, ChapterCandidate (with score int and signals list[str]), Chapter, TextSegment, AudioChunk, ConversionPlan, ConversionManifest, ChapterResult, ConversionReport.
- M1-02: Write `src/epub2audio/errors.py` — domain exceptions. Include at minimum: InvalidEpubError, DrmProtectedEpubError, MissingDependencyError, UnsupportedLanguageError, SegmentTooLongError, FingerprintMismatchError, ConfigChangedError. All inherit from a base Epub2AudioError.
- Hard constraints: models.py may not import from any other epub2audio module. errors.py may not import from any other epub2audio module.
- Acceptance: `uv run mypy src/epub2audio/models.py src/epub2audio/errors.py` passes with strict mode.

#### tasks/active/M1-epub-engineer.md
Task contract for the EPUB Engineer covering M1-03 through M1-11:
- M1-03: Write `src/epub2audio/config.py` — TOML config loading with pydantic-settings. Settings: voice (default af_heart), language (default en-us), speed (default 1.0), bitrate (default 96k), sample_rate (default 24000), normalize (default True), resume (default True), workers (default 1), output_dir (default Path(".")).
- M1-04: Write `src/epub2audio/epub/reader.py` — safe EPUB open using ebooklib. Must guard against ZIP path traversal and zip bombs. Must detect DRM (raises DrmProtectedEpubError) and raise InvalidEpubError for unreadable files.
- M1-05: Write `src/epub2audio/epub/metadata.py` — extract BookMetadata from OPF via ebooklib.
- M1-06: Write `src/epub2audio/epub/navigation.py` — extract spine order + EPUB3 nav + EPUB2 NCX → list[NavigationEntry]. Never assume filename order = reading order.
- M1-07: Write `src/epub2audio/epub/chapters.py` — scoring engine per architecture.md scoring table → list[ChapterCandidate] → list[Chapter]. Score ≥ 2 → include, 0-1 → warn, < 0 → exclude.
- M1-08: Write `src/epub2audio/epub/cover.py` — extract cover image bytes.
- M1-09: Write `src/epub2audio/epub/cleanup.py` — minimal XHTML → plain text for Milestone 1 (word count only; full cleanup deferred to M2).
- M1-10: Write `src/epub2audio/utils/names.py` — filename sanitisation. Must handle: Windows reserved names, special chars, > 200 char names, duplicate titles (suffix with -2 -3 etc), return format "NNN - Title.mp3".
- M1-11: Write `src/epub2audio/cli.py` — Typer app with `inspect` command. Rich table output showing: chapter number, title, source doc(s), word count, status (included/warned/excluded), reason. Also `--json` flag for machine-readable output.
- Hard constraints: epub/ must never import from tts/, audio/, or pipeline/. Only models.py types as return values.
- Acceptance: `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` produces readable table output.

#### tasks/active/M1-tester.md
Task contract for the Tester covering M1-12 through M1-17:
- M1-12: Write `tests/fixtures/builders.py` — programmatic EPUB factory using ebooklib. Must support building: simple EPUB3 with nav doc, simple EPUB2 with NCX, multi-chapter single XHTML file. No copyrighted content — use generated placeholder text.
- M1-13: Generate `tests/fixtures/simple_epub3.epub` by running the builder. 2 chapters, cover image, nav doc.
- M1-14: Generate `tests/fixtures/simple_epub2.epub` by running the builder. 2 chapters, NCX toc.
- M1-15: Write `tests/epub/test_metadata.py` — test BookMetadata extraction: title, author, language, identifier.
- M1-16: Write `tests/epub/test_navigation.py` — test spine ordering (filename order ≠ reading order), EPUB3 nav resolution, EPUB2 NCX resolution, fragment resolution.
- M1-17: Write `tests/epub/test_chapters.py` — test scoring engine, chapter-title detection, front-matter classification, back-matter classification.
- Hard constraints: never commit copyrighted content. Test behaviour not implementation. Never suppress a failing test.
- Acceptance: `uv run pytest tests/epub/ -v` passes with no suppressed failures.

### 4. Move completed pre-work tasks

Write `tasks/completed/PRE-01.md` and `tasks/completed/PRE-02.md` with completion notes.

### 5. Update docs/status.md

Update status: Milestone 1 is now In Progress. List the three active task contracts and the agents assigned to them.

## Constraints

- Do not write feature code — create stubs and task contracts only.
- Make the task contracts concrete enough that each agent can execute without ambiguity.
- If uv sync or the importability check fails, fix it before declaring PRE-02 done.

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