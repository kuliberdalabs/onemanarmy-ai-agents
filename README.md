# onemanarmy

A one-person company running an army of agents: the workshop, in the open.

One person runs a company with AI agents spread across several models, where a few plan, most execute and some only watch. This repository is that workshop: the rules the agents work under, the gates that check their work, the security tiers they run in, and the evals that decide which model does which job. It rests on three habits: an agent's "done" is a claim until someone checks the real artifact, a gate counts only after it has failed once on a known-bad input, and model choice follows results measured per task class.

Status: 0.1.0, unreleased. Everything below runs locally with Python 3.10 or newer, bash and zsh, standard library only.

## Layout

| Folder | What it holds | Status |
|---|---|---|
| [core/](core/README.md) | Rules for handing work to agents and taking it back, an `AGENTS.md` starter template, gate-selftest, the doctrine-guard hook, the session-end skill, six shell pitfall reproducers | Usable. 19 unit tests, 6 of 6 pitfalls reproduced, hook selftest 14 of 14 cases |
| [tiers/](tiers/README.md) | Security overlays 0, 1 and 2 for Claude Code and OpenClaw, a static check, and a behavioral test that asks the agent to break its tier and then inspects the world | Draft. Static check and 44 tests pass. Claude Code tiers 1 and 2 held 7 of 7 cases on 2026-10-10. Tier 0 and all OpenClaw tiers have not had a behavioral run |
| [onboarding/](onboarding/README.md) | An 18-question owner interview in English and Polish, a context folder template, and a placeholder checker | Draft. 25 tests pass. No recorded interview run in this repository yet |
| [packs/](packs/README.md) | Capability lanes (marketing, local SEO, ads, motion, n8n) | Private for now. This folder holds the entry rule and the list of planned lanes |
| [evals/](evals/SCHEMA.md) | The ledger schema and dated eval notes, each with its raw CSV | Two notes: Codex CLI workers (13 runs, 2026-09-27) and Claude, Codex and Kimi workers (119 ledger rows, 2026-10-09) |
| [field-notes/](field-notes/README.md) | Short dated notes from the workshop | Format defined, no notes yet |
| [examples/](examples/first-job/README.md) | A first real job for a new user: 12 messy receipts into an expense ledger, with an acceptance gate and its bad fixtures | Usable. Gate and fixtures pass 20 tests and gate-selftest (2 of 2 PASS). One run each with Codex and Claude Code on 2026-10-10, both PASS on the first round |

`scripts/` holds the skill validator and `tests/` the unit tests for core, tiers and onboarding. `.github/workflows/ci.yml` runs the unit tests and the core checks; it has not run on a hosted runner yet, because nothing is pushed.

## Start here

[START-HERE.md](START-HERE.md) is a path of about 40 minutes for Claude Code or Codex. You copy and fill the `AGENTS.md` template, add the doctrine-guard hook (Claude Code only), install the session-end skill, run gate-selftest on its example registry and read why three of its gates cannot fail, then give your agent one real job (`examples/first-job`) and let a gate you run decide whether it is done. Each step ends with output you can compare against.

Already delegating work to agents? Read [core/docs/completion-control.md](core/docs/completion-control.md) and [core/docs/controller-worker-contract.md](core/docs/controller-worker-contract.md), then point [core/gate-selftest/](core/gate-selftest/README.md) at your own gates. If your agents run with few or no permission prompts, read [tiers/](tiers/README.md) next.

To check the repository itself, from its root:

```sh
python3 -m unittest discover tests           # 125 tests: core, tiers, onboarding, first-job
bash tests/test_pitfalls.sh                  # 6/6 reproduced
python3 scripts/validate_skill.py core/skills/session-end
python3 core/gate-selftest/selftest.py --meta-only
python3 core/gate-selftest/selftest.py --registry examples/first-job/gate/registry.yaml   # examples/first-job: PASS: 2
bash core/hooks/doctrine-guard/doctrine-guard.sh --selftest
python3 tiers/tiercheck.py
```

## Why trust it

Trust the receipts more than the prose. Each one carries a date and, where it is a measurement, a version and an `n`.

