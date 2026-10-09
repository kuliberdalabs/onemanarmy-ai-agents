# Verification ladder

A green check is evidence only for the layer it touched. This page says which check to run for a code change, when to climb to a more expensive one, and how to tell a check that works from one that only exits 0.

The rule of thumb: run the cheapest check that can catch a realistic mistake in this change, and climb a level whenever the change crosses the boundary that level covers. Who freezes the acceptance criteria and who may touch them is covered in [completion-control.md](completion-control.md) and [controller-worker-contract.md](controller-worker-contract.md). This page covers the evidence.

## The five levels

| Level | What you run | What it catches | What it cannot see |
|---|---|---|---|
| 1. Static | The diff itself, plus the narrow formatter, linter, type check, schema check or compile step for the files you touched. | Typos, wrong types, broken imports, invalid config syntax. | Anything that depends on behavior. |
| 2. Focused | The smallest existing tests that run the changed branch, plus a regression test for the failure you observed, when one is worth keeping. | Logic errors inside the unit you changed. | How the unit talks to anything outside it. |
| 3. Integration | The real adapter, database, filesystem, queue, browser or process boundary the change touches. An API mock is fine when the API itself is out of scope. | Wrong field names, encoding, ordering, permissions, timeouts at the boundary. | Whether the built thing starts and behaves in its real environment. |
| 4. Runtime boundary | The built command, service, export, render or migration rehearsal, started the way it will be started: clean environment, real config loading path, real shell. | Missing files in the build, config that loads from a different place, shell and environment differences. | Whether the output is what was ordered. |
| 5. Real artifact | Read back what the user actually gets (the exported file, the deployed page, the rows in the table, the draft in the outbox) and check it against the acceptance criteria frozen before the run. | The gap between "the process succeeded" and "the result is right". | Nothing inside its scope. This is the level the completion claim is about. |

Unit tests that reimplement the integration are not a level 3 check. They test your model of the boundary, and the bug usually lives in the difference between that model and the boundary.

A failure at a higher level outranks any number of green checks below it. When a worker's own tests show 35 of 35 passing and the real model shows 8 regressions on 25 protected cases, the result is 8 regressions.

Before an irreversible step (deploy, money, a client system, deletion, anything public) there is one more gate, and it concerns authority: the action and the exact target need a still-valid approval. See [authority-model.md](authority-model.md).

## Rules for the upper levels

Each rule names the failure it prevents.

- **Verify configuration through the path that loads it.** A settings screen or a file labelled "current" can disagree with what the process read at start. Prevents: a fix that is visible in the config and absent at runtime.
- **Do not edit a state file while the process that owns it is running.** The writer holds its own copy and overwrites yours on the next save, or both writes interleave. Prevents: edits that silently vanish and corrupted state.
- **A manual fix outside the code lives until the next rebuild.** A limit set by hand on a finished render was lost when the tool rebuilt it with the old parameter, and the rebuilt file failed the gate. Put the fix into the tool as a parameter, or record it as debt where the next rebuild will see it. Prevents: regressions that look like new bugs.
- **Check shared UI after navigation as well as after a direct load.** A shared call-to-action block rendered correctly on direct entry and broke after a click from the home page, because the order of CSS chunks depended on the entry route and two rules had equal specificity. Prevents: layout bugs that only users see.
- **Fetch pages the way a browser does before claiming something is missing.** A CDN injected an analytics script only for requests with `Accept: text/html`; a `curl` with the default `Accept: */*` saw a page without it and reported a false negative. Prevents: "it is not on the page" claims that are wrong.
- **After an operation against an API, count the objects by reading them back.** Exit codes and "added" counters report what the client believed. Prevents: batches that report 8 items added when the target holds 7 (see `dash-arg-help.sh` below).

## Positive controls: a check has to prove it can fail

A check is trusted only after it has passed on a known-good input and failed on a known-bad one. Until then, "clean" means "the check ran", or less.

