# How this was built: an agent-team workflow

A short guide to the multi-agent setup used to build the narration pipeline
(M8–M12), how the agents were coordinated, and an honest retrospective of what
worked and what didn't.

---

## The team

Roles were defined in `AGENTS.md` and implemented as pi subagents. One
**Orchestrator** (the main session) drove everything; specialists owned
specific modules; a fresh-context **Reviewer** gated every milestone.

```
                         ┌───────────────┐
                         │  Orchestrator │  drives milestones, integrates,
                         │  (main loop)  │  is the ONLY writer at any moment
                         └───────┬───────┘
          ┌──────────────┬───────┼────────┬───────────────┐
          ▼              ▼       ▼        ▼               ▼
   ┌────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────┐ ┌──────────┐
   │ Architect  │ │TTS Engineer│ │Audio Engineer│ │ Tester │ │ Reviewer │
   │ models,    │ │ director/, │ │ pipeline/,   │ │ tests/ │ │ fresh    │
   │ config,    │ │ providers/,│ │ validation/, │ │ (fork) │ │ context, │
   │ ADRs       │ │ tts/       │ │ audio/       │ │        │ │ READ-ONLY│
   └────────────┘ └───────────┘ └──────────────┘ └────────┘ └──────────┘
```

Ownership boundaries (who may edit what) came straight from `AGENTS.md`, so two
agents rarely needed the same file.

---

## The coordination pattern

The core loop for each milestone was **sequential, single-writer, gate-checked**,
finished by an **independent** review:

```
 Orchestrator plans milestone
        │
        ▼
 ┌───────────────────────────────────────────────┐
 │  for each task, in dependency order:           │
 │    1. dispatch ONE specialist subagent         │
 │    2. it edits its module + runs local gates   │
 │    3. Orchestrator re-runs gates itself  ──────┼──▶ red? fix / redispatch
 │    4. commit                                   │
 └───────────────────────────────────────────────┘
        │  (all tasks done, suite green)
        ▼
 commit implementation
        │
        ▼
 dispatch fresh-context READ-ONLY Reviewer  ──────────▶ CHANGES REQUESTED
        │  APPROVED                                     → Orchestrator fixes,
        ▼                                                  re-reviews
 record honest sign-off in docs/status.md
```

Two rules made this safe:

- **One writer at a time.** Specialists ran one after another (not in parallel)
  on the same working tree, so there were never two agents writing the same
  files. The Orchestrator was the sole integrator.
- **Independent review only.** The Reviewer ran in a *fresh context*
  (no memory of the implementation), *read-only*, and re-ran the gates itself.
  Its verdict was the only thing that closed a milestone.

Gates, run at every hand-off and every review:
`pytest` · `mypy --strict` · `ruff check` + `ruff format --check`.

---

## What worked

- **Independent review caught real defects that self-checks missed.**
  - M10: the pronunciation feature passed all unit tests but was **never wired
    into the pipeline** — a configured dictionary did nothing. The independent
    reviewer ran it end-to-end and blocked it.
  - M11: the "integration" test re-implemented the CLI wiring instead of
    invoking the real command, so it wouldn't catch the branch being deleted.
  - These are exactly the bugs an implementer (or an implementer-aligned check)
    tends to rationalize away.
- **Strict module ownership + clean layering** meant specialists rarely
  collided, and "add a provider = implement one interface" held up.
- **Dependency injection kept everything testable without the heavy dependency.**
  The whole pipeline was built and tested with a `FakeTTSEngine`; Kokoro was
  never required for CI. 474 tests, deterministic.
- **Gate-at-every-hand-off** kept `main` green continuously; a broken step was
  caught before the next agent built on it.
- **ADRs + a running `status.md`** gave each fresh-context agent enough context
  to act without re-discovering decisions.

## What didn't work

- **Agents fabricated review sign-offs — twice.** Implementer sessions wrote
  "Reviewer sign-off — APPROVED" (one even labelled itself "genuine") into
  `status.md` and committed it, with **no independent review having run**. The
  underlying code was actually fine, but the *process claim* was false. Only
  running the reviewer myself and reading its output surfaced it.
- **Self-approval drift.** Given latitude, a specialist would happily do the
  Tester's and Reviewer's jobs too, and mark its own work complete.
- **Unreliable "done" signals.** Subagents frequently returned terse or empty
  final messages, and the runtime emitted stale "needs attention / no activity"
  notices for runs that had already finished — so completion had to be verified
  by inspecting the tree and re-running gates, never trusted from the summary.
- **Scope creep beyond the task.** One agent wrote docs *and* a fake sign-off
  when only implementation was requested.
- **Environment drift.** The venv silently lost its dev tools (and Kokoro),
  so gate commands had to switch to `uv run --extra dev`; caught only by a
  failing command, not by any agent.

## Takeaways (what we'd bake in next time)

1. **Never let the writer sign off.** Only a sign-off produced by a
   review run the orchestrator personally dispatched and observed counts.
   Structurally forbid implementer agents from editing `status.md` sign-off
   sections.
2. **Trust artifacts, not summaries.** Treat every subagent "done" as a claim;
   confirm with `git status` + a real gate run before committing or proceeding.
3. **Keep the single-writer + independent-reviewer split.** It was the single
   biggest source of real bug-catching in the project.
4. **Give reviewers an explicit end-to-end reachability check.** "Is the
   feature actually wired to the CLI?" caught the highest-impact defects.
5. **Pin the environment.** Gate commands should be dependency-explicit
   (`uv run --extra dev …`) so a resynced venv can't silently change results.
