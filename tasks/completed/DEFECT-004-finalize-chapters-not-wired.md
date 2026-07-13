# DEFECT-004 — `finalize_chapters()` not wired into product path; converter drops fragment source_docs

**Found by:** Reviewer (M5 sign-off, 2026-07-12)
**Severity:** Medium (feature reachable only via unit tests; no data corruption in current shipped path)
**Milestone origin:** 5 — Chapter-detection hardening
**Blocks M5 detection-layer closure?** No (per Orchestrator decision — detection layer is
approved and unit-tested). This is a required M6 follow-up before the two
acceptance criteria are true end-to-end.

---

## Summary

M5 delivered `merge_consecutive_chapters()`, `split_multi_chapter_docs()`, and the
orchestrating `finalize_chapters()` in `src/epub2audio/epub/chapters.py`. These are
correct and covered by 77 passing unit tests. **However, they are not invoked by the
real product path:**

- `src/epub2audio/cli.py:77` (`inspect`) calls only `select_chapters(candidates)`.
- `src/epub2audio/pipeline/planner.py:40` (`convert`) calls only `select_chapters(candidates)`.

Neither calls `finalize_chapters()`. As a result, `epub2audio inspect` and
`epub2audio convert` do **not** merge multi-file chapters or split single-file
multi-chapter documents. The feature exists but is dead code from the user's
perspective.

## Second, coupled issue: converter fragment handling

`src/epub2audio/pipeline/converter.py:104-108` (`_load_chapter_text`) does:

```python
for doc_path in chapter.source_docs:
    item = book.get_item_with_href(doc_path)   # doc_path may be "path.xhtml#frag"
    ...
    texts.append(xhtml_to_text(content))       # no start_fragment / end_fragment
```

If `finalize_chapters()` were wired in as-is, split chapters carry `source_docs`
entries of the form `"chapters.xhtml#prologue"`. Then:

1. `get_item_with_href("chapters.xhtml#prologue")` returns `None` (ebooklib matches
   on href without the fragment) → the chapter's text is **silently dropped** (only a
   warning is logged). This trips the adversarial "text completeness" concern.
2. Even if the fragment were stripped, every split chapter sharing one file would
   receive the **full document text** (duplicated across chapters), because
   `xhtml_to_text` is called without `start_fragment`/`end_fragment`.

## Steps to reproduce (once wired)

1. Build an EPUB with one file containing two `#`-anchored TOC entries (see
   `tests/fixtures/builders.build_multi_chapter_single_file`).
2. Wire `finalize_chapters()` into `planner.py`.
3. Run `epub2audio convert book.epub out/`.
4. Observe: split chapters produce empty/duplicated MP3 text.

## Expected behaviour

- `inspect` and `convert` show merged / split chapters produced by `finalize_chapters()`.
- Split-chapter text is extracted per fragment via
  `xhtml_to_text(content, start_fragment=..., end_fragment=...)`.

## Actual behaviour

- Product path ignores `finalize_chapters()` entirely.
- Converter would drop or duplicate fragment text if wired without changes.

## Suggested fix

1. Replace `select_chapters(candidates)` with
   `finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)` in
   both `cli.py` (`inspect`) and `pipeline/planner.py`.
2. In `_load_chapter_text`, split `doc_path` on `#`; call `get_item_with_href` with the
   bare path and pass the fragment (and the next chapter's fragment as `end_fragment`)
   into `xhtml_to_text`.
3. Add an e2e test asserting split-chapter text is non-empty and non-duplicated, and an
   `inspect` test asserting merged `source_docs` render.

## Relevant files / lines

- `src/epub2audio/cli.py:77`
- `src/epub2audio/pipeline/planner.py:40`
- `src/epub2audio/pipeline/converter.py:104-110`
- `src/epub2audio/epub/chapters.py:688-718` (`finalize_chapters`)
