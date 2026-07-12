# epub2audio — Build Plan

> Status: **Not started** — repository is empty (only `CLAUDE.md` exists).
> This plan will be executed in the near future.

---

## State of the Repo

**Empty** — only `CLAUDE.md` exists. We're building from scratch.

---

## Build Plan — Fast Vertical Slices

The spec defines 6 milestones. Execution order is strictly sequential; each milestone must
be runnable before the next begins.

---

## Pre-work: Architecture & Skeleton

Do this first (~20 min), everything else depends on it.

| Task | What |
|---|---|
| `pyproject.toml` | uv project, all deps declared, entry point `epub2audio = "epub2audio.cli:app"` |
| `src/epub2audio/` layout | All module stubs with `__init__.py` |
| `models.py` | All Pydantic data models up front (everything else depends on these) |
| `errors.py` | Domain exceptions |
| `config.py` | TOML config + Pydantic settings + precedence logic |

---

## Milestone 1 — Inspectable EPUB Plan

**Goal:** `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` works and
displays ordered chapter candidates, inclusion decisions, titles, source documents,
word counts, and warnings.

**Execution order (build sequentially):**

```
1.  pyproject.toml + package skeleton
2.  models.py       (BookMetadata, Chapter, ChapterCandidate, ConversionPlan, etc.)
3.  errors.py
4.  config.py       (defaults + TOML loading + precedence)
5.  epub/reader.py      → open EPUB safely (anti-zip-bomb, anti-path-traversal)
6.  epub/metadata.py    → extract title, author, language, identifier, cover flag
7.  epub/navigation.py  → spine order, EPUB3 nav doc, EPUB2 NCX → NavigationEntry[]
8.  epub/chapters.py    → scoring engine → ChapterCandidate[] → Chapter[]
9.  epub/cover.py       → extract cover bytes
10. epub/cleanup.py     → strip scripts/nav/hidden, keep paragraphs (basic, enough for word count)
11. cli.py              → `inspect` command (Rich table output + --json)
12. tests/fixtures/     → build 3 programmatic EPUBs via builders.py
13. tests/epub/         → unit tests for metadata, spine, nav, chapter scoring
```

### Chapter-Detection Scoring Approach

Each candidate document/section gets a weighted score from these signals:

| Signal | Weight | Rationale |
|---|---|---|
| TOC/NCX entry points here | +4 | Strongest signal — publisher declared it |
| `epub:type="chapter"` / `"part"` | +3 | Semantic markup |
| `<h1>` / `<h2>` matching title pattern | +2 | "Chapter N", "Part N", named chapters |
| Spine boundary | +1 | New file = possible new chapter |
| CSS class/id containing "chapter" | +1 | Soft signal |
| Short document (<200 words) | −2 | Probably nav/title/copyright |
| Known front/back matter title keyword | −3 | "copyright", "index", "cover" |
| No text content | −10 | Hard exclude |
| `epub:type` in front/back matter set | −3 | Publisher declared non-chapter |

Threshold:
- Score ≥ 2 → **include** as chapter
- Score 0–1 → **warn** (shown in inspect output)
- Score < 0 → **exclude** (reason logged and shown in inspect output)

---

## Milestone 2 — Fake-TTS Audiobook Pipeline

**Goal:** `uv run epub2audio convert tests/fixtures/simple_epub3.epub` produces
valid MP3s per chapter without requiring Kokoro.

**Execution order:**

```
1.  epub/cleanup.py      → full HTML→text pipeline (footnotes, lists, images, tables)
2.  text/normalize.py    → conservative unicode/punct normalization
3.  text/segment.py      → paragraph→sentence→clause segmentation
4.  text/pauses.py       → silence insertion specs
5.  tts/base.py          → TTSEngine Protocol
6.  tts/fake.py          → FakeTTSEngine (silence or tone, deterministic)
7.  audio/chunks.py      → AudioChunk handling
8.  audio/concatenate.py → WAV concatenation via soundfile
9.  audio/encode.py      → FFmpeg MP3 encoding (arg arrays, no shell)
10. audio/normalize.py   → FFmpeg two-pass loudness normalization
11. audio/metadata.py    → FFmpeg ID3 tag embedding + cover art
12. audio/validate.py    → FFprobe validation
13. pipeline/planner.py  → ConversionPlan from EPUB parse
14. pipeline/converter.py → orchestrate full pipeline
15. pipeline/manifest.py → write/read manifest JSON
16. pipeline/resume.py   → fingerprint + skip completed segments
17. cli.py               → `convert` command with all flags
18. tests/test_e2e.py    → end-to-end test with FakeTTS
```

---

## Milestone 3 — Kokoro Integration

**Goal:** A short chapter converts locally with the selected Kokoro voice.

```
1. tts/kokoro.py   → KokoroTTSEngine, isolate all kokoro imports
2. tts/voices.py   → voice catalogue, language→lang_code map (en-us→a, en-gb→b, etc.)
3. cli.py          → `voices` command, `doctor` command
4. Integration smoke test (marked @pytest.mark.slow @pytest.mark.requires_model)
```

---

## Milestone 4 — Reliability

