Build a Local EPUB-to-Audiobook CLI Using Kokoro TTS

You are a senior Python engineer leading a small team of coding agents. Build a reliable, local-first command-line application that converts an EPUB ebook into an audiobook using Kokoro text-to-speech.

The primary output must be one MP3 file per logical book chapter.

The tool must run locally after its models and dependencies have been downloaded. It must not require an OpenAI, ElevenLabs, or other paid API key.

Project Name

Use the working project name:

epub2audio

The installed CLI command must also be:

epub2audio

Primary User Story

As a user, I want to run:

epub2audio book.epub --output ./audiobooks

and receive:

audiobooks/
└── Book Title/
    ├── cover.jpg
    ├── metadata.json
    ├── 001 - Chapter One.mp3
    ├── 002 - Chapter Two.mp3
    ├── 003 - Chapter Three.mp3
    └── conversion-report.json

Each MP3 should contain one logical chapter in the same reading order as the EPUB.

The program must make a strong effort to distinguish real chapters from navigation pages, title pages, copyright pages, dedications, indexes, endnotes, and other front or back matter.

Technical Direction

Use:

* Python 3.11 or newer
* uv for dependency and virtual-environment management
* EbookLib for EPUB parsing
* BeautifulSoup with lxml for HTML parsing and cleanup
* The official Python kokoro package for TTS
* soundfile for writing intermediate WAV files
* FFmpeg for MP3 encoding, concatenation, normalization, and metadata
* Typer for the command-line interface
* Rich for progress reporting and terminal output
* Pydantic for configuration and data models
* pytest for tests
* Ruff for formatting and linting
* mypy or Pyright for static type checking

Prefer standard-library modules when an additional dependency does not provide substantial value.

Do not use cloud services.

Supported Platform Priorities

Prioritize platforms in this order:

1. Apple Silicon macOS
2. Intel macOS
3. Linux
4. Windows

Avoid architecture-specific implementation choices unless they are isolated behind an interface.

The initial release may use CPU inference. Detect and use an available supported acceleration backend only when it is stable and does not complicate installation.

Important Legal and Product Boundary

This application is intended for ebooks the user has the legal right to process.

Do not add DRM-removal functionality.

If an EPUB is encrypted or DRM-protected, fail clearly with an actionable message explaining that the application only supports accessible, non-DRM EPUB files.

Do not transmit book content, metadata, or audio to an external service.

CLI Requirements

Implement these commands:

epub2audio convert BOOK.epub
epub2audio inspect BOOK.epub
epub2audio voices
epub2audio doctor
epub2audio config

Running this must behave like convert:

epub2audio BOOK.epub

Convert command

Example:

epub2audio convert book.epub \
  --output ./audiobooks \
  --voice af_heart \
  --language en-us \
  --speed 1.0 \
  --bitrate 96k \
  --normalize \
  --resume

Support these options:

--output PATH
--voice VOICE
--language LANGUAGE
--speed FLOAT
--bitrate BITRATE
--sample-rate INTEGER
--normalize / --no-normalize
--resume / --no-resume
--overwrite
--include-front-matter
--include-back-matter
--chapter REGEX_OR_NUMBER
--chapter-start INTEGER
--chapter-end INTEGER
--dry-run
--keep-intermediates
--workers INTEGER
--config PATH
--verbose
--quiet

Default behavior:

* Voice: a sensible bundled American English voice, preferably af_heart
* Language: infer from EPUB metadata, falling back to American English
* Speed: 1.0
* MP3 bitrate: 96k
* Output: current directory
* Normalization: enabled
* Resume: enabled
* Intermediate files: deleted after successful conversion
* Workers: conservative default of 1 for TTS generation

Do not silently use a voice incompatible with the selected language.

Inspect command

This command must parse the EPUB without producing audio and display a proposed conversion plan.

Example:

epub2audio inspect book.epub

Display:

* Book title
* Author
* Declared language
* Cover availability
* EPUB version when available
* Spine item count
* Table-of-contents entry count
* Detected logical chapters
* Chapter number
* Proposed chapter title
* Source document or documents
* Character and word counts
* Whether each item will be included or excluded
* Exclusion reason
* Estimated audio duration
* Warnings and ambiguities

Support JSON output:

epub2audio inspect book.epub --json

Voices command

