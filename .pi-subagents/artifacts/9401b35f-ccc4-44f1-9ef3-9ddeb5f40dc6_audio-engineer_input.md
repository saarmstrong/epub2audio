# Task for audio-engineer

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
Read your task contract at tasks/active/M2-audio-engineer.md and execute it fully.

Additional context:
- All source stubs are already in place under src/epub2audio/audio/, src/epub2audio/pipeline/, and src/epub2audio/utils/.
- The TTS Engineer is running in parallel and will produce tts/base.py (TTSEngine Protocol) and tts/fake.py (FakeTTSEngine). Before implementing converter.py (M2-18), check that tts/base.py contains the full TTSEngine Protocol — if it is still a stub, reference the canonical definition from docs/architecture.md and write converter.py against that interface (the Protocol signature will not change).
- Start with utils/subprocess.py and utils/files.py — these have no dependencies and unblock everything else.
- All FFmpeg calls must use argument arrays via utils/subprocess.py. Never shell=True or string interpolation.
- pyproject.toml already has soundfile and numpy as dependencies.
- FFmpeg and FFprobe are assumed to be available on the system (standard macOS install).
- For converter.py: import TTSEngine from tts.base, not from kokoro or fake — the engine is injected at call time.
- For cli.py convert command: use `try: from epub2audio.tts.kokoro import KokoroTTSEngine; engine = KokoroTTSEngine() except Exception: from epub2audio.tts.fake import FakeTTSEngine; engine = FakeTTSEngine()` for engine selection.
- The existing inspect command must not regress.

When done, move tasks/active/M2-audio-engineer.md to tasks/completed/M2-audio-engineer.md.

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