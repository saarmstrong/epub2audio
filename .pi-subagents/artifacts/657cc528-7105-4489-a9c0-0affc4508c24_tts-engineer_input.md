# Task for tts-engineer

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
Read your task contract at tasks/active/M2-tts-engineer.md and execute it fully.

Additional context:
- All source stubs are already in place under src/epub2audio/text/ and src/epub2audio/tts/.
- Start with DEFECT-002 (fix word_count in epub/chapters.py) since you're already extending epub/cleanup.py — fix word_count in score_candidates so the true count is passed through to Chapter.word_count.
- docs/architecture.md has the canonical TTSEngine Protocol definition.
- The Audio Engineer is running in parallel writing audio/ and pipeline/ modules. They will import TTSEngine from tts/base.py — make sure your Protocol is correct and importable.
- FakeTTSEngine (M2-06) must produce numpy zeros arrays — numpy is already a project dependency.
- pyproject.toml already configures mypy strict and ruff rules.

When done, move tasks/active/M2-tts-engineer.md to tasks/completed/M2-tts-engineer.md.

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