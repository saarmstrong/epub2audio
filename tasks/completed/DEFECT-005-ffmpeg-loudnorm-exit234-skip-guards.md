# DEFECT-005 — FFmpeg `loudnorm` exit 234 on silent input; pipeline tests fail instead of skipping

**Found by:** Reviewer (M5 sign-off, 2026-07-12)
**Severity:** Medium (pre-existing; environment-dependent; not M5 scope)
**Milestone origin:** 4 — Reliability (surfaced now that FFmpeg is installed on the
review machine)

---

## Summary

With FFmpeg present on the review machine, 16 M4 pipeline / e2e tests fail (they
previously *skipped* when FFmpeg was absent). The failing FFmpeg command is the
`loudnorm` normalization pass, which returns exit status **234** on FakeTTS silent
input:

```
ffmpeg -y -i chapter.wav -af loudnorm=I=-18.0:TP=-2.0:LRA=7.0:\
  measured_I=-inf:measured_TP=-inf:measured_LRA=0.00:measured_thresh=-70.00:\
  offset=inf:linear=true:print_format=none chapter_norm.wav.tmp
→ returned non-zero exit status 234
```

The `measured_I=-inf` / `offset=inf` values are produced by FakeTTS pure-silence
audio; `loudnorm` linear mode rejects the resulting filter args.

## Affected tests (16)

- `tests/pipeline/test_converter_resume.py` (8)
- `tests/pipeline/test_segment_resume.py` (4)
- `tests/test_e2e.py` (4)

Cascade effect: because the chapter fails normalization, `duration_seconds` stays
`0.0` and downstream assertions (`> 0`, "two MP3s", "no errors in report") fail.

## Expected behaviour

Either:
- The two-pass `loudnorm` measurement is guarded so pure-silence input degrades
  gracefully (skip normalization, or fall back to copy), **or**
- These tests skip when the input is silent / when running against FakeTTS, matching
  the M2–M4 conditional-approval pattern.

## Actual behaviour

Tests hard-fail on any machine where FFmpeg is installed.

## Suggested fix

1. In `audio/normalize.py`, detect degenerate `measured_*` values (`-inf`/`inf`) from
   the first `loudnorm` pass and skip the linear second pass (copy through instead of
   erroring).
2. Add a regression test using pure-silence WAV input.
3. Revisit the M2/M4 "deferred to CI" note — CI must exercise this path with real
   (non-silent) audio.

## Relevant files

- `src/epub2audio/audio/normalize.py`
- `src/epub2audio/pipeline/converter.py` (`_process_chapter` error handling)
