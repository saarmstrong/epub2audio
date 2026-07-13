# Task for epub-engineer

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
Read your task contract at tasks/active/M1-epub-engineer.md and execute it fully.

Additional context:
- The package skeleton is already in place (all __init__.py stubs exist under src/epub2audio/).
- The Architect is writing src/epub2audio/models.py and src/epub2audio/errors.py in parallel. 
- Start with M1-03 (config.py) which has no dependency on models.py.
- Before starting M1-04 and beyond, read src/epub2audio/models.py to verify it contains the full Pydantic models (not just a stub). If it still contains only a stub, wait briefly and check again — the Architect will complete it.
- docs/architecture.md has the canonical model field specs if you need to reference them.
- tests/fixtures/simple_epub3.epub will be created by the Tester agent running in parallel. Your final acceptance test (M1-11) depends on that fixture. If it does not exist when you reach M1-11, create a minimal EPUB yourself for a quick smoke test, noting that the Tester's full fixture will replace it.
- pyproject.toml configures dependencies (ebooklib, beautifulsoup4, lxml, typer, rich, pydantic-settings).

When done, move tasks/active/M1-epub-engineer.md to tasks/completed/M1-epub-engineer.md.

## Acceptance Contract
Acceptance level: attested
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Return a concise result and residual risks when applicable

Required evidence: manual-notes, residual-risks

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