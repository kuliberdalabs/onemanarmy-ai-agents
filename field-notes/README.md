# field-notes

Short dated notes from running the workshop: something we tried, the numbers it produced, and what we changed because of it. No notes yet; this page sets the format.

A field note is smaller than an eval. An eval in [`evals/`](../evals/SCHEMA.md) is a planned measurement with a fixed ledger. A field note reports what happened in ordinary work, and it may point to an eval when there is one. If a note ends up deciding which model does which job, the measurement behind it belongs in `evals/`.

## File name

`YYYY-MM-DD-short-slug.md`, dated by when the thing happened, for example `2026-11-03-hook-missed-shell-writes.md`. One note per finding.

## Format

```markdown
# One line that states the finding

> **As of:** YYYY-MM-DD
> **Tools:** harness, CLI and model ids with exact versions
> **n:** how many runs, tasks or days this rests on

## What we tried

What we set out to do, in which setup, and what we expected.

## Numbers

What we measured, with the source of each number: a ledger, a log line,
a test count. A number with no source gets cut or marked as an estimate.

## What changed in the workshop

The concrete change and its path: a rule line edited, a gate added with
its negative control, a model moved to or from a task class, a tier
tightened. If nothing changed, say so and why.

## Unknowns

What this does not show: one domain, one run, no variance, an untested
version.
```

## Rules

- The "what changed" section is required. A note that changed nothing still says so, so a reader can tell a finding we acted on from one we only observed.
- Every number has a source and an `n`. A single run is labelled as one.
- Dates and versions on everything. A note about a model or CLI is true for the version it names and nothing later.
- No real client data, names or credentials. Examples use fictional companies and `.invalid` domains, such as `office@example-bookkeeping.invalid`.
- No rankings. Write which model or tool works for which task class, under which check.
