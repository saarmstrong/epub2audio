# epub2audio

Convert EPUB ebooks to MP3 audiobooks using Kokoro TTS.

## Features

- **Three output formats** — `--format mp3` (one MP3 per chapter, default), `--format m4b` (single M4B with chapter markers), or `--format both` (MP3s + M4B in one run)
- **Expressive narration** — Narration Director analyzes scenes, detects dialogue, attributes speakers, and sets pace/intensity per scene; never rewrites prose
- **Provider-agnostic** — add a new TTS engine by implementing one Protocol (`NarrationProvider`); Kokoro is the built-in provider; OpenAI/Gemini/Azure/ElevenLabs stubs ready
- **Pronunciation dictionary** — `pronunciations.yaml` for proper nouns, technical terms, invented words; provider-neutral hints applied per-adapter
- **Optional validation** — `--validate` runs post-conversion quality checks and writes `validation-report.json`
- **Automatic chapter detection** — from EPUB structure (TOC, spine, semantic markup, heading scoring)
- **Multi-file chapter merging** — combines split chapters into single tracks
- **Single-file chapter splitting** — separates combined chapters by TOC fragments
- **Resume interrupted conversions** — segment-level caching; pick up where you left off
- **Configurable voice, speed, language** — 9 Kokoro voices available
- **Cover art and metadata embedding** — ID3 tags (MP3) and book-level tags + cover (M4B)
- **Loudness normalization** — EBU R128 standard (-18 LUFS, -2 dBTP)
- **Local processing only** — no data sent to external services

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg (with libmp3lame encoder)
- espeak-ng (for Kokoro phonemization)

```bash
# macOS
brew install ffmpeg espeak-ng

# Ubuntu/Debian
sudo apt install ffmpeg espeak-ng

# Windows (via Chocolatey)
choco install ffmpeg espeak-ng
```

### Install epub2audio

```bash
# Clone and install with uv
git clone https://github.com/user/epub2audio.git
cd epub2audio
uv sync

# Or install with pip
pip install epub2audio
```

### Install Kokoro TTS

```bash
pip install kokoro misaki

# The model downloads automatically on first use (~400MB)
```

## Quick Start

```bash
# Convert an EPUB to MP3 audiobook
epub2audio convert book.epub --output ./audiobooks

# Preview conversion plan without generating audio
epub2audio inspect book.epub

# List available voices
epub2audio voices

# Check environment and dependencies
epub2audio doctor
```

## CLI Reference

### `convert` — Convert EPUB to audiobook

With `--format mp3` (default) produces one MP3 per chapter. With `--format m4b`
produces a single `.m4b` audiobook (AAC) with embedded chapter markers and cover
art. With `--format both`, produces both per-chapter MP3s and a single M4B in one
run from the same audio (no re-synthesis).

```bash
epub2audio convert BOOK.epub [OPTIONS]

Options:
  --output, -o PATH        Output directory [default: current dir]
  --voice TEXT             Kokoro voice [default: af_heart]
  --language TEXT          Language code [default: from EPUB or en-us]
  --speed FLOAT            Speech speed [default: 1.0]
  --format TEXT            Output format: mp3, m4b, or both [default: mp3]
  --bitrate TEXT           Audio bitrate [default: 96k]
  --sample-rate INT        Audio sample rate [default: 24000]
  --normalize / --no-normalize  Loudness normalization [default: enabled]
  --resume / --no-resume   Resume interrupted conversion [default: enabled]
  --overwrite              Overwrite existing files
  --include-front-matter   Include preface, foreword, etc.
  --include-back-matter    Include appendix, notes, etc.
  --chapter TEXT           Convert specific chapter (regex or number)
  --chapter-start INT      Start from chapter N
  --chapter-end INT        End at chapter N
  --dry-run                Show plan without converting
  --keep-intermediates     Preserve intermediate WAV files
  --workers INT            Parallel workers [default: 1]
  --validate               Run post-conversion quality checks; writes
                           validation-report.json [default: disabled]
  --config PATH            Config file path
  --verbose, -v            Verbose output
  --quiet, -q              Minimal output
```

### `inspect` — Preview Conversion Plan

