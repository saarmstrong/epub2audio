# Task for audio-engineer

You are reviving a previous subagent conversation.

Original run: b7c2f319-8925-4a26-a36c-9cbb82baaf08
Original agent: audio-engineer
Original session file: /Users/andyarmstrong/.pi/agent/sessions/--Users-andyarmstrong-Projects-epub2mp3--/2026-07-12T20-53-31-077Z_019f581b-4945-7463-9bbf-7f7fae9ff6a5/eb317a02/run-0/session.jsonl

Use the stored session context as background. Answer the orchestrator's follow-up below. Do not assume the original child process is still alive.

Follow-up:
The root cause is that **FakeTTSEngine produces pure silence (zeros)**, which FFmpeg can't process (exit 234 on both loudnorm and libmp3lame).

**Fix FakeTTSEngine** in `src/epub2audio/tts/fake.py`:

Change from pure zeros to low-amplitude noise:
```python
# Instead of:
data = np.zeros(n_samples, dtype=np.float32)

# Use:
data = np.random.uniform(-0.001, 0.001, size=n_samples).astype(np.float32)
```

This produces valid (nearly silent) audio that FFmpeg can process. Keep the normalize_loudness silence detection as a fallback, but this fixes the root cause.

After this fix:
1. Run `uv run pytest tests/pipeline/test_converter_resume.py -v` - should pass
2. Run `uv run pytest tests/ -v` - verify all pass
3. Output your result

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