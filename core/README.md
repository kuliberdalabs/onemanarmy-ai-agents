# core

The part of the workshop that does not depend on which tools or models you run. It holds the rules for handing work to agents and accepting it back, a template to start your own rule files from, and the tools that check the checks. Everything here runs from the repository root with Python 3 and bash. Two pieces also need zsh, because the pitfalls they reproduce are zsh behaviours.

## What is in it

| Folder | What it is |
|---|---|
| `docs/` | Six short pages: completion control, the controller and worker contract, the verification ladder, the authority model, negative controls, and how rules get written. |
| `starter/` | `AGENTS.template.md` and `CLAUDE.template.md` with placeholders, plus one filled example for a one-person consultancy. |
| `gate-selftest/` | A runner that feeds every gate a known-bad and a known-good input and sorts it into PASS, CANNOT-FAIL or FALSE-ALARM. A gate that accepts the bad input is a gate that cannot fail. |
| `pitfalls/` | Six small scripts. Each one reproduces a shell mistake that made a check pass when it should not have, and prints `REPRODUCED` when it still does on your machine. |
| `hooks/doctrine-guard/` | A Claude Code `PreToolUse` hook that asks a human before an agent edits rule files such as `AGENTS.md`, `CLAUDE.md` or `SKILL.md`. |
| `skills/session-end/` | One skill that closes a session into the project that owns the work, as a short update instead of a handoff document. |

## Reading order

1. `docs/completion-control.md`. "Done" is a claim; this page sets how much control a task needs before you believe it.
2. `docs/verification-ladder.md`. Which check to run for which change, and how to tell a check that works from one that only exits 0.
3. `docs/negative-controls.md`. Why gates need a bad input they must reject, with the incidents behind it. Then run `python3 core/gate-selftest/selftest.py --registry core/gate-selftest/registry.example.yaml` and read the three naive gates it flags.
4. `docs/controller-worker-contract.md`. The mechanics of delegating to cheaper models and taking the result back.
5. `docs/authority-model.md`. What an agent may do on its own and what always needs an explicit yes.
6. `starter/AGENTS.template.md`, then the filled example in `starter/examples/`. Copy, replace the placeholders, delete what does not apply.
7. `docs/how-we-write-rules.md`, when you are ready to write rules of your own.

The model comparisons that decide which model gets which job live outside core, in `evals/` at the repository root.

## Checks

From the repository root:

```sh
python3 -m unittest discover tests
bash tests/test_pitfalls.sh
python3 scripts/validate_skill.py core/skills/session-end
python3 core/gate-selftest/selftest.py --meta-only
bash core/hooks/doctrine-guard/doctrine-guard.sh --selftest
```

The same five run in CI. Run the last-but-one on a fresh machine before you trust anything else in this folder: it proves the runner itself can still tell a failing gate from a passing one.
