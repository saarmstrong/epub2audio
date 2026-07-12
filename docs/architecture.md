# epub2audio — Architecture

---

## Guiding Principles

1. **EPUB parser never calls Kokoro.** The two subsystems are fully decoupled.
2. **Kokoro adapter knows nothing about EPUB.** It receives plain text strings.
3. **FFmpeg always via argument arrays.** Never shell string interpolation.
4. **Stream, don't buffer.** Process segments and chapters incrementally; never hold a
   full decoded audiobook in memory.
5. **Reliability before concurrency.** Default to 1 TTS worker. Parallelise only encoding
   and validation where safe.
6. **Interfaces first.** TTS and audio encoder are Protocols so they can be swapped.

---

## Module Map

```
src/epub2audio/
├── cli.py              Typer app, all commands, Rich output
├── config.py           TOML + Pydantic settings, config precedence
├── models.py           All shared Pydantic data models
├── errors.py           Domain exceptions
├── logging.py          Structured logging setup (never logs book text)
│
├── epub/
│   ├── reader.py       Open EPUB safely (ZIP traversal guard, DRM detection)
│   ├── metadata.py     Extract BookMetadata from OPF
│   ├── navigation.py   Spine order, EPUB3 nav, EPUB2 NCX → NavigationEntry[]
│   ├── chapters.py     Scoring engine → ChapterCandidate[] → Chapter[]
│   ├── cleanup.py      XHTML → clean narration text
│   └── cover.py        Extract cover image bytes
│
├── text/
│   ├── normalize.py    Conservative unicode/punct normalization
│   ├── segment.py      Chapter text → TextSegment[] (para/sentence/clause)
│   ├── pronunciation.py Pronunciation dictionary substitution
│   └── pauses.py       Silence insertion specifications
│
├── tts/
│   ├── base.py         TTSEngine Protocol
│   ├── kokoro.py       KokoroTTSEngine (all kokoro imports isolated here)
│   └── voices.py       Voice catalogue, language→lang_code map
│
├── audio/
│   ├── chunks.py       AudioChunk model and helpers
│   ├── concatenate.py  WAV concatenation via soundfile
│   ├── encode.py       FFmpeg MP3 encoding
│   ├── normalize.py    FFmpeg two-pass loudness normalisation
│   ├── metadata.py     FFmpeg ID3 + cover art embedding
│   └── validate.py     FFprobe validation
│
├── pipeline/
│   ├── planner.py      ConversionPlan from parsed EPUB
│   ├── converter.py    Orchestrate full pipeline
│   ├── manifest.py     Write/read ConversionManifest (atomic)
│   └── resume.py       Fingerprint check, skip valid segments
│
└── utils/
    ├── files.py        Safe temp files, atomic replace, disk space
    ├── names.py        Filename sanitisation, duplicate resolution
    └── subprocess.py   Safe subprocess runner (arg arrays only)
```

---

## Core Data Models (`models.py`)

| Model | Purpose |
|---|---|
| `BookMetadata` | Title, author, language, identifier, publisher, date, rights |
| `BookDocument` | One XHTML spine item: path, content hash, nav entries |
| `NavigationEntry` | TOC/NCX entry: title, doc path, fragment, depth |
| `ChapterCandidate` | Scored candidate with signals and score breakdown |
| `Chapter` | Confirmed chapter: title, source docs, word count, stable ID |
| `TextSegment` | One TTS call unit: text, hashes, word count, status, audio path |
| `AudioChunk` | Raw audio from one TTS call: numpy array, sample rate |
| `ConversionPlan` | Ordered list of Chapter objects with effective config snapshot |
| `ConversionManifest` | Full run state for resume: segments, hashes, paths, timestamps |
| `ChapterResult` | Per-chapter outcome: duration, warnings, output path |
| `ConversionReport` | Final JSON report written to output directory |

---

## TTS Engine Protocol

```python
class TTSEngine(Protocol):
    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]: ...
```

Implementations: `KokoroTTSEngine`, `FakeTTSEngine` (tests only).

---

## Chapter-Detection Scoring

Each candidate document or section is scored. Threshold: ≥ 2 → include.

| Signal | Weight | Notes |
|---|---|---|
| TOC / NCX entry points here | +4 | Strongest signal |
| `epub:type="chapter"` or `"part"` | +3 | Semantic markup |
| `<h1>` / `<h2>` matches title pattern | +2 | "Chapter N", named chapters |
| Spine boundary | +1 | New file = possible boundary |
| CSS class/id contains "chapter" | +1 | Soft signal |
| Short document (< 200 words) | −2 | Probably nav/title/copyright |
| Title keyword in front/back matter set | −3 | "copyright", "index", "cover" |
| `epub:type` is front/back matter type | −3 | Publisher-declared |
| No readable text content | −10 | Hard exclude |

Score ≥ 2 → **include** · Score 0–1 → **warn** · Score < 0 → **exclude** (reason recorded)

---

## Configuration Precedence

1. CLI flags
2. `--config` file (explicit)
3. `epub2audio.toml` in current directory
4. `~/.config/epub2audio/config.toml`
5. Application defaults

---

## Audio Pipeline (per chapter)

```
Chapter text
  └─ cleanup.py       → plain text + pause markers
  └─ normalize.py     → normalized text
  └─ segment.py       → TextSegment[]
       └─ tts engine  → AudioChunk[] per segment
       └─ chunks.py   → segment WAV files
  └─ concatenate.py   → chapter WAV (lossless)
  └─ normalize.py     → loudness-normalized WAV (-18 LUFS, -2 dBTP)
  └─ encode.py        → chapter MP3 (96k, mono, 24 kHz)
  └─ metadata.py      → ID3 tags + cover art embedded
  └─ validate.py      → FFprobe check → ChapterResult
```

---

## Resume Strategy

1. Before synthesis: write `ConversionManifest` with EPUB fingerprint + config hash.
2. Each `TextSegment` has a `source_hash` and `normalized_hash`.
3. On restart: load manifest, verify fingerprint and config hash.
4. For each segment: if output WAV exists and hash matches → skip.
5. For each chapter: if final MP3 exists and passes FFprobe → skip.
6. If voice/speed/language/segmentation config changes → clear affected segment hashes.

---

## Security Notes

- ZIP entries validated against path traversal before extraction.
- XML parsed with `defusedxml` or lxml with entity expansion disabled.
- All subprocess calls use `subprocess.run(args_list, ...)` — no `shell=True`.
- Temporary files created with `tempfile.mkstemp` and cleaned up on success.
- Manifest written to `.tmp` then `os.replace()` (atomic on POSIX).
