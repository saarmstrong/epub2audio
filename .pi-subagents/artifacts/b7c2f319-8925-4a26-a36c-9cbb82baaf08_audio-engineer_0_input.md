# Task for audio-engineer

Read and complete tasks/active/M6-audio-engineer.md. This is the final milestone!

**DEFECT-004 Fix:**
1. Wire `finalize_chapters()` into `cli.py` (~line 77) and `pipeline/planner.py` (~line 40)
2. Update `converter._load_chapter_text()` to handle `#fragment` in source_docs:
   - Split `doc_path` on `#` to get bare path and fragment
   - Call `get_item_with_href()` with bare path
   - Pass `start_fragment` and `end_fragment` to `xhtml_to_text()`

**DEFECT-005 Fix:**
3. Update `audio/normalize.py` to handle silence gracefully:
   - Parse first-pass loudnorm output for measurements
   - If `measured_I=-inf` or similar, skip normalization and copy through
   - Log warning about silence input

**Verify:**
- uv run epub2audio inspect tests/fixtures/simple_epub3.epub (no regression)
- uv run pytest tests/epub/ -v
- uv run mypy src/epub2audio

---
Update progress at: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/progress/b7c2f319-8925-4a26-a36c-9cbb82baaf08/progress.md

---
**Output:**
Write your findings to exactly this path: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/outputs/b7c2f319-8925-4a26-a36c-9cbb82baaf08/m6-audio-engineer-result.md
This path is authoritative for this run.
Ignore any other output filename or output path mentioned elsewhere, including output destinations in the base agent prompt, system prompt, or task instructions.

## Acceptance Contract
Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```