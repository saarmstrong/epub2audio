# epub2audio — Product Specification

> Source of truth for what this tool must do. Derived from `CLAUDE.md`.
> If CLAUDE.md and this file conflict, CLAUDE.md wins until this file is updated.

---

## Primary User Story

```
epub2audio book.epub --output ./audiobooks
```

Produces:

```
audiobooks/
└── Book Title/
    ├── cover.jpg
    ├── metadata.json
    ├── 001 - Chapter One.mp3
    ├── 002 - Chapter Two.mp3
    └── conversion-report.json
```

One MP3 per logical chapter. Track order matches EPUB reading order.

---

## CLI Commands

| Command | Purpose |
|---|---|
| `epub2audio BOOK.epub` | Alias for convert |
| `epub2audio convert BOOK.epub` | Convert EPUB to MP3 chapters |
| `epub2audio inspect BOOK.epub` | Show conversion plan without generating audio |
| `epub2audio voices` | List available Kokoro voices |
| `epub2audio doctor` | Check environment and dependencies |
| `epub2audio config show\|path\|init` | Manage configuration |

### Convert options

```
--output PATH
--voice VOICE
--language LANGUAGE
--speed FLOAT
--bitrate BITRATE
--sample-rate INTEGER
--normalize / --no-normalize
--resume / --no-resume
--overwrite
--include-front-matter
--include-back-matter
--chapter REGEX_OR_NUMBER
--chapter-start INTEGER
--chapter-end INTEGER
--dry-run
--keep-intermediates
--workers INTEGER
--config PATH
--verbose
--quiet
```

### Defaults

| Setting | Default |
|---|---|
| Voice | `af_heart` |
| Language | Inferred from EPUB metadata, fallback `en-us` |
| Speed | `1.0` |
| Bitrate | `96k` |
| Output | Current directory |
| Normalize | Enabled |
| Resume | Enabled |
| Intermediates | Deleted after successful conversion |
| Workers | `1` |

---

## Chapter Detection

Chapter boundaries are determined by scoring candidate documents/sections across
multiple signals. See `docs/architecture.md` for the scoring table.

### Recognized chapter-title patterns

- Chapter 1, Chapter One, CHAPTER I
- 1, I (standalone)
- Prologue, Epilogue, Introduction
- Part One, Book Two, Interlude, Afterword

### Front matter (excluded by default)

cover, title page, copyright, dedication, contents, table of contents,
foreword, preface, acknowledgments

> Forewords, prefaces, introductions, afterwords, and appendices are **not** excluded
> merely because they are unnumbered. Only obvious navigation-only or empty pages are
> excluded unconditionally.

### Back matter (excluded by default)

notes, bibliography, glossary, index, about the author, also by, advertisements

---

## Audio Pipeline

```
EPUB chapter
→ cleaned chapter text
→ text segments
→ Kokoro audio pieces
→ segment WAV files
→ chapter WAV
→ normalized chapter audio  (-18 LUFS, -2 dBTP, LRA 7 LU)
→ chapter MP3  (96 kbps, mono, 24 kHz)
→ metadata + cover embedded
→ FFprobe validation
```

---

## MP3 Metadata

Embed when available: title, album (book title), artist (author), album artist,
track number, total tracks, genre (`Audiobook`), date, comment, cover art.

---

## Resume & Recovery

- Manifest written before synthesis begins.
- On restart: verify EPUB fingerprint + config hash; reuse valid segments.
- Voice, speed, language, segmentation, or audio setting changes → invalidate affected artifacts.
- Manifests written atomically.
- Chapter not marked complete until final MP3 passes FFprobe validation.

---

## Validation

Every final MP3 checked with FFprobe:
- File exists and is non-empty
- Audio stream present, codec is MP3
- Duration > 0 and plausible for word count
- Expected sample rate and channel count
- Metadata present

---

## Security Constraints

- Path traversal prevention on ZIP entries
- No unsafe XML external entity expansion
- FFmpeg invoked via argument arrays — never shell interpolation
- No script or active content from EPUB is executed
- No book content in logs
- No telemetry

---

## Legal Boundary

- DRM-protected EPUBs → clear error, nonzero exit, no processing
- No DRM-removal functionality exists or will be added
- No content transmitted to external services

---

## Out of Scope for v1

DRM removal · GUI · mobile · voice cloning · character-specific voices ·
LLM rewriting · cloud TTS · full DAISY · M4B output · Audiobookshelf integration ·
distributed synthesis · real-time playback
