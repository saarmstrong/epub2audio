# Backlog

Tasks are ordered by milestone. Move a task to `tasks/active/` when starting it,
then to `tasks/completed/` when done and reviewed.

---

## Pre-work

- [ ] `PRE-01` — Create `src/epub2audio/` package skeleton (all `__init__.py` stubs)
- [ ] `PRE-02` — Run `uv sync` and verify the package is importable

---

## Milestone 1 — Inspectable EPUB Plan

- [ ] `M1-01` — Write `models.py`: all Pydantic models (`BookMetadata`, `BookDocument`, `NavigationEntry`, `ChapterCandidate`, `Chapter`, `ConversionPlan`, etc.)
- [ ] `M1-02` — Write `errors.py`: domain exceptions (`InvalidEpubError`, `DrmProtectedEpubError`, `MissingDependencyError`, etc.)
- [ ] `M1-03` — Write `config.py`: TOML config, Pydantic settings, precedence logic
- [ ] `M1-04` — Write `epub/reader.py`: safe EPUB open (ZIP traversal guard, DRM detection, zip-bomb check)
- [ ] `M1-05` — Write `epub/metadata.py`: extract `BookMetadata` from OPF
- [ ] `M1-06` — Write `epub/navigation.py`: spine order + EPUB3 nav + EPUB2 NCX → `NavigationEntry[]`
- [ ] `M1-07` — Write `epub/chapters.py`: scoring engine → `ChapterCandidate[]` → `Chapter[]`
- [ ] `M1-08` — Write `epub/cover.py`: extract cover image bytes
- [ ] `M1-09` — Write `epub/cleanup.py`: basic XHTML → plain text (enough for word count in inspect)
- [ ] `M1-10` — Write `utils/names.py`: filename sanitisation, duplicate resolution
- [ ] `M1-11` — Write `cli.py`: `inspect` command (Rich table + `--json`)
- [ ] `M1-12` — Write `tests/fixtures/builders.py`: programmatic EPUB factory
- [ ] `M1-13` — Generate `tests/fixtures/simple_epub3.epub` via builder
- [ ] `M1-14` — Generate `tests/fixtures/simple_epub2.epub` via builder
- [ ] `M1-15` — Write `tests/epub/test_metadata.py`
- [ ] `M1-16` — Write `tests/epub/test_navigation.py`
- [ ] `M1-17` — Write `tests/epub/test_chapters.py`
- [ ] `M1-18` — Reviewer: run `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` and verify output

---

## Milestone 2 — Fake-TTS Audiobook Pipeline

- [ ] `M2-01` — Extend `epub/cleanup.py`: full HTML→text (footnotes, lists, images, tables)
- [ ] `M2-02` — Write `text/normalize.py`: conservative unicode/punct normalization
- [ ] `M2-03` — Write `text/segment.py`: paragraph→sentence→clause segmentation
- [ ] `M2-04` — Write `text/pauses.py`: silence insertion specs
- [ ] `M2-05` — Write `tts/base.py`: `TTSEngine` Protocol
- [ ] `M2-06` — Write `tts/fake.py`: `FakeTTSEngine` (deterministic silence/tone)
- [ ] `M2-07` — Write `audio/chunks.py`: `AudioChunk` helpers
- [ ] `M2-08` — Write `audio/concatenate.py`: WAV concatenation via soundfile
- [ ] `M2-09` — Write `audio/encode.py`: FFmpeg MP3 encoding
- [ ] `M2-10` — Write `audio/normalize.py`: FFmpeg two-pass loudness normalization
- [ ] `M2-11` — Write `audio/metadata.py`: FFmpeg ID3 + cover art embedding
- [ ] `M2-12` — Write `audio/validate.py`: FFprobe validation
- [ ] `M2-13` — Write `utils/subprocess.py`: safe subprocess runner
- [ ] `M2-14` — Write `utils/files.py`: safe temp files, atomic replace, disk space check
- [ ] `M2-15` — Write `pipeline/planner.py`: `ConversionPlan` from parsed EPUB
- [ ] `M2-16` — Write `pipeline/manifest.py`: write/read `ConversionManifest` (atomic)
- [ ] `M2-17` — Write `pipeline/resume.py`: fingerprint + skip valid segments
- [ ] `M2-18` — Write `pipeline/converter.py`: full pipeline orchestration
- [ ] `M2-19` — Extend `cli.py`: `convert` command with all flags
- [ ] `M2-20` — Write `tests/test_e2e.py`: end-to-end test with `FakeTTSEngine`
- [ ] `M2-21` — Reviewer: verify all fixture chapters produce valid MP3s

---

