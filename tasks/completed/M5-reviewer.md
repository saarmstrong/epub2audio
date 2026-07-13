# M5 — Reviewer Task: Chapter-Detection Hardening Sign-off

**Milestone:** 5 — Chapter-detection hardening  
**Agent:** Reviewer  
**Depends on:** M5-epub-engineer, M5-tester  
**Blocks:** Milestone 5 closure

---

## Overview

Verify that chapter-detection hardening is complete and the "Multi-file chapters
can be merged" and "Multi-chapter single-file can be split" acceptance criteria
are satisfied.

---

## Verification Checklist

### 1. Gate Verification

```bash
# All tests pass
uv run pytest tests/ -v

# Type checking
uv run mypy src/epub2audio

# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

### 2. Code Review

- [ ] `chapters.py` changes are well-structured
- [ ] Merge/split logic is clearly separated from scoring
- [ ] New scoring weights are documented
- [ ] Fragment extraction (if implemented) is safe
- [ ] No regression in existing chapter detection

### 3. Manual Testing

```bash
# Test multi-file merge
uv run epub2audio inspect tests/fixtures/multifile_chapter.epub
# Verify: Chapters with multiple source_docs displayed correctly

# Test single-file split
uv run epub2audio inspect tests/fixtures/singlefile_multichapter.epub
# Verify: Multiple chapters from one source file

# Test existing EPUBs still work
uv run epub2audio inspect tests/fixtures/simple_epub3.epub
# Verify: No regression (2 chapters, correct reading order)
```

### 4. Acceptance Criteria Verification

| Criterion | Test |
|-----------|------|
| Multi-file chapters can be merged | `inspect` shows combined source_docs |
| Multi-chapter single-file can be split | `inspect` shows fragment-based chapters |

### 5. Edge Cases

- [ ] Empty sections handled gracefully
- [ ] Invalid fragment references don't crash
- [ ] Very large single-file EPUBs perform acceptably
- [ ] Mixed h1/h2 structures detected correctly

---

## Sign-off Template

```markdown
## Reviewer Sign-off — Milestone 5 (YYYY-MM-DD)

**Result: APPROVED / APPROVED WITH CONDITIONS / REJECTED**

Gates verified:
- `uv run pytest tests/ -v` → N passed, M skipped
- `uv run mypy src/epub2audio` → Success, N files, 0 errors
- `uv run ruff check src/ tests/` → All checks passed
- `uv run ruff format --check src/ tests/` → N files formatted

Manual verification:
- Multi-file merge test: PASS / FAIL
- Single-file split test: PASS / FAIL
- Existing EPUB regression test: PASS / FAIL

Acceptance criteria:
- Multi-file chapters can be merged: ✅ / ❌
- Multi-chapter single-file can be split: ✅ / ❌

Defects found:
- (list any issues)

Outstanding (does not block M5):
- (list any deferred issues)
```

---

## Bookkeeping

After approval:
1. Update `docs/status.md`:
   - Move M5 to ✅ Complete
   - Add sign-off block
   - Update acceptance criteria
2. Move task files to `tasks/completed/`:
   - `M5-epub-engineer.md`
   - `M5-tester.md`
   - `M5-reviewer.md`

---

## Exit Criteria

- [ ] All gate checks pass
- [ ] Multi-file merge verified
- [ ] Single-file split verified
- [ ] No regression in existing fixtures
- [ ] `docs/status.md` updated with M5 sign-off
- [ ] Task files moved to `tasks/completed/`
