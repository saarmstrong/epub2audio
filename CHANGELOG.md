# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Narration Director** (`director/`): deterministic, rule-based scene
  analysis that annotates text with mood, pace, intensity, dialogue/speaker,
  emphasis hints, and pause timing.  Provider-neutral — never rewrites prose
  or invents dialogue.  Controlled by `scene_analysis` setting.
- **Provider-adapter abstraction** (`providers/`): `NarrationProvider` Protocol
  with `render()` + `synthesize()` methods.  Adding a new TTS engine requires
  implementing this one interface.  Built-in: `KokoroProvider` (wraps
  `KokoroTTSEngine`).  Stubs: OpenAI, Gemini, Azure, ElevenLabs.
- **Pronunciation dictionary** (`pronunciation/`): `pronunciations.yaml` maps
  terms to IPA + respelling.  Director emits provider-neutral hints; adapters
  apply them (Kokoro: text substitution; future Azure: SSML `<phoneme>`).
  Configure via `pronunciation_dictionary` setting or `--config`.
- **`output_format: both`** (`--format both`): produce per-chapter MP3s and a
  single M4B in one run from the same synthesis pass; no re-encoding.
- **M4B output format** (`--format m4b`): a single `.m4b` audiobook (AAC) with
  embedded chapter markers, book-level tags, and cover art. The default
  remains one MP3 per chapter (`--format mp3`).
- **Optional validation stage** (`--validate`): post-conversion quality checks
  written to `validation-report.json`.  Checks: missing chapters, skipped text,
  invalid metadata, M4B timestamp overlaps, chapter-duration anomalies,
  missing output files, pipeline errors.
- **`provider` setting** (default `"kokoro"`): selects the TTS provider;
  validated at startup against the supported set.
- **`scene_analysis` setting** (default `true`): disable to treat each chapter
  as a single scene (divider lines still stripped; all other annotation
  preserved).
- `output/` and `metadata/` additive re-export shims toward the Feature.md
  target layout (`epub2audio.output`, `epub2audio.metadata`).
- `examples/pronunciations.yaml` and `examples/epub2audio.toml` reference
  configuration files.
- Per-chapter AAC segments are cached under `.epub2audio-work/`, so a failed
  final mux resumes without re-synthesizing audio.

## [0.1.0] - 2026-07-12

### Added

- Initial release of epub2audio
- EPUB to MP3 conversion using Kokoro TTS
- Automatic chapter detection from EPUB structure (TOC, spine, semantic markup)
- Multi-file chapter merging for EPUBs that split chapters across files
- Single-file chapter splitting for EPUBs with multiple chapters per file
- Resume interrupted conversions with segment-level caching
- Cover art and ID3 metadata embedding
- Loudness normalization (EBU R128: -18 LUFS, -2 dBTP)
- CLI commands:
  - `convert` — full EPUB to MP3 conversion
  - `inspect` — preview conversion plan
  - `voices` — list available Kokoro voices
  - `doctor` — check environment and dependencies
- Configuration via TOML files (`~/.config/epub2audio/config.toml` or `epub2audio.toml`)
- 9 Kokoro voices (American English male/female)
- Configurable voice, speed, language, bitrate, sample rate
- DRM detection (rejects protected EPUBs with clear error)
- No network calls — all processing is local

### Security

- No content sent to external services
- No DRM removal functionality
- FFmpeg invoked via argument arrays (no shell interpolation)
- Path traversal prevention on EPUB ZIP entries
