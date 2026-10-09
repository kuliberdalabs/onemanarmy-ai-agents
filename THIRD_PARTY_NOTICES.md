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
| Codex CLI | `core/starter/`, `evals/2026-09-27-codex-workers/` | Codex CLI documentation |

## Tested with

Versions on the machine where 0.1.0 was built and checked:

| Tool | Version | What ran on it |
|---|---|---|
| Claude Code | 2.1.296 | The tier hold test, tiers 1 and 2, on 2026-10-10 |
| Claude Code | 2.1.295 | The doctrine-guard hook, checked with piped `PreToolUse` JSON on 2026-10-09, not inside a live session |
| Codex CLI | 0.157.1 | The worker eval in `evals/2026-09-27-codex-workers/` |
| Codex CLI | codex-cli 0.160.0 | Installed version; nothing in this release depends on it |
| OpenClaw | 2026.9.6 | Installed version. The fragments in `tiers/openclaw/` were written from the documentation and have not been loaded into a running gateway |
| Python | 3.14.7 and 3.11 | All unit tests, gate-selftest, the validator, the tier tools, the placeholder checker |
| zsh | 5.9 | `core/pitfalls/`, the example gates |
| bash | 5.3.9 and 3.2.57 | `core/pitfalls/`, `core/hooks/doctrine-guard/`, `tests/test_pitfalls.sh` |
| OS | macOS (Darwin, arm64) | All of the above. The CI workflow targets ubuntu-latest and has not run on a hosted runner yet |

Model and CLI behaviour changes between versions. Treat each line as true for the version and date it names.
