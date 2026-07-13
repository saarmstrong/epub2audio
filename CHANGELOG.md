# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
