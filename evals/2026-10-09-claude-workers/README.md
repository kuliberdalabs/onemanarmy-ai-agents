# Claude Haiku, Sonnet, Opus and Fable as workers, with Codex, Kimi and Grok as controls

> **As of:** measured 2026-10-09, one day
> **Tools:** Claude Code 2.1.296 for all Claude runs (workers ran as subagents of one workflow in a Claude Code session, effort `high` for workers and planners). Codex CLI 0.160.0 (`codex exec`, sandbox `workspace-write`, effort `high`). Kimi CLI 2.1.1. Grok CLI 1.0.50. These versions were read with `--version` on 2026-10-10, the day after the runs; nobody logged them at run time, so an auto-update in between is possible.
> **Models:** `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-1`, `gpt-6.1-sol`, `kimi-code/k3`, `grok-4.7`
> **Domain:** 8 task classes of routine agent work, all synthetic; one language pair (Polish input, Polish and English output); one day
> **n:** 119 ledger rows. 102 graded worker runs: Haiku 38, Sonnet 16, Opus 16, Fable 7, Haiku planned by Fable 14, Codex 8, Kimi 3. Plus 14 Fable planner calls (not graded on their own) and 3 Grok attempts that never ran the model. Per task class: Haiku 5 runs on 7 classes and 3 on the eighth, Sonnet and Opus 2 each, Fable, Codex and Kimi 1 each.
> **Confidence:** medium for Haiku on routine gated work (5 runs per class, no failure that mattered). Low for every other model (n=2 or n=1). Low for anything outside these 8 classes. Not high: one domain, one day.
> **Unknowns:** run-to-run variance for the n=1 and n=2 models; hard tasks (every model hit the ceiling of the automated gates); the permission mode of the Claude workers; long multi-hour or browser work; other languages; token usage for 12 of 38 Haiku runs and for all Kimi runs; Grok's quality (blocked).

Raw rows: [`ledger.csv`](ledger.csv) and [`judge_scores.csv`](judge_scores.csv). Column meanings: [`../SCHEMA.md`](../SCHEMA.md). Every number below is recomputed from those two files by [`recompute.py`](recompute.py), which prints the tables in this note.

## What was tested

Eight task classes, each frozen before its first run, each with a hidden grader and two controls: the grader had to pass a known-good reference answer and fail a known-bad one before it was allowed to judge a worker. Workers got a written brief and a fresh copy of the task directory, and wrote only into it. The gate was a score of at least 0.95 from the automated grader, on the first attempt.

| Class | What the worker does | Grader | Runs per model |
|---|---|---|---|
| `classify` | Label a synthetic email corpus for a small accounting office (155 messages) against a written label policy | Errors on critical fields, plus duplicate detection | Haiku 5, Sonnet 2, Opus 2, Fable 1, Fable-planned Haiku 2, Codex 1, Kimi 1 |
| `fix` | Fix an invoice package with 3 seeded bugs when the ticket describes only 2 | 24 hidden tests | same as `classify` |
| `diagnose` | Find the root cause of duplicate outgoing mails when there are red herrings (SMTP retries, clock) | Cause class, file, line and evidence lines | Haiku 5, Sonnet 2, Opus 2, Fable 1, Fable-planned Haiku 2, Codex 1 |
| `diagnose-open` | The same bug without a list of candidate causes. Added after the first diagnose task saturated | Keywords, file and line, failures read by hand | Haiku 3, Sonnet 2, Opus 2, Codex 1 |
| `sweep` | Find 38 leaked identifiers in 45 files, with decoys | F1 on (file, line) | Haiku 5, Sonnet 2, Opus 2, Fable 1, Fable-planned Haiku 2, Codex 1 |
| `generalize` | Rewrite a skill from our own setup into a public one under a leak policy | Mechanisms kept, leaks, format; then blind judges | same as `sweep` |
| `write-pl` | Write a Polish LinkedIn post from a draft under style rules | Banlist, facts, numbers, length; then blind judges | same as `classify` |
| `build` | Build a contact-merging CLI from a specification | 21 hidden tests | same as `sweep` |

The ledger task column carries `<class>/<slug>`. Rows from the Fable-planned Haiku arm end in `+fable-plan`; the planner call is its own row, `<class>/fable-plan-for-haiku`, with the model `claude-fable-5-1`.

## Gate results

First attempt, threshold 0.95. "Accepted" is the controller's `result`. "Grader pass" is the automated score alone.

