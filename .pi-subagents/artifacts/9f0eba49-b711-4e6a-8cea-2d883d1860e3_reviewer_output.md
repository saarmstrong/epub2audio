All gates green, sign-off command produces the correct table, and nothing is staged. Here is my review summary.

## Milestone 1 Review — Summary

**Sign-off command** (`uv run epub2audio inspect tests/fixtures/simple_epub3.epub`) produces a Rich table with 2 chapters in correct reading order: **Chapter One = `b_chapter_01.xhtml`, Chapter Two = `a_chapter_02.xhtml`** — proving spine order is used, not filename order (the fixture deliberately inverts filename vs. reading order). EPUB2 fixture verified identically.

**Quality gates (all green):**
- `pytest tests/` → **35/35 pass** (also under `-W error::UserWarning`)
- `ruff check src/ tests/` → clean
- `ruff format --check` → clean
- `mypy src/epub2audio` → 0 errors (strict, 38 files)

**Known issues investigated:**
1. **errors.py parallel write** — coherent; all 8 exceptions present, correct `__init__` signatures with custom attributes (`dependency`, `language`, `segment_length`, `changed_keys`), no cross-module imports. ✅
2. **XMLParsedAsHTMLWarning** — **FIXED.** Switched `cleanup.py` and `chapters.py` from the lenient HTML parser (`"lxml"`) + `catch_warnings` suppression to the correct `BeautifulSoup(content, features="xml")` XML parser, and removed the now-dead `warnings`/`XMLParsedAsHTMLWarning` scaffolding. Warning count is 0, no regressions. ✅
3. **word_count = 0 for long chapters** — confirmed cosmetic (visible as `0` in JSON, blank in table); no text loss/corruption; tracked in **DEFECT-002**, deferred to M2. ✅
4. **pyproject.toml suppressions** — `B008`, `RUF001/2/3`, and the ebooklib mypy override are all legitimate and hide nothing. ✅
5. **builders.py concurrent write** — full 8-function API present with edge-case fixes intact. ✅

**Boundary/security:** no `kokoro` imports outside `tts/kokoro.py`; no `epub/` imports in `tts/`/`audio/`; no `subprocess`/`shell=True`; no book content in logs.

**MILESTONE 1 SIGN-OFF: APPROVED** — All success conditions met, all gates pass, chapter ordering/selection/completeness verified, `docs/status.md` updated, the single residual issue (DEFECT-002) is cosmetic and explicitly deferred to M2.