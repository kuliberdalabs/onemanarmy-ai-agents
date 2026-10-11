# Third-party notices

## Text and code

This repository ships no third-party text or code. Every file was written for it, and all of it is under the [MIT licence](LICENSE). The tools use only the Python standard library and POSIX shell utilities; `tiers/json5lite.py` is a small JSON5 subset reader written here.

`tiers/README.md` cites one news report on malicious skills in a public registry, with a link to the source and the figures it reported.

## Formats and tools referenced

These are not ours. The files here follow their formats or configure them; nothing from their specifications or documentation is copied.

| Format or tool | Used by | Source |
|---|---|---|
| AGENTS.md | `core/starter/` | [agents.md](https://agents.md) |
| Agent Skills (`SKILL.md` folders) | `core/skills/session-end/`, `scripts/validate_skill.py` | [agentskills.io](https://agentskills.io) |
| Claude Code hooks (`PreToolUse` JSON) and settings files | `core/hooks/doctrine-guard/`, `tiers/claude-code/`, `tiers/hold_test.py` | Claude Code documentation |
| OpenClaw configuration | `tiers/openclaw/` | [docs.openclaw.ai](https://docs.openclaw.ai), pages read on 2026-10-10 and cited per key in each fragment |
| Codex CLI | `core/starter/`, `evals/2026-09-27-codex-workers/`, the Codex rows of `evals/2026-10-09-claude-workers/` | Codex CLI documentation |
| Kimi CLI, Grok CLI | The control rows of `evals/2026-10-09-claude-workers/` | Their own documentation |

## Tested with

Versions on the machine where 0.1.0 was built and checked:

| Tool | Version | What ran on it |
|---|---|---|
| Claude Code | 2.1.296 | On 2026-10-11: the first-job run with Haiku (receipts in `examples/first-job/runs/`), the live check of the tier 1 read fence, and the re-run of the tier hold test for tiers 1 and 2. On 2026-10-10: an earlier hold test run, whose results predate the current runner and do not count |
| Claude Code | 2.1.295 | The doctrine-guard hook, checked with piped `PreToolUse` JSON on 2026-10-09, not inside a live session |
| Claude Code | unknown (2.1.295 or 2.1.296) | The Claude rows of `evals/2026-10-09-claude-workers/`. Nobody logged the version at run time |
| Codex CLI | 0.157.1 | The worker eval in `evals/2026-09-27-codex-workers/` |
| Codex CLI | 0.160.0 | The Codex rows of `evals/2026-10-09-claude-workers/` (version read on 2026-10-10, the day after the runs) and the first-job run on 2026-10-10 |
| Kimi CLI | 2.1.1 | The Kimi rows of `evals/2026-10-09-claude-workers/` (version read on 2026-10-10) |
| Grok CLI | 1.0.50 | Three attempts in `evals/2026-10-09-claude-workers/`, all refused by the account before they reached the model |
| OpenClaw | 2026.9.6 | Installed version. The fragments in `tiers/openclaw/` were written from the documentation and have not been loaded into a running gateway. The `apply_patch` delete that tier 1 now denies was reproduced on this version, outside a gateway |
| Python | 3.14.7 and 3.11.15 | All unit tests, gate-selftest, the validator, the tier tools, the placeholder checker. The python3 that ships with macOS (3.9) is below the supported floor of 3.11 |
| zsh | 5.9 | `core/pitfalls/`, the example gates |
| bash | 5.3.9 and 3.2.57 | `core/pitfalls/`, `core/hooks/doctrine-guard/`, `tests/test_pitfalls.sh` |
| OS | macOS (Darwin, arm64) | All of the above. CI runs the unit tests and the repository checks on GitHub-hosted Ubuntu with Python 3.11 and 3.13 |

Model and CLI behaviour changes between versions. Treat each line as true for the version and date it names.