| Model | Graded runs | Accepted | Grader pass | Notes |
|---|---:|---:|---:|---|
| `claude-haiku-5-5` | 38 | 38 | 37 | One `diagnose-open` run scored 0.4. The answer named the right cause, file and line; the grader's red-herring keyword (the clock) appeared in the explanation. Read by hand and accepted, so it is counted as a grader false negative |
| `claude-sonnet-5-5` | 16 | 15 | 15 | One `generalize` run kept a leak string (`_reference`), score 0.925. Rejected |
| `claude-opus-5-5` | 16 | 16 | 16 | |
| `claude-fable-5-1` | 7 | 7 | 7 | |
| Haiku planned by Fable | 14 | 14 | 14 | Worker rows only. Plan rows are not graded |
| `gpt-6.1-sol`, effort high | 8 | 8 | 8 | 7 classes once, `diagnose-open` once |
| `kimi-code/k3`, effort high | 3 | 3 | 3 | `fix`, `classify`, `write-pl` only |
| `grok-4.7` | 0 | 0 | 0 | Blocked. All 3 attempts returned HTTP 402 "Grok Build usage balance exhausted" within 4 seconds. That is an account problem, not a model result. The rows are in the ledger as `rejected` with score `unknown` |

The ledger's `accepted_unchanged` column is the "accepted at first attempt, as delivered" flag. `score` and `run_id` are two trailing columns added for this note (see the schema).

The external-CLI rows come from the controller's ledger, not from the first grading pass: that pass ran while the Codex `build` run and the Kimi `classify` run were still writing and marked them missing. The final scores are in the ledger.

## Blind judges: Polish post and English skill

The automated gates cannot tell a good post from a passable one: every `write-pl` run above scored 1.0 on the mechanical gate. So the 13 outputs of `write-pl` and the 13 of `generalize` (Claude models and Codex, 26 texts) were anonymised in a hash-shuffled order and scored 1 to 10 by two judges separately, `fable` and `opus`, who did not know the author. The table shows the mean of both judges over all runs of that model.

| Model | Polish post | English skill | Runs |
|---|---:|---:|---:|
| Opus 5.5 | 8.25 | 7.75 | 2 |
| Sonnet 5.5 | 7.25 | 7.75 | 2 |
| Fable 5.1 | 7.00 | 7.50 | 1 |
| Codex gpt-6.1-sol | 5.00 | 5.00 | 1 |
| Haiku 5.5 | 4.40 (runs 3.5 to 5.5) | 6.70 (runs 5.5 to 7.5) | 5 |
| Haiku planned by Fable | 3.50 | 6.75 | 2 |
| Kimi k3, separate judge session | 5.00 (judges gave 4 and 6) | not judged | 1 |

The judges agreed closely on the 26 texts: 10 identical, 15 one point apart, 1 two points apart. Typical defects the judges named in the Haiku posts: monotone staccato sentences, phrases lifted from the draft, mirrored "not X, but Y" sentences that dodge the banlist, the same fact stated twice. The Kimi post invented a claim ("no accountant lost her job") and still passed the mechanical gate at 1.0.

Kimi's post was judged in a second session, with two earlier texts mixed in as calibration. Haiku run 1 scored 4.5 in both sessions. Opus run 2 scored 8.5 in the first and 7.5 in the second, so the second session read one point lower on the high end. Read Kimi's 5.0 against the calibration texts, not against the first table.

## Cost proxy

API list prices applied to the token counts in the Claude Code transcripts. This is a proxy for relative cost, not a bill: the work ran inside subscriptions. Prices used, USD per million tokens, input and output: Haiku 0.10 and 0.50, Sonnet 2 and 10, Opus 4 and 20, Fable 10 and 50. Cache writes were priced at 1.25 times input, cache reads at 0.1 times. These are the figures the controller's script used; check them against the current price list before reusing the dollar numbers.

**Output tokens are undercounted.** The transcripts store the usage of the last stream chunk, so the output counts in the ledger are a lower bound (a 155-message labelling run shows 794). The proxy is therefore low, and it is lowest for the models with the highest output price.

For Claude rows, `input_tokens` is fresh input plus cache writes plus cache reads, and `cached_input_tokens` is the cache-read part. Fresh input is a few dozen tokens per run, so "uncached" here is almost all cache writes.

| Model | Rows with token data | Median wall time | Mean proxy per task | Class-averaged, relative to Haiku |
|---|---:|---:|---:|---:|
| Haiku 5.5 | 26 of 38 | 66 s | 0.0125 USD | 1.0x |
| Sonnet 5.5 | 16 of 16 | 37.5 s | 0.205 USD | 16.4x |
| Opus 5.5 | 16 of 16 | 52.5 s | 0.460 USD | 36.2x |
| Fable 5.1 | 7 of 7 | 162 s | 1.234 USD | 97.6x |
| Fable planner call, then Haiku worker | 14 of 14 each | 51.5 s plan, 91.5 s worker | 1.005 USD plan, 0.014 USD worker | 80.6x for plan plus worker |

