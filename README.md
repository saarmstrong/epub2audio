# epub2audio

Convert EPUB ebooks into audiobooks using local, offline text-to-speech.

> **Legal notice:** This tool is intended for ebooks you have the legal right to process.
> It does not remove DRM. DRM-protected EPUBs are rejected with a clear error message.
> No book content is transmitted to any external service.

---

## Status

🚧 **Under active development.** See [`docs/status.md`](docs/status.md) for current milestone.

---

## What it does

`epub2audio` reads an EPUB file, detects logical chapters in reading order, converts each
chapter to speech using [Kokoro TTS](https://github.com/remsky/Kokoro-FastAPI), and
writes one MP3 file per chapter with embedded metadata and cover art.

```
audiobooks/
└── My Book/
    ├── cover.jpg
    ├── metadata.json
    ├── 001 - Prologue.mp3
    ├── 002 - Chapter One.mp3
    └── conversion-report.json
```

---

## Platform support

| Platform | Status |
|---|---|
| Apple Silicon macOS | Primary target |
| Intel macOS | Supported |
| Linux | Supported |
| Windows | Not yet verified |

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- FFmpeg + FFprobe
- espeak-ng (required by Kokoro on some platforms)

### Install system dependencies

**macOS**
```bash
brew install ffmpeg espeak-ng
```

**Debian / Ubuntu**
```bash
sudo apt-get install ffmpeg espeak-ng
```

---

## Installation

```bash
git clone https://github.com/yourname/epub2audio
cd epub2audio
uv sync
```

---

## Quick start

```bash
# Check your environment
uv run epub2audio doctor

# Preview chapter detection without generating audio
uv run epub2audio inspect book.epub

# Convert
uv run epub2audio convert book.epub --output ./audiobooks
```

---

## Commands

### `inspect`
Parse an EPUB and display the proposed conversion plan — chapters, word counts,
inclusion/exclusion decisions — without generating any audio.

```bash
epub2audio inspect book.epub
epub2audio inspect book.epub --json
```

### `convert`
Convert an EPUB to MP3 audiobook chapters.

```bash
epub2audio convert book.epub \
  --output ./audiobooks \
  --voice af_heart \
  --language en-us \
  --speed 1.0 \
  --bitrate 96k \
  --normalize \
  --resume
```

Key flags:
- `--dry-run` — plan and validate without generating audio
- `--resume` / `--no-resume` — continue an interrupted conversion
- `--include-front-matter` — include cover, title page, copyright, etc.
- `--include-back-matter` — include index, bibliography, etc.
- `--chapter N` — convert only chapter N (number or regex)
- `--verbose` — show full diagnostic output

### `voices`
List available Kokoro voices grouped by language.

```bash
epub2audio voices
epub2audio voices --sample af_heart
```

### `doctor`
Check that all required tools and models are installed and working.

```bash
epub2audio doctor
```

### `config`
Manage the TOML configuration file.

```bash
epub2audio config show
epub2audio config path
epub2audio config init
```

---

## Configuration

`epub2audio` reads `epub2audio.toml` from the current directory, then
`~/.config/epub2audio/config.toml`. CLI flags always take precedence.

```toml
[tts]
voice = "af_heart"
language = "en-us"
speed = 1.0

[audio]
format = "mp3"
bitrate = "96k"
sample_rate = 24000
normalize = true
loudness_lufs = -18.0
true_peak_db = -2.0

[conversion]
resume = true
include_front_matter = false
include_back_matter = false
keep_intermediates = false
workers = 1

[text]
announce_chapter_titles = true
pause_after_heading_ms = 700
pause_between_sections_ms = 450
pause_between_paragraphs_ms = 180
```

---

## Resume behaviour

If a conversion is interrupted, re-run the same command. epub2audio will verify the
EPUB fingerprint and configuration, then skip already-completed segments and chapters.
Change voice, speed, language, or audio settings to invalidate cached audio automatically.

---

## Privacy

- All processing is local. No content, metadata, or audio leaves your machine.
- No telemetry is collected or transmitted.
- Book text is never written to log files.

---

## Current limitations

See [`docs/status.md`](docs/status.md) for what is and is not yet implemented.

- No DRM removal (by design)
- No M4B output (planned)
- No graphical interface (planned)
- Windows support not yet verified