- **Worker evals with numbers.** On 2026-09-27 two Codex CLI models ran as workers on the same tasks, 13 runs in total. On one task a worker's own tests showed 35 of 35 passing while the real model showed 8 regressions on 25 protected cases; the controller rejected it. Raw rows and the per-task-class verdict: [evals/2026-09-27-codex-workers/](evals/2026-09-27-codex-workers/README.md).
- **Cheap is fine until a person reads the output.** On 2026-10-09 the cheapest Claude model in the test (Haiku 5.5) was accepted on 38 of 38 tasks behind automated gates (37 by the grader alone; the other was a grader false negative, accepted after a hand read), at roughly a sixteenth of the mid-tier model's API cost proxy. On a Polish social post it scored 4.4 out of 10 from two blind judges (mean of 5 runs, range 3.5 to 5.5), against 7.25 for Sonnet 5.5 and 8.25 for Opus 5.5. Its posts passed the mechanical text gate all the same, so for text a person reads that gate alone is not enough. The routing follows: routine gated work goes to the cheap model, copy for people does not. All models hit the ceiling of the gates, n is 5 for Haiku and 1 or 2 for the rest, and both judges are Claude models that also appear as workers. Write-up and raw rows: [evals/2026-10-09-claude-workers/](evals/2026-10-09-claude-workers/README.md).
- **Gates with negative controls.** gate-selftest runs every registered check on a known-bad and a known-good input, and it first runs itself on a gate that always passes, an honest gate and a gate that always fails; if it cannot sort those three, it exits 3 and reports nothing. Its example registry flags three naive gates shaped after real incidents. One of them is a log check that reported clean for three days, because under zsh `log` is a builtin that printed an error and nothing for grep to match. Reproducer: [core/pitfalls/zsh-log-builtin.sh](core/pitfalls/zsh-log-builtin.sh).
- **Tiers tested by behavior.** The hold test asks the agent to write outside its workspace, delete a file, send mail, post over HTTP and push to git, and then looks at the files, the mail shim, the network sink and the remote to see whether anything happened. Its own probes are checked first: each one must read "no effect" on a clean world and "effect" after a scripted action. In the tier 1 run every "asks" case recorded a permission denial, so the harness stopped the action, and the model's own reluctance played no part in the result.
- **The onboarding checker fails on purpose in its tests.** The shipped template must fail it, a filled copy must pass, and one leftover placeholder must be caught.

## What this is not

- Not a framework. Nothing here runs your agents. You copy rules, templates, configuration overlays and small stdlib tools into your own setup.
- Not a skills dump. Core ships one skill. Capability packs enter only after dogfooding and an eval against the bare model, and none has entered yet.
- Not an OS sandbox. The tiers configure the sandboxes and permission rules your harness already has. Tier 1 on Claude Code is rule-level: a script that deletes files inside the workspace is not asked about, because the sandbox allows workspace writes. The doctrine-guard hook catches the Edit, Write and MultiEdit tools and does not see shell writes such as `sed -i`.
- Not a benchmark or a leaderboard. Each eval covers one domain with a small `n`, and model facts go stale as models and CLIs change.

## Built on, works with

None of these are ours. The files here follow their formats or configure them; nothing from their documentation is copied.

- [agents.md](https://agents.md), the format for agent instruction files. The starter templates follow it.
- [Agent Skills](https://agentskills.io), the `SKILL.md` folder format. `core/skills/session-end` and the validator follow it.
- [OpenClaw](https://docs.openclaw.ai), an agent gateway. `tiers/openclaw/` holds configuration fragments for it.
- [Claude Code](https://docs.claude.com/en/docs/claude-code), Anthropic's coding agent CLI. The doctrine-guard hook, `tiers/claude-code/` and the hold test target it.
- [Codex](https://github.com/openai/codex), OpenAI's coding agent CLI. The starter works with it, and the 2026-09-27 eval ran on it.

Tool versions this release was checked with: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Changes: [CHANGELOG.md](CHANGELOG.md). Licence: [MIT](LICENSE). Polish start page: [README.pl.md](README.pl.md).

Built by Kuliberda Labs (Kraków), AI agents and n8n automations for service firms. [kuliberda.ai](https://kuliberda.ai)
