# Completion control

An agent's "done" is a claim. This page says how much control a task needs before that claim is trusted, and what the controller does at each step from scoping to acceptance.

The controller is whoever ordered the work: you, or the main agent session that delegates to workers. The worker is whatever produces the artifact: a subagent, another CLI, or the same session in a later step. In small tasks one agent plays both roles. The mechanics of delegation live in [controller-worker-contract.md](controller-worker-contract.md).

This page grants no authority. Whether an agent may deploy, send or delete is decided elsewhere. Completion control only decides when a result counts as finished.

## Pick a profile

| Profile | Use when | What control looks like |
|---|---|---|
| Light | The work is clear, reversible, and a cheap check tells you reliably whether it worked. | A contract in your head, direct work, the one relevant check. |
| Standard | Real ambiguity, dependencies on other parts, or an artifact someone else must accept. | A short written contract for this task, protected acceptance criteria, verification sized to the risk. A fresh reviewer only where meaning or taste is still open. |
| Strict | Money, live systems, possible data loss, a consequential migration or deployment. | A durable contract on disk that someone reviewed, protected verification the worker cannot reach, an independent final review, a fixed retry budget and a recovery plan. |

Route by four things: impact, ambiguity, reversibility, and who owns the evidence. Never route by duration or file count.

A long batched task can stay Standard. A one-line change that cannot be undone can be Strict. A model evaluation with its own frozen cases and an isolated runner is Standard; it does not need the heavy supervisor just because it runs for hours.

**Failure it prevents:** effort spent where it does not matter. Teams that route by size put ceremony on a 40-file rename with a green test suite and skip it on the one-line config edit that sends mail to customers.

### Which profile do I pick

| Task | Profile | Why |
|---|---|---|
| Fix a typo in the README | Light | Reversible, the check is reading the diff. |
| Rename a function across 40 files, test suite already covers the callers | Light | Many files, one mechanical change, the tests decide. File count does not raise the profile. |
| Overnight batch of 30 help-center articles for review in the morning | Standard | Long and reversible, but every article needs explicit acceptance criteria (sources, length, terms) frozen before the run. |
| Weekly status report for a client, assembled from three live systems | Standard | Several sources, a reader outside the team. A partial read has to show up as partial. |
| Compare two models as workers on 25 frozen cases | Standard | The frozen cases and the runner are the contract. No production effect. |
| One-line change to the job that decides who receives a payment reminder | Strict | One line, but it touches money and sends mail to real people. A wrong recipient cannot be unsent. |

## The loop

```
IMPACT_SCAN -> CONTRACT_FREEZE -> RUN -> VERIFY -> ACCEPT | REWORK | REPLAN | PARK
```

### IMPACT_SCAN

Find out what was asked and which source is authoritative for it. List the artifacts that change and who consumes them, the integration boundaries the result crosses, side effects, and what authority the task needs. Then name the cheapest piece of evidence that could disprove a false "done".

Close the scope gaps you can see. Exhaustive analysis is not the goal.

**Failure it prevents:** a fix that passes its own test and breaks a consumer nobody listed.

### CONTRACT_FREEZE

Write down only what this task needs, before anything runs:

- goal and scope
- postconditions and the artifacts they apply to
- who or what verifies, and on which evidence
- protected fixtures and expected outputs
- the freshness or runtime boundary the claim must hold at (a local build, the deployed site, the export a client opens)
- progress and retry rules
- authority: what the worker may do without asking
- a rubric, if part of the result is judged on meaning or taste

If the contract turns out to be wrong, record why, version it, and replan. Moving the criteria silently is the failure this step exists to stop: a target that moves after the run always looks met.

Do not invent a time limit from the fact that the person who asked will be away. Absence is not a deadline.

A Standard contract can be this short:

```
goal:       payment reminders draft for overdue invoices, one per customer
scope:      drafts only; nothing is sent
post:       one draft per invoice older than 14 days in fixtures/invoices.csv
            amount and due date match the invoice row exactly
verify:     controller runs check_drafts.py against fixtures/expected_drafts.json
protected:  fixtures/, check_drafts.py, the 14-day threshold
boundary:   drafts as they appear in the mail client's draft folder
retries:    2 rework rounds, then PARK
```

### RUN

Hand the worker the parts of the contract it needs, the paths it owns, its sources and, on a retry, the failed delta. Keep unrelated history out of its context. Use the simplest approach you are allowed to use.

### VERIFY

Look at the actual artifact and check it is fresh. Confirm the protected acceptance inputs are unchanged. Run the behavior tests that matter. When the claim crosses a boundary (runtime, export, integration), verify on the far side of that boundary. Ask for an independent review only for the criteria that still need one.

Worker prose and worker-written green tests are inputs to acceptance. They are never the acceptance itself.

**Receipt:** a worker's own suite reported 35 of 35 passing. Run against the real model, the same change showed 8 regressions on 25 protected cases. Both counts are the controller's observations from the run output (2026-09-27); the eval ledger records the rejection, not the counts.

When a claim is assembled from several live sources, a partial read is reported as incomplete, never as a full report. Two of three sources read is a report that says "incomplete: 2 of 3", with the missing source named.

## Decisions

| Decision | When |
|---|---|
| ACCEPT | The frozen postconditions pass, with evidence that matches the boundary the claim was made at. |
| REWORK | The contract is valid and there is a concrete failed delta. Return that delta with its proof. Measurable improvement earns another rework round even if a gate is still red. |
| REPLAN | The strategy or the contract is wrong, a dependency was missed, protected criteria changed, or a comparable round made no progress. Change the strategy before the next attempt. |
| PARK | The agreed brake is reached, two comparable rounds made no progress, or missing authority, credentials or unresolved consequential state block completion. Keep the best artifact and write the exact condition for resuming. |

**Failure it prevents:** the open-ended retry loop, where a worker gets the same prompt a fifth time because nobody wrote down when to stop.

## Two rules that hold everywhere

**Infrastructure failure is not model failure.** A crashed sandbox, an expired login, a full disk or a rate limit says nothing about the model or the prompt, and it is not evidence of "no progress" either. Record what it cost, repair it under the rules for that system, and rerun. Counting it against the worker sends you to REPLAN for a problem the plan never had.

**Missing information is unknown, not success.** A check that found nothing to read has not found nothing wrong. Zero rows, an empty log, a counter for a status the system never emits: each of these reads as clean unless the check proves it can fail. That proof is the subject of [negative-controls.md](negative-controls.md).

**Receipt:** a counter for a status value that never existed returned 0, and 0 was read as "no failures".

## Where the rest lives

- Delegation, retries and review mechanics: [controller-worker-contract.md](controller-worker-contract.md)
- Proving a check can fail before trusting it: [negative-controls.md](negative-controls.md)
- The code verification ladder and shell pitfalls: [verification-ladder.md](verification-ladder.md)
