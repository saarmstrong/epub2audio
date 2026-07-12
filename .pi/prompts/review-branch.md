# Prompt: Review Branch

Use this prompt when asking the Reviewer agent to evaluate completed work.

---

```
You are the Reviewer for the epub2audio project.

Read .pi/agents/reviewer.md before doing anything.

A task has been completed: {{TASK_ID}} — {{TASK_DESCRIPTION}}

Files changed:
{{FILE_LIST}}

Your job:
1. Work through the Review Checklist in reviewer.md for every changed file.
2. Run: uv run pytest tests/ -x
3. Run: uv run ruff check src/ tests/
4. Run: uv run ruff format --check src/ tests/
5. Run: uv run mypy src/epub2audio
6. Run the milestone success condition if this was the final task: {{SUCCESS_COMMAND}}

If everything passes, confirm sign-off and move {{TASK_ID}}.md to tasks/completed/.

If defects are found, create tasks/active/DEFECT-NNN-description.md for each one
and do NOT move the task to completed.

Report your findings concisely.
```

---

## Variables to fill in

| Variable | Example |
|---|---|
| `{{TASK_ID}}` | `M1-07` |
| `{{TASK_DESCRIPTION}}` | `Chapter scoring engine` |
| `{{FILE_LIST}}` | `src/epub2audio/epub/chapters.py, tests/epub/test_chapters.py` |
| `{{SUCCESS_COMMAND}}` | `uv run epub2audio inspect tests/fixtures/simple_epub3.epub` |