**Goal:** Interrupting and restarting conversion reuses valid completed work.

```
1. Manifest write/read with atomic replacement
2. Resume: verify EPUB fingerprint + config hash; skip valid segments
3. Retry logic (configurable attempts; reduce segment size on suspected length error)
4. Output validation via FFprobe for every final MP3
5. Disk space pre-flight check
6. conversion-report.json and metadata.json output
```

---

## Milestone 5 — Chapter-Detection Hardening

**Goal:** All adversarial fixture types produce deterministic, sensible chapter plans.

```
1. Multi-chapter XHTML splitting (TOC fragment anchors + heading evidence)
2. Cross-file chapter merging (consecutive files belonging to same logical chapter)
3. Fragment-based TOC link resolution
4. Footnote modes: skip / inline / end-of-chapter
5. Adversarial test fixtures (all 21 cases from spec)
```

---

## Milestone 6 — Release Readiness

```
1. README.md
2. ARCHITECTURE.md
3. CONTRIBUTING.md
4. TROUBLESHOOTING.md
5. CHANGELOG.md
6. LICENSE (MIT or Apache-2.0 — decide before this milestone)
7. GitHub Actions CI (ruff, mypy, pytest on macOS + Linux)
8. Example epub2audio.toml config file
9. Document known limitations clearly
```

---

## Proposed File Structure

```
epub2mp3/
├── pyproject.toml
├── uv.lock
├── PLAN.md
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── TROUBLESHOOTING.md
├── CHANGELOG.md
├── LICENSE
├── .ruff.toml
├── mypy.ini
├── src/
│   └── epub2audio/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── errors.py
│       ├── logging.py
│       ├── epub/
│       │   ├── __init__.py
│       │   ├── reader.py
│       │   ├── metadata.py
│       │   ├── navigation.py
│       │   ├── chapters.py
│       │   ├── cleanup.py
│       │   └── cover.py
│       ├── text/
│       │   ├── __init__.py
│       │   ├── normalize.py
│       │   ├── segment.py
│       │   ├── pronunciation.py
│       │   └── pauses.py
│       ├── tts/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── kokoro.py
│       │   └── voices.py
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── chunks.py
│       │   ├── concatenate.py
│       │   ├── encode.py
│       │   ├── normalize.py
│       │   ├── metadata.py
│       │   └── validate.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── planner.py
│       │   ├── converter.py
│       │   ├── manifest.py
│       │   └── resume.py
│       └── utils/
│           ├── __init__.py
│           ├── files.py
│           ├── names.py
│           └── subprocess.py
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── builders.py          ← programmatic EPUB factory (no copyrighted content)
    │   ├── simple_epub3.epub    ← generated by builders.py
    │   └── simple_epub2.epub    ← generated by builders.py
    ├── epub/
    │   ├── test_metadata.py
    │   ├── test_navigation.py
    │   └── test_chapters.py
    ├── text/
    │   ├── test_normalize.py
    │   └── test_segment.py
    ├── audio/
    │   └── test_encode.py
    ├── pipeline/
    │   └── test_manifest.py
    └── test_e2e.py
```

---

## EPUB Fixtures Needed for Milestone 1

All fixtures are generated programmatically by `tests/fixtures/builders.py`.
No copyrighted content is committed.

| # | Fixture | Purpose |
|---|---|---|
| 1 | `simple_epub3.epub` | EPUB 3 + nav doc, one file per chapter, cover, 2 chapters |
| 2 | `simple_epub2.epub` | EPUB 2 + NCX, one file per chapter, 2 chapters |
| 3 | `multi_chapter_single_file.epub` | Multiple chapters in one XHTML (tests splitting) |

Remaining 18 adversarial fixtures are deferred to Milestone 5.

---

## Principal Technical Risks

| Risk | Mitigation |
|---|---|
| **Kokoro API instability** — the `kokoro` PyPI package is young | Isolate entirely in `tts/kokoro.py`; wrap generator loop defensively |
| **EPUB structural chaos** — real books break every assumption | Score-based chapter detection with fallback to spine order |
| **Chapter detection false positives/negatives** | `inspect` shows all decisions and scores; user overrides via flags |
| **FFmpeg unavailable** | `doctor` command catches this; clear OS-specific install instructions |
| **Large books exhaust memory** | Stream segments; process chapter by chapter; never hold full audio in RAM |
| **Resume invalidation bugs** | Hash EPUB content + relevant config subset; cover in dedicated tests |
| **`espeak-ng` missing on macOS** | `doctor` checks for it; README documents `brew install espeak-ng` |
| **Filename collisions / reserved names** | `utils/names.py` sanitizer with duplicate-resolution and Windows reserved name check |

---

## Key Design Constraints (do not violate)

- EPUB parser must **never** call Kokoro
- Kokoro adapter must **never** know about EPUB structure
- FFmpeg always invoked via **argument arrays**, never shell interpolation
- Book content must **never** be logged or transmitted
- All public functions and classes must have **docstrings and type annotations**
- Every final MP3 must pass **FFprobe validation** before being considered done
- Tests must **never** be suppressed to get a green build
