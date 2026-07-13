# 001 — AudioChunk: frozen=False exception

**Date:** 2026-07-12  
**Status:** Accepted  
**Author:** Architect

---

## Context

All Pydantic models in this project use `model_config = ConfigDict(frozen=True)` to provide
immutability guarantees and enable safe use in sets and as dict keys.  The project spec
flags `AudioChunk.data` as requiring `Any` type annotation because it holds a NumPy ndarray.

NumPy arrays are **not hashable**.  When Pydantic attempts to freeze a model it calls
`__hash__` on the model (which in turn hashes every field), raising `TypeError: unhashable
type: 'numpy.ndarray'` at construction time.

---

## Decision

`AudioChunk` uses:

```python
model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)
```

This is the **only** model in the codebase permitted to use `frozen=False`.

---

## Consequences

- `AudioChunk` instances cannot be used in sets or as dict keys.  This is acceptable because
  they are short-lived objects returned by the TTS engine and immediately drained into WAV
  files; they are never stored in a container requiring hashability.
- `arbitrary_types_allowed=True` suppresses the Pydantic validation error for the ndarray.
  The `data` field is documented and annotated as `Any`; callers are expected to treat it as
  a NumPy ndarray without relying on Pydantic's runtime type checking.
- By convention `AudioChunk` is treated as **logically immutable** — callers must not mutate
  `data` after construction.  This is enforced by code review rather than the runtime.
- All other models remain `frozen=True` unchanged.

---

## Alternatives Considered

1. **Store raw bytes instead of ndarray** — would remove the numpy dependency from models.py
   but force all consumers to decode bytes on every access and lose the ability to pass chunks
   directly to soundfile/scipy without a copy.

2. **Wrap ndarray in a custom Pydantic validator that returns a copy** — avoids the frozen
   constraint but adds complexity and overhead without a clear benefit.

3. **Make AudioChunk a plain dataclass** — breaks the consistent Pydantic API used throughout
   the codebase and prevents future JSON serialization of chunk metadata.
