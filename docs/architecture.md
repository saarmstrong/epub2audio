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
│   ├── pronunciation.py (legacy stub; pronunciation now lives in pronunciation/)
│   └── pauses.py       Silence insertion specifications
│
├── director/           Narration Director (Layer 1) — M8
│   ├── plan.py         build_narration_plan() → NarrationPlan[]
│   ├── scenes.py       Scene splitting on break lines
│   ├── scoring.py      Intensity/pace/mood signals (pure functions)
│   ├── dialogue.py     Dialogue detection + speaker attribution
│   └── emphasis.py     ALL-CAPS and *wrapped* emphasis hints
│
├── pronunciation/      Provider-neutral lexicon — M10
│   ├── lexicon.py      PronunciationLexicon, load_lexicon(path)
│   └── __init__.py     Public API re-export
│
├── providers/          Provider adapters (Layer 2) — M9
│   ├── base.py         NarrationProvider Protocol + ProviderRequest
│   ├── kokoro.py       KokoroProvider (wraps KokoroTTSEngine)
│   ├── openai.py       Stub — NotImplementedError
│   ├── gemini.py       Stub — NotImplementedError
│   ├── azure.py        Stub — NotImplementedError
│   └── elevenlabs.py   Stub — NotImplementedError
│
├── tts/                TTS engines (Layer 3)
│   ├── base.py         TTSEngine Protocol
│   ├── kokoro.py       KokoroTTSEngine (all kokoro imports isolated here)
│   └── voices.py       Voice catalogue, language→lang_code map
│
├── audio/
│   ├── chunks.py       AudioChunk helpers
│   ├── concatenate.py  WAV concatenation via soundfile
│   ├── encode.py       FFmpeg MP3 + AAC encoding
│   ├── normalize.py    FFmpeg two-pass loudness normalisation
│   ├── metadata.py     FFmpeg ID3 + cover art embedding
│   ├── chapters_meta.py FFmetadata chapter file for M4B
│   ├── mux_m4b.py      FFmpeg M4B container mux
│   └── validate.py     FFprobe validation (mp3 + aac + chapter count)
│
├── output/             Additive shim (Feature.md target layout) — M12
│   └── __init__.py     Re-exports: encode_mp3, encode_aac, build_m4b, …
│
├── metadata/           Additive shim (Feature.md target layout) — M12
│   └── __init__.py     Re-exports: embed_metadata, extract_metadata, BookMetadata
│
├── validation/         Optional post-conversion checks — M11
│   ├── checks.py       Pure check functions + validate_conversion()
│   └── __init__.py     Public API re-export
│
├── pipeline/
│   ├── planner.py      ConversionPlan from parsed EPUB
│   ├── converter.py    Orchestrate full pipeline (Director → provider → audio)
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
| `NarrationDirection` | Provider-neutral delivery: mood, pace, intensity |
| `NarrationSegment` | Directed narration unit: type, speaker, text, hints, pauses |
| `NarrationPlan` | Scene plan: chapter, scene, default direction, segments |
| `EmphasisHint` | Verbatim phrase + emphasis level |
| `PronunciationHint` | Verbatim term + IPA + respelling |
| `ValidationIssue` | Single validation finding: code, severity, message, chapter_id |
| `ValidationReport` | Aggregated validation result: ok, issues, severity counts |

---

## Narration Pipeline (M8–M12)

The narration pipeline introduces three new layers between text extraction and
TTS synthesis.  The existing audio assembly and output path are unchanged.

### Three-Layer Architecture

