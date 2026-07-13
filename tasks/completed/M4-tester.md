# M4 — Tester Task: Resume & Manifest Tests

**Milestone:** 4 — Reliability (resume, manifest, report)  
**Agent:** Tester  
**Depends on:** M4-audio-engineer (partial — skeleton tests can be written first)  
**Blocks:** M4-reviewer

---

## Overview

Write tests that verify the segment-level resume functionality delivered by the Audio Engineer in M4. These tests ensure interrupted conversions can resume without re-synthesizing completed segments.

---

## Test Files to Create

### `tests/pipeline/test_resume.py`

Unit tests for the resume logic.

```python
# Test cases:

def test_segment_needs_synthesis_with_valid_cached_wav():
    """segment_needs_synthesis returns False when WAV exists and is non-empty."""

def test_segment_needs_synthesis_with_missing_wav():
    """segment_needs_synthesis returns True when audio_path file doesn't exist."""

def test_segment_needs_synthesis_with_empty_wav():
    """segment_needs_synthesis returns True when WAV file is 0 bytes."""

def test_segment_needs_synthesis_with_none_audio_path():
    """segment_needs_synthesis returns True when audio_path is None."""

def test_check_resume_detects_voice_change():
    """check_resume returns changed keys when voice differs from manifest."""

def test_check_resume_detects_speed_change():
    """check_resume returns changed keys when speed differs from manifest."""

def test_check_resume_unchanged_config():
    """check_resume returns empty list when config matches manifest."""

def test_check_resume_raises_on_epub_change():
    """check_resume raises FingerprintMismatchError when EPUB changed."""
```

### `tests/pipeline/test_manifest.py`

Tests for manifest persistence with segments.

```python
def test_manifest_segments_populated_after_synthesis():
    """Manifest.segments contains TextSegment entries after chapter synthesis."""

def test_manifest_segments_have_audio_path():
    """Each TextSegment in manifest.segments has a non-None audio_path."""

def test_manifest_segments_have_done_status():
    """Completed segments have status='done'."""

def test_manifest_preserved_on_interrupt():
    """Manifest file exists after partial conversion (simulated interrupt)."""

def test_manifest_segments_cleared_on_config_change():
    """Segments are cleared when TTS-affecting config changes."""
```

### `tests/pipeline/test_converter_resume.py`

Integration tests for the full resume flow.

```python
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg not installed")
class TestConverterResume:
    
    def test_resume_skips_completed_segments(self, tmp_path, fake_tts_engine):
        """Second conversion run skips segments that were synthesized in first run."""
        # 1. Run partial conversion (interrupt after 1 segment)
        # 2. Count TTS calls
        # 3. Run again with --resume
        # 4. Verify TTS call count is lower (segments were skipped)
    
    def test_resume_reuses_segment_wavs(self, tmp_path, fake_tts_engine):
        """Resumed run uses existing segment WAVs from work directory."""
        # 1. Run conversion
        # 2. Note segment WAV mtimes
        # 3. Run again with --resume
        # 4. Verify WAV mtimes unchanged (files not rewritten)
    
    def test_full_conversion_cleans_work_dir(self, tmp_path, fake_tts_engine):
        """Work directory is cleaned after successful full conversion."""
        # 1. Run full conversion (no interrupt)
        # 2. Verify .epub2audio-work/ is empty or deleted
    
    def test_interrupted_conversion_preserves_work_dir(self, tmp_path, fake_tts_engine):
        """Work directory preserved when conversion is interrupted."""
        # 1. Run partial conversion
        # 2. Verify .epub2audio-work/ contains segment WAVs
    
    def test_keep_intermediates_preserves_work_dir(self, tmp_path, fake_tts_engine):
        """--keep-intermediates preserves segment WAVs after success."""
        # 1. Run full conversion with keep_intermediates=True
        # 2. Verify .epub2audio-work/ still contains WAVs
    
    def test_voice_change_invalidates_segments(self, tmp_path, fake_tts_engine):
        """Changing voice between runs clears cached segments."""
        # 1. Run conversion with voice=af_heart
        # 2. Run again with voice=af_bella
        # 3. Verify all segments re-synthesized (TTS called for all)
    
    def test_speed_change_invalidates_segments(self, tmp_path, fake_tts_engine):
        """Changing speed between runs clears cached segments."""
    
    def test_bitrate_change_keeps_segments(self, tmp_path, fake_tts_engine):
        """Changing bitrate doesn't invalidate cached segment WAVs."""
        # Only the MP3 encoding step should re-run
```

---

## Test Fixtures Needed

Add to `tests/conftest.py` or `tests/pipeline/conftest.py`:

```python
@pytest.fixture
def conversion_with_interrupt(tmp_path, simple_epub3, fake_tts_engine):
    """Run a conversion that stops after N segments (simulates interrupt)."""
    # Returns (output_dir, manifest, segment_count)

@pytest.fixture  
def fake_tts_engine_with_counter():
    """FakeTTSEngine that counts synthesize() calls."""
    # Returns (engine, call_counter)
```

---

## Edge Cases to Cover

1. **Empty chapter** — chapter with no narration text should be skipped, not cached
2. **Corrupt WAV** — segment WAV that exists but is invalid → re-synthesize
3. **Manifest missing segments key** — old manifest format → start fresh
4. **Work dir deleted manually** — manifest references missing files → re-synthesize

---

## Exit Criteria

- [ ] All test files created in `tests/pipeline/`
- [ ] Tests pass with the Audio Engineer's implementation
- [ ] Edge cases covered (empty chapter, corrupt WAV, missing work dir)
- [ ] Tests run without FFmpeg where possible (mock encode/validate)
- [ ] `uv run pytest tests/pipeline/ -v` all pass
- [ ] `uv run ruff check tests/` passes
