# DEFECT-001 — navigation.py crashes when book.toc is a Link object

**Filed by:** Tester  
**Date:** 2026-07-12  
**Severity:** Medium — affects fallback spine path for EPUBs with empty TOC  
**Assigned to:** EPUB Engineer

---

## Steps to Reproduce

```python
from tests.fixtures.builders import build_no_nav_epub
from epub2audio.epub.reader import open_epub
from epub2audio.epub.navigation import extract_navigation
from pathlib import Path

p = Path("/tmp/no_nav_test.epub")
build_no_nav_epub(p)
book = open_epub(p)
entries = extract_navigation(book)  # raises TypeError
```

## Expected Behaviour

When an EPUB has no EPUB3 nav document and an empty NCX navMap, 
`extract_navigation` should fall back to spine order and return one 
`NavigationEntry` per spine item with `title=""` and `fragment=None`.

## Actual Behaviour

```
TypeError: 'Link' object is not iterable
```

## Root Cause

In `src/epub2audio/epub/navigation.py`, line 139:

```python
toc: list[object] = list(book.toc) if book.toc else []
```

When ebooklib reads an EPUB with an empty NCX `<navMap/>`, it sets 
`book.toc` to a single `ebooklib.epub.Link` object (not a list or tuple).  
Calling `list()` on a `Link` raises `TypeError` because `Link` is not 
iterable.

The truthiness check `if book.toc` evaluates to `True` for a `Link` 
object, so the guard does not help.

## Fix

In `extract_navigation`, normalise `book.toc` to a list before processing:

```python
raw_toc = book.toc
if raw_toc is None:
    toc: list[object] = []
elif isinstance(raw_toc, list):
    toc = raw_toc
else:
    # ebooklib returns a single Link (not a list) when navMap is empty
    toc = [raw_toc] if raw_toc else []
```

Then filter out any resulting entries that have empty `href` (the 
degenerate Link produced from an empty navMap typically has `href=""`).

## Affected Test

`tests/epub/test_navigation.py::test_fallback_spine_order_on_no_nav`

## File / Line

`src/epub2audio/epub/navigation.py` line 139

---

## Resolution

**Closed 2026-07-12** — Test run showed the test actually PASSES (was
marked xfail prematurely). The `extract_navigation` implementation
handled this edge case correctly when the no-nav fixture was properly
built with `build_no_nav_epub` (EpubNcx included, empty toc list).
The xfail marker was removed and the test passes cleanly.
