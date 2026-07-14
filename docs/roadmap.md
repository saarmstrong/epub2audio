# Roadmap — Feature Candidates from Comparable Projects

_Status: proposed, not yet scheduled into a committed milestone. Last updated: 2026-07-13._

M1–M12 (see [status.md](status.md)) delivered the full `Feature.md` vision: MP3/M4B/both
output, the rule-based Narration Director, provider abstraction, pronunciation
dictionary, and optional validation. This document tracks features observed in
comparable local-TTS-audiobook projects — [abogen](https://github.com/denizsafak/abogen)
and [TTS-Story](https://github.com/Xerophayze/TTS-Story) — evaluated for fit against
this project's architecture and CLAUDE.md constraints (local-first, no cloud
services, no LLM prose rewriting, deterministic chapter detection).

Corresponding backlog tasks live in [tasks/backlog.md](../tasks/backlog.md) under
Milestones 13–16. Each milestone below is independent; they do not need to land
in rank order, but rank reflects value-to-effort and should guide scheduling.

---

## Ranked candidates

### 1. Per-character voice mapping (Milestone 13)

**Source:** TTS-Story (`[alice]...[/alice]` / `[speaker1]...[/speaker1]` speaker tags,
one Kokoro voice per detected character).

**Why it's #1:** the Narration Director already attributes speakers per
`NarrationSegment` (`director/` package, M8) but the pipeline renders every
segment with a single `--voice`. Mapping detected/tagged speakers to distinct
Kokoro voices is the highest-leverage change available — it's the difference
between "one narrator reads all dialogue" and "each character sounds different,"
which is the single biggest perceived-quality jump of anything evaluated here.

**Fit:** high. `NarrationSegment.speaker` already exists; this is a
speaker→voice lookup at the provider boundary, not a new subsystem.

**Actionable scope:**
- A `voice_map` setting (TOML table: `speaker_name = "voice_id"`, config-only,
  no CLI flag needed for the mapping itself) consumed at the `NarrationProvider`
  layer, not the Director (keeps the Director provider-neutral per ADR-003).
- Fallback: unmapped or `"unknown"` speakers use the existing single `--voice`.
- No change to speaker *detection* — reuse M8's existing attribution heuristics.
- Validation: extend `validation/` to flag speakers in the plan with no voice
  mapping and no fallback (currently would silently use default — should be a
  `ValidationIssue`, not silent).

---

### 2. Voice blending as reusable named presets (Milestone 13)

**Source:** abogen (Voice Mixer, weighted blend), TTS-Story (`custom_*` voice codes).

**Why it's #2:** natural pairing with #1 — once speakers map to voices, blended
voices become another valid target (e.g. a narrator voice that's a blend of two
Kokoro voices). TTS-Story's approach of exposing the blend as a first-class
voice identifier (`custom_narrator`) is cleaner than a one-off mix string
because it composes with everything else that already accepts `--voice`.

**Fit:** high. No new provider needed — Kokoro supports weighted voice blends
natively; this is a mapping/config feature in `tts/voices.py`.

**Actionable scope:**
- `voices.py`: parse `custom_<name> = "af_heart:0.6,af_bella:0.4"` entries from
  config into a resolved blend before handing to `KokoroTTSEngine`.
- `voices` CLI command: list custom presets alongside built-in voices, with
  `--sample custom_narrator` support (reuses existing sample-generation path).
- Validate blend weights sum sanely and referenced base voices exist —
  reuse the existing voice-validation error path (`UnknownVoiceError`).

---

### 3. Subtitle / timestamp export (Milestone 14)

**Source:** abogen (SRT/ASS/VTT output; line/sentence/word-level modes).

**Why it's #3:** you already compute per-segment audio duration for resume
(`TextSegment.audio_duration`, segment manifest). Emitting an SRT/VTT file
alongside the MP3/M4B is close to free given that data already exists — it's
mostly a new writer, not new computation.

**Fit:** high, but lower user-value than #1/#2 for an audiobook-first tool
(subtitles matter more for video/short-form use cases than long-form audiobooks).

**Actionable scope:**
- `--subtitle-format {none,srt,vtt}` on `convert` (default `none`).
- New `audio/subtitles.py`: consume the same segment timing data used for
  `conversion-report.json` per-chapter durations; write one `.srt`/`.vtt` per
  chapter (or one for the whole book in `--format m4b` mode, matching M4B's
  single-file structure).
- Sentence-level granularity to start (matches existing segmentation); word-level
  highlighting (abogen's karaoke mode) is out of scope — would need sub-segment
  timing Kokoro doesn't expose today.

---

### 4. GPU backend detection (Milestone 14)

**Source:** abogen (CUDA/ROCm/MPS detection with CPU fallback), TTS-Story
(explicit RTX 3090 throughput numbers).

**Why it's #4:** CLAUDE.md already scopes this — "Detect and use an available
supported acceleration backend only when it is stable and does not complicate
installation" — this closes that gap rather than adding new scope. Apple
Silicon (MPS) is your #1 supported platform, so this is also the most
directly relevant acceleration path.

**Fit:** high; contained to `doctor` and the Kokoro adapter's init path.

**Actionable scope:**
- `doctor`: report detected backend (MPS / CUDA / CPU) and whether Kokoro/torch
  can use it, without changing exit-code semantics for CPU-only environments
  (CPU remains fully supported, per CLAUDE.md's platform priorities).
- `tts/kokoro.py`: pass through an explicit device selection if the installed
  `kokoro`/`torch` build supports it; never silently fail over — if a requested
  backend is unavailable, fall back to CPU and say so in `doctor`/`--verbose`
  logs, don't guess silently.
- No new CLI flag required initially; auto-detect. A `--device` override can
  follow if auto-detection proves unreliable in practice.

---

### 5. Plain-text / Markdown input with chapter markers (Milestone 15)

**Source:** abogen (chapter markers, timestamp-tagged text), TTS-Story
(section-heading detection for non-EPUB input).

**Why it's #5:** genuinely useful (not every source is an EPUB) but the biggest
scope item here — it's a second input pipeline, not an extension of the
existing one. EPUB-specific chapter detection (spine/TOC/NCX scoring) doesn't
transfer; plain text needs its own boundary-detection convention.

**Fit:** medium. Needs a new reader behind a format-agnostic interface,
parallel to (not reusing) `epub/chapters.py`.

**Actionable scope:**
- Accept `.txt`/`.md` input in the CLI's format dispatch (currently EPUB-only).
- Chapter boundaries from explicit `<<CHAPTER: Title>>`-style markers when
  present; fall back to heading-pattern detection (reuse the existing
  chapter-*title* pattern list from `epub/chapters.py`, not the EPUB-specific
  spine/TOC scoring).
- Front/back-matter classification does not apply (no EPUB semantic types
  available) — document this as a known limitation rather than faking scores.

---

### 6. Batch / queue mode (Milestone 15)

**Source:** abogen (Queue Mode, per-item overrides), TTS-Story (job queue with
ETA, cancel, real-time progress).

**Why it's #6:** useful for library-scale conversion but additive on top of
the existing single-book pipeline — no core pipeline changes needed, just an
orchestration layer.

**Fit:** medium. CLAUDE.md's concurrency guidance already allows "limited
concurrency for tasks such as parsing, encoding, validation, or cover
processing" while keeping TTS generation conservative — a queue that processes
books sequentially (or with limited parallel encode/validate stages) fits
without violating the single-worker-TTS default.

**Actionable scope:**
- `epub2audio convert *.epub --output ./audiobooks` (glob/multi-path support)
  as the minimal version — no new subcommand needed.
- Per-book manifest/resume already exists per book; queueing is sequential
  dispatch over existing `convert_epub()` calls plus aggregated progress
  reporting in Rich.
- ETA/cancel are Rich-progress features, not architecture changes.

---

### 7. Local voice-cloning provider (Milestone 16, stretch)

**Source:** TTS-Story (Chatterbox/VoxCPM/IndexTTS voice cloning from a 10–15s
sample, all locally-runnable per their docs).

**Why it's ranked last:** highest effort, and only in scope if the underlying
engine can run fully offline after setup (per CLAUDE.md's no-cloud-services
rule) — needs verification per engine before starting.

**Fit:** medium — the `NarrationProvider` Protocol (M9, ADR-004) was
specifically designed so a new engine is "implement one Protocol," so the
integration point already exists. The work is in the adapter and sample
management, not the core pipeline.

**Actionable scope:**
- Pick one local, offline-capable engine to prototype against (verify no
  network calls occur after model download — same bar as Kokoro).
- New `providers/<engine>.py` adapter implementing `NarrationProvider`,
  following the existing stub pattern (`providers/{openai,gemini,azure,
  elevenlabs}.py` already establish the shape; this would be the first
  *real* non-Kokoro adapter).
- Reference-sample storage: a local directory + config entry, not a managed
  "sample library" service.

---

## Considered and rejected

Recorded so these aren't re-proposed without new information.

- **Gemini/LLM speaker-memory preprocessing** (TTS-Story) — conflicts directly
  with CLAUDE.md: "Do not use a general-purpose LLM to rewrite or summarize the
  book" and the no-cloud-services rule. The rule-based Director (ADR-003)
  exists specifically to get deterministic speaker attribution without this.
- **Cloud-hosted TTS engines** (Replicate-hosted Kokoro, hosted Chatterbox,
  etc.) — conflicts with "Do not use cloud services" / "No book content is
  sent over the network." Only locally-runnable engines are candidates for
  Milestone 16.
- **Desktop GUI / Web UI** (abogen PyQt + Flask, TTS-Story web queue UI) —
  explicitly listed under CLAUDE.md's "Initial Scope Exclusions" ("Graphical
  interface"). Not reconsidered here; would need an explicit scope change from
  the user first.
