# gpt-6-sol and gpt-6-luna as Codex CLI workers

> **As of:** measured 2026-09-27, written up 2026-10-09
> **Tool:** Codex CLI 0.157.1, `codex exec`, sandbox `workspace-write`
> **Models:** `gpt-6-sol`, `gpt-6-luna`, model ids as reported by the CLI
> **Domain:** an email-triage assistant for a small accounting office, synthetic corpus (one domain, one day)
> **n:** 13 runs. 6 pairs: 5 on the same task, plus 1 cross pair where sol generated hard cases and luna labelled them. 1 unpaired follow-up run (sol).
> **Confidence:** medium. Sol was ahead on all 5 same-task pairs, but each cell is a single run.
> **Unknowns:** run-to-run variance (no repeats); other languages and domains; effort sweeps (both models ran each task at the same effort); behaviour on newer CLI versions; wall time includes contention, because some runs went in parallel on one machine.

Raw rows: [`ledger.csv`](ledger.csv). Column meanings: [`../SCHEMA.md`](../SCHEMA.md).

What the ledger backs: time, tokens, the controller's verdict and the number of corrections for each of the 13 runs, and the totals below. It does not back the per-task numbers in the paired comparison, the follow-up run and the addendum (scenario, finding and test counts, critical errors, regressions, characters, cost per 1,000 calls). Those are the controller's observations from each run's output and from the call log of the classifier test. The outputs and the log belong to a private test bed and are not published, so read those numbers as observations, not as recomputable data. Command counts come from the CLI's own report, which the schema leaves out of the CSV.

## What was tested

The system under test classifies inbound mail for a small accounting office: is it a new-client inquiry, which category, what priority, does a human need to review it, should the sender get an auto-confirmation, is it a duplicate. Everything ran on a synthetic Polish corpus with fictional senders on `.invalid` domains.

Workers got a written brief, one output directory, and common rules: no network, no secrets, no commits, write only to the output directory, end with a summary that says what is uncertain. The controller checked every result on the real artifact. The classifier fixes were checked by running the real production model over the corpus; the workers' own test results did not count.

## Verdict

Use sol for anything that needs judgement, independent verification, or code under constraints. Use luna for narrow tasks with an explicit spec where someone else checks the output. On complex tasks luna was not the cheaper option: it used more tokens and more time, and the work was worse.

## Paired comparison

| Task (effort) | gpt-6-sol | gpt-6-luna | Use for this class |
|---|---|---|---|
| `simulation-oracle/reminder-clock` (high): simulate the reminder and escalation timers and act as test oracle | 790 s, 3.9M input. 43 scenarios, 5 findings, one of them a subtle error in seconds | 1669 s, 9.1M input. 29 scenarios, 3 of the 5 findings. Its oracle rounded to the minute exactly as the code under test does, so it could not catch the seconds error. Rejected as an oracle | sol, clearly |
| `generation/corpus-70` (medium): generate 70 labelled emails from a labelling policy | 225 s. Richer text (184 characters on average). Blind labelling found 0 label errors. Still too few long emails | 199 s. Flat text (95 characters on average), skipped the instruction to write long emails with signatures, footers and quoted history. 4 label errors in 70 | sol for a reference corpus |
| `labelling/blind-70` (medium): label the other model's corpus blind, by policy | 136 s. Caught the 4 real generator errors. 2 of its own labels overruled (1 over-eager, 1 disputed) | 120 s. 2 disagreements, both its own errors against an explicit policy rule. Otherwise agreed | sol for reference labels; luna is enough as a second voice |
| `guarded-code/test-controller` (high): write a Python test controller with safety guards, without running it | 380 s, 0 of 30 commands failed. One factual error: flagged a risk that outgoing headers were dropped, when a preload module it never opened already set them | 374 s, 5 of 13 commands failed. Its mock test made 3 local HTTP requests despite the no-network rule (the sandbox blocked them; it reported this itself). One extra false FAIL, on non-ASCII characters | sol. Both observe steps gave false FAILs (see pitfalls). The ledger counts 3 controller corrections for this run; the header claim is one, and the note does not itemize the other two |
| `logic-fix/classifier-rules` (high): fix the classification rules from dev-set failures, checked on the real model | 528 s, 36/36 own tests. Critical errors 35 to 11 on 155 emails, hidden holdout 15 to 7, 0 regressions on 25 protected cases | 652 s, 35/35 own tests. Critical errors 35 to 32, 28 unnecessary reviews, 8 regressions on 25 protected cases from over-broad rules. Rejected | sol, decisively |
| Cross pair (medium): sol `generation/hard-cases-15`, luna `labelling/blind-hard-15` | 164 s. 15 hard cases: 2,500-character emails with the request in the last paragraph, forwards with the signature above the quoted original, long legal footers, text without diacritics | 41 s. 1 category disagreement; both labels were valid under the policy | sol to write hard cases; luna fine to label them |

