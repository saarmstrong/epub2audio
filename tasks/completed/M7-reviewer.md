# M7 — Reviewer Task: M4B sign-off

**Milestone:** 7 — M4B output format  
**Agent:** Reviewer  
**Depends on:** M7-architect, M7-audio-engineer, M7-tester

---

## Overview

Verify the M4B feature end-to-end, confirm zero regression to the MP3 path, and
enforce project boundary/security rules. Do not implement primary features
(fix only trivial lint/format issues, as in prior milestones).

---

## Gates to Verify

- [ ] `uv run pytest tests/ -q` — all pass (M4B e2e runs with FFmpeg, skips cleanly without)
- [ ] `uv run mypy src/epub2audio` — 0 errors (strict)
- [ ] `uv run ruff check src/ tests/` and `ruff format --check` — clean
- [ ] `uv run epub2audio convert <fixture> -o /tmp/m4b --format m4b` — one `.m4b`,
      `ffprobe -show_chapters` shows correct chapters + offsets, cover present
- [ ] `uv run epub2audio convert <fixture> -o /tmp/mp3` (default) — MP3 path unchanged
- [ ] `--help` shows `--format` with `mp3`/`m4b`

## Boundary / Security Checks

- [ ] No `epub/` imports inside `audio/`; no `kokoro` imports outside `tts/kokoro.py`
- [ ] No `shell=True`; all FFmpeg via `utils/subprocess` argument arrays
- [ ] Atomic writes (`.tmp` + `os.replace`) for all new outputs
- [ ] No narration/body text in logs
- [ ] Decision record `002-m4b-output-format.md` matches implementation; status → Accepted

## Deliverable

- [ ] Append an "M7 Reviewer Sign-off" section to `docs/status.md`
- [ ] Move all `tasks/active/M7-*.md` to `tasks/completed/` on approval
- [ ] Update `README.md` / `CHANGELOG.md` are done (coordinate with Audio Engineer)
