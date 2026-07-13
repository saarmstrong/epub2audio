# DEFECT-002 — Chapter.word_count is 0 for documents with ≥ 200 words

**Filed by:** Reviewer
**Date:** 2026-07-12
**Severity:** Low — cosmetic in M1; must be resolved before M2 planning uses word counts
**Assigned to:** EPUB Engineer (deferred to Milestone 2)

---

## Steps to Reproduce

```bash
uv run epub2audio inspect tests/fixtures/simple_epub3.epub --json
```

Observe that both included chapters report `"word_count": 0`, even though each
chapter contains ~200 words of narration text (no `short_document` penalty
signal fires for them, confirming they are ≥ 200 words).

## Expected Behaviour

`Chapter.word_count` should equal the actual word count of the cleaned
narration text, computed via `epub/cleanup.py:word_count(xhtml_to_text(...))`,
as specified in the M1-epub-engineer contract for `select_chapters`
(M1-07: "`word_count`: count words in plain text of the doc").

## Actual Behaviour

`select_chapters` derives the count only from the `short_document(N_words)`
scoring signal via `_extract_word_count_from_signals`. That signal only fires
for documents **under** 200 words. Any chapter ≥ 200 words therefore falls
through to the `return 0` placeholder.

Result:
- JSON `inspect` output reports `word_count: 0` for all real chapters.
- The Rich table's `Words` column is blank for all included chapters.

## Impact Assessment

- **No silent text loss / corruption.** Every chapter is still selected,
  ordered correctly, and present in the output. Only the numeric word-count
  field is a placeholder. This was verified against both fixtures.
- Becomes a real bug in M2 if the planner/segmenter uses `word_count` for
  progress estimation, batching, or reporting.

## Root Cause

`src/epub2audio/epub/chapters.py` — `select_chapters()` calls
`_extract_word_count_from_signals(candidate.signals)`, and
`_extract_word_count_from_signals()` returns `0` when no
`short_document(...)` signal is present (see the function's own docstring:
"return 0 as a placeholder").

## Suggested Fix (M2)

`score_candidates` already reads and cleans each document's content. Carry the
real `word_count` forward — e.g. embed it in every candidate (not only short
ones) or thread the book/content through to `select_chapters` — so the true
count is stored on `Chapter.word_count`.

## File / Line

`src/epub2audio/epub/chapters.py` — `select_chapters()` and
`_extract_word_count_from_signals()`.

---

## Status

**Open — deferred to Milestone 2.** Explicitly accepted as a known limitation
for the Milestone 1 sign-off; does not block M1 because `inspect` chapter
ordering, selection, and completeness are all correct.