Display locally supported Kokoro voices grouped by language.

Include:

* Voice identifier
* Language
* Display label when known
* Whether required voice data is installed
* A short sample-generation option

Example:

epub2audio voices --sample af_heart

Doctor command

Check the complete local environment:

* Python version
* FFmpeg availability
* FFprobe availability
* espeak-ng availability when required by the selected Kokoro installation
* Kokoro import
* Model availability
* Voice availability
* Temp-directory write access
* Output-directory write access
* Available disk space
* Basic TTS smoke test
* Basic MP3 encoding smoke test

Return a nonzero exit code when a required component is unavailable.

Provide exact installation guidance appropriate to the detected operating system.

Config command

Support:

epub2audio config show
epub2audio config path
epub2audio config init

Use a TOML configuration file.

Example:

[tts]
voice = "af_heart"
language = "en-us"
speed = 1.0
[audio]
format = "mp3"
bitrate = "96k"
sample_rate = 24000
normalize = true
loudness_lufs = -18.0
true_peak_db = -2.0
[conversion]
resume = true
include_front_matter = false
include_back_matter = false
keep_intermediates = false
workers = 1
[text]
announce_chapter_titles = true
pause_after_heading_ms = 700
pause_between_sections_ms = 450
pause_between_paragraphs_ms = 180

Apply configuration precedence in this order:

1. CLI flags
2. Explicit --config file
3. Project-local configuration
4. User configuration
5. Application defaults

Architecture

Use clear modules with narrow responsibilities.

A suggested structure is:

epub2audio/
├── __init__.py
├── __main__.py
├── cli.py
├── config.py
├── models.py
├── errors.py
├── logging.py
├── epub/
│   ├── __init__.py
│   ├── reader.py
│   ├── metadata.py
│   ├── navigation.py
│   ├── chapters.py
│   ├── cleanup.py
│   └── cover.py
├── text/
│   ├── __init__.py
│   ├── normalize.py
│   ├── segment.py
│   ├── pronunciation.py
│   └── pauses.py
├── tts/
│   ├── __init__.py
│   ├── base.py
│   ├── kokoro.py
│   └── voices.py
├── audio/
│   ├── __init__.py
│   ├── chunks.py
│   ├── concatenate.py
│   ├── encode.py
│   ├── normalize.py
│   ├── metadata.py
│   └── validate.py
├── pipeline/
│   ├── __init__.py
│   ├── planner.py
│   ├── converter.py
│   ├── manifest.py
│   └── resume.py
└── utils/
    ├── files.py
    ├── names.py
    └── subprocess.py

Use interfaces or protocols for the TTS engine and audio encoder so they can be replaced later.

For example:

class TTSEngine(Protocol):
    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> AudioChunk:
        ...

The EPUB parser must not directly invoke Kokoro.

The Kokoro implementation must not know anything about EPUB files.

Core Data Models

Create typed models for at least:

BookMetadata
BookDocument
NavigationEntry
ChapterCandidate
Chapter
TextSegment
AudioChunk
ConversionPlan
ConversionManifest
ChapterResult
ConversionReport

A logical Chapter may reference one or more EPUB documents.

Include stable identifiers and source hashes so interrupted runs can resume safely.

EPUB Parsing Requirements

EPUB structure is inconsistent across publishers. Do not assume one XHTML file always equals one chapter.

Determine reading order primarily from the EPUB spine.

Use the navigation document, EPUB 2 NCX table of contents, headings, document landmarks, and file structure as supporting signals.

Required parsing behavior

1. Read EPUB metadata:
    * Title
    * Creator or author
    * Language
    * Publisher
    * Identifier
    * Date
    * Description
    * Rights
    * Series information when available
2. Read the EPUB spine in declared order.
3. Resolve spine references to content documents.
4. Parse EPUB 3 navigation and EPUB 2 NCX data when available.
5. Build a normalized navigation map linking TOC entries to:
    * Document paths
    * Fragment identifiers
    * Titles
    * Hierarchy depth
6. Detect chapter boundaries using several signals:
    * TOC entries
    * Spine boundaries
    * <h1>, <h2>, and other meaningful headings
    * Semantic EPUB types such as chapter, part, prologue, and epilogue
    * CSS classes and IDs containing chapter-related terms
    * Common chapter-title patterns
    * Meaningful page breaks
    * Document size and textual continuity
