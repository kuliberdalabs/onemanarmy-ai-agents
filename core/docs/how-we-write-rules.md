# How we write rules for agents

*Updated: 2026-10-09 | scope: rule files, memory routers, skills, eval ledgers | applies to every model we run*

We run one set of rules across Claude Code, Codex and cheaper worker models. This page is the house style for writing those rules, so you can copy the method without our content. Each convention names the failure it prevents.

## Conventions

1. **One kernel, thin per-tool layers.** Rules every model needs live in a single `AGENTS.md`. A tool file (`CLAUDE.md`) imports it (`@AGENTS.md`) and adds only what differs for that tool. *Prevents:* two copies drifting until two models follow different approval rules.

2. **A dated header on every file.** First line: `*Updated: 2026-10-06 | scope | which models*`. *Prevents:* an agent trusting a file nobody has touched since the tools changed under it.

3. **One dated line per rule, with the incident behind it.** Short imperative, then the reason. A rule nobody can tie to an incident gets marked as a preference or dropped. *Prevents:* rules nobody dares delete because nobody remembers why they exist.

4. **A changed rule edits its old line.** New date, new text, same place. No "update:" lines appended below; git keeps the history. *Prevents:* two contradicting lines in one file, with the model following whichever it weighed last.

5. **Line caps, and a written list of what not to add.** Each file has a cap that a startup check flags (our file of user corrections: 60 lines). The kernel says what agents must not add without a concrete failure mode: abstractions, dependencies, tests, audits, approval gates. *Prevents:* rule files that grow until agents skim them, and agents adding process to look careful.

6. **A router, never a preload.** The memory file holds almost no facts. It gives the order of places to look (nearest project file first), a topic-to-file map, and a "where new knowledge goes" list. Knowledge files are opened by searching the task's nouns. *Prevents:* every session paying context for every domain, and copied facts going stale next to their real owner.

7. **Promote a lesson only when it recurs.** A one-off failure is written into the project that owns it. It moves to a domain knowledge file when it happens again in that domain, and into the kernel only if it applies to almost every task. *Prevents:* global rules born from one bad afternoon.

8. **Trigger cards load playbooks on demand.** A card is about 13 lines: one bold trigger, three or four inline non-negotiables, the path to the full playbook. *Prevents:* a 300-line checklist in every context window, while the few rules that must never slip stay loaded all the time.

9. **Receipts live inside skills.** Under the step it justifies, an italic `*Receipt YYYY-MM-DD: ...*` with the number. *Prevents:* the next editor "simplifying" a step whose reason they cannot see.

10. **Claims about models and workers go into a ledger with numbers.** As-of date, CLI version, model id, effort, wall time, tokens, result, controller corrections, n and unknowns (see [`evals/SCHEMA.md`](../../evals/SCHEMA.md)). *Prevents:* "model X is better at Y" surviving for months on one impression. Lesson 2026-09-27: on an editing task, a worker given no target length and no mandatory categories flattened the scope and returned a fraction of the content; the rerun with the target length and the required sections stated up front returned usable output. Give both before the worker starts (one task, no ledger row).

11. **Results come back as a decision card.** About twelve lines in three blocks: *Decision needed* (options and one recommendation, or "none"), *What shipped* (artifact path or URL), *Parked and one lesson*. How the work was done stays in the project's own file. *Prevents:* the person who decides reading a work log to find the one question meant for them.

## Example lines (invented, in our format)

A rule with its incident, and the same rule after a change. The second line replaces the first in place:

```
- 2026-03-02 · Test a migration against the fixture database before calling it done. Why: a column rename broke two reports.
- 2026-05-19 · Test a migration against a restored copy of last night's backup before calling it done. Why: the fixture DB passed; the real one held 41,000 rows with a NULL email and the NOT NULL step failed on deploy.
```

A receipt inside a skill, under the step it protects:

```
3. Keep reminder emails as drafts until a human sends them.
   *Receipt 2026-04-17: a retry re-sent 23 reminders, 9 of them to clients who had already paid.*
```

A trigger card:

```markdown
# Database migrations: trigger card
**When the task writes, changes or runs a migration, read `playbooks/migrations.md` and run its checklist before committing.**
Always, inline:
- Every migration has a down step, or a written reason it cannot have one.
- Test on a restored backup copy; the fixture database alone does not count.
- No agent session runs a migration against production.
```

## What this style costs

- **Edit in place hides history.** The file shows only the current rule. The previous wording lives in `git log`, which few people read before arguing about a rule.
- **A date tells you age and nothing more.** A rule dated last month can be wrong since yesterday's CLI release. Ledger rows age fastest; model facts go stale within weeks, so every eval note carries its as-of date and gets re-measured before anyone quotes it.
- **Caps force deletions.** Somebody has to decide which rule goes when the check flags the cap. That judgment is the real maintenance cost, and it does not automate.
- **Routers rot silently.** Move or rename a knowledge file and the router points at nothing, with no error. We check pointers when we touch the router, and that is all.
- **Trigger cards depend on recognition.** If the agent does not notice the task touches the area, the playbook never loads. The inline non-negotiables exist for that miss.
- **Receipts leak context.** A receipt is only useful with its number, and the place it happened is often private. Before publishing, drop the place and keep the failure and the number.