## Milestone 3 — Kokoro Integration

- [ ] `M3-01` — Write `tts/kokoro.py`: `KokoroTTSEngine` (all kokoro imports isolated here)
- [ ] `M3-02` — Write `tts/voices.py`: voice catalogue, language→lang_code map
- [ ] `M3-03` — Extend `cli.py`: `voices` command
- [ ] `M3-04` — Extend `cli.py`: `doctor` command (Python, FFmpeg, FFprobe, espeak-ng, Kokoro, model, disk)
- [ ] `M3-05` — Write `tests/tts/test_kokoro_smoke.py` (marked `@pytest.mark.slow @pytest.mark.requires_model`)
- [ ] `M3-06` — Reviewer: run `epub2audio doctor` and `epub2audio voices` and verify

---

## Milestone 4 — Reliability

- [ ] `M4-01` — Manifest: atomic write, fingerprint verification on resume
- [ ] `M4-02` — Resume: verify config hash, invalidate affected artifacts on change
- [ ] `M4-03` — Retry logic: configurable retries, reduce segment size on length error
- [ ] `M4-04` — Disk space pre-flight check in converter
- [ ] `M4-05` — Write `conversion-report.json` on completion
- [ ] `M4-06` — Write `metadata.json` on completion
- [ ] `M4-07` — Write `tests/pipeline/test_manifest.py`: serialisation + invalidation
- [ ] `M4-08` — Reviewer: interrupt a conversion mid-chapter, restart, verify resume

---

## Milestone 5 — Chapter-Detection Hardening

- [ ] `M5-01` — Multi-chapter XHTML splitting (fragment anchors + heading evidence)
- [ ] `M5-02` — Cross-file chapter merging (consecutive files = one logical chapter)
- [ ] `M5-03` — Fragment-based TOC link resolution
- [ ] `M5-04` — Footnote modes: `skip` / `inline` / `end-of-chapter`
- [ ] `M5-05` — Add all 21 adversarial fixture types to `builders.py`
- [ ] `M5-06` — Write tests for all adversarial fixtures
- [ ] `M5-07` — Reviewer: verify all fixtures produce deterministic, correct chapter plans

---

## Milestone 6 — Release Readiness

- [ ] `M6-01` — Complete `README.md`
- [ ] `M6-02` — Write `docs/architecture.md` (final)
- [ ] `M6-03` — Write `CONTRIBUTING.md`
- [ ] `M6-04` — Write `TROUBLESHOOTING.md`
- [ ] `M6-05` — Write `CHANGELOG.md`
- [ ] `M6-06` — Add `LICENSE`
- [ ] `M6-07` — Write GitHub Actions CI (ruff + mypy + pytest on macOS + Linux)
- [ ] `M6-08` — Add example `epub2audio.toml`
- [ ] `M6-09` — Reviewer: verify all 20 acceptance criteria

---

## Milestone 7 — M4B Output Format

- [x] `M7-*` — `--format m4b` single-file audiobook (complete; Reviewer-approved 2026-07-12)

---

## Milestone 8 — Narration Data Models + Rule-Based Director Skeleton

_Design: `docs/decisions/003-narration-pipeline.md`. Rule-based (deterministic, no LLM), additive._

