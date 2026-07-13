# M4 — Reviewer Task: Reliability Sign-off

**Milestone:** 4 — Reliability (resume, manifest, report)  
**Agent:** Reviewer  
**Depends on:** M4-audio-engineer, M4-tester  
**Blocks:** Milestone 4 closure

---

## Overview

Verify that DEFECT-003 is fixed and the "Interrupted conversions resume" and "Config changes invalidate correct artifacts" acceptance criteria are met.

---

## Verification Checklist

### 1. Code Review

- [ ] `converter.py` changes are minimal and focused
- [ ] Work directory path is under output dir (not system temp)
- [ ] Manifest segment population is atomic and crash-safe
- [ ] Config invalidation is correct (TTS settings vs encoding settings)
- [ ] No regression in existing functionality

### 2. Gate Verification

```bash
# All tests pass
uv run pytest tests/ -v

# Type checking
uv run mypy src/epub2audio

# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

### 3. Manual Resume Test (requires FFmpeg)

```bash
# Step 1: Start conversion
uv run epub2audio convert tests/fixtures/simple_epub3.epub -o /tmp/m4-test

# Step 2: Verify work dir created
ls -la /tmp/m4-test/.epub2audio-work/

# Step 3: Verify manifest has segments
cat /tmp/m4-test/manifest.json | jq '.segments | length'
# Should be > 0

# Step 4: Delete the MP3s but keep work dir and manifest
rm /tmp/m4-test/*.mp3

# Step 5: Resume
uv run epub2audio convert tests/fixtures/simple_epub3.epub -o /tmp/m4-test --resume

# Step 6: Verify logs show "resumed from cached WAV"
# Step 7: Verify MP3s regenerated
ls -la /tmp/m4-test/*.mp3
```

### 4. Config Invalidation Test

```bash
# Step 1: Run with default voice
uv run epub2audio convert tests/fixtures/simple_epub3.epub -o /tmp/m4-config

# Step 2: Note segment count in manifest
cat /tmp/m4-config/manifest.json | jq '.segments | length'

# Step 3: Run again with different voice
uv run epub2audio convert tests/fixtures/simple_epub3.epub -o /tmp/m4-config --voice af_bella --resume

# Step 4: Verify work dir was cleared and segments re-synthesized
# (logs should show synthesis, not resume)
```

### 5. Acceptance Criteria Status

Update `docs/status.md` acceptance criteria:

| Criterion | Status |
|---|---|
| Interrupted conversions resume | ✅ or ❌ |
| Config changes invalidate correct artifacts | ✅ or ❌ |

---

## Sign-off Template

```markdown
## Reviewer Sign-off — Milestone 4 (YYYY-MM-DD)

**Result: APPROVED / APPROVED WITH CONDITIONS / REJECTED**

Gates verified:
- `uv run pytest tests/ -v` → N passed, M skipped
- `uv run mypy src/epub2audio` → Success, N files, 0 errors
- `uv run ruff check src/ tests/` → All checks passed
- `uv run ruff format --check src/ tests/` → N files formatted

Manual verification:
- Resume test: PASS / FAIL
- Config invalidation test: PASS / FAIL

Defects found:
- (list any issues)

Outstanding (does not block M4):
- (list any deferred issues)
```

---

## Exit Criteria

- [ ] All gate checks pass
- [ ] Manual resume test passes
- [ ] Config invalidation test passes
- [ ] DEFECT-003 can be moved to `tasks/completed/`
- [ ] `docs/status.md` updated with M4 sign-off
- [ ] Acceptance criteria updated
