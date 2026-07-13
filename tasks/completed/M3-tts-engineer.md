# M3 — TTS Engineer Task Contract

_Assigned: 2026-07-12_
_Milestone: 3 — Kokoro Integration_
_Agent: TTS Engineer_

---

## Scope

Implement four tasks that bring real Kokoro TTS synthesis into the project:

- M3-01 — `src/epub2audio/tts/kokoro.py`: `KokoroTTSEngine`
- M3-02 — `src/epub2audio/tts/voices.py`: voice catalogue and language map
- M3-03 — Extend `src/epub2audio/cli.py`: `voices` command
- M3-04 — Extend `src/epub2audio/cli.py`: `doctor` command

Do **not** modify any file outside `src/epub2audio/tts/` and `src/epub2audio/cli.py`.
Do **not** write tests (that is the Tester's contract).

---

## M3-01 — `src/epub2audio/tts/kokoro.py`: KokoroTTSEngine

Replace the existing stub with a full implementation.

### Class signature

```python
class KokoroTTSEngine:
    """TTS engine backed by the local Kokoro neural TTS model.

    All kokoro imports are isolated in this module. Importing this class
    is always safe; instantiation raises MissingDependencyError when the
    kokoro package is not installed.
    """

    def __init__(self, lang_code: str = "a") -> None: ...
    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        language: str,
        speed: float,
    ) -> list[AudioChunk]: ...
```

### Implementation rules

1. **All kokoro imports must be inside `try/except ImportError` blocks — never at module level.**
   This ensures `from epub2audio.tts.kokoro import KokoroTTSEngine` always succeeds,
   even when the `tts` extras are not installed.

2. **`__init__`**:
   ```python
   try:
       from kokoro import KPipeline
   except ImportError as exc:
       raise MissingDependencyError("kokoro") from exc
   self._pipeline = KPipeline(lang_code=lang_code)
   ```

3. **`synthesize`**:
   - Call `get_lang_code(language)` from `tts/voices.py` to map the BCP-47
     `language` arg to a Kokoro `lang_code`.
   - Call `self._pipeline(text, voice=voice, speed=speed)` — this returns a
     generator of `(graphemes, sample_rate, audio_array)` tuples.
   - Collect **all** pieces: `[AudioChunk(sample_rate=sr, data=audio) for _, sr, audio in generator]`.
   - Do **not** hardcode `sample_rate=24000`; read it from each piece returned by the pipeline.
   - Propagate `UnsupportedLanguageError` from `get_lang_code` unchanged.

4. **Structural Protocol compatibility**: The class must satisfy
   `isinstance(obj, TTSEngine)` checks structurally (i.e., have the right method
   signatures). Import `TTSEngine` at module level from `tts/base.py` is fine
   (no kokoro involved there); the kokoro import guard is only for `kokoro.*`.

5. **`AudioChunk`** is imported from `epub2audio.models` (already defined there).

### Acceptance gate (M3-01)

```
uv run mypy src/epub2audio/tts/kokoro.py                           # 0 errors
python -c "from epub2audio.tts.kokoro import KokoroTTSEngine"      # succeeds without kokoro installed
```

---

## M3-02 — `src/epub2audio/tts/voices.py`: voice catalogue and language map

Replace the existing stub with the following full implementation.

### Required content

```python
"""Voice catalogue and language map for Kokoro TTS."""

from epub2audio.errors import UnsupportedLanguageError

# Language code map (Kokoro lang_code values)
LANGUAGE_MAP: dict[str, str] = {
    "en-us": "a",
    "en-gb": "b",
    "fr-fr": "f",
    "ja":    "j",
    "ko":    "k",
    "cmn":   "z",
    "zh":    "z",
}

# Curated voice catalogue: voice_id → human-readable description
VOICE_CATALOGUE: dict[str, str] = {
    "af_heart":    "Afrikaans Heart (default)",
    "af_bella":    "Afrikaans Bella",
    "af_sarah":    "Afrikaans Sarah",
    "am_adam":     "American Adam",
    "am_michael":  "American Michael",
    "bf_emma":     "British Emma",
    "bf_isabella": "British Isabella",
    "bm_george":   "British George",
    "bm_lewis":    "British Lewis",
}


def get_lang_code(language: str) -> str:
    """Return the Kokoro lang_code for a BCP-47 language tag.

    Raises UnsupportedLanguageError for unsupported languages.
    """
    key = language.lower()
    if key not in LANGUAGE_MAP:
        raise UnsupportedLanguageError(language)
    return LANGUAGE_MAP[key]


def list_voices() -> list[tuple[str, str]]:
    """Return sorted list of (voice_id, description) pairs."""
    return sorted(VOICE_CATALOGUE.items())
```

### Notes

- `UnsupportedLanguageError` is already defined in `errors.py`; check its
  constructor signature before raising it.
- Do not add any other public symbols — keep the interface minimal.

### Acceptance gate (M3-02)

```
uv run mypy src/epub2audio/tts/voices.py    # 0 errors
```

---

## M3-03 — Extend `src/epub2audio/cli.py`: `voices` command

Add a new Typer sub-command `voices` that lists the available Kokoro voices.

### Specification

```python
@app.command()
def voices() -> None:
    """List available Kokoro TTS voices."""
    from epub2audio.tts.voices import VOICE_CATALOGUE, list_voices

    table = Table(title="Kokoro TTS Voices")
    table.add_column("Voice ID", style="cyan", no_wrap=True)
    table.add_column("Description")
    for voice_id, description in list_voices():
        table.add_row(voice_id, description)
    console.print(table)
    console.print(f"{len(VOICE_CATALOGUE)} voices available.")
```

- Import `list_voices` and `VOICE_CATALOGUE` locally (inside the function body)
  to avoid a top-level cycle risk.
- The Rich `console` object is already defined in `cli.py`; use the existing one.
- The existing `inspect` and `convert` commands must not regress.

### Acceptance gate (M3-03)

```
uv run epub2audio voices    # prints table with ≥ 9 rows
```

---

## M3-04 — Extend `src/epub2audio/cli.py`: `doctor` command

Add a new Typer sub-command `doctor` that inspects the runtime environment.

### Specification

```python
@app.command()
def doctor() -> None:
    """Check the epub2audio environment and dependencies."""
```

Checks to perform (print ✅ or ❌ prefix for each line):

| # | Item | Source | Pass condition |
|---|---|---|---|
| 1 | Python | `sys.version` | Always ✅; show version string |
| 2 | FFmpeg | `shutil.which("ffmpeg")` | ✅ path / ❌ "not found" |
| 3 | FFprobe | `shutil.which("ffprobe")` | ✅ path / ❌ "not found" |
| 4 | espeak-ng | `shutil.which("espeak-ng")` | ✅ path / ⚠️ "not found (optional)" |
| 5 | kokoro package | `import kokoro; kokoro.__version__` | ✅ version / ⚠️ "not installed (optional)" |
| 6 | misaki package | `import misaki; misaki.__version__` | ✅ version / ⚠️ "not installed (optional)" |
| 7 | Disk space | `shutil.disk_usage(".")` | Always ✅; show free GB |

**Exit code rules**:
- Exit **0** if FFmpeg and FFprobe are both present.
- Exit **1** if either FFmpeg or FFprobe is missing.
- `espeak-ng`, `kokoro`, and `misaki` are optional — their absence is a warning, not an error.

Use `raise typer.Exit(code=1)` (or `typer.Exit(code=0)`) to set the process exit code.
Print a Rich table or formatted lines — either is acceptable, but the output must be
human-readable and show ✅/❌ symbols clearly.

### Acceptance gate (M3-04)

```
uv run epub2audio doctor                    # exits 0 or 1 (never crashes)
uv run mypy src/epub2audio/cli.py           # 0 errors
```

---

## Cross-cutting requirements

- All four tasks must pass `uv run mypy src/epub2audio/tts/kokoro.py src/epub2audio/tts/voices.py src/epub2audio/cli.py` → 0 errors.
- `uv run ruff check` → clean (no new violations).
- `uv run ruff format src/ tests/` → already formatted (no diff).
- `uv run pytest tests/ -v` → the existing 112 tests still pass (0 regressions).
- All public functions and classes must have docstrings and type annotations (strict mypy).
- `src/epub2audio/` must remain importable at all times during implementation.

---

## Done criteria

All four tasks fully implemented, all acceptance gates above pass, and this file moved to `tasks/completed/`.
