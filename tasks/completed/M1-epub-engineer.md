# M1-EPUB-Engineer Task Contract

**Agent:** EPUB Engineer  
**Milestone:** 1 — Inspectable EPUB Plan  
**Tasks:** M1-03 through M1-11  
**Date assigned:** 2026-07-12  
**Depends on:** M1-architect.md (models.py and errors.py must be complete and type-checking before starting M1-04+)

---

## M1-03 — Write `src/epub2audio/config.py`

### Goal

TOML-based configuration with Pydantic Settings. Replace the current stub.

### Settings class: `Settings`

```python
class Settings(BaseSettings):
    voice: str = "af_heart"
    language: str = "en-us"
    speed: float = 1.0
    bitrate: str = "96k"
    sample_rate: int = 24000
    normalize: bool = True
    resume: bool = True
    workers: int = 1
    output_dir: Path = Path(".")
```

### Config sources (in precedence order, highest first)

1. CLI flags (passed as `_cli_settings` or via `model_validate`)
2. Explicit `--config` file path (TOML)
3. `epub2audio.toml` in the current working directory
4. `~/.config/epub2audio/config.toml`
5. Application defaults (the field defaults above)

### Implementation notes

- Use `pydantic_settings.BaseSettings` with a custom `model_config` that sets `env_prefix = "EPUB2AUDIO_"` and `env_file = None`.
- Provide a `load_settings(config_path: Path | None = None) -> Settings` function that handles the TOML search order.
- Use `tomllib` (stdlib ≥ 3.11) to read TOML files; file-not-found is not an error (use defaults).
- All speed/bitrate/sample_rate values should be validated (speed 0.25–4.0, workers 1–16).
- Full docstrings and type annotations required.

### Acceptance

`uv run mypy src/epub2audio/config.py` — zero errors.

---

## M1-04 — Write `src/epub2audio/epub/reader.py`

### Goal

Safe EPUB opening using ebooklib. Replace the current stub.

### Public API

```python
def open_epub(path: Path) -> ebooklib.epub.EpubBook:
    """Open an EPUB file safely, guarding against common attacks and errors."""
```

### Security requirements (all mandatory)

1. **ZIP path traversal guard**: before extraction, check every ZIP entry name. If any entry path contains `..` or starts with `/`, raise `InvalidEpubError`.
2. **Zip bomb guard**: if any single uncompressed entry > 100 MB, raise `InvalidEpubError`. If total uncompressed size > 500 MB, raise `InvalidEpubError`.
3. **DRM detection**: inspect the ZIP for `META-INF/encryption.xml`. If present and non-empty, raise `DrmProtectedEpubError`.
4. **General error guard**: wrap `ebooklib.epub.read_epub` in a try/except; on any exception, raise `InvalidEpubError(str(e))`.

### Notes

- Inspect the ZIP directly (using `zipfile.ZipFile`) before passing to ebooklib.
- `ebooklib.epub.read_epub` is called after the ZIP is validated.
- Return type is `ebooklib.epub.EpubBook`.

### Acceptance

`uv run mypy src/epub2audio/epub/reader.py` — zero errors.

---

## M1-05 — Write `src/epub2audio/epub/metadata.py`

### Goal

Extract `BookMetadata` from an ebooklib `EpubBook`. Replace the current stub.

### Public API

```python
def extract_metadata(book: ebooklib.epub.EpubBook) -> BookMetadata:
    """Extract book metadata from an opened EpubBook."""
```

### Field mapping

| `BookMetadata` field | OPF source |
|---|---|
| `title` | `book.title` — fallback to `"Unknown Title"` if missing/empty |
| `author` | `book.get_metadata("DC", "creator")` — first entry, fallback `"Unknown Author"` |
| `language` | `book.get_metadata("DC", "language")` — first entry, fallback `"en"` |
| `identifier` | `book.get_metadata("DC", "identifier")` — first entry, fallback `""` |
| `publisher` | `book.get_metadata("DC", "publisher")` — first entry or `None` |
| `date` | `book.get_metadata("DC", "date")` — first entry or `None` |
| `rights` | `book.get_metadata("DC", "rights")` — first entry or `None` |

### Notes

- `get_metadata` returns a list of `(value, attributes)` tuples; take index 0 if present.
- Handle None / empty gracefully at every step.

### Acceptance

`uv run mypy src/epub2audio/epub/metadata.py` — zero errors.

---

## M1-06 — Write `src/epub2audio/epub/navigation.py`

### Goal

Build a reading-order list of `NavigationEntry` objects from an EpubBook. Replace the current stub.

### Public API

```python
def extract_navigation(book: ebooklib.epub.EpubBook) -> list[NavigationEntry]:
    """Extract navigation entries in spine reading order.

    Tries EPUB3 nav document first, then EPUB2 NCX, then falls back to spine order.
    Never assumes filename order equals reading order.
    """
```

