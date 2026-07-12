# epub2audio — Project Status

_Last updated: 2026-07-12_

---

## Current Milestone

**Pre-work** — Repository scaffolding in progress. No code written yet.

---

## Milestone Tracker

| # | Milestone | Status | Notes |
|---|---|---|---|
| Pre | Repo structure + docs | 🟡 In progress | File structure created, no src/ code yet |
| 1 | Inspectable EPUB plan | ⬜ Not started | |
| 2 | Fake-TTS pipeline (MP3s without Kokoro) | ⬜ Not started | |
| 3 | Kokoro integration | ⬜ Not started | |
| 4 | Reliability (resume, manifest, report) | ⬜ Not started | |
| 5 | Chapter-detection hardening | ⬜ Not started | |
| 6 | Release readiness (docs, CI, packaging) | ⬜ Not started | |

---

## What Works Today

Nothing yet — pre-development.

---

## What is Explicitly Not Implemented

- All features (no code exists)

---

## Known Risks / Open Questions

- Kokoro PyPI package API stability — isolate in `tts/kokoro.py`
- `espeak-ng` requirement on macOS needs verification with actual Kokoro install
- Chapter-detection scoring thresholds will need tuning against real EPUBs

---

## Acceptance Criteria Progress

| Criterion | Done? |
|---|---|
| Valid non-DRM EPUB converts locally | ⬜ |
| One MP3 per logical chapter | ⬜ |
| Track order matches reading order | ⬜ |
| Human-readable sanitized chapter names | ⬜ |
| Does not assume filename order = reading order | ⬜ |
| Multi-file chapters can be merged | ⬜ |
| Multi-chapter single-file can be split | ⬜ |
| Navigation-only and empty pages excluded | ⬜ |
| `inspect` shows conversion plan | ⬜ |
| Every MP3 passes FFprobe validation | ⬜ |
| MP3s contain book/track metadata | ⬜ |
| Cover art embedded | ⬜ |
| Interrupted conversions resume | ⬜ |
| Config changes invalidate correct artifacts | ⬜ |
| Failed synthesis never silently omits text | ⬜ |
| No content sent over network | ✅ (by design — no network calls planned) |
| No DRM removal | ✅ (by design) |
| Unit + e2e tests pass | ⬜ |
| Ruff + type checking pass | ⬜ |
| New user can install from README | ⬜ |
