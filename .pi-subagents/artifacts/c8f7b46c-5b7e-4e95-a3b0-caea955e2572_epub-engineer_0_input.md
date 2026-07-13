# Task for epub-engineer

Read and complete tasks/active/M5-epub-engineer.md. This is Milestone 5: Chapter-Detection Hardening.

Key deliverables:

**D1: Multi-File Chapter Merging**
- Consecutive spine items where only the first has a TOC entry should merge
- Add `merge_consecutive_chapters()` function
- Combined `source_docs` and summed word counts

**D2: Single-File Chapter Splitting**
- Documents with fragment-based TOC entries should split
- Multiple h1 elements in one doc should split
- Support `doc.xhtml#fragment` in source_docs

**D3: Scoring Refinements**
- Add `titlepage`, `halftitlepage`, `seriespage`, `loi`, `lot`, `errata` to exclusion epub:types
- Adjust weights as needed

**D4: Fragment Extraction** (if needed)
- Update `xhtml_to_text()` to support `start_fragment` and `end_fragment` params

Key files:
- src/epub2audio/epub/chapters.py (main changes)
- src/epub2audio/epub/cleanup.py (fragment extraction)
- src/epub2audio/models.py (possibly extend source_docs or add ChapterSection)
- tests/fixtures/builders.py (new fixture builders)

Run tests: uv run pytest tests/ -v
Type check: uv run mypy src/epub2audio

---
Create and maintain progress at: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/progress/c8f7b46c-5b7e-4e95-a3b0-caea955e2572/progress.md

---
**Output:**
Write your findings to exactly this path: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/outputs/c8f7b46c-5b7e-4e95-a3b0-caea955e2572/m5-epub-engineer-result.md
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