The last column averages per task class first, over the 7 classes every model ran, so that Haiku's uneven number of runs per class does not move it. Haiku's 12 rows without token data are all from runs 4 and 5, which have no usable usage data in the controller's usage file; wall time is also unknown for them. Wall times include contention: runs went in parallel batches on one machine.

Codex and Kimi cannot be put in this table, and their token counts must not be compared with the Claude ones (different CLIs count cache and overhead differently, see the schema). For the record: the 8 Codex runs took 78 to 177 s (median 110 s) and used 1,558,831 input tokens, of which 331,439 uncached (32,000 to 64,000 per run), and 22,346 output tokens. The 3 Kimi runs took 196, 284 and 370 s; the CLI did not report usage.

The whole Claude side moved one weekly subscription meter by roughly 4 points (11% to 15%). That is a coarse reading: other work ran in parallel. The Codex meter could not be read per run because the runs were ephemeral.

## Which worker for which task class

Per class, not a ranking. Every row holds for the classes and the day measured.

| Task class | Worker | Controller check that stays |
|---|---|---|
| Sweeps, inventories, extraction, labelling against a written policy, scoped fixes with tests, diagnosis from evidence, builds from a specification with tests | Haiku 5.5. 28 of 28 accepted on these classes (27 by the grader alone) at about a sixteenth of Sonnet's cost proxy | The gate decides. Read every grader failure by hand before rejecting: 1 of 38 was a false negative |
| Text that a person reads, Polish above all (posts, copy) | Sonnet 5.5; Opus 5.5 when it goes out publicly. Haiku scored 4.40 against 7.25 and 8.25 | A human or judge read. A mechanical text gate passes weak text, so it is necessary and not sufficient |
| Rewriting an internal skill for public release | Opus 5.5 or Sonnet 5.5 (7.75 each). Haiku (6.70, range 5.5 to 7.5) only with a read | Run the leak scan on every output. Sonnet's one miss was a leak string the mechanical scan caught |
| Planning for a cheaper worker | Do not use Fable for it on routine work. The planned Haiku runs matched unplanned Haiku on the gates, wrote worse Polish (3.50), and cost about 80x as much | None needed; skip the step |
| Independent review, hard code | Not decided by this eval. Codex `gpt-6.1-sol` passed all 8 and scored 5.0 on writing, n=1. See the [2026-09-27 note](../2026-09-27-codex-workers/README.md) for where it earned its place | Run on the real system |
| Kimi k3, Grok 4.7 | No routing from this data. Kimi passed 3 of 3 gates, n=1, with an invented claim in its post. Grok never ran | Treat as untested |
| Acceptance, verdicts, anything sent outside | Neither: stays with the controller or a human | n/a |

Design, synthesis and review of causes were not in the 8 classes. Whatever routing exists for them is unchanged by this note.

## Limitations

- **Ceiling effect on routine tasks.** Every model reached the top of the automated gates. The test says Haiku is enough where the gate decides. It does not say where Haiku breaks: long builds, hours-long work, browser work and hard problems were not in it. The next test should be one hard class from a real backlog.
- **n=2 for Sonnet and Opus, n=1 for Fable, Codex and Kimi.** The judge-score differences between Sonnet, Opus and Fable are within what two runs can show by chance. The Haiku gap to the others (4.40 against 7.25) is wide and rests on 5 runs and two judges: every Haiku post scored below every Sonnet post.
- **The judges are Claude models, and they are also evaluated models.** The two judges were run as Fable and Opus, and both appear above as workers, so self-preference is possible. Two judges agreeing limits this bias and does not remove it. The judge scale also moved by one point between sessions (see above).
- **Isolation was not perfect.** The path of the controller directory, which held graders and hidden tests, was visible in the working-directory line of the agents' context. No tool call touched it; this was checked in the transcripts. Later batches started from a neutral directory.
- **Scope discipline is a harness problem, not a prompt problem.** In one extra read-only run, outside the ledger (n=1), Haiku was told not to modify files and edited one anyway, because it took a question visible in its context for an assignment. Sonnet in the same run only read. Limit what Haiku can do with permissions, not with the brief.
- **Token counts.** Output counts are a lower bound. Claude tokens are not comparable with Codex or Kimi tokens.
- **Contention and versions.** Parallel batches inflate wall time. CLI versions were read the day after.
