# Controller and worker contract

How a controller hands work to workers and takes it back. Read [completion-control.md](completion-control.md) first: it defines the profiles, the loop and the four decisions. This page covers the mechanics around them.

Each rule carries the failure it prevents and, where we have one, the incident that produced it. Dates are when we hit it.

## The controller

**The controller keeps scope, the frozen contract, worker choice, the retry budget and acceptance.** Delegating a task never delegates those decisions.
- Prevents: a worker that both does the work and decides it is finished.

**Delegate only when it pays.** Good reasons: branches that are truly independent, a bounded specialist job, a fresh pair of eyes for review. "The task sounds big" is not one of them.
- Prevents: coordination cost on work one agent would have finished faster.

**One owned artifact per worker.** Each worker gets one artifact to build, or one correction (the largest failed delta), plus the part of the contract that applies, concrete paths, the evidence available and the shape of the answer you want back. Unrelated context stays out.
- Prevents: two workers editing the same file from different assumptions.
- Receipt: an overnight build ran the data model, API and module stubs in one worker and the front end in another, both against one API contract with a fixture; then the modules filled the stubs in parallel. No write conflicts. (2026-09)

**Every brief has a field "deviations from the contract, with reason".** The worker fills it when it departs from the contract. That field is where its judgment becomes visible and reviewable.
- Prevents: silent deviations, found only when something downstream breaks.

**The brief is the worker's whole world.** A step you did not name does not run. If the output is text for people, name the editing pass. If facts must be sourced, say so. A fact check and a language check are separate gates; passing one says nothing about the other.
- Prevents: the step that "everyone knows" and the worker never heard of.

**Keep worker scrollback below the controller.** Promote decisions, evidence paths, failed deltas and residual risk. Leave the rest in the worker's log.
- Prevents: the controller's context filling with transcripts until it loses the contract.

## The worker

**A worker may add tests. It never touches fixtures, thresholds, expected outputs, protected files or pass criteria after the freeze.** Those belong to the controller.
- Prevents: the worker making the target easier until it hits it.

**DONE means ready for controller verification.** Acceptance is the controller's call, made on the artifact. A blocked worker returns the exact blocker and keeps any safe partial work.
- Prevents: "done" in a worker's summary being copied into a status report unchecked.
- Receipt: a worker's own suite reported 35 of 35 passing; the protected cases, run on the real model, showed 8 regressions out of 25.

**Write large files per section.** A worker producing a file over roughly 400 to 600 lines writes it section by section, or one file at a time.
- Prevents: losing the whole run to the output limit.
- Receipt: a single monolithic write hit the 64k-token output limit and killed the worker. Resuming the same worker by message, with its context kept, was cheap and worked. (2026-08)

**The worker returns text; the controller writes report files.** A worker that synthesizes findings returns them in its final message. The controller saves the file. A critic or reviewer starts only after the file exists.
- Prevents: a report that exists only in a refused write, and a reviewer reading a file that is not there yet.
- Receipt: the agent harness refused a subagent's report-file write twice, with the message that subagents should return findings as text. (2026-10-01)

**Unknown scripts and env files are inspected only by counting key names.** "Do not print tokens" is not enough when the worker does not know a file holds tokens. Briefs say: for unknown scripts, CLI wrappers and `*.env` files, use `grep -c` on key names, never `cat`, `head` or `less`.
- Prevents: a live credential landing in a transcript, a log and possibly a commit.
- Receipt: a worker ran `head -c` on a CLI wrapper script to see what it was. The wrapper held live tokens, and they went straight into the transcript. (2026-10-01)

```sh
grep -c '^API_TOKEN=' .env                                 # 1 if the key is set, 0 if not
grep -cE '^[A-Za-z_][A-Za-z0-9_]*=' .env                   # how many keys the file defines
grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' .env | cut -d= -f1     # key names only, no values
```

## Shared trees

When several workers write into one tree at the same time:

**Do not audit a tree that is still being edited.** Freeze edits, or audit a snapshot.
- Prevents: findings against a file that changed under the auditor, and fixes for problems that no longer exist.

**Global renames and sanitizing run only after every writing worker has returned.**
- Prevents: a worker writing the old name back into a file the rename already cleaned.

**Parallel edits to shared files work under three habits:** read the file right before editing, edit minimally and additively, and on an edit conflict re-read and retry.
- Receipt: five to six workers edited one set of shared files this way with no lost change. (mid-2026)

**A red typecheck between worker returns is normal.** The gate that counts is the one at each worker's return.
- Prevents: stopping a parallel build because a half-finished neighbor does not compile yet.

## Retries

**On a failed contract, return only the largest useful delta.** Reuse the same worker when its context helps. Change the worker, prompt, tool or decomposition when the strategy itself is the problem.
- Prevents: a full re-run that fixes one thing and breaks two.

**Count progress by measurement.** A round with measurable improvement stays rework, even if a gate is still red. One measured round without progress forces a strategy change. Two comparable rounds without progress, or the retry cap, means PARK: keep the best artifact and write the exact condition for resuming.
- Prevents: the retry loop that runs until the budget is gone with nothing to show for it.

**Durable loops keep state on disk.** A loop that runs headless or overnight stores its contract, attempts, verdicts, artifacts and evidence in files. It continues across independent units and never uses transcript length as program state.
- Prevents: a loop that loses its place when a session is compacted or restarted.

## Review

**A fresh reviewer is a bounded gate.** Use one for open questions of meaning or for high-impact work. It judges the frozen contract against the real artifact, reports only material gaps, and cannot rewrite acceptance.
- Prevents: review as ceremony, and a reviewer that quietly moves the target.

**Agreement of two workers reading the same artifact is not evidence.** If both read the same measurement file, they inherit the same error. Check causality in the code or in an independent source.
- Receipt: two workers assessed the same measurement artifact and repeated the same error. (2026-10-01)

**Independent reviewers do help when they differ in tool, and the fixes go to separate workers.**
- Receipt: two different CLIs given one audit prompt found the same top-severity defect and complemented each other on the second tier. Fixes went to a backend worker and a front-end worker; the controller then verified on the artifact with a request, a screenshot and the UI. (2026-09-25)

**Tell the fixer to delete an unsourced claim.** After a review flags an unsupported statement, a fixer tends to keep it and add plausible technical detail around it. Control and fix prompts say: delete the unsourced claim, do not prop it up with details.
- Receipt: a reviewer on a different model caught unsourced claims and invented first-person scenes in a batch of articles. The fixes that followed drifted into technical detail around those claims, so the fix prompt now says to delete them. (2026-10-04)
