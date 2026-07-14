# Project: AI Narration Pipeline

## Objective

Refactor the existing EPUB-to-MP3 project into a modular audiobook generation pipeline capable of producing expressive narration across multiple TTS providers.

The architecture should remain provider-agnostic while allowing provider-specific optimizations.

The immediate goals are:

1. Add M4B as a first-class output format.
2. Introduce a narration preprocessing ("Narration Director") stage.
3. Preserve compatibility with the current MP3 generation.
4. Lay the groundwork for OpenAI, Gemini, Kokoro, Azure, ElevenLabs, and future providers.

---

# High-Level Pipeline

```
EPUB
 ↓
Extract Metadata
 ↓
Extract Chapters
 ↓
Clean HTML
 ↓
Narration Director
 ↓
Narration Plan
 ↓
TTS Adapter
 ↓
Audio Segments
 ↓
Audio Assembly
 ├── MP3
 └── M4B
```

---

# Narration Director

Introduce a new module responsible for analyzing the text before it reaches TTS.

The Narration Director must NEVER rewrite the book.

It should only produce structured annotations.

Output should resemble:

```json
{
  "chapter": 4,
  "scene": 2,
  "defaultDirection": {
    "mood": "restrained cyberpunk noir",
    "pace": 0.95,
    "intensity": 0.30
  },
  "segments": [
    {
      "id": "...",
      "type": "narration",
      "speaker": "narrator",
      "text": "...",
      "direction": "...",
      "pauseAfterMs": 350,
      "pace": 0.95,
      "emphasis": []
    }
  ]
}
```

The narration plan should contain:

- scene mood
- pacing
- narration style
- dialogue detection
- likely speaker
- emphasis hints
- pronunciation hints
- pause timing
- provider-neutral delivery instructions

This plan must not depend on any specific TTS engine.

---

# Provider Adapters

Create adapters that consume the narration plan.

Each adapter converts it into provider-specific controls.

Examples:

- Kokoro
    - punctuation optimization
    - pause insertion
    - pronunciation
    - speech rate

- OpenAI
    - natural-language narration instructions

- Gemini
    - narration prompts

- Azure
    - SSML generation

- ElevenLabs
    - provider settings and prompting

No business logic should live inside provider implementations.

---

# Kokoro Optimization

Implement a Kokoro adapter that optimizes narration by:

- improving punctuation
- inserting natural pauses
- splitting overly long spoken segments
- applying pronunciation dictionaries
- adjusting speaking speed

Do NOT attempt to rewrite prose.

Do NOT invent dialogue.

---

# Pronunciation Dictionary

Create a pronunciation subsystem.

Allow:

```
pronunciations.yaml
```

Example:

```
Ono-Sendai
Hosaka
Tessier-Ashpool
Neuromancer
```

Support provider-specific pronunciation implementations where available.

---

# M4B Support

Implement a new audiobook output module.

Requirements:

- AAC encoding
- embedded cover art
- embedded metadata
- chapter markers
- title
- author
- narrator
- optional series metadata

Reuse existing generated audio whenever possible.

MP3 generation should continue to work unchanged.

---

# Intermediate Audio

Generate intermediate chapter audio before packaging.

Prefer lossless intermediates when practical.

Each chapter should expose:

- duration
- filename
- chapter title

The packaging stage should be independent of TTS generation.

---

# Scene Segmentation

Avoid directing individual sentences.

Instead:

- analyze scenes
- apply one default direction
- create local overrides only when emotion changes significantly

Maintain narration consistency.

---

# Quality Assurance

Introduce an optional validation stage.

Checks should include:

- skipped text
- pronunciation failures
- missing chapters
- invalid metadata
- overlapping timestamps
- chapter duration consistency

Future work may include multimodal audio review.

---

# New Project Structure

```
src/

epub/
audio/
director/
providers/
output/
metadata/
pronunciation/
validation/
```

---

# Configuration

Introduce configurable options:

```
provider:
output_format:
voice:
bitrate:
sample_rate:
scene_analysis:
pronunciation_dictionary:
```

Support:

```
output_format:
  mp3
  m4b
  both
```

---

# Design Principles

- Provider agnostic
- Extensible
- Minimal coupling
- Preserve original text
- Scene-aware narration
- Modular adapters
- Clean interfaces
- Testable components

---

# Deliverables

1. Refactored architecture.
2. Working MP3 output.
3. Working M4B output.
4. Narration Director abstraction.
5. Kokoro provider implementation.
6. Documentation explaining the architecture.
7. Unit tests for narration plans, metadata generation, and M4B chapter creation.

When implementing, favor maintainability and clean abstractions over quick fixes. Design the system so additional TTS providers can be added by implementing a single provider interface without modifying the rest of the pipeline.