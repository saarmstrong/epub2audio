# epub2audio — Agent Team

This document defines the agent roles, responsibilities, and collaboration rules for
building epub2audio. Read this before taking any task.

---

## Roles

### Orchestrator
Coordinates milestones, assigns tasks, resolves cross-agent conflicts, keeps the project
runnable at every milestone boundary. Does not write feature code.
→ `.pi/agents/orchestrator.md`

### Architect
Owns `models.py`, `errors.py`, interfaces/Protocols, and cross-cutting design decisions.
All other agents consult the Architect before adding a new public type or changing a
module boundary.
→ `.pi/agents/architect.md`

### EPUB Engineer
Owns everything under `src/epub2audio/epub/` and EPUB test fixtures.
→ `.pi/agents/epub-engineer.md`

### TTS Engineer
Owns `src/epub2audio/text/` and `src/epub2audio/tts/`.
→ `.pi/agents/tts-engineer.md`

### Audio Engineer
Owns `src/epub2audio/audio/` and `src/epub2audio/pipeline/`.
→ `.pi/agents/audio-engineer.md`

### Tester
Owns `tests/`, `tests/fixtures/builders.py`, and CI configuration.
Writes tests alongside every feature agent; does not implement features.
→ `.pi/agents/tester.md`

### Reviewer
Reviews diffs, runs tests, challenges assumptions, reports concrete defects.
Must not implement primary features unless explicitly asked.
→ `.pi/agents/reviewer.md`

---

## Collaboration Rules

1. Read `docs/status.md` before starting any session.
2. Read the relevant agent role file before taking a task.
3. Take tasks only from `tasks/active/`. Move completed tasks to `tasks/completed/`.
4. Never mark a milestone complete without Reviewer sign-off.
5. Keep `src/` importable at all times — no half-wired modules.
6. Add or update tests with every behaviour change.
7. Never suppress a failing test to get a green build.
8. All public functions and classes must have docstrings and type annotations.
9. Document ambiguities in `docs/decisions/` rather than silently resolving them.
10. Update `docs/status.md` at the end of every session.
