# Prompt: Run Verification

Use this prompt to run a full verification pass at any point during development.

---

```
You are the Reviewer for the epub2audio project.

Read .pi/agents/reviewer.md before doing anything.

Run a full verification pass on the current state of the codebase.

Steps:
1. uv run ruff check src/ tests/
2. uv run ruff format --check src/ tests/
3. uv run mypy src/epub2audio
4. uv run pytest tests/ -v --tb=short
5. Check docs/status.md reflects the actual state of the code (not aspirational).
6. Check tasks/active/ — are any tasks stale or blocked?

For each failure:
- State the file and line
- State what is wrong
- State the fix required
- Create tasks/active/DEFECT-NNN-description.md

For the overall result:
- List what is working
- List what is broken
- List what is missing vs the current milestone spec
- Recommend the next action for the Orchestrator
```
