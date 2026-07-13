# M7 — Architect Task: M4B format seam (models, config, decision)

**Milestone:** 7 — M4B output format  
**Agent:** Architect  
**Depends on:** None  
**Blocks:** M7-audio-engineer, M7-tester, M7-reviewer

---

## Overview

Establish the type/config seam for a second output format (M4B) without
touching audio internals. See `docs/decisions/002-m4b-output-format.md`.

---

## Deliverables

### D1: `Settings.output_format`

`src/epub2audio/config.py`:

```python
from typing import Literal

output_format: Literal["mp3", "m4b"] = Field(
    default="mp3", description="Output container: per-chapter MP3 files or a single M4B."
)
```

- Default `"mp3"` (back-compat). Add a `field_validator` if a plain string
  needs normalizing/lowercasing.

### D2: Chapter offset model

`src/epub2audio/models.py` — add a marker type for M4B chapter timestamps:

```python
class ChapterMarker(BaseModel):
    """Start/end offsets (ms) of a chapter inside a single audiobook file."""
    model_config = ConfigDict(frozen=True)
    chapter_id: str
    title: str
    start_ms: int
    end_ms: int
```

- Extend `ConversionReport` with an optional `chapter_markers: list[ChapterMarker] = []`
  and an optional single `output_path: str | None` for the M4B artifact.
  Keep existing per-chapter `chapter_results` intact.

### D3: Decision record

- Finalize `docs/decisions/002-m4b-output-format.md` (status → Accepted once
  Audio Engineer confirms the seam is workable). Update `docs/decisions/README.md`
  index.

### D4: config_hash coverage

- Confirm `pipeline/manifest.config_hash()` includes `output_format` so switching
  format invalidates the manifest correctly (coordinate with Audio Engineer on
  whether a format switch should reuse segment WAVs — it should; only final
  assembly differs).

---

## Files to Modify

- `src/epub2audio/config.py`
- `src/epub2audio/models.py`
- `src/epub2audio/pipeline/manifest.py` (verify config_hash)
- `docs/decisions/002-m4b-output-format.md`, `docs/decisions/README.md`

---

## Exit Criteria

- [ ] `Settings.output_format` present, defaults to `"mp3"`
- [ ] `ChapterMarker` + report fields added, all frozen, documented, typed
- [ ] `config_hash` accounts for `output_format`
- [ ] `uv run mypy src/epub2audio` passes (strict)
- [ ] `uv run ruff check src/` passes
- [ ] Existing tests still pass (no behaviour change to MP3 path)