### Algorithm

1. **EPUB3 nav**: find the item with `epub:type="nav"` using `book.get_items_of_type(ebooklib.ITEM_NAVIGATION)`. Parse its `<nav epub:type="toc">` element; extract `<a href>` links and label text. Each link = one `NavigationEntry`. Resolve fragment: split href on `#`.
2. **EPUB2 NCX**: if no EPUB3 nav, find the NCX item (`book.get_items_of_type(ebooklib.ITEM_NCXTOC)`). Parse `<navPoint>` elements; extract `<text>` label and `<content src>`. Split src on `#` to get doc_path and fragment.
3. **Spine fallback**: if neither nav nor NCX found, produce one `NavigationEntry` per spine item with `title = ""`, `fragment = None`, `depth = 0`.

### Critical constraint

**Never assume filename order = reading order.** The spine (`book.spine`) defines order; nav/NCX labels provide titles.

### Acceptance

`uv run mypy src/epub2audio/epub/navigation.py` — zero errors.

---

## M1-07 — Write `src/epub2audio/epub/chapters.py`

### Goal

Score every candidate chapter and produce an ordered list of `Chapter` objects. Replace the current stub.

### Public API

```python
def score_candidates(
    book: ebooklib.epub.EpubBook,
    nav_entries: list[NavigationEntry],
) -> list[ChapterCandidate]:
    """Score each spine item as a chapter candidate."""

def select_chapters(
    candidates: list[ChapterCandidate],
) -> list[Chapter]:
    """Apply threshold rules and return confirmed chapters."""
```

### Scoring table (from `docs/architecture.md`)

| Signal | Weight |
|---|---|
| TOC/NCX entry points here | +4 |
| `epub:type="chapter"` or `"part"` | +3 |
| `<h1>` or `<h2>` matches title pattern ("Chapter N", named chapter) | +2 |
| Spine boundary (each file) | +1 |
| CSS class/id contains "chapter" | +1 |
| Short document (< 200 words) | −2 |
| Title keyword in front/back matter set | −3 |
| `epub:type` is front/back matter type | −3 |
| No readable text content | −10 |

Front/back matter keywords: `{"copyright", "index", "cover", "toc", "contents", "dedication", "preface", "foreword", "introduction", "acknowledgements", "about", "colophon", "half-title"}`.

Front/back matter epub:types: `{"cover", "frontmatter", "bodymatter", "backmatter", "toc", "landmarks", "loi", "lot", "preface", "copyright-page", "colophon", "index", "glossary", "bibliography", "acknowledgements", "dedication", "epigraph"}`.

### Thresholds

- Score ≥ 2 → **include**
- Score 0–1 → **warn** (included but `signals` list contains warning text)
- Score < 0 → **exclude** (not in output, reason recorded in signals)

### `select_chapters` → `list[Chapter]`

For each included candidate:
- `chapter_id`: `f"ch{index+1:03d}"` (1-based, zero-padded to 3 digits)
- `title`: candidate title or `f"Chapter {index+1}"`
- `source_docs`: `[candidate.doc_path]`
- `word_count`: count words in plain text of the doc (use `epub/cleanup.py`)
- `stable_id`: SHA-256 of `chapter_id + title` (first 12 chars of hex)

### Acceptance

`uv run mypy src/epub2audio/epub/chapters.py` — zero errors.

---

## M1-08 — Write `src/epub2audio/epub/cover.py`

### Goal

Extract the cover image bytes from an EpubBook. Replace the current stub.

### Public API

```python
def extract_cover(book: ebooklib.epub.EpubBook) -> bytes | None:
    """Return cover image bytes, or None if no cover found."""
```

### Algorithm

1. Check `book.get_metadata("OPF", "cover")` — if present, use the item ID to fetch the cover image.
2. Look for an item with `id="cover-image"` or `id="cover"`.
3. Look for the first image item with `epub:type="cover-image"` in its properties.
4. Look for an `<img>` in the first spine item that has class/id containing "cover".
5. If nothing found, return `None`.

### Acceptance

`uv run mypy src/epub2audio/epub/cover.py` — zero errors.

---

## M1-09 — Write `src/epub2audio/epub/cleanup.py`

### Goal

Minimal XHTML → plain text for Milestone 1 (word count + `inspect` output only). Full HTML cleanup is deferred to M2. Replace the current stub.

### Public API

```python
def xhtml_to_text(content: bytes) -> str:
    """Convert XHTML bytes to plain text suitable for word counting.

    Milestone 1 implementation: strips tags, decodes entities, collapses whitespace.
    Full cleanup (footnotes, lists, tables) deferred to M2.
    """

def word_count(text: str) -> int:
    """Return the word count of a plain-text string."""
```

