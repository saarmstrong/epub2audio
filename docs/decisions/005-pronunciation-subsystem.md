# 005 — Pronunciation subsystem: lexicon in Director, enriched PronunciationHint

**Date:** 2026-07-13
**Status:** Accepted — architecture recorded here; implementation tracked as M10
**Author:** Architect

---

## Context

`Feature.md` ("Pronunciation Dictionary") requires a `pronunciations.yaml`
lexicon so that proper nouns like *Ono-Sendai*, *Tessier-Ashpool*, and
*Neuromancer* are spoken correctly.  The spec further requires
*provider-specific pronunciation implementations where available* — meaning
Kokoro (grapheme-based) and Azure (SSML `<phoneme>`) must each apply the
lexicon in their own way.

ADR-003 established that **providers are pure plan-mappers** with no analysis
logic and no knowledge of the lexicon.  This creates a tension: if the
`PronunciationHint` carries only the raw `term`, every provider must load
the lexicon itself and re-scan the segment text to retrieve the pronunciation
— violating the "no business logic in providers" principle.

The resolution is to decide *where* lexicon resolution happens and *what the
hint carries* across the Director→provider boundary.

---

## Decision

### 1. Lexicon loaded and resolved by the Director only

A new `pronunciation/` package (implemented by the TTS Engineer in M10) is
loaded at Director startup.  The Director, when building a `NarrationPlan`,
scans each segment's text for lexicon terms and, for every match, resolves
the full entry (IPA transcription, phonetic respelling, or both) from the
lexicon.  The resolved data is **baked directly into the `PronunciationHint`**
attached to the segment.

The provider adapter receives a fully resolved plan.  It never opens
`pronunciations.yaml`, never imports the `pronunciation/` package, and never
re-scans text for lexicon terms.

### 2. Enriched `PronunciationHint` with two optional provider-neutral fields

`models.PronunciationHint` gains two optional fields (both default to `None`):

```python
class PronunciationHint(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str         # verbatim substring of the segment text
    ipa: str | None = None        # IPA transcription, e.g. "/oʊnoʊ sɛnˈdaɪ/"
    respelling: str | None = None # phonetic respelling, e.g. "Oh-no Sen-DYE"
```

Both representations are **provider-neutral**: they do not embed SSML,
Kokoro tokens, or any engine-specific markup.  A provider adapter picks
whichever field it can use:

| Provider  | Field used   | Mechanism                                   |
|-----------|--------------|---------------------------------------------|
| Kokoro    | `respelling` | Substitute the term with the respelling before synthesis |
| Azure     | `ipa`        | Wrap the term in `<phoneme alphabet="ipa">` |
| Others    | Either / both / neither | Fallback to engine's own G2P |

Defaulting to `None` preserves backward compatibility: all existing
`PronunciationHint(term=…)` constructions and tests continue to work without
modification.

### 3. PyYAML dependency

`pyyaml>=6.0` is added to `[project].dependencies` in `pyproject.toml`
(runtime, not a TTS extra) because `pronunciations.yaml` is a core feature,
not optional.  `types-PyYAML` is added to the `dev` optional-dependencies so
`mypy --strict` has stubs when the `pronunciation/` package is implemented.
`tomllib` (stdlib on 3.11+) cannot parse YAML.

---

## Consequences

- **Zero provider-side lexicon coupling.** A new provider never needs to know
  about `pronunciations.yaml`; it only needs to handle the already-resolved
  `ipa` / `respelling` fields it understands.
- **Backward-compatible model extension.** Both new fields are `Optional`
  with `None` defaults.  All existing tests and construction sites remain
  valid.
- **Single scan of segment text.** The Director does one pass per segment;
  no adapter re-scans text.
- **Testable without a real TTS engine.** Unit tests for the Director can
  assert that `PronunciationHint.respelling` is set correctly from a toy
  lexicon, entirely independently of Kokoro or Azure.
- **New runtime dependency: PyYAML.** It is well-maintained, widely used,
  and has no sub-dependencies beyond the C extension (optional).  The risk
  is minimal.
- **`pronunciation/` package scope is M10 (TTS Engineer).** This ADR records
  the *interface*; the package implementation, YAML loading, and Director
  integration are out of scope for the Architect's M10 tasks.

---

## Alternatives Considered

### A — Hint carries only `term`; provider loads the lexicon

Each provider adapter would load `pronunciations.yaml` from
`Settings.pronunciation_dictionary`, look up the `term`, and apply its
preferred representation.

**Rejected.**  This:
1. Violates ADR-003's "no business logic in providers" rule — every adapter
   re-implements lexicon loading and text scanning.
2. Couples each provider to the `pronunciation/` package, creating a fan-out
   dependency that grows with the number of providers.
3. Makes the `NarrationPlan` incomplete: a serialized plan cannot be replayed
   by a different provider without re-loading the lexicon, breaking the plan's
   role as a self-contained, provider-neutral artifact.

### B — Separate `resolvedPronunciations` map on `NarrationSegment`

Store a `dict[str, ResolvedPronunciation]` alongside `pronunciation_hints`
so the hint list stays as bare `term` references and the resolved data is
kept separately.

**Rejected.**  It complicates the adapter: the adapter must join two
collections to apply a pronunciation.  Embedding the resolution directly in
`PronunciationHint` is simpler, keeps all pronunciation information for a
term co-located, and requires no extra join step.

### C — Store only `respelling` (drop IPA)

Simpler model; only grapheme-based engines are currently planned.

**Rejected.**  ADR-003 §6 explicitly anticipates an Azure adapter that emits
SSML `<phoneme>`.  Omitting `ipa` now would force a breaking model change
when Azure is implemented.  Adding it now as `Optional[str]` costs nothing
and keeps the model forward-compatible.
