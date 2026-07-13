# Task for reviewer

Run the full Milestone 1 review for epub2audio. This is the milestone sign-off review.

## Context

Three agents just completed their M1 work in parallel:
- **Architect**: wrote `src/epub2audio/models.py` and `src/epub2audio/errors.py`
- **EPUB Engineer**: wrote `src/epub2audio/config.py`, all `epub/` modules, `utils/names.py`, `cli.py`
- **Tester**: wrote `tests/fixtures/builders.py`, generated both `.epub` fixtures, wrote `tests/epub/test_*.py`

All task contracts are in `tasks/completed/`. `tasks/active/` is empty. 35 tests currently pass.

## Your checklist (from your agent role)

Run every item from the "Review Checklist — Every Task" and "Milestone Sign-off Checklist" in your role definition.

## Known issues to investigate — start here

These were flagged by the agents themselves:

### 1. `errors.py` parallel write (medium)
Both the Architect and EPUB Engineer independently wrote `src/epub2audio/errors.py`. Verify the on-disk version is coherent, matches the M1-architect.md contract, has all 8 required exceptions, has correct `__init__` signatures with custom attributes, and no cross-imports from other epub2audio modules.

### 2. `XMLParsedAsHTMLWarning` — 52 warnings per test run (medium)
`epub/cleanup.py` and `epub/chapters.py` call `BeautifulSoup(content, "lxml")` on XHTML bytes. This invokes the HTML parser, which generates `XMLParsedAsHTMLWarning`. The correct call is `BeautifulSoup(content, features="xml")` (the lxml XML parser). Fix this in both files and re-run tests to confirm no regressions.

### 3. `word_count = 0` for chapters with ≥ 200 words (low — M2 deferred)
`Chapter.word_count` is only populated when the `short_document` scoring signal fires. Long chapters report `0`. Confirm this is visible in `inspect` output and note it in your report. No fix required for M1 — just verify it does not silently corrupt data.

### 4. `pyproject.toml` additions (low)
EPUB Engineer added:
- `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` for `ebooklib`
- Ruff ignore rules: `B008` (Typer defaults), `RUF001`, `RUF002`, `RUF003` (en-dash in strings/docstrings)
Verify these are acceptable project-wide suppressions and do not hide real issues.

### 5. `builders.py` concurrent writes (low)
Both EPUB Engineer and Tester touched `tests/fixtures/builders.py`. Verify the final file has the full builder API (8 functions from M1-tester.md contract) and the two bugs the EPUB Engineer fixed are present.

## Milestone sign-off command

```bash
uv run epub2audio inspect tests/fixtures/simple_epub3.epub
```

Must produce a Rich table with at least 2 chapters in correct reading order.

Also run:
```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/epub2audio
```

## Output

- Fix issues 1 and 2 directly if they are defects (you have `edit` access).
- For anything you cannot fix or that is out of scope, create `tasks/active/DEFECT-NNN-short-title.md` per your role definition.
- End with a clear **MILESTONE 1 SIGN-OFF: APPROVED** or **MILESTONE 1 SIGN-OFF: BLOCKED** with your reasoning.
- Update `docs/status.md` to reflect the outcome.

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