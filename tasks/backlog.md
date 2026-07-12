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