7. Score chapter candidates instead of relying on a single heuristic.
8. Produce deterministic results for the same EPUB and configuration.

Chapter-title patterns

Recognize titles such as:

Chapter 1
Chapter One
CHAPTER I
1
I
Prologue
Epilogue
Introduction
Part One
Book Two
Interlude
Afterword

Do not treat every numbered heading as a chapter automatically.

Multi-chapter documents

Some EPUBs contain multiple chapters in one XHTML document.

Split these at meaningful internal anchors or headings when supported by the TOC or strong structural evidence.

Split chapters

Some EPUBs divide one chapter across multiple XHTML files.

Merge consecutive content documents when the navigation and headings indicate they belong to the same logical chapter.

Front and back matter

Classify probable front and back matter.

Examples include:

cover
title page
copyright
dedication
contents
table of contents
foreword
preface
acknowledgments
notes
bibliography
glossary
index
about the author
also by
advertisements

Do not exclude forewords, prefaces, introductions, afterwords, or appendices merely because they are not numbered chapters. Treat these as meaningful content unless configuration says otherwise.

Exclude obvious navigation-only pages and pages with no meaningful readable text.

Provide inclusion decisions in the inspection report.

HTML and Text Cleanup

Convert XHTML into natural narration text while retaining useful semantic boundaries.

Remove:

* Scripts
* Styles
* Navigation menus
* Hidden elements
* Repeated running headers
* Repeated running footers
* Page-number-only elements
* Empty nodes
* Decorative image alt text
* EPUB accessibility artifacts that duplicate visible text
* Soft hyphens
* Zero-width characters
* Excess whitespace

Preserve:

* Paragraph boundaries
* Section boundaries
* Emphasis when it affects pronunciation
* Block quotations
* Poetry line breaks where possible
* Ordered and unordered lists
* Scene breaks
* Meaningful captions
* Footnote references according to configuration
* Abbreviations and punctuation

Images

Do not narrate arbitrary image filenames.

Narrate alt text only when it is meaningful and not obviously decorative.

Make image narration configurable:

ignore
alt-text
announce

Default to alt-text.

Footnotes and endnotes

Support configurable modes:

skip
inline
end-of-chapter

Default to end-of-chapter.

Avoid reading backlink labels such as “return to text.”

Links

Read visible link text, but never read raw URLs unless the URL itself is the visible content and cannot be replaced meaningfully.

Tables

For small, simple tables, produce understandable row-oriented narration.

For large or complex tables, either:

* Produce a concise announcement that a table was omitted, or
* Save the table as text in the conversion report

Make this behavior configurable.

Lists

Convert bullet lists into speech-friendly sentences with appropriate pauses.

Do not repeatedly say “bullet” unless configured.

Text Normalization

Create a conservative normalization pipeline.

Normalize:

* Unicode quotation marks where necessary
* Ellipses
* Em dashes
* Repeated whitespace
* Soft hyphens
* Broken words caused by formatting
* Roman numerals in chapter headings when unambiguous
* Common abbreviations
* Initials
* Dates
* Times
* Currency
* Measurements
* Ordinal numbers

Do not aggressively rewrite prose.

Preserve punctuation because it influences TTS pacing.

Do not use a general-purpose LLM to rewrite or summarize the book.

Pronunciation substitutions

Support an optional pronunciation dictionary:

[pronunciations]
"Chani" = "CHAH-nee"
"Bene Gesserit" = "BEN-ee JESS-er-it"

Apply pronunciation replacements only for TTS input. Do not alter chapter titles or exported source text.

Support plain replacements initially. Design the model so phonetic or engine-specific pronunciation formats can be added later.

Text Segmentation

Do not send an entire chapter to Kokoro in a single call.

Break chapters into stable, speech-friendly segments.

Segmentation priorities:

1. Section boundaries
2. Paragraph boundaries
3. Sentence boundaries
4. Clause boundaries
5. Hard length limit as a last resort

Never split:

* In the middle of a word
* Between an opening quotation mark and its first word
* Inside a decimal number
* Inside common abbreviations when avoidable
* Between initials when avoidable

Make maximum segment size configurable.

Choose a conservative default supported by Kokoro’s practical behavior.

Each segment must have:

