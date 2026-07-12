# Prompt: Start Milestone

Use this prompt when beginning a new milestone.

---

```
You are working on the epub2audio project. Your role is: {{ROLE}}

Before doing anything:
1. Read AGENTS.md
2. Read docs/status.md
3. Read docs/architecture.md
4. Read .pi/agents/{{ROLE_FILE}}
5. Read tasks/backlog.md and identify all tasks for Milestone {{N}}

The current milestone is: Milestone {{N}} — {{MILESTONE_NAME}}

Success condition:
{{SUCCESS_CONDITION}}

Start with the first unstarted task for this milestone. Move it to tasks/active/
before beginning. Work through tasks sequentially. After completing each task:
- Run the relevant tests
- Update docs/status.md
- Move the task to tasks/completed/

Do not begin the next milestone until the Reviewer has signed off on this one.
```

---

## Variables to fill in

| Variable | Example |
|---|---|
| `{{ROLE}}` | `EPUB Engineer` |
| `{{ROLE_FILE}}` | `epub-engineer.md` |
| `{{N}}` | `1` |
| `{{MILESTONE_NAME}}` | `Inspectable EPUB Plan` |
| `{{SUCCESS_CONDITION}}` | `uv run epub2audio inspect tests/fixtures/simple_epub3.epub shows ordered chapters` |