Unpaired follow-up, `logic-fix/classifier-rules-round2` (sol, medium): 202 s, 39/39 tests, both named defects fixed without widening scope. On the real model: 9 critical errors on 155 (dev part 20 to 3, holdout 15 to 6, both from the starting point), 1 changed result on the protected set, left open for discussion with the fixture locked.

## Totals

Recomputed from `ledger.csv` with the snippet in [`../SCHEMA.md`](../SCHEMA.md).

| | runs | wall time | input tokens | of which uncached | output tokens |
|---|---:|---:|---:|---:|---:|
| gpt-6-luna, all runs | 6 | 3055 s | 14,924,152 | 540,024 | 119,916 |
| gpt-6-sol, all runs | 7 | 2425 s | 9,069,142 | 515,286 | 103,321 |
| gpt-6-luna, 5 same-task pairs | 5 | 3014 s | 14,828,550 | 510,214 | 118,265 |
| gpt-6-sol, 5 same-task pairs | 5 | 2059 s | 7,951,301 | 418,117 | 86,052 |

Sol ran one task more and still used less time and fewer tokens in total. The same-task rows remove that difference. Every call carried a fixed overhead of about 24k input tokens from the instruction file and hooks loaded per call. These are Codex CLI counts; do not compare them with token counts from another CLI.

## Which worker for which task class

| Model and effort | Task classes | Controller check that stays |
|---|---|---|
| luna, medium | data generation from a schema, reformatting, second-voice labelling against an explicit policy, summaries | Sample the output. Expect about 5% label errors (4 in 70 here) and flattened soft requirements such as length and variety |
| sol, medium | a narrow fix with a clear defect description, hard-case generation, reference labelling | Run the fix on the real system, not only the worker's tests |
| sol, high | simulations and test oracles, code with safety constraints, fixes to production logic | Check the result on the real runtime anyway |
| neither | acceptance, verdicts read from the run registry, policy decisions, anything sent outside | These stay with the controller or a human |

## Shared pitfalls

- Both models wrote honest notes about the limits of their checks, and both could still state things about code they had not read. Sol's header claim above is the example. Check any claim about a file against that file.
- Both built an automated observe step that produced false FAILs on real data. Neither knew the runtime data shape: when the mail fetcher pulled several messages in one batch, they could not attribute the model call to a message. The verdict came from the run registry and the controller's own check; the workers' observe scripts were set aside.
- Give workers failures from the dev part of the set only and keep a holdout they never see. Without it, luna's fix would have looked like a success on its own tests (35/35 PASS) while it was a regression on the real model.

## Addendum: narrow schema-bound calls

A worker running for minutes in a CLI and a single model call inside a pipeline are different roles, and one does not predict the other.

The same two models were also tried as the classifier itself: one short call per email, a JSON schema for the output, reasoning effort low, no temperature, output capped at 2,000 tokens, the same prompt for every model. Corpus of 155 synthetic emails, a 70-email holdout inside it, and 25 protected cases.

| Model | critical errors /155 | in holdout /70 | errors caused by the model | protected changes /25 | USD per 1,000 calls |
|---|---:|---:|---:|---:|---:|
| gpt-4.1-mini | 9 | 6 | 6 | 1 | 0.38 |
| gpt-6-luna | 3 | 1 | 0 | 1 | 0.13 |
| gpt-6-sol | 3 | 1 | 0 | 1 | 2.18 |

Cost per call is computed from measured tokens and the vendor's list prices on 2026-09-27 (USD per 1M input/output tokens: gpt-4.1-mini 0.40/1.60, gpt-6-luna 0.10/0.50, gpt-6-sol 2.00/10.00). The 3 remaining errors were identical for both gpt-6 models and came from deterministic pre-filters in front of the model, so a stronger model could not remove them.

The general point: a model that is weak as an autonomous worker can be the right choice for a narrow, schema-bound call with a good prompt. For that kind of call, start with the cheapest model that passes, and move up only when it fails the holdout. Keep worker evals and call evals in separate tables, because a verdict from one gets misapplied to the other.
