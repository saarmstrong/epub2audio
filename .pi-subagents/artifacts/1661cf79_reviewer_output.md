M5 sign-off complete. Summary of what I did and found:

**Finalized M5 sign-off** — Milestone 5 (Chapter-detection hardening) is marked ✅ Complete at the detection layer.

**Gates (M5 scope) — all GREEN:**
- 77 epub tests pass ✅
- mypy strict clean (39 files, 0 errors) ✅
- ruff check clean ✅
- ruff format clean ✅ (I applied the mechanical whitespace fix to 5 Tester files — the Tester's "ruff clean" claim was inaccurate; format was red)
- No regression on `simple_epub3.epub` ✅

**Code review:** `merge_consecutive_chapters()`, `split_multi_chapter_docs()`, `finalize_chapters()` orchestration, D3 scoring weights, and D4 fragment extraction are all correct, documented, and unit-tested (8 merge + 9 split tests). Fragment extraction degrades gracefully on missing anchors (no crash).

**Bookkeeping done:** status.md updated (M5→Complete, criteria updated, sign-off block added, current milestone advanced to M6); M5 task files moved to `tasks/completed/`.

**Two defects filed** (both non-blocking for M5 detection-layer closure):
- **DEFECT-005** — confirmed the 16 failures are the pre-existing M4 FFmpeg `loudnorm` exit-234 issue on FakeTTS silent input, **not M5 scope**. Recommended silence guard + FFmpeg skip guards, as you requested.
- **DEFECT-004** — I must flag this honestly: `finalize_chapters()` is **not wired** into `cli.py` (`inspect`) or `pipeline/planner.py` (`convert`) — both still call `select_chapters()` only. So merge/split is currently reachable only via unit tests, not the shipped product path. Worse, `converter._load_chapter_text` doesn't strip `#fragment` from source_docs and doesn't pass fragment bounds to `xhtml_to_text`, so wiring it as-is would silently drop/duplicate split-chapter text. The two acceptance criteria are therefore satisfied at the detection layer (✅¹) but need product integration in M6 to be true end-to-end.

Full suite: 188 passed, 16 failed (all DEFECT-005 FFmpeg), 6 skipped, 1 xfailed — 0 failures in M5 scope. No staged files.