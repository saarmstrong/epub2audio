# Task for tester

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
Read your task contract at tasks/active/M2-tester.md and execute it fully.

Additional context:
- The TTS Engineer and Audio Engineer are running in parallel writing all the implementation modules.
- Write all test files immediately — import them correctly against the final module paths even if those modules are currently stubs.
- For test_e2e.py: guard the full test run with `shutil.which("ffmpeg")` — skip if FFmpeg not found. Mark @pytest.mark.integration. The test imports FakeTTSEngine and convert_epub — write these imports now even if the modules are stubs.
- For unit tests (test_normalize.py, test_segment.py, test_encode.py, test_manifest.py): write the full test logic. For tests that require real implementations (e.g. segment_text), if the module is still a stub when you run pytest, note it in your report but do NOT skip or suppress the test — leave it as a real failing test that documents what must pass.
- Run `uv run pytest tests/ -v` at the end. The 35 existing M1 tests must still pass. New tests may fail if implementations are stubs — that is acceptable and expected; document which tests are pending implementation.
- mypy and ruff must pass on all test files regardless of whether implementations are complete.

When done, move tasks/active/M2-tester.md to tasks/completed/M2-tester.md.

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