* Stable index
* Source chapter identifier
* Source-text hash
* Normalized-text hash
* Character count
* Word count
* Status
* Audio path
* Audio duration
* Error details when applicable

Kokoro Integration

Use the official kokoro Python package and its supported pipeline API.

Isolate all Kokoro imports in the TTS adapter.

Initialize the pipeline once per language or process when possible.

Conceptually, usage will resemble:

from kokoro import KPipeline
pipeline = KPipeline(lang_code="a")
generator = pipeline(
    text,
    voice="af_heart",
    speed=1.0,
)

Do not assume the generator returns only one audio buffer.

Collect all generated audio pieces in order.

Use the sample rate reported or required by the supported Kokoro API. Validate it rather than scattering a magic number throughout the code.

Support explicit mappings between user-friendly language identifiers and Kokoro language codes.

Examples:

en-us -> a
en-gb -> b

Do not guess unsupported language mappings.

Voice validation

Before conversion:

* Verify the selected voice exists.
* Verify that it supports the selected language.
* Produce a clear error listing valid alternatives.
* Avoid downloading or initializing unrelated voices.

Model downloads

Allow dependencies and model files to download during setup or the first explicit run.

After required artifacts are present, conversion must be able to operate without network access.

Do not implement custom model downloading unless the official package requires it. Prefer the package’s documented mechanism.

Audio Assembly

Kokoro may produce multiple audio buffers per text segment.

The pipeline should be:

EPUB chapter
→ cleaned chapter text
→ text segments
→ Kokoro audio pieces
→ segment WAV files
→ chapter WAV
→ normalized chapter audio
→ chapter MP3
→ metadata and validation

Pauses

Insert configurable silence:

* After chapter titles
* Between sections
* Between paragraphs when needed
* Around scene breaks
* Before end-of-chapter notes

Avoid an audible pause between every generated TTS chunk when the chunks are part of one continuous paragraph.

Generate silence at the chapter audio sample rate.

Concatenation

Prefer lossless concatenation of WAV or raw PCM intermediates before final MP3 encoding.

Do not concatenate separately encoded MP3 chunks unless no better approach is available.

Normalization

Normalize completed chapter audio, not every tiny segment independently.

Use FFmpeg loudness normalization.

Defaults:

Integrated loudness: -18 LUFS
True peak: -2 dB
Loudness range target: 7 LU

Use two-pass loudness normalization if practical and correctly implemented.

Make normalization optional.

Prevent clipping.

MP3 output

Use FFmpeg and libmp3lame.

Default:

96 kbps
mono
24 kHz or an appropriate compatible output rate

Make bitrate and sample rate configurable.

Do not upsample unless required for compatibility.

MP3 metadata

Embed, where available:

* Title: chapter title
* Album: book title
* Artist: book author
* Album artist: book author
* Track number
* Total track count
* Disc number when parts are mapped to discs
* Genre: Audiobook
* Date or publication year
* Comment indicating local generation
* Cover art

Use safe temporary output files and atomic replacement.

Cover Extraction

Extract the official EPUB cover when available.

Support common EPUB 2 and EPUB 3 cover declarations.

Convert unsupported cover formats to JPEG or PNG when necessary.

Preserve aspect ratio.

Embed cover art into each MP3 unless disabled.

Also copy the cover into the audiobook output directory.

If no cover exists, continue without failure.

Do not generate an artificial cover in the initial release.

File Naming

Output chapter files using zero-padded track numbers:

001 - Chapter One.mp3
002 - The Test.mp3
003 - Epilogue.mp3

Sanitize names for macOS, Linux, and Windows.

Remove or replace:

/
\
:
*
?
"
<
>
|
control characters

Avoid reserved Windows device names.

Trim trailing spaces and periods.

Limit filename length conservatively.

Resolve duplicate titles deterministically:

005 - Interlude.mp3
006 - Interlude (2).mp3

Preserve the true title in metadata even when the filename is sanitized.

Resume and Recovery

Long books may take substantial processing time. The converter must safely resume.

Create a manifest before synthesis begins.

Record:

* Application version
* EPUB path
* EPUB fingerprint
* Relevant configuration
* Book metadata
* Chapter plan
* Segment plan
* Completed segment hashes
* Intermediate paths
* Output paths
* Audio durations
* Failures
* Timestamps

On resume:

