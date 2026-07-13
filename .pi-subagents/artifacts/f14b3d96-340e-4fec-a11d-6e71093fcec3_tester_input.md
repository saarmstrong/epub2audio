# Task for tester

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
Read your task contract at tasks/active/M1-tester.md and execute it fully.

Additional context:
- The package skeleton is already in place (all __init__.py stubs exist).
- The Architect is writing models.py and errors.py in parallel. The EPUB Engineer is writing epub/ modules in parallel.
- Start immediately with M1-12 (tests/fixtures/builders.py) — this only depends on ebooklib, not on models.py.
- After completing builders.py, run M1-13 and M1-14 to generate the .epub fixtures.
- For M1-15, M1-16, M1-17 (test files): write the full test code. Reference `from epub2audio.models import ...` and `from epub2audio.epub.xxx import ...` as the contracts specify — these are the correct final imports even though the implementations are being written in parallel.
- Before running `uv run pytest tests/epub/ -v`, check that src/epub2audio/models.py and src/epub2audio/epub/chapters.py contain full implementations (not stubs). If they are still stubs, record the test files as complete and note that pytest execution awaits the Architect and EPUB Engineer completing their work. Do NOT suppress tests or mark them as skipped to get a green build.
- pyproject.toml configures ebooklib as a dependency.

When done (test files written and fixtures generated, pytest attempted if implementations are ready), move tasks/active/M1-tester.md to tasks/completed/M1-tester.md.

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