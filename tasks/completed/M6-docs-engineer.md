# M6 — Documentation Task: README & User Documentation

**Milestone:** 6 — Release readiness  
**Agent:** Any (can be done in parallel)  
**Depends on:** None  
**Blocks:** M6-reviewer

---

## Overview

Create user-facing documentation so a new user can install and use epub2audio
from the README. This addresses the acceptance criterion "New user can install from README".

---

## Deliverables

### D1: README.md

Create a comprehensive README with:

```markdown
# epub2audio

Convert EPUB ebooks to MP3 audiobooks using Kokoro TTS.

## Features

- One MP3 per logical chapter
- Automatic chapter detection from EPUB structure
- Multi-file chapter merging
- Single-file chapter splitting  
- Resume interrupted conversions
- Configurable voice, speed, language
- Cover art and metadata embedding
- Loudness normalization (EBU R128)

## Installation

### Prerequisites

- Python 3.11+
- FFmpeg (with libmp3lame)
- espeak-ng (for Kokoro phonemization)

### Install

\`\`\`bash
# Install from source
git clone https://github.com/user/epub2audio.git
cd epub2audio
uv sync

# Or with pip
pip install epub2audio
\`\`\`

### Install Kokoro TTS

\`\`\`bash
pip install kokoro
# Download model (first run will auto-download)
\`\`\`

## Quick Start

\`\`\`bash
# Convert an EPUB
epub2audio convert book.epub --output ./audiobooks

# Preview conversion plan
epub2audio inspect book.epub

# List available voices
epub2audio voices

# Check environment
epub2audio doctor
\`\`\`

## Configuration

Create `~/.config/epub2audio/config.toml`:

\`\`\`toml
voice = "af_heart"
language = "en-us"
speed = 1.0
bitrate = "96k"
normalize = true
\`\`\`

## CLI Reference

[Document all commands and options]

## Troubleshooting

[Common issues and solutions]
```

### D2: CHANGELOG.md

Create initial changelog:

```markdown
# Changelog

## [0.1.0] - 2026-07-12

### Added
- Initial release
- EPUB to MP3 conversion via Kokoro TTS
- Chapter detection with merge/split support
- Resume interrupted conversions
- Cover art and metadata embedding
- CLI commands: convert, inspect, voices, doctor
```

### D3: Update pyproject.toml

Ensure package metadata is complete:
- description
- authors  
- license
- repository URL
- keywords
- classifiers

### D4: LICENSE file

Add appropriate license file (MIT or Apache 2.0).

---

## Exit Criteria

- [ ] README.md with installation and usage instructions
- [ ] CHANGELOG.md with v0.1.0 release notes
- [ ] pyproject.toml metadata complete
- [ ] LICENSE file present
- [ ] A new user can follow README to install and run `epub2audio doctor`
