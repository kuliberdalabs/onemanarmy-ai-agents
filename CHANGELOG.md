# Changelog

Notable changes to this repository. Versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - unreleased

First release. The date is set when it is published.

### Added

- `core/`: the rules for handing work to agents and taking it back (completion control, the controller and worker contract, the authority model, the verification ladder, negative controls, how rules get written); an `AGENTS.md` starter with a thin `CLAUDE.md` layer and a filled example for a fictional one-person consultancy; gate-selftest with its meta triangle and an example registry of three naive and three fixed gates; the doctrine-guard hook for Claude Code with a 14-case selftest; the session-end skill; six shell pitfall reproducers. Core started as an earlier unpublished draft and was moved under `core/` with its paths updated.
- `tiers/`: security overlays 0, 1 and 2 for Claude Code (`settings.json`) and OpenClaw (JSON5 fragments with a documentation source per key), a static check that the overlays parse and get stricter with the tier number, and a behavioral hold test with 7 cases. Each case has a liveness rule: a crashed run or a missing canary token reads `ERROR` and never `PASS`, so a tier cannot look held because the agent did nothing. Claude Code tiers 1 and 2 held 7 of 7 on 2026-10-10. Not yet run: tier 0, and every OpenClaw tier.
- `onboarding/`: an 18-question owner interview in English and Polish, a first-run script, the synthesis procedure, a context folder template and a placeholder checker.
- `evals/`: the ledger schema and two notes, each with its raw `ledger.csv`: Codex CLI workers measured 2026-09-27, and Claude, Codex and Kimi workers measured 2026-10-09.
- `packs/` and `field-notes/`: the pack entry rule with the planned lanes, and the field note format. Both hold only their README.
- `examples/first-job/`: a first real job with a self-proving gate. The agent turns 12 messy fictional receipts into an expense ledger, a gate you run decides whether it is done, and gate-selftest checks the gate against a known-bad input. It passed live on Codex CLI and on Claude Code with Haiku on 2026-10-10, one run each.
- `START-HERE.md`, a setup path of about 40 minutes for Claude Code and Codex, ending in that first job, and `README.pl.md`, a Polish start page.
- `scripts/validate_skill.py`, unit tests for core, tiers, onboarding and the first job (125 in total), and a CI workflow that runs the tests, the pitfall reproducers, the skill validator, the hook selftest, the meta triangle and the example registry.