### Implementation notes

- Use `bs4.BeautifulSoup(content, "lxml")` to parse.
- Call `.get_text(separator=" ")` on the soup object.
- Collapse whitespace: `" ".join(text.split())`.
- `word_count` is just `len(text.split())`.
- No need to handle footnotes, tables, or images yet.

### Acceptance

`uv run mypy src/epub2audio/epub/cleanup.py` — zero errors.

---

## M1-10 — Write `src/epub2audio/utils/names.py`

### Goal

Filename sanitisation for MP3 output files. Replace the current stub.

### Public API

```python
def sanitize_filename(title: str, index: int) -> str:
    """Return a sanitized filename in the format 'NNN - Title.mp3'.

    Handles Windows reserved names, special characters, long names, and duplicates.
    """

def make_unique(names: list[str]) -> list[str]:
    """Given a list of names (already sanitized), append -2, -3 etc. to duplicates."""
```

### Sanitisation rules

1. **Format**: `f"{index:03d} - {safe_title}.mp3"` where `index` is 1-based.
2. **Forbidden characters**: replace `[/\\:*?"<>|]` and ASCII control chars with `_`.
3. **Windows reserved names**: if the stem (before `.mp3`) equals a Windows reserved name (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`), append `_` to the stem.
4. **Max length**: if the total filename (including extension) exceeds 200 characters, truncate the title portion to fit, preserving the `NNN - ` prefix and `.mp3` suffix.
5. **Trailing dots/spaces**: strip trailing dots and spaces from the title portion (Windows restriction).

### `make_unique`

- Detect duplicates (case-insensitive comparison of the full filename).
- Append `-2`, `-3` etc. before the `.mp3` extension for collisions.
- First occurrence keeps original name; subsequent ones get suffix.

### Acceptance

`uv run mypy src/epub2audio/utils/names.py` — zero errors.

---

## M1-11 — Write `src/epub2audio/cli.py`

### Goal

Typer CLI app with an `inspect` command. Replace the current stub.

### Public API

```python
app = typer.Typer(...)

@app.command()
def inspect(
    epub_path: Path = typer.Argument(..., help="Path to the EPUB file"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    config: Path | None = typer.Option(None, "--config", help="Path to config TOML"),
) -> None:
    """Inspect an EPUB file and show the conversion plan as a table."""
```

### `inspect` command behaviour

1. Call `open_epub(epub_path)` → `EpubBook`
2. Call `extract_metadata(book)` → `BookMetadata`
3. Call `extract_navigation(book)` → `list[NavigationEntry]`
4. Call `score_candidates(book, nav_entries)` → `list[ChapterCandidate]`
5. Call `select_chapters(candidates)` → `list[Chapter]`
6. Display a **Rich table** with columns:
   - `#` (chapter number, 1-based)
   - `Title`
   - `Source Doc(s)` (comma-separated filenames)
   - `Words`
   - `Status` (✅ Included / ⚠️ Warned / ❌ Excluded — use colour)
   - `Signals` (semicolon-separated scoring signals)
7. Print a summary line: `f"Found {n} chapter(s) to convert."` (in green)

### `--json` flag behaviour

- Output `{"metadata": {...}, "chapters": [...], "warnings": [...]}` as JSON to stdout.
- `metadata` is `BookMetadata.model_dump()`.
- `chapters` is a list of `Chapter.model_dump()` for included chapters.
- `warnings` is a list of `{"title": ..., "signals": [...]}` for warned candidates.
- Exit without printing the Rich table.

### Error handling

- `InvalidEpubError` and `DrmProtectedEpubError` → print error to stderr, exit code 1.
- `FileNotFoundError` → print error to stderr, exit code 1.

### Notes

- Import `from epub2audio.epub.reader import open_epub` etc. — all epub/ imports.
- `cli.py` must not import from `tts/`, `audio/`, or `pipeline/` at module level.
- The Typer `app` object must be importable as `epub2audio.cli:app` (matches `pyproject.toml`).

### Acceptance criterion

```bash
uv run epub2audio inspect tests/fixtures/simple_epub3.epub
```

Produces a readable Rich table with at least 2 chapters listed.

---

## Done criteria

- [ ] All 9 modules fully implemented (not stubs)
- [ ] `uv run mypy src/epub2audio/config.py src/epub2audio/epub/ src/epub2audio/utils/names.py src/epub2audio/cli.py` passes with 0 errors
- [ ] `epub/` never imports from `tts/`, `audio/`, or `pipeline/`
- [ ] All public functions/classes have docstrings and type annotations
- [ ] `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` produces readable table output
- [ ] Task moved to `tasks/completed/`