- [x] `M8-01` — Architect: add `NarrationDirection`, `NarrationSegment`, `NarrationPlan` to `models.py` (frozen Pydantic, matching Feature.md JSON shape)
- [x] `M8-02` — TTS Engineer: create `director/` package with rule-based `build_narration_plan(chapter_text, chapter_index) -> NarrationPlan`
- [x] `M8-03` — TTS Engineer: scene grouping + one `default_direction` per scene; local overrides only on significant emotion/intensity change
- [x] `M8-04` — TTS Engineer: dialogue detection + likely-speaker labelling (quote/attribution heuristics); reuse `text/segment.py`
- [x] `M8-05` — TTS Engineer: fold `text/pauses.py` pause timing + emphasis hints into plan segments; never rewrite prose
- [x] `M8-06` — Tester: `tests/director/` unit tests for narration plans (deliverable #7) incl. "text preserved / no invented dialogue" assertions
- [x] `M8-07` — Reviewer: verify plans are deterministic and provider-neutral (no SSML / engine tokens)

---

## Milestone 9 — Provider-Adapter Abstraction + Kokoro Adapter

- [x] `M9-01` — Architect: `providers/base.py` — `NarrationProvider` Protocol (`render()` + `synthesize()`) and `ProviderRequest` model
- [x] `M9-02` — TTS Engineer: `providers/kokoro.py` — wrap `KokoroTTSEngine`; punctuation optimization, pause insertion, long-segment splitting, pronunciation-dict application, speed mapping (mapping only, no analysis)
- [x] `M9-03` — Architect: interface stubs `providers/{openai,gemini,azure,elevenlabs}.py` (Protocol + `NotImplementedError` + docstrings)
- [x] `M9-04` — Audio Engineer: inject `NarrationProvider` into `pipeline/converter.py`; drive Director → render → synthesize; re-key segment resume on plan-segment hash
- [x] `M9-05` — Tester: adapter unit tests + boundary test (no analysis logic / cross-layer imports in `providers/`)
- [x] `M9-06` — Reviewer: verify MP3 + M4B outputs unchanged; adding a provider needs no pipeline/director edits

_Carry-forward from M8 review (non-blocking):_
- [x] `M9-07` — Tidy: `director/plan._pause_after_ms` re-segments an already-segmented `TextSegment`; pass the `TextSegment` to `get_pause` instead of re-running `segment_text`
- [x] `M9-08` — Tidy: remove `# type: ignore[arg-type]` in `director/emphasis.py` by typing `_add(level: Literal["light","moderate","strong"])`
- [x] `M9-09` — Tester: add end-to-end **completeness** assertion (all non-divider narration text lands in some segment), not just substring containment

---

## Milestone 10 — Pronunciation Subsystem

- [x] `M10-01` — TTS Engineer: `pronunciation/` — load `pronunciations.yaml` into a provider-neutral lexicon + matcher
- [x] `M10-02` — Architect: add YAML dependency; decision record if choice is non-trivial
- [x] `M10-03` — TTS Engineer: Director emits pronunciation hints; Kokoro adapter applies them
- [x] `M10-04` — `config.py`: add `pronunciation_dictionary` path setting
- [x] `M10-05` — Tester: lexicon load + application tests; example `pronunciations.yaml`
- [x] `M10-06` — Reviewer: verify hints are provider-neutral and applied only in adapters
- [x] `M10-07` (review-found defect) — wire `pronunciation_dictionary` end-to-end: `convert_epub` loads the lexicon and threads it into `build_narration_plan`; + ffmpeg-gated e2e wiring tests; + `examples/pronunciations.yaml`. Independent Reviewer APPROVED (`c06c00c`).

---

## Milestone 11 — Optional Validation Stage

- [x] `M11-01` — Audio Engineer: `validation/` — skipped text, missing chapters, invalid metadata, overlapping timestamps, chapter-duration consistency, pronunciation failures
- [x] `M11-02` — Audio Engineer: CLI `--validate` flag → validation report next to `conversion-report.json` (off by default)
- [x] `M11-03` — Tester: validation-stage unit tests
- [x] `M11-04` — Reviewer: run `convert --validate`, verify report + no false positives on fixtures

---

## Milestone 12 — Additive Restructure Reconciliation + Config + Docs

- [x] `M12-01` — Add `output/` + `metadata/` thin re-export shims toward Feature.md layout (keep `src/` importable)
- [x] `M12-02` — `config.py`: add `provider`, `scene_analysis`, and `output_format: both`
- [x] `M12-03` — Wire `output_format: both` (emit MP3 and M4B in one run)
- [x] `M12-04` — Write `docs/architecture.md` narration-pipeline section (deliverable #6)
- [x] `M12-05` — Update README + CHANGELOG + example `epub2audio.toml`
- [x] `M12-06` — Reviewer: verify all Feature.md deliverables (1–7) satisfied

_Carry-forward from M11 review (non-blocking):_
- [x] `M12-07` — Validation: flag a `None` M4B `output_path` as `missing_output_file` when chapters exist (currently only caught indirectly via `report.errors`)
- [x] `M12-08` — Tests: broaden the `validation/` AST import-boundary test to cover `import x` statements and `__init__.py` (not just `ImportFrom` in `checks.py`)
- [x] `M12-09` — Consider a `model_validator` on `ValidationReport` to prevent count drift on externally-constructed/deserialized reports (or document the ADR-006 tradeoff explicitly)

---

## Milestones 13–16 — Proposed (not yet committed)

_Sourced from a feature comparison against [abogen](https://github.com/denizsafak/abogen)
and [TTS-Story](https://github.com/Xerophayze/TTS-Story). Full rationale, fit
assessment, and rejected candidates are in [docs/roadmap.md](../docs/roadmap.md) —
read it before starting any task below. Ranked 1 (highest value/effort) to 7._

### Milestone 13 — Per-Character Voices + Voice Presets (rank 1–2)

_Design note: `voice_map` and `custom_*` voice resolution belong in the
provider/`tts` layer, not `director/` — the Director must stay provider-neutral
per ADR-003. Write a decision record if the config shape is non-obvious._

- [ ] `M13-01` — Architect: design `voice_map` config shape (TOML table,
      speaker name → voice id) and where it's resolved (provider boundary);
      decision record if non-trivial
- [ ] `M13-02` — TTS Engineer: `providers/kokoro.py` — resolve
      `NarrationSegment.speaker` to a mapped voice, fall back to default
      `--voice` for unmapped/`"unknown"` speakers
- [ ] `M13-03` — Tester: unit tests for voice-map resolution + fallback; no
      change to speaker detection itself (reuse M8 heuristics)
- [ ] `M13-04` — Audio/Validation: extend `validation/` to flag speakers with
      no voice mapping and no fallback as a `ValidationIssue` (not silent)
- [ ] `M13-05` — TTS Engineer: `tts/voices.py` — parse `custom_<name> =
      "af_heart:0.6,af_bella:0.4"` config entries into resolved Kokoro voice
      blends
- [ ] `M13-06` — CLI: `voices` command lists custom presets alongside built-in
      voices; `--sample custom_<name>` reuses existing sample-generation path
- [ ] `M13-07` — TTS Engineer: validate blend weights + referenced base voices
      exist, reusing `UnknownVoiceError`
- [ ] `M13-08` — Reviewer: verify Director stays provider-neutral (no
      speaker/voice-map leakage outside `providers/`), voice-map fallback and
      blend validation both covered by tests

### Milestone 14 — Subtitles + GPU Backend Detection (rank 3–4)

- [ ] `M14-01` — Audio Engineer: `audio/subtitles.py` — write SRT/VTT from
      existing per-segment `TextSegment.audio_duration` data; one file per
      chapter (MP3 mode) or one for the book (M4B mode)
- [ ] `M14-02` — CLI: `--subtitle-format {none,srt,vtt}` on `convert`
      (default `none`)
- [ ] `M14-03` — Tester: subtitle-timing tests against known segment durations
- [ ] `M14-04` — Reliability Specialist: `doctor` — detect available
      acceleration backend (MPS / CUDA / CPU); report without changing
      CPU-only exit-code semantics
- [ ] `M14-05` — TTS Engineer: `tts/kokoro.py` — pass through explicit device
      selection when the installed `kokoro`/`torch` build supports it; log and
      fall back to CPU if unavailable, never fail silently
- [ ] `M14-06` — Reviewer: verify CPU-only environments are unaffected
      (Apple Silicon / Intel macOS / Linux priority order unchanged)

### Milestone 15 — Plain-Text Input + Batch Mode (rank 5–6)

- [ ] `M15-01` — Architect: define a format-agnostic reader interface
      alongside `epub/reader.py` (does not reuse EPUB spine/TOC/NCX scoring)
- [ ] `M15-02` — EPUB/Text Specialist: `.txt`/`.md` reader; chapter boundaries
      from explicit markers first, heading-pattern fallback (reuse title
      patterns from `epub/chapters.py`, not EPUB-specific scoring)
- [ ] `M15-03` — Document as a known limitation: no front/back-matter
      classification for non-EPUB input (no semantic types available)
- [ ] `M15-04` — Tester: fixtures + tests for marker-based and heading-fallback
      chapter detection on plain text
- [ ] `M15-05` — CLI: accept multiple/glob input paths on `convert` for
      sequential batch conversion (no new subcommand)
- [ ] `M15-06` — Reliability Specialist: aggregate Rich progress across a
      multi-book run; each book keeps its own manifest/resume state unchanged
- [ ] `M15-07` — Reviewer: verify batch mode doesn't violate the
      single-worker-TTS default and per-book resume is unaffected

### Milestone 16 — Local Voice-Cloning Provider (rank 7, stretch)

- [ ] `M16-01` — Architect: pick one candidate engine (e.g. Chatterbox/VoxCPM/
      IndexTTS) and verify it is fully offline-capable after model download —
      same network bar as Kokoro — before any implementation starts
- [ ] `M16-02` — TTS Engineer: new `providers/<engine>.py` implementing
      `NarrationProvider` (first real non-Kokoro adapter; existing stubs in
      `providers/{openai,gemini,azure,elevenlabs}.py` establish the shape)
- [ ] `M16-03` — TTS Engineer: local reference-sample storage (a config-pointed
      directory, not a managed service)
- [ ] `M16-04` — Tester: adapter unit tests + boundary test (no cross-layer
      imports, matching the M9-05 pattern)
- [ ] `M16-05` — Reviewer: verify no network calls occur during synthesis;
      verify adding this provider required no `director/`/pipeline edits
