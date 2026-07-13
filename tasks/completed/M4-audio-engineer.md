# M4 — Audio Engineer Task: Segment Resume & Manifest Persistence

**Milestone:** 4 — Reliability (resume, manifest, report)  
**Agent:** Audio Engineer  
**Depends on:** None  
**Blocks:** M4-tester, M4-reviewer

---

## Overview

Fix DEFECT-003: segment-level resume is non-functional. The manifest's `segments` list is never populated, and segment WAVs are written to a temporary directory that is deleted when the conversion ends. This task makes interrupted conversions resumable by persisting segment state.

---

## Deliverables

### D1: Persistent Work Directory

Change `converter.py` to write segment WAVs to a persistent per-book work directory rather than an OS temp directory.

Location: `<output_dir>/.epub2audio-work/<chapter_id>/`

This directory survives across runs. Only cleaned up when:
- A chapter's final MP3 is successfully validated (unless `--keep-intermediates`)
- The manifest fingerprint changes (full invalidation)

**Implementation notes:**
- Create the work dir structure: `output_dir / ".epub2audio-work" / chapter_id`
- Segment WAV naming: `seg_NNNN.wav` (4-digit zero-padded)
- Update `_process_chapter` to use this persistent location

### D2: Manifest Segment Population

Update the conversion loop to populate `manifest.segments` with each `TextSegment` after successful synthesis.

Each segment entry must include:
- `audio_path`: Absolute or relative path to the segment WAV
- `status`: `"done"` for successful synthesis
- `normalized_hash`: Hash of the normalized text (for matching on resume)

**Implementation notes:**
- After each segment synthesis, append to a running list
- After each chapter, update the manifest with the new segments
- Write manifest atomically after each chapter (already done, but segments empty)

### D3: Resume Logic Integration

Wire up the existing `segment_needs_synthesis()` function in `resume.py`:

1. In `_process_chapter`, before synthesizing each segment:
   - Look up segment by `normalized_hash` in `manifest.segments`
   - If found and `segment_needs_synthesis()` returns `False`, skip synthesis
   - Use the existing `audio_path` from the manifest

2. Log when skipping resumed segments:
   ```
   "Chapter %r segment %d: resumed from cached WAV"
   ```

### D4: Config Change Invalidation

When `check_resume()` detects config changes:
1. Clear the work directory for affected chapters
2. Clear the manifest's segment list
3. Log which settings changed

**Config keys that invalidate segments:**
- `voice`, `language`, `speed` — affect TTS output
- `normalize`, `bitrate`, `sample_rate` — only invalidate final MP3, not segments

Implement a two-tier invalidation:
- TTS-affecting changes → clear segment WAVs
- Encoding-affecting changes → keep segment WAVs, regenerate MP3s

### D5: Cleanup Rules

Update the cleanup logic:

1. After successful chapter MP3 validation:
   - If `--keep-intermediates` is False: delete `<work_dir>/<chapter_id>/`
   - If `--keep-intermediates` is True: preserve segment WAVs

2. On full conversion success:
   - If all chapters complete and `--keep-intermediates` is False:
     - Remove `.epub2audio-work/` directory entirely

3. Never delete work dir if conversion was interrupted (to enable resume)

---

## Implementation Plan

1. Modify `_new_manifest()` — no changes needed (already creates empty segments)

2. Modify `_process_chapter()`:
   - Accept a mutable segment accumulator list
   - Use persistent work dir instead of temp dir
   - After each segment synthesis, create a `TextSegment` with `audio_path` set
   - Append to the accumulator

3. Modify the main chapter loop in `convert_epub()`:
   - Pass a segment accumulator to `_process_chapter`
   - After each chapter, update `manifest.segments` with accumulated segments
   - Write manifest (already done)

4. Add `clear_segment_cache()` helper:
   - Called when config hash changes
   - Deletes work dir contents
   - Resets manifest.segments to []

5. Update cleanup in `_process_chapter()`:
   - Respect `--keep-intermediates` flag
   - Only clean up on success

---

## Testing Verification

Before marking complete, verify:

```bash
# 1. Start a conversion, interrupt after chapter 1
uv run epub2audio convert tests/fixtures/simple_epub3.epub --output /tmp/test-resume

# 2. Verify work dir exists with segment WAVs
ls -la /tmp/test-resume/.epub2audio-work/

# 3. Resume conversion
uv run epub2audio convert tests/fixtures/simple_epub3.epub --output /tmp/test-resume --resume

# 4. Verify logs show "resumed from cached WAV" for chapter 1 segments

# 5. Verify final MP3s are valid
ffprobe /tmp/test-resume/*.mp3
```

---

## Files to Modify

- `src/epub2audio/pipeline/converter.py` — main changes
- `src/epub2audio/pipeline/resume.py` — config invalidation helpers
- `src/epub2audio/config.py` — add `keep_intermediates` setting if not present

---

## Exit Criteria

- [ ] Segment WAVs written to persistent `.epub2audio-work/` directory
- [ ] `manifest.segments` populated with `TextSegment` entries after synthesis
- [ ] Interrupted conversions resume and skip already-synthesized segments
- [ ] Config changes (voice/language/speed) invalidate segment cache
- [ ] `--keep-intermediates` preserves segment WAVs after success
- [ ] All existing tests still pass
- [ ] `uv run mypy src/epub2audio` passes
- [ ] `uv run ruff check src/` passes