```
 EPUB
  │
  ▼
 epub/                          Layer 0 — EPUB parsing (unchanged)
  │  clean chapter text
  ▼
 director/                      Layer 1 — Narration Director
  │  NarrationPlan[] per scene
  │   ├─ NarrationDirection (mood, pace, intensity)
  │   └─ NarrationSegment[]  (type, speaker, text, emphasis, pauses,
  │                            pronunciation_hints)
  ▼
 providers/                     Layer 2 — Provider adapter (mapping only)
  │  ProviderRequest per segment
  │   ├─ Kokoro  → text (punctuation-normalised, respellings applied),
  │   │           voice, speed (pace × settings.speed)
  │   ├─ OpenAI  → text + instructions payload  [stub]
  │   ├─ Gemini  → text + narration prompt payload  [stub]
  │   ├─ Azure   → SSML payload  [stub]
  │   └─ ElevenLabs → voice_settings + prompt payload  [stub]
  ▼
 tts/                           Layer 3 — TTS engine (raw I/O, unchanged)
  │  AudioChunk[] per segment
  ▼
 audio/                         Audio assembly (unchanged)
  │  WAV concat → loudness normalise → encode → tag → validate
  ▼
 output/                        Output packaging (additive shim over audio/)
  └─ MP3 per chapter  (output_format: mp3 or both)
  └─ M4B single file  (output_format: m4b or both)
```

### Layer 1 — Narration Director (`director/`)

Fully deterministic rule-based analysis; no LLM, no network.  Identical
input always yields identical output (reproducible plans, safe for tests).

| Module | Responsibility |
|---|---|
| `scenes.py` | Split chapter on break lines (`* * *`, `---`); one scene per block |
| `scoring.py` | Pure-function intensity/pace/mood signals from text |
| `dialogue.py` | Detect spoken dialogue; attribute speaker (or `"unknown"`) |
| `emphasis.py` | ALL-CAPS and `*wrapped*` emphasis hints (verbatim substrings) |
| `plan.py` | Orchestrate → `NarrationPlan[]` (one per scene) |

**Invariants enforced by tests:**
- Every `NarrationSegment.text` is a substring of the normalized source text.
- No prose is rewritten; no dialogue invented.
- Plans contain no engine-specific data (no SSML, no Kokoro tokens).
- `scene_analysis=False` still strips divider lines (never narrated).

### Layer 2 — Provider Adapters (`providers/`)

Adapters are **thin mappers only** — no analysis, no scene logic.  They
receive a finished `NarrationSegment` with all delivery decisions made and
translate it to provider controls.

```python
class NarrationProvider(Protocol):
    def render(
        self,
        segment: NarrationSegment,
        defaults: NarrationDirection,
        settings: Settings,
    ) -> ProviderRequest: ...

    def synthesize(self, request: ProviderRequest) -> list[AudioChunk]: ...
```

**Adding a new provider = implementing this single Protocol.**  No changes to
the Director, pipeline, or audio assembly are required.

### Narration Plan Models (`models.py`)

| Model | Purpose |
|---|---|
| `NarrationDirection` | `mood`, `pace`, `intensity` — scene or segment delivery |
| `NarrationSegment` | `id`, `type`, `speaker`, `text`, `direction`, `pause_after_ms`, `pace`, `emphasis`, `pronunciation_hints` |
| `NarrationPlan` | `chapter`, `scene`, `default_direction`, `segments` |
| `EmphasisHint` | `phrase` (verbatim substring), `level` (`light`/`moderate`/`strong`) |
| `PronunciationHint` | `term` (verbatim substring), `ipa`, `respelling` |
| `ProviderRequest` | `segment_id`, `text`, `voice`, `language`, `speed`, `pause_after_ms`, `payload` |

### Pronunciation Subsystem (`pronunciation/`)

```
pronunciations.yaml
  └─ load_lexicon(path)  →  PronunciationLexicon
       └─ Director.build_narration_plan(text, chapter, lexicon=lex)
            └─ PronunciationHint[] on each segment
                 └─ KokoroProvider.render()  applies respelling substitution
```

- Lexicon loaded once per conversion run from `settings.pronunciation_dictionary`.
- Director emits hints (which terms appear) — it never applies them.
- Provider adapters apply them in provider-specific ways (Kokoro: text
  substitution; a future Azure adapter: SSML `<phoneme>`).
- A `null` respelling is a no-op for Kokoro (term flagged, original preserved).