This matters most for checks shaped like "zero lines found means clean". Such a check is clean by default. If the command never ran, the log path is wrong, or the pattern can never match, it still reports zero. A check for unwanted system prompts reported clean for three days because zsh resolved `log` to its builtin, which printed an error the check discarded and produced no output at all. One run against material that contained a prompt would have caught it on day one.

Three rules follow:

- **Run the check once on material where the thing is present** and confirm it finds it. Prevents: checks that cannot fail.
- **Take the known-bad fixture from an artifact that really failed.** A fixture written to fit the check proves only that the check fits it. Prevents: a check tuned to its own fixture.
- **Treat a detector's alarm as a hypothesis.** Set its threshold on material whose state you know, with a positive and a negative control, and confirm an alarm with a second method before changing anything. A freeze detector raised 8 alarms on 8 renders that a human had already accepted, and two accepted renders were overwritten before anyone checked. Prevents: "fixing" good work because a threshold was miscalibrated.

The tool and the full method for this live in [negative-controls.md](negative-controls.md).

## Exit codes that lie

Each row below has a reproducer in [`core/pitfalls/`](../pitfalls/). Each script prints `REPRODUCED` and exits 0 only when the pitfall shows on the machine it runs on. A pitfall whose script stops reproducing gets fixed or cut, never kept as prose.

| Pitfall | What lies | Fix | Reproducer | Shell |
|---|---|---|---|---|
| zsh `log` builtin | `log show ...` runs the zsh builtin, not the system binary. It prints "too many arguments" to stderr and nothing to stdout. A check that drops stderr and counts lines reports 0 lines with exit 0. | Call `/usr/bin/log` by path; give the check a positive control. | `zsh-log-builtin.sh` | zsh |
| Pipe hides the exit code | `run_tests \| tail -n 5` returns tail's status. A test run piped into `tail` let `&& git commit` go ahead after a red test. | `run_tests >test.log 2>&1; rc=$?; tail test.log`, or `set -o pipefail`. | `pipe-swallows-exit.sh` | bash, sh |
| `grep -q` under pipefail | Lies the other way: `producer \| grep -q x` fails when x is found, because grep exits early and the producer dies of SIGPIPE (141). Under `set -e` a server bootstrap script stopped with no message after writing its SSH config and before reloading the service. | `out=$(producer); grep -q x <<<"$out"` | `pipefail-grep-q.sh` | bash |
| Dash-leading argument | argparse reads `-hVtq...` (an id, a hash, a base64 fragment) as `-h`, prints help and exits 0. The loop counted it as added. | Put `--` before positional arguments; count results by reading back. | `dash-arg-help.sh` | bash + python3 |
| No word splitting in zsh | No exit code at all, just a wrong parse: `set -- $row` gives one argument in zsh and three in bash, and `for v in $ids` runs once. | Split explicitly (`${=row}` in zsh) or run the snippet under bash with an array. | `zsh-no-wordsplit.sh` | zsh, bash |
| `pgrep -f` matches the waiter | A wait loop `while pgrep -f "render out.mp4"` carries the phrase in its own command line and never ends. On Linux one loop matches its own shell. macOS pgrep excludes its ancestors, so there it takes a second process with the phrase, such as a wait loop left over from a timed-out earlier wait. Nothing errors. | Use a character class: `pgrep -f "render[ ]out.mp4"`. | `pgrep-self-match.sh` | bash |

Run them all with:

```sh
tests/test_pitfalls.sh
```

The runner fails if any script reports `NOT REPRODUCED`, exits non-zero, or if it finds no scripts at all. Requirements: bash, zsh, python3 and pgrep. Verified on macOS with bash 3.2 and 5.3 and zsh 5.9 (2026-10-09).

## Before a causal story, read the timeline

When you explain why something broke, check the order of events in the record before you trust memory. For code and deploys that record is `git log` (and the deploy log): commit order beats anyone's recollection of the session, including an agent's. Prevents: a confident explanation built on events in the wrong order.

The same applies to labels. Before reporting that something is broken, look at the raw data behind the label. In one review, 2 of 5 reported gaps were misreadings: a column showed only the first of several sources, and a service shown as "not loaded" had been parked on purpose by an operator script. Prevents: fixing things that were never broken.
