# doctrine-guard

A Claude Code `PreToolUse` hook. When an agent tries to edit a file that other sessions treat as rules (`AGENTS.md`, `CLAUDE.md`, `SKILL.md`, harness settings), the hook stops the edit and asks a human. Every other file stays fully editable.

Claude Code only. Bash 3.2+ and `python3` (stdlib) for JSON.

## Why: rules ratchet one way

Rules files have an asymmetry. Adding a clause takes one line and feels responsible. Removing a bad clause needs a human to notice it, trace where it came from and argue it out. So without a guard, constraints only accumulate.

The damage compounds because agents read these files as fact. One agent hits an edge case, writes a cautious rule into `AGENTS.md`, and every later session obeys it as policy. The next agent finds a related case and adds another clause on top. A few weeks later the rules file describes the guesses of past sessions, and nobody decided any of it.

The fix is a one-way ratchet in the other direction: **files that agents depend on change only by a human; agents propose diffs.** An agent that thinks a rule is wrong or missing says so in chat with the exact change and the reason. A human applies it or does not.

The hook separates two kinds of file:

| Kind | Examples | Who edits |
|---|---|---|
| Doctrine: what we are and how we work | `AGENTS.md`, `CLAUDE.md`, `MEMORY.md`, `SKILL.md`, `.claude/settings*.json`, `.claude/rules/*` | A human, or an agent with a human's yes on that edit |
| State: what happened and what is in progress | `STATE.md`, `HANDOFF.md`, `CHANGELOG.md`, logs, scratchpads, source code | Any agent, freely |

Blocking state files would stop normal work, and people would switch the hook off within a day. So state stays open.

## Install

```sh
mkdir -p .claude/hooks
cp core/hooks/doctrine-guard/doctrine-guard.sh .claude/hooks/
chmod +x .claude/hooks/doctrine-guard.sh
.claude/hooks/doctrine-guard.sh --selftest
```

Then merge `doctrine-guard.settings.example.json` into `.claude/settings.json` (project) or `~/.claude/settings.json` (all projects; adjust the command path). The matcher is `Edit|Write|MultiEdit`. Open `/hooks` in Claude Code to confirm it loaded.

Once installed, the hook also guards `settings.json` and its own script. An agent that could edit either one could switch the guard off, so those edits need a human too.

## Configure

Edit the `PROTECT` and `ALLOW` arrays at the top of the script, or set environment variables:

| Variable | Effect |
|---|---|
| `DOCTRINE_GUARD_PROTECT` | Colon-separated globs. Replaces the built-in protected list. |
| `DOCTRINE_GUARD_ALLOW` | Colon-separated globs. Replaces the built-in state list. Checked first, so it wins. |
| `DOCTRINE_GUARD_MODE` | `ask` (default) prompts the human. `deny` always refuses and tells the agent to propose a diff in chat. |

Globs match the absolute path, and `*` also matches `/`, so `*/AGENTS.md` covers every `AGENTS.md` in the tree. Each built-in entry carries a one-line reason that the human sees in the prompt, so the person approving knows what the file does.

Use `deny` when nobody watches the session, such as overnight or headless runs. The outcome then does not depend on how a permission prompt is handled with no human present.

## Test

`--selftest` pipes sample hook JSON through the script: five cases that must pass silently (a state file, a source file, malformed JSON, no path, a file left out of an env-var list) and nine that must be stopped, including a relative path, a path with a quote in it and deny mode. It exits 0 when every case matches and 1 otherwise.

The selftest has to be able to fail. Delete the `AGENTS.md` line from `PROTECT` in a copy, run `--selftest` on the copy, and three cases report `FAIL` with exit 1. Do that once after you change the lists.

To try one case by hand:

```sh
printf '%s' '{"tool_name":"Edit","tool_input":{"file_path":"/repo/AGENTS.md"}}' \
  | .claude/hooks/doctrine-guard.sh
```

A protected path prints a `permissionDecision` JSON. Any other path prints nothing, which leaves the decision to Claude Code's normal permission rules.

## What it does not do

- **Shell writes pass through.** `cat > AGENTS.md`, `sed -i`, `python3 -c "open(...).write(...)"` are not seen. The hook catches routine drift and honest mistakes. It does not stop an agent set on getting around it. Matching every shell command against file paths would raise false alarms on normal work, and an agent can always build a path the matcher misses.
- **It fails open.** Malformed input or a missing `file_path` gives no decision, so the normal permission prompt and your other hooks still apply. A guard that blocks every edit when it breaks gets removed.
- **Other tools are out of scope.** Only the three tools in the matcher reach it. Add more to the matcher only if their input carries `tool_input.file_path`.
- **Claude Code only.** Other agent CLIs have different hook formats or none. For them, the same rule goes in the instructions file as text, which an agent can ignore.