* Verify the EPUB fingerprint.
* Verify relevant configuration has not changed.
* Reuse only valid completed segments.
* Regenerate missing, invalid, or changed segments.
* Do not restart completed chapters unnecessarily.

If voice, speed, language, segmentation, pronunciation rules, or audio settings change, invalidate affected artifacts.

Write manifests atomically.

Do not mark a chapter complete until the final MP3 passes validation.

Validation

Validate every final MP3 with FFprobe.

Check:

* File exists
* File size is nonzero
* Audio stream exists
* Codec is MP3
* Duration is plausible
* Duration is not zero
* Sample rate is valid
* Channel count is expected
* Metadata is present when available
* Track numbering is correct

Estimate expected duration from word count.

Use a broad range because narration speed varies.

Flag suspiciously short or long chapters in the report rather than automatically deleting them.

Conversion Report

Write conversion-report.json.

Include:

* Book metadata
* Input fingerprint
* Start and completion timestamps
* Tool version
* Effective configuration
* Number of included chapters
* Number of excluded items
* Total words
* Total generated duration
* Per-chapter word count and duration
* Warnings
* Exclusion decisions
* Failed or retried segments
* Output paths
* Versions of Kokoro, EbookLib, FFmpeg, and Python

Also write metadata.json containing normalized book metadata and track information.

Error Handling

Create meaningful domain exceptions, such as:

InvalidEpubError
DrmProtectedEpubError
MissingDependencyError
UnsupportedLanguageError
UnknownVoiceError
ChapterDetectionError
SynthesisError
AudioEncodingError
OutputValidationError
ResumeConflictError

Translate exceptions into readable CLI messages.

Use nonzero exit codes.

Do not show a Python stack trace by default.

Show full diagnostic details with --verbose.

When one segment fails:

* Retry a configurable number of times.
* Reduce segment size if the error may be length-related.
* Record the failure.
* Stop the chapter if recovery fails.
* Preserve valid intermediate work for resume.

Do not silently omit failed text.

Progress Reporting

Display high-level progress with Rich:

Parsing EPUB
Detecting chapters
Preparing 27 chapters
Chapter 4/27: The Door
Segment 12/38
Encoding MP3
Validating output

Include:

* Current chapter
* Current segment
* Completed chapter count
* Approximate elapsed progress when reliably calculable

Do not present an unreliable completion-time estimate.

Provide quiet and verbose modes.

Logs must not include the complete book text.

Dry Run

With --dry-run:

* Parse the EPUB.
* Detect chapters.
* Normalize and segment text.
* Validate configuration and dependencies.
* Display or write the conversion plan.
* Do not initialize expensive TTS inference unless necessary.
* Do not generate audio.

Security and Privacy

Treat EPUB content as untrusted input.

Prevent:

* Path traversal from ZIP entries
* Arbitrary filesystem writes
* Unsafe external entity expansion
* Shell injection
* Command injection through metadata
* Unsafe temporary-file handling
* Zip bombs where practical

Invoke FFmpeg through argument arrays, never through an interpolated shell command.

Never execute scripts or active content found in an EPUB.

Do not log complete chapter text.

Do not send telemetry.

Performance

Optimize for reliability before concurrency.

TTS generation may default to a single worker.

Allow limited concurrency for tasks such as parsing, encoding, validation, or cover processing when safe.

Avoid holding the entire decoded audiobook in memory.

Process segments and chapters incrementally.

Clean intermediate files only after their downstream output has been verified.

Estimate required disk space before conversion and warn when space appears insufficient.

Testing Strategy

Implement unit, integration, and end-to-end tests.

Unit tests

Cover:

* Metadata extraction
* Spine ordering
* TOC resolution
* Fragment resolution
* Chapter-title detection
* Front-matter classification
* Back-matter classification
* HTML cleanup
* Footnote handling
* List conversion
* Image-alt handling
* Text normalization
* Sentence segmentation
* Filename sanitization
* Configuration precedence
* Resume invalidation
* Manifest serialization
* FFmpeg argument construction

EPUB fixtures

Create small legal test fixtures programmatically.

Include cases such as:

1. EPUB 2 with NCX
2. EPUB 3 with navigation document
3. One XHTML file per chapter
4. Multiple chapters in one XHTML file
5. One chapter split across multiple files
6. Missing TOC
7. Misordered filenames but correct spine
8. Duplicate chapter titles
9. Fragment-based TOC links
10. Footnotes and backlinks
11. Images with meaningful alt text
12. Decorative images
13. Poetry
14. Lists
15. Tables
16. No cover
17. Unicode titles
18. Invalid EPUB
19. Encrypted or inaccessible content
20. Extremely short chapter
21. Very long chapter

Do not commit copyrighted ebook content to the repository.

TTS tests

Mock Kokoro in most automated tests.

Provide an opt-in real Kokoro smoke test marked:

integration
slow
requires_model

The smoke test should synthesize a short public-domain or original sentence and verify that nonempty audio is produced.

End-to-end test

Generate a tiny original EPUB fixture containing:

* Title page
* Table of contents
* Two chapters
* One footnote
* One decorative image
* One meaningful image
* Cover art

Convert it with a fake deterministic TTS engine.

Validate the complete chapter-MP3 pipeline.

Add a separate opt-in end-to-end test using the real Kokoro engine.

Code Quality

All public functions and classes must have docstrings.

Use type annotations throughout.

Keep functions focused.

Avoid large multipurpose modules.

Use dependency injection for:

* TTS engine
* Audio encoder
* Filesystem-sensitive operations
* Subprocess runner
* Clock when timestamps affect tests

Run in CI:

ruff check .
ruff format --check .
mypy epub2audio
pytest

Documentation

Create:

README.md
CONTRIBUTING.md
ARCHITECTURE.md
TROUBLESHOOTING.md
LICENSE
CHANGELOG.md

The README must include:

* What the tool does
* Legal-use note
* Platform support
* Installation with uv
* FFmpeg installation
* Kokoro setup
* Basic conversion
* Voice selection
* Inspect command
* Resume behavior
* Configuration
* Common troubleshooting
* Privacy statement
* Example output
* Current limitations

Include installation examples for:

macOS

brew install ffmpeg espeak-ng

Debian or Ubuntu

sudo apt-get install ffmpeg espeak-ng

Confirm exact package requirements against the Kokoro package used by the implementation.

Do not claim Windows support is complete until CI or manual testing verifies it.

Packaging

Use pyproject.toml.

Create a console entry point:

[project.scripts]
epub2audio = "epub2audio.cli:app"

Use a src/ layout unless there is a strong reason not to.

Pin only where necessary. Use sensible compatible version ranges.

Record dependency versions in the conversion report.

Provide:

uv sync
uv run epub2audio doctor
uv run epub2audio inspect tests/fixtures/sample.epub
uv run epub2audio convert tests/fixtures/sample.epub

Agent Team Structure

Use the following roles when multiple agents are available.

Agent 1: Technical Lead

Responsibilities:

* Own architecture and interfaces
* Define data models
* Coordinate work
* Resolve cross-module decisions
* Review every integration
* Keep the project runnable throughout development

Agent 2: EPUB Specialist

Responsibilities:

* EPUB loading
* Metadata
* Spine and TOC resolution
* Chapter detection
* Cover extraction
* HTML cleanup
* EPUB fixtures and parser tests

Agent 3: TTS and Text Specialist

Responsibilities:

* Text normalization
* Text segmentation
* Kokoro adapter
* Voice and language handling
* Pronunciation substitutions
* TTS mocks and smoke tests

Agent 4: Audio Specialist

Responsibilities:

* WAV handling
* Silence insertion
* Concatenation
* FFmpeg encoding
* Loudness normalization
* Metadata and cover embedding
* FFprobe validation

Agent 5: Reliability and CLI Specialist

Responsibilities:

* Typer CLI
* Configuration
* Manifests
* Resume behavior
* Progress UI
* Logging
* Error handling
* Doctor command

Agent 6: Verification Agent

This agent must not implement primary features unless asked.

Responsibilities:

* Review requirements
* Challenge assumptions
* Inspect diffs
* Run tests
* Add adversarial fixtures
* Verify chapter ordering
* Verify no text is silently omitted
* Verify interruption recovery
* Verify CLI documentation
* Report concrete defects with reproduction steps

Each implementation agent must have its work reviewed by the verification agent or another agent before integration.

Development Sequence

Implement in vertical slices.

Milestone 1: Inspectable EPUB plan

Deliver:

* Package skeleton
* CLI
* EPUB metadata parsing
* Spine parsing
* TOC parsing
* Basic chapter detection
* inspect command
* Tests and fixtures

Success condition:

epub2audio inspect sample.epub

shows ordered logical chapters without generating audio.

Milestone 2: Fake-TTS audiobook pipeline

Deliver:

* Text cleanup
* Segmentation
* Fake deterministic TTS engine
* WAV assembly
* FFmpeg MP3 encoding
* Basic metadata
* End-to-end test

Success condition:

A test EPUB becomes one valid MP3 per chapter without requiring Kokoro.

Milestone 3: Kokoro integration

Deliver:

* Kokoro adapter
* Voice validation
* Language mapping
* Real synthesis smoke test
* voices command
* doctor checks

Success condition:

A short chapter converts locally with the selected Kokoro voice.

Milestone 4: Reliability

Deliver:

* Manifest
* Resume
* Atomic writes
* Retry behavior
* Output validation
* Conversion report
* Disk-space checks

Success condition:

Interrupting and restarting conversion reuses valid completed work.

Milestone 5: Chapter-detection hardening

Deliver:

* Multi-chapter XHTML support
* Split-chapter merging
* Front and back matter classification
* Fragment handling
* Footnotes
* Adversarial fixtures

Success condition:

All fixture types produce deterministic, sensible chapter plans.

Milestone 6: Release readiness

Deliver:

* Documentation
* Cross-platform CI
* Packaging
* Changelog
* Example configuration
* Clear known limitations

Required Acceptance Criteria

The project is complete only when all of the following are true:

1. A valid non-DRM EPUB can be converted locally.
2. The default output is one MP3 per logical chapter.
3. Track order matches the EPUB reading order.
4. Chapter names are human-readable and safely sanitized.
5. The converter does not assume filename order equals reading order.
6. Multi-file chapters can be merged.
7. Multiple chapters in a single XHTML file can be split when structural evidence exists.
8. Navigation-only and empty pages are excluded.
9. Users can inspect the proposed chapter plan before synthesis.
10. Every final MP3 passes FFprobe validation.
11. Final files contain book and track metadata when available.
12. Cover art is embedded when available.
13. Interrupted conversions can resume.
14. Configuration changes invalidate the correct cached artifacts.
15. Failed synthesis never causes text to be silently omitted.
16. No book content is sent over the network.
17. No DRM-removal capability exists.
18. Unit and end-to-end tests pass.
19. Ruff and type checking pass.
20. A new user can install and run the program from the README.

Initial Scope Exclusions

Do not make these required for version 1:

* DRM removal
* Graphical interface
* Mobile application
* Voice cloning
* Character-specific voices
* Automatic speaker detection
* LLM-based prose rewriting
* Cloud TTS providers
* Full DAISY support
* Perfect pronunciation for every proper noun
* M4B output
* Audiobookshelf integration
* Distributed synthesis
* Real-time playback during conversion

Design interfaces so M4B output and alternative TTS engines can be added later.

Implementation Rules for the Coding Agents

1. Inspect the repository before editing.
2. Write a brief implementation plan.
3. Work on one coherent vertical slice at a time.
4. Add or update tests with every behavior change.
5. Run focused tests before the entire suite.
6. Never suppress a failing test merely to get a green build.
7. Do not replace deterministic parsing with an LLM call.
8. Do not silently discard EPUB content.
9. Document any unavoidable ambiguity in chapter detection.
10. Keep the application runnable at the end of every milestone.
11. Have another agent review material changes.
12. Update architecture and user documentation when behavior changes.
13. Do not leave placeholder implementations presented as complete.
14. Clearly identify features that are implemented, partially implemented, or deferred.

First Task

Begin with Milestone 1.

Before writing code:

1. Inspect the repository.
2. Confirm whether it is empty or existing.
3. Produce the proposed file structure.
4. Identify the first EPUB fixtures needed.
5. State the chapter-detection scoring approach.
6. Identify the principal technical risks.
7. Create a short, executable task breakdown for the implementation agents.

Then implement the smallest complete vertical slice that supports:

uv run epub2audio inspect tests/fixtures/simple_epub3.epub

The command must display ordered chapter candidates, inclusion decisions, titles, source documents, word counts, and warnings.

Do not begin Kokoro synthesis until this inspection pipeline is tested and working.