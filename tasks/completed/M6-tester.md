# M6 — Tester Task: Integration & E2E Tests

**Milestone:** 6 — Release readiness  
**Agent:** Tester  
**Depends on:** M6-audio-engineer  
**Blocks:** M6-reviewer

---

## Overview

Write tests verifying the product integration of merge/split and the FFmpeg
silence handling fix.

---

## Test Files

### `tests/epub/test_chapters_integration.py` (new)

Test that `finalize_chapters()` is properly wired:

```python
def test_inspect_shows_merged_chapters(tmp_path):
    """epub2audio inspect displays merged source_docs."""
    # Create multifile_chapter.epub
    # Run inspect via CLI runner
    # Assert output shows multiple source_docs for one chapter

def test_inspect_shows_split_chapters(tmp_path):
    """epub2audio inspect displays fragment-based chapters."""
    # Create singlefile_multichapter.epub
    # Run inspect via CLI runner
    # Assert output shows chapters with #fragment in source_doc

def test_planner_uses_finalize_chapters(tmp_path):
    """plan_conversion returns merged/split chapters."""
    # Build fixture, call plan_conversion directly
    # Assert chapters have correct source_docs structure
```

### `tests/pipeline/test_converter_fragments.py` (new)

Test fragment handling in converter:

```python
def test_load_chapter_text_with_fragment(tmp_path):
    """_load_chapter_text extracts only fragment-bounded text."""
    # Create EPUB with fragment-based chapter
    # Call _load_chapter_text
    # Assert text is fragment-specific, not full document

def test_load_chapter_text_strips_fragment_for_lookup(tmp_path):
    """source_doc 'path.xhtml#frag' finds 'path.xhtml' item."""
    # Create EPUB
    # Call _load_chapter_text with fragment source_doc
    # Assert no "not found" warning

def test_split_chapters_have_distinct_text(tmp_path):
    """Each split chapter extracts its own section, not duplicates."""
    # Create multi-chapter single file
    # Extract text for each chapter
    # Assert texts are different and non-empty
```

### `tests/audio/test_normalize_silence.py` (new)

Test FFmpeg silence handling:

```python
import numpy as np
import soundfile as sf

def test_normalize_silence_input_graceful(tmp_path):
    """normalize_loudness handles pure-silence input without crashing."""
    # Create silence WAV
    silence = np.zeros(24000, dtype=np.float32)  # 1 second silence
    input_wav = tmp_path / "silence.wav"
    sf.write(input_wav, silence, 24000)
    
    output_wav = tmp_path / "output.wav"
    
    # Should not raise
    normalize_loudness(input_wav, output_wav)
    
    # Output should exist
    assert output_wav.exists()

def test_normalize_silence_logs_warning(tmp_path, caplog):
    """normalize_loudness logs warning for silence input."""
    # Similar setup
    # Assert "skipping normalization" or similar in logs
```

### Update `tests/pipeline/test_converter_resume.py`

After DEFECT-005 fix, the 16 failing tests should pass. Verify:
- Tests that were failing now pass OR
- Tests properly skip when FFmpeg loudnorm can't handle the input

---

## Exit Criteria

- [ ] `test_chapters_integration.py` tests inspect/planner wiring
- [ ] `test_converter_fragments.py` tests fragment text extraction
- [ ] `test_normalize_silence.py` tests silence handling
- [ ] Previously failing 16 tests now pass or skip correctly
- [ ] `uv run pytest tests/ -v` all pass (except model-gated skips)
- [ ] `uv run ruff check tests/` passes
