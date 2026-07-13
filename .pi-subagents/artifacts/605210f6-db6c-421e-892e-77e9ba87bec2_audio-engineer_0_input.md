# Task for audio-engineer

Read and complete tasks/active/M4-audio-engineer.md. This is the Milestone 4 reliability task. Fix DEFECT-003 by:

1. Creating a persistent work directory at <output>/.epub2audio-work/<chapter_id>/ for segment WAVs
2. Populating manifest.segments with TextSegment entries after each synthesis (with audio_path set)
3. Wiring up segment_needs_synthesis() to skip already-cached segments on resume
4. Implementing config change invalidation (voice/language/speed changes clear segment cache)
5. Adding proper cleanup rules (delete work dir only on full success unless --keep-intermediates)

Key files:
- src/epub2audio/pipeline/converter.py (main changes)
- src/epub2audio/pipeline/resume.py (invalidation helpers)
- tasks/active/DEFECT-003-segment-resume-not-persisted.md (root cause analysis)

Run tests after changes: uv run pytest tests/ -v
Verify types: uv run mypy src/epub2audio

---
Create and maintain progress at: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/progress/605210f6-db6c-421e-892e-77e9ba87bec2/progress.md

---
**Output:**
Write your findings to exactly this path: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/outputs/605210f6-db6c-421e-892e-77e9ba87bec2/m4-audio-engineer-result.md
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