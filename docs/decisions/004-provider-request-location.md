# 004 — ProviderRequest placement: `providers/base.py` not `models.py`

**Date:** 2026-07-13
**Status:** Accepted
**Author:** Architect

---

## Context

Milestone 9 (M9-01) requires a `ProviderRequest` Pydantic model — the output
of `NarrationProvider.render()`, consumed by `NarrationProvider.synthesize()`.
The spec says: *"prefer `providers/base.py` to keep `models.py` free of
provider concerns, unless you judge it belongs in `models.py` — record the
choice."*

Two candidate locations:

1. `models.py` — the existing base-layer module that already hosts
   `NarrationSegment`, `NarrationPlan`, `AudioChunk`, and all other shared
   Pydantic models.
2. `providers/base.py` — the new module that also holds the
   `NarrationProvider` Protocol.

---

## Decision

`ProviderRequest` is placed in **`providers/base.py`**.

---

## Rationale

### models.py is provider-neutral by design

ADR-003 §4 states: *"The plan is provider-neutral: no SSML, no Kokoro tokens,
no engine-specific fields ever appear in it."*  `ProviderRequest` carries a
`payload: dict[str, Any]` field whose contents are **provider-specific**
(SSML for Azure, instruction strings for OpenAI/Gemini, voice settings for
ElevenLabs).  Adding it to `models.py` would break the invariant that
`models.py` holds only provider-neutral types.

### models.py is a zero-import base layer

`models.py` must never import from any other epub2audio module (see module
docstring and AGENTS.md hard rules).  `ProviderRequest` needs no imports
from `models.py` beyond the types already exported there, so this constraint
is not the deciding factor — but it reinforces that `models.py` is
intentionally narrow.

### Co-location with the Protocol it serves

`ProviderRequest` is inseparably linked to `NarrationProvider`: it is the
return type of `render()` and the parameter type of `synthesize()`.  Placing
both in `providers/base.py` makes the contract self-contained and means a
contributor can read the entire Layer-2 contract in one file.

### No circular imports are introduced

```
models.py          (no epub2audio imports)
config.py          (no epub2audio imports)
providers/base.py  → imports models.py, config.py
providers/*.py     → imports providers/base.py, models.py, config.py
```

The dependency graph remains a clean DAG.

---

## Consequences

- `from epub2audio.providers import ProviderRequest` is the canonical import
  path; `from epub2audio.providers.base import ProviderRequest` also works.
- `models.py` remains free of provider concerns; future shared domain types
  continue to go there.
- If a `ProviderRequest` field ever becomes needed outside the `providers/`
  package (e.g. in `pipeline/converter.py`), it can still be imported from
  `providers/base.py` without introducing a cycle, because `pipeline/`
  already depends on `providers/` (per ADR-003 §8).

---

## Alternatives Considered

**Put `ProviderRequest` in `models.py`**: Rejected.  It would pollute the
provider-neutral base layer with a type that carries engine-specific data in
its `payload` field, violating ADR-003 §4.