### Full Narration Pipeline (per chapter, M8–M12)

```
Chapter text
  └─ epub/cleanup.py       → plain narration text
  └─ pronunciation/        → PronunciationLexicon (loaded once)
  └─ director/plan.py      → NarrationPlan[] per scene
       └─ scenes: scene splitting, one NarrationDirection per scene
       └─ dialogue: type/speaker classification
       └─ scoring: intensity/pace/mood signals
       └─ emphasis: ALL-CAPS and *wrapped* hints
       └─ pronunciation: lexicon term matching → PronunciationHint[]
  └─ providers/kokoro.py   → ProviderRequest per segment
       └─ resolve effective direction (per-segment or scene default)
       └─ pace × settings.speed = speed (clamped)
       └─ apply pronunciation respellings
       └─ normalize punctuation for Kokoro
  └─ tts/kokoro.py         → AudioChunk[] per segment
  └─ audio/chunks.py       → segment WAV files
  └─ audio/concatenate.py  → chapter WAV (lossless)
  └─ audio/normalize.py    → -18 LUFS, -2 dBTP
  └─ audio/encode.py       → MP3 (needs_mp3) and/or AAC (needs_m4b)
  └─ audio/metadata.py     → ID3 tags + cover art (MP3 only)
  └─ audio/validate.py     → FFprobe check → ChapterResult
```

### Output Format Selection

| `output_format` | Per-chapter MP3 | Book-level M4B | Report |
|---|---|---|---|
| `mp3` (default) | ✓ per chapter, ID3+cover | ✗ | `chapter_results[].output_path` = MP3 |
| `m4b` | ✗ | ✓ muxed after all chapters | `chapter_results[].output_path` = `None`; `report.output_path` = M4B |
| `both` | ✓ per chapter, ID3+cover | ✓ muxed after all chapters | `chapter_results[].output_path` = MP3; `report.output_path` = M4B |

Both MP3 and M4B are encoded from the **same** per-chapter loudness-normalised
WAV — no re-synthesis, no quality loss from transcoding.

### Validation Stage (`validation/`, optional `--validate`)

Pure post-conversion quality gate reading only the `ConversionReport`,
`ConversionPlan`, and `Settings`.  Zero imports from `epub/`, `director/`,
`providers/`, `tts/`, `audio/`, or `pipeline/`.

| Check | Severity | What it catches |
|---|---|---|
| `missing_chapter` | error | Plan chapters absent from the report |
| `skipped_text` | error | Chapter with words but zero/no audio |
| `invalid_metadata` | error | Empty title/author/language/identifier |
| `overlapping_timestamps` | error | M4B marker start ≥ end, or consecutive overlap |
| `non_contiguous_timeline` | warning | Gap between consecutive M4B markers |
| `chapter_duration` | warning | Zero-duration chapter (de-duped vs skipped) |
| `missing_output_file` | error | Output path recorded but file absent; null M4B output |
| `report_error` | error | Pipeline errors in `ConversionReport.errors` |
| `pronunciation` | — | Stub; real check deferred pending per-segment tracking |

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

See the full narration pipeline diagram in the **Narration Pipeline (M8–M12)**
section above.  The simplified audio-only view:

```
Chapter text
  └─ cleanup.py       → plain narration text
  └─ Director         → NarrationPlan[] (scenes/dialogue/emphasis/pauses)
  └─ Provider adapter → ProviderRequest[] (voice/speed/text/payload)
  └─ TTS engine       → AudioChunk[] per segment
  └─ chunks.py        → segment WAV files
  └─ concatenate.py   → chapter WAV (lossless)
  └─ normalize.py     → loudness-normalized WAV (-18 LUFS, -2 dBTP)
  └─ encode.py        → MP3 and/or AAC (same WAV, no re-synthesis)
  └─ metadata.py      → ID3 tags + cover art (MP3 path)
  └─ validate.py      → FFprobe check → ChapterResult
  └─ mux_m4b.py       → single .m4b (M4B/both path, after all chapters)
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