```bash
epub2audio inspect BOOK.epub

# Shows:
# - Book metadata (title, author)
# - Chapter list with word counts
# - Excluded documents (front/back matter)
# - Scoring signals for each document
```

### `voices` — List Available Voices

```bash
epub2audio voices

# Shows table of 9 Kokoro voices with descriptions
```

### `doctor` — Check Environment

```bash
epub2audio doctor

# Checks: Python, FFmpeg, FFprobe, espeak-ng, Kokoro, disk space
# Exit 0 = all OK, Exit 1 = missing dependencies
```

## Configuration

Create `~/.config/epub2audio/config.toml`:

```toml
# Default voice (see 'epub2audio voices' for options)
voice = "af_heart"

# Language code (BCP-47)
language = "en-us"

# Speech speed multiplier
speed = 1.0

# MP3 encoding
bitrate = "96k"
sample_rate = 24000

# Processing options
normalize = true
resume = true
```

Or per-project `epub2audio.toml` in the current directory.

## Output Structure

```
audiobooks/
└── Book Title/
    ├── cover.jpg
    ├── metadata.json
    ├── 001 - Chapter One.mp3
    ├── 002 - Chapter Two.mp3
    ├── ...
    └── conversion-report.json
```

With `--format m4b`, a single file is written instead of per-chapter MP3s:

```
audiobooks/
└── Book Title.m4b        # single AAC audiobook with embedded chapter markers
```

With `--format both`, you get everything at once from a single synthesis pass:

```
audiobooks/
├── 001 - Chapter One.mp3
├── 002 - Chapter Two.mp3
├── ...
├── Book Title.m4b
└── conversion-report.json
```

## Pronunciation Dictionary

For proper nouns, technical terms, or invented words that Kokoro mispronounces,
create a `pronunciations.yaml` file (see `examples/pronunciations.yaml`):

```yaml
pronunciations:
  Ono-Sendai:
    ipa: "ˈoʊnoʊ sɛnˈdaɪ"
    respelling: "Oh-no Sen-DYE"
  Tessier-Ashpool:
    respelling: "Tess-ee-AY Ash-pool"
  Hosaka: "Ho-SAH-kah"        # shorthand: bare string = respelling
  Chiba: null                  # flag only; no substitution for Kokoro
```

Then reference it in your config or pass it on the command line:

```toml
# epub2audio.toml
pronunciation_dictionary = "pronunciations.yaml"
```

## Post-Conversion Validation

```bash
epub2audio convert book.epub -o ./out --validate
```

Writes `validation-report.json` alongside `conversion-report.json`.  Checks
include: missing chapters, skipped text, invalid metadata, M4B timestamp
overlaps, chapter-duration anomalies, and missing output files.

## Configuration

All settings can be set in `epub2audio.toml` (see `examples/epub2audio.toml`):

```toml
# Output format: mp3, m4b, or both
output_format = "mp3"

# TTS provider (kokoro is the only built-in provider)
provider = "kokoro"

# Voice and language
voice = "af_heart"
language = "en-us"
speed = 1.0

# Audio quality
bitrate = "96k"
sample_rate = 24000
normalize = true

# Narration Director
scene_analysis = true   # analyse scenes for direction; false = flat narration

# Pronunciation
pronunciation_dictionary = "pronunciations.yaml"  # optional
```

## Troubleshooting

### "FFmpeg not found"

Install FFmpeg with MP3 support:
```bash
# Verify installation
ffmpeg -version
ffprobe -version
```

### "espeak-ng not found"

Kokoro requires espeak-ng for phonemization:
```bash
# Verify installation
espeak-ng --version
```

### "Kokoro model not found"

The model downloads on first use. Ensure you have ~400MB free space and internet access.

### Chapters not detected correctly

Use `epub2audio inspect book.epub` to see scoring signals. Front/back matter is excluded by default; use `--include-front-matter` or `--include-back-matter` to include them.

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Type checking
uv run mypy src/epub2audio

# Linting
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Kokoro](https://github.com/hexgrad/kokoro) — High-quality TTS engine
- [ebooklib](https://github.com/aerkalov/ebooklib) — EPUB parsing
- [FFmpeg](https://ffmpeg.org/) — Audio encoding
