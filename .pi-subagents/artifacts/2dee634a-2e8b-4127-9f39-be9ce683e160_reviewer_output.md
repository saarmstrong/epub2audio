All verifications pass. Here is my review summary.

## Milestone 3 Review — Summary

**Verification commands (all run):**
- `epub2audio voices` → Rich table, **9 voices** including `af_heart` (default), "9 voices available." footer, **exit 0** ✅
- `epub2audio doctor` → status line for Python, FFmpeg, FFprobe, espeak-ng, kokoro, misaki, disk; FFmpeg+FFprobe absent → **exit 1** (correct) ✅
- `pytest tests/ -v` → **117 passed, 11 skipped, 0 failed** ✅
- `ruff check` / `ruff format --check` / `mypy` (strict) → all clean ✅
- `inspect` and `convert --help` → no CLI regressions (spine order preserved) ✅

**Defects fixed directly:**
1. **`tts/voices.py`** — `af_heart`/`af_bella`/`af_sarah` were labelled "Afrikaans". In Kokoro `af_` = American English female (the `a` maps to `en-us` → `"a"` in this module's own `LANGUAGE_MAP`); none are Afrikaans. Relabelled to "American …". Would have actively misled users.
2. **`tts/kokoro.py`** — the class docstring implied `synthesize(language=...)` selects the pipeline language; it only validates. Added an explicit "Single-language scope (by design)" section documenting that the engine is locked to its init-time `lang_code`.
3. **Hygiene** — removed stray untracked scratch artifacts `0.wav` and `test_kokoro.py` from the repo root.

**Known issues investigated:** language-scope is intentional (now documented); mypy overrides are exactly 3 stanzas, no duplicates, all legitimate; the 6 smoke tests carry `slow`+`requires_model` marks and skip cleanly by default (structurally correct); doctor exit-code contract verified via code path (0 iff both ffmpeg+ffprobe, else 1, never 2+); import boundaries clean — the only non-`tts/kokoro.py` kokoro import is a guarded `__version__` read in `doctor`, `tts/kokoro.py` imports without the package, no `epub/` imports in `tts/`/`audio/`.

**No staged files.** `docs/status.md` updated with the M3 sign-off.

**MILESTONE 3 SIGN-OFF: APPROVED**