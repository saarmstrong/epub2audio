# M1-Architect Task Contract

**Agent:** Architect  
**Milestone:** 1 — Inspectable EPUB Plan  
**Tasks:** M1-01, M1-02  
**Date assigned:** 2026-07-12

---

## M1-01 — Write `src/epub2audio/models.py`

### Goal

Implement all shared Pydantic data models as specified in `docs/architecture.md`. Replace the current stub.

### Required models

All models must use `model_config = ConfigDict(frozen=True)`.

| Model | Fields |
|---|---|
| `BookMetadata` | `title: str`, `author: str`, `language: str`, `identifier: str`, `publisher: str \| None`, `date: str \| None`, `rights: str \| None` |
| `BookDocument` | `path: str`, `content_hash: str`, `nav_entries: list[NavigationEntry]` |
| `NavigationEntry` | `title: str`, `doc_path: str`, `fragment: str \| None`, `depth: int` |
| `ChapterCandidate` | `doc_path: str`, `title: str \| None`, `score: int`, `signals: list[str]` |
| `Chapter` | `chapter_id: str`, `title: str`, `source_docs: list[str]`, `word_count: int`, `stable_id: str` |
| `TextSegment` | `text: str`, `source_hash: str`, `normalized_hash: str`, `word_count: int`, `status: str`, `audio_path: str \| None` |
| `AudioChunk` | `sample_rate: int`, `data: Any` (numpy array — annotate as `Any` with a comment) |
| `ConversionPlan` | `book_metadata: BookMetadata`, `chapters: list[Chapter]`, `config_snapshot: dict[str, Any]` |
| `ConversionManifest` | `epub_fingerprint: str`, `config_hash: str`, `chapters: list[Chapter]`, `segments: list[TextSegment]`, `created_at: str`, `updated_at: str` |
| `ChapterResult` | `chapter_id: str`, `duration_seconds: float`, `warnings: list[str]`, `output_path: str \| None` |
| `ConversionReport` | `book_metadata: BookMetadata`, `chapter_results: list[ChapterResult]`, `total_duration_seconds: float`, `warnings: list[str]`, `errors: list[str]` |

### Constraints

- `models.py` **must not** import from any other `epub2audio` module.
- Use `from __future__ import annotations` at the top.
- Use `pydantic.ConfigDict` and `pydantic.BaseModel`.
- `AudioChunk.data` should be typed `Any` with a comment explaining it holds a numpy array; frozen=True cannot apply to numpy arrays so `AudioChunk` is the **one exception** — use `model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)` for that model only.
- All models must have class-level docstrings.

### Acceptance criterion

```
uv run mypy src/epub2audio/models.py
```
Must pass with zero errors in strict mode (as configured in `pyproject.toml`).

---

## M1-02 — Write `src/epub2audio/errors.py`

### Goal

Implement all domain exceptions. Replace the current stub.

### Required exceptions

All must inherit from `Epub2AudioError(Exception)`.

| Exception | When raised |
|---|---|
| `Epub2AudioError` | Base class. All domain errors inherit from this. |
| `InvalidEpubError` | EPUB file is malformed, missing required OPF, or unreadable. |
| `DrmProtectedEpubError` | EPUB file has DRM encryption markers. |
| `MissingDependencyError` | A required external tool (FFmpeg, espeak-ng) is not found. Carries `dependency: str` attribute. |
| `UnsupportedLanguageError` | Language code not supported by the configured TTS voice. Carries `language: str` attribute. |
| `SegmentTooLongError` | A text segment exceeds the TTS engine's maximum token length. Carries `segment_length: int` attribute. |
| `FingerprintMismatchError` | Resume fingerprint does not match the current EPUB. |
| `ConfigChangedError` | Config hash changed in ways that require re-synthesis. Carries `changed_keys: list[str]` attribute. |

### Constraints

- `errors.py` **must not** import from any other `epub2audio` module.
- Use `from __future__ import annotations` at the top.
- Each exception must have a class-level docstring.
- Custom attributes must be set in `__init__` and passed to `super().__init__(message)`.

### Acceptance criterion

```
uv run mypy src/epub2audio/errors.py
```
Must pass with zero errors in strict mode (as configured in `pyproject.toml`).

---

## Done criteria

- [ ] `src/epub2audio/models.py` fully implemented (not a stub)
- [ ] `src/epub2audio/errors.py` fully implemented (not a stub)
- [ ] `uv run mypy src/epub2audio/models.py src/epub2audio/errors.py` passes with 0 errors
- [ ] No imports from other `epub2audio` modules in either file
- [ ] All classes have docstrings
- [ ] Task moved to `tasks/completed/`
