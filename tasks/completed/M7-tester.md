# M7 — Tester Task: M4B unit + e2e coverage

**Milestone:** 7 — M4B output format  
**Agent:** Tester  
**Depends on:** M7-architect, M7-audio-engineer (contracts)  
**Blocks:** M7-reviewer

---

## Overview

Cover the M4B assembly path with fast unit tests (no FFmpeg) and an
FFmpeg-gated e2e test, following the existing `shutil.which("ffmpeg")` skip
pattern used by `tests/pipeline/test_e2e.py`.

---

## Deliverables

### D1: FFmetadata writer — `tests/audio/test_chapters_meta.py` (no FFmpeg)

- One `[CHAPTER]` block per marker; `TIMEBASE=1/1000`; correct START/END.
- Escaping of `=`, `;`, `#`, `\`, and newlines in title/tag values.
- Book tags header present; empty marker list handled.

### D2: AAC encoder args — `tests/audio/test_encode_aac.py` (mocked)

- Patch `epub2audio.audio.encode.run_command`; assert argument array uses
  `-c:a aac`, `-ac 1`, `-f mp4`, atomic `.tmp` then rename (mirror
  `test_encode.py`).

### D3: Validation — `tests/audio/test_validate_m4b.py`

- Parameterized codec check: AAC passes, wrong codec raises `Epub2AudioError`.
- Chapter-count mismatch raises. (Mock ffprobe JSON incl. `chapters`.)

### D4: e2e — `tests/pipeline/test_e2e_m4b.py` (FFmpeg-gated)

```python
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg not installed")
```

- Convert `simple_epub3.epub` with `output_format="m4b"` via FakeTTS.
- ffprobe the output: single `.m4b`, one AAC stream, **2 chapters** at expected
  offsets, positive total duration, cover stream present.
- Silence guard: FakeTTS silence must not break the mux (loudnorm degenerate
  path from DEFECT-005 already handles per-chapter).

### D5: MP3 regression guard

- Add/verify a test asserting `--format mp3` (default) still yields one MP3 per
  chapter — no behaviour change.

---

## Files to Add

- `tests/audio/test_chapters_meta.py`
- `tests/audio/test_encode_aac.py`
- `tests/audio/test_validate_m4b.py`
- `tests/pipeline/test_e2e_m4b.py`

---

## Exit Criteria

- [ ] Unit tests pass without FFmpeg
- [ ] e2e M4B test passes with FFmpeg installed (skips cleanly without)
- [ ] MP3 regression test green
- [ ] `uv run ruff check tests/` + `ruff format --check tests/` clean
