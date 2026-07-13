# M6 — Reviewer Task: Release Readiness Sign-off

**Milestone:** 6 — Release readiness (docs, CI, packaging)  
**Agent:** Reviewer  
**Depends on:** M6-audio-engineer, M6-docs-engineer, M6-tester  
**Blocks:** Project completion

---

## Overview

Final milestone review. Verify all acceptance criteria are met and the project
is ready for release.

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

### 2. DEFECT-004 Verification (Product Integration)

```bash
# Test merged chapters in inspect
uv run epub2audio inspect tests/fixtures/multifile_chapter.epub
# Verify: Chapter shows multiple source_docs

# Test split chapters in inspect
uv run epub2audio inspect tests/fixtures/singlefile_multichapter.epub
# Verify: Multiple chapters from same file with #fragments
```

### 3. DEFECT-005 Verification (FFmpeg Silence)

```bash
# The 16 previously failing tests should now pass
uv run pytest tests/pipeline/test_converter_resume.py tests/test_e2e.py -v
# Verify: No exit 234 failures
```

### 4. Documentation Verification

- [ ] README.md exists and is comprehensive
- [ ] Installation instructions work
- [ ] Quick start example works
- [ ] CHANGELOG.md exists
- [ ] LICENSE file exists

### 5. Final Acceptance Criteria

| Criterion | Verify |
|-----------|--------|
| Valid non-DRM EPUB converts locally | Manual test with real EPUB |
| One MP3 per logical chapter | Check output structure |
| Track order matches reading order | Verify MP3 numbering |
| Multi-file chapters can be merged | inspect shows merged docs |
| Multi-chapter single-file can be split | inspect shows fragments |
| Every MP3 passes FFprobe validation | Run ffprobe on outputs |
| MP3s contain book/track metadata | Check ID3 tags |
| Cover art embedded | Verify cover in MP3 |
| Failed synthesis never silently omits text | Check warning logs |
| New user can install from README | Fresh install test |

### 6. Security Review

- [ ] No `shell=True` in subprocess calls
- [ ] No book content in log statements
- [ ] DRM detection works (rejects protected EPUBs)
- [ ] No network calls

---

## Sign-off Template

```markdown
## Reviewer Sign-off — Milestone 6 / Final Release (YYYY-MM-DD)

**Result: APPROVED / APPROVED WITH CONDITIONS / REJECTED**

Gates verified:
- `uv run pytest tests/ -v` → N passed, M skipped
- `uv run mypy src/epub2audio` → Success
- `uv run ruff check src/ tests/` → All passed
- `uv run ruff format --check src/ tests/` → All formatted

DEFECT-004 verification:
- Merged chapters in inspect: PASS / FAIL
- Split chapters in inspect: PASS / FAIL
- Fragment text extraction: PASS / FAIL

DEFECT-005 verification:
- Silence handling: PASS / FAIL
- Previously failing tests: PASS / FAIL

Documentation:
- README complete: YES / NO
- Installation works: YES / NO

Acceptance criteria: [X/Y] complete

Outstanding issues:
- (list any remaining issues)
```

---

## Bookkeeping

After approval:
1. Update `docs/status.md`:
   - Move M6 to ✅ Complete
   - Add final sign-off block
   - All acceptance criteria should be ✅
2. Move all M6 tasks to `tasks/completed/`
3. Close DEFECT-004 and DEFECT-005
4. Tag release v0.1.0

---

## Exit Criteria

- [ ] All gates pass
- [ ] DEFECT-004 fixed and verified
- [ ] DEFECT-005 fixed and verified  
- [ ] Documentation complete
- [ ] All acceptance criteria met
- [ ] Project ready for v0.1.0 release
