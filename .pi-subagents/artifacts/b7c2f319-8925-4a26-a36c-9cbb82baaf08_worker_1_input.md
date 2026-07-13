# Task for worker

[Read from: /Users/andyarmstrong/Projects/epub2mp3/context.md, /Users/andyarmstrong/Projects/epub2mp3/plan.md]

Create user documentation for epub2audio. Read tasks/active/M6-docs-engineer.md.

**Create README.md** with:
- Project description and features
- Prerequisites (Python 3.11+, FFmpeg, espeak-ng)
- Installation instructions (uv sync, pip install)
- Quick start (convert, inspect, voices, doctor commands)
- Configuration (config.toml example)
- CLI reference summary

**Create CHANGELOG.md** with v0.1.0 release notes

**Create LICENSE** file (MIT license)

**Update pyproject.toml** metadata:
- description, authors, license, repository, keywords, classifiers

Verify: The README should enable a new user to install and run `epub2audio doctor`

---
Update progress at: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/progress/b7c2f319-8925-4a26-a36c-9cbb82baaf08/progress.md

---
**Output:**
Write your findings to exactly this path: /Users/andyarmstrong/Projects/epub2mp3/.pi-subagents/artifacts/outputs/b7c2f319-8925-4a26-a36c-9cbb82baaf08/m6-docs-result.md
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