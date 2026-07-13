# M2 — TTS Engineer Task Contract

**Milestone:** 2 — Fake-TTS Audiobook Pipeline
**Agent:** TTS Engineer
**Date opened:** 2026-07-12
**Depends on:** M1 complete ✅

---

## Scope

Tasks: DEFECT-002, M2-01, M2-02, M2-03, M2-04, M2-05, M2-06.

These tasks complete the EPUB text-extraction layer, all text-processing modules,
and the TTS protocol + fake engine needed for the M2 pipeline.

---

## DEFECT-002 — Fix `Chapter.word_count` (epub/chapters.py)

**Root cause:** `select_chapters` calls `_extract_word_count_from_signals`, which
returns 0 for chapters ≥ 200 words because the `short_document` signal only fires
for short documents.

**Fix:** In `score_candidates`, compute the true word count via
`word_count(xhtml_to_text(content))` from `epub/cleanup.py` for **every**
candidate (not only short ones). Store it on the candidate so `select_chapters`
can assign it to `Chapter.word_count` directly.

**Acceptance:** `uv run epub2audio inspect tests/fixtures/simple_epub3.epub --json`
shows non-zero `word_count` for both chapters.

**Note:** Assigned here because the TTS Engineer is already extending
`epub/cleanup.py` in M2-01; fixing word count is a natural companion.

---

## M2-01 — Extend `epub/cleanup.py`: full HTML → narration text

Upgrade the existing `xhtml_to_text` function with full cleanup rules.

**Rules to add:**
- Strip `<script>`, `<style>`, `<nav>` elements entirely.
- Strip footnote links: `<a epub:type="noteref">`.
- Strip decorative images: `<img>` with no `alt` or `alt=""`.
- Convert `<li>` items to `• item` lines.
- Convert `<br>` to newlines.
- Preserve paragraph structure: each `<p>` → separate paragraph, separated by blank line.
- Handle `<table>`: extract cell text in row order, cells joined with ` | `.
- Image alt text: if `<img alt="...">` has meaningful alt text (non-empty, non-whitespace,
  not `"image"`), prepend `[Image: alt text]` to the paragraph.
- Footnote content (`<aside epub:type="footnote">`): skip entirely for M2; full handling
  deferred to M5.

**Preserved API (must not change signatures):**
```python
def xhtml_to_text(content: bytes) -> str: ...
def word_count(text: str) -> int: ...
```

**Acceptance:** `uv run mypy src/epub2audio/epub/cleanup.py` → 0 errors.

---

## M2-02 — Write `text/normalize.py`

Conservative unicode/punctuation normalization. Preserve narration intent; do not alter meaning.

**Normalizations:**
- Curly quotes → straight: `"` / `"` → `"`, `'` / `'` → `'`
- Em-dashes: ` — ` or `—` → ` - `
- Ellipsis: `…` → `...`
- Non-breaking space (`\u00a0`) → regular space
- Ligatures: `ﬁ` → `fi`, `ﬂ` → `fl`

**Must NOT alter:** numbers, proper nouns, abbreviations, initials, decimal points.

**Public API:**
```python
def normalize_text(text: str) -> str:
    """Normalize unicode punctuation in text for TTS consumption."""
```

**Acceptance:** `uv run mypy src/epub2audio/text/normalize.py` → 0 errors.

---

## M2-03 — Write `text/segment.py`

Segment chapter text into `TextSegment` objects for TTS calls.

**Priority order for splitting:**
1. Section boundary
2. Paragraph boundary
3. Sentence boundary
4. Clause boundary
5. Hard character limit (configurable, default 500 chars)

**Never split:**
- Mid-word
- Between opening quote and first word
- Inside a decimal number (`3.14`)
- Inside common abbreviations: `Dr.`, `Mr.`, `Mrs.`, `Ms.`, `Prof.`, `St.`, `vs.`, `etc.`
- Between initials: `J. R. R.`

**Public API:**
```python
def segment_text(text: str, max_chars: int = 500) -> list[TextSegment]:
    """Segment text into TTS-sized chunks, respecting linguistic boundaries."""
```

Each `TextSegment` must have:
- `text`: the segment string
- `source_hash`: `hashlib.sha256(text.encode()).hexdigest()`
- `normalized_hash`: `hashlib.sha256(normalize_text(text).encode()).hexdigest()`
- `word_count`: `len(text.split())`
- `status`: `"pending"`
- `audio_path`: `None`

**Note:** `TextSegment` is already defined in `models.py`. Import it from there.

**Acceptance:** `uv run mypy src/epub2audio/text/segment.py` → 0 errors.

---

## M2-04 — Write `text/pauses.py`

Silence insertion specifications between segments.

**Public API:**
```python
class PauseSpec(BaseModel):
    duration_ms: int
    reason: str

def get_pause(before: TextSegment, after: TextSegment) -> PauseSpec | None:
    """Return a pause to insert between two segments, or None."""
```

**Rules (detect boundary type from trailing punctuation/whitespace in `before.text`):**
- Paragraph boundary → 600 ms
- Sentence boundary → 300 ms
- Clause boundary → 150 ms
- Continuation → no pause (return `None`)

**Acceptance:** `uv run mypy src/epub2audio/text/pauses.py` → 0 errors.

---

## M2-05 — Write `tts/base.py`: TTSEngine Protocol

Implement the canonical Protocol from `docs/architecture.md`.

**Public API:**
```python
from typing import Protocol, runtime_checkable
from epub2audio.models import AudioChunk

@runtime_checkable
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

**Constraints:**
- Import `AudioChunk` from `epub2audio.models`.
- Import `Protocol` and `runtime_checkable` from `typing`.
- Use `@runtime_checkable` decorator.

**Acceptance:** `uv run mypy src/epub2audio/tts/base.py` → 0 errors.

---

## M2-06 — Write `tts/fake.py`: FakeTTSEngine

Deterministic fake TTS for tests: same input always produces same output.

**Synthesis rule:** Generate a silent WAV (numpy zeros array) of
`len(text.split()) * 150` milliseconds at 24000 Hz, mono, float32.

**Public API:**
```python
class FakeTTSEngine:
    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]:
        """Return a single AudioChunk of deterministic silence proportional to word count."""
```

**Constraints:**
- Must satisfy `isinstance(FakeTTSEngine(), TTSEngine)` (structural subtype).
- File must be `tts/fake.py` — NOT `tts/kokoro.py`.
- No `kokoro` imports anywhere in this file.
- Use `numpy` for array generation.

**Acceptance:** `uv run mypy src/epub2audio/tts/fake.py` → 0 errors.

---

## Done Criteria

All of the following must be true before this contract is moved to `tasks/completed/`:

- [ ] DEFECT-002 closed: `uv run epub2audio inspect tests/fixtures/simple_epub3.epub --json` shows non-zero `word_count` for both chapters.
- [ ] All 7 modules/changes pass `uv run mypy src/epub2audio/` (strict, 0 errors).
- [ ] All 7 modules/changes pass `uv run ruff check src/epub2audio/` (0 issues).
- [ ] `uv run ruff format --check src/epub2audio/` passes.
- [ ] `uv run pytest tests/ -v` continues to pass with ≥ 35 tests, 0 failures.
- [ ] All public functions and classes have docstrings and type annotations.

---

## Files to Create / Modify

| File | Action |
|---|---|
| `src/epub2audio/epub/cleanup.py` | Modify — full cleanup rules |
| `src/epub2audio/epub/chapters.py` | Modify — DEFECT-002 fix |
| `src/epub2audio/text/normalize.py` | Create |
| `src/epub2audio/text/segment.py` | Create |
| `src/epub2audio/text/pauses.py` | Create |
| `src/epub2audio/tts/base.py` | Create |
| `src/epub2audio/tts/fake.py` | Create |

Do NOT touch: `audio/`, `pipeline/`, `cli.py`, `models.py`, `errors.py`.
