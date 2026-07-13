# Task for tester

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
Read your task contract at tasks/active/M3-tester.md and execute it fully.

Additional context:
- The TTS Engineer is implementing kokoro.py, voices.py, and the CLI commands in parallel. Write test files now — import paths will be correct even if implementations are stubs.
- For test_kokoro_smoke.py: the @pytest.mark.slow and @pytest.mark.requires_model markers are already registered in pyproject.toml. These tests must NOT run in the default `pytest tests/` invocation — they only run with explicit `-m "slow and requires_model"`.
- For test_kokoro_import_without_package_raises_missing_dependency: use `unittest.mock.patch.dict(sys.modules, {"kokoro": None})` combined with `importlib.reload` on the kokoro module to simulate a missing package, then assert MissingDependencyError is raised on instantiation.
- For test_voices_command.py: prefer `from typer.testing import CliRunner` and `from epub2audio.cli import app` over subprocess — cleaner and faster.
- Run `uv run pytest tests/ -v` at the end; all 112 existing tests must still pass. New voices/doctor CLI tests should pass if TTS Engineer has finished; if not, note which are pending.
- mypy and ruff must pass on all new test files.

When done, move tasks/active/M3-tester.md to tasks/completed/M3-tester.md.

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