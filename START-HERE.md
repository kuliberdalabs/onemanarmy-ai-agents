# Start here: about 40 minutes

Four steps take you from an empty project to one with a rules file every agent reads, a guard on that rules file, a skill that closes sessions into the project, and one check that has proved it can fail. Each step ends with a result you can check from the shell, so you know it worked before moving on. The last block is a short check in a live agent session (about 3 minutes), which confirms the agent loads what you set up. Step 5 puts your agent on one real job, and a gate you run decides whether it is done. The timings add up to about 40 minutes with step 5 and the live-session block included. A cold-start tester, who had seen none of this before, estimated 35 to 45 minutes.

Where Claude Code and Codex differ, the step has two columns. Everything else is the same for both.

## Before you start (2 minutes)

You need `git`, `python3` 3.10 or newer, `bash` and `zsh`. macOS has all of them; on Debian or Ubuntu, `sudo apt-get install zsh` adds the missing one.

```sh
git clone https://github.com/kuliberdalabs/onemanarmy-ai-agents.git   # or unpack the zip you were given
cd /path/to/your-project          # the project your agent works in
export OM=/path/to/onemanarmy-ai-agents
python3 --version                 # 3.10 or newer
```

`OM` is only a shortcut for the commands below. Nothing here installs anything outside your project unless a step says so.

## Step 1. Rules file (9 minutes)

Copy the kernel template and fill it in.

| Claude Code | Codex |
|---|---|
| `cp "$OM/core/starter/AGENTS.template.md" AGENTS.md`<br>`cp "$OM/core/starter/CLAUDE.template.md" CLAUDE.md` | `cp "$OM/core/starter/AGENTS.template.md" AGENTS.md` |
| `CLAUDE.md` imports `AGENTS.md` with its first line, `@AGENTS.md`, and holds only what is specific to Claude Code. | Codex reads `AGENTS.md` from the project on its own. No second file. |

Open the file and replace every double-brace placeholder: your name, your organisation, the chat language, the state file (`STATE.md` is a fine default), the command that proves a change works, and any actions that must always wait for you. Delete lines that do not apply.

When a placeholder has nothing to say yet, write this:

- `{{VERIFY_COMMAND}}`: "none yet; open the file itself".
- `{{HOOKS_IN_USE}}` (in `CLAUDE.md`): "doctrine-guard", which you install in step 2. If you skip step 2, write "none".
- `{{EXTRA_EXPLICIT_ACTIONS}}`: "edits to AGENTS.md and SKILL.md files (propose the diff in chat)", or "none". Codex users put the Codex wording from step 2 here, because for them this line is the only guard.
- `{{WHEN_TO_USE_SUBAGENTS}}` (in `CLAUDE.md`): "only when I ask", until you have a reason to write more. Run `grep -o '{{[A-Za-z_-]*}}' AGENTS.md CLAUDE.md` to list what is left, including the date, the decisions file and, in `CLAUDE.md`, the hooks and subagent lines. A filled example for a one-person consultancy is in [core/starter/examples/AGENTS.solo-consultant.md](core/starter/examples/AGENTS.solo-consultant.md).

**Expected result:**

```sh
grep -c '{{' AGENTS.md CLAUDE.md   # Codex: grep -c '{{' AGENTS.md
```

prints `AGENTS.md:0` and `CLAUDE.md:0` (Codex, with one file: just `0`). The live-session question for this step is in the last block.

## Step 2. Guard the rules file (5 minutes)

Agents add cautious clauses to rule files and never remove them. The hook sends every edit of `AGENTS.md`, `CLAUDE.md`, `SKILL.md` and the harness settings to you for a yes or no. The reasoning is in [core/hooks/doctrine-guard/README.md](core/hooks/doctrine-guard/README.md).

| Claude Code | Codex |
|---|---|
| `mkdir -p .claude/hooks`<br>`cp "$OM/core/hooks/doctrine-guard/doctrine-guard.sh" .claude/hooks/`<br>`chmod +x .claude/hooks/doctrine-guard.sh`<br>`.claude/hooks/doctrine-guard.sh --selftest` | The hook is written for Claude Code's `PreToolUse` format and has no Codex version. Skip the commands. Add the rule as text instead: in `AGENTS.md`, put "edits to AGENTS.md and SKILL.md files (propose the diff in chat)" into the always-explicit list where `{{EXTRA_EXPLICIT_ACTIONS}}` was. The agent reads that line; nothing enforces it. |
| If `.claude/settings.json` does not exist yet:<br>`cp "$OM/core/hooks/doctrine-guard/doctrine-guard.settings.example.json" .claude/settings.json`<br>If it exists, merge the `hooks` block from the example into it by hand. Do this merge in your own editor or terminal, not through the agent: the guard also protects `.claude/settings.json`. | |

**Expected result (Claude Code):** the selftest ends with

```
selftest: all cases passed
```

and exit code 0. The hook was verified with piped `PreToolUse` JSON on 2026-10-09 (Claude Code 2.1.295), not from inside a live session, so the `/hooks` display may differ by version. A hand test from the project root:

```sh
printf '%s' "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$PWD/AGENTS.md\"}}" | .claude/hooks/doctrine-guard.sh
```

prints one line of JSON containing `"permissionDecision": "ask"`. The same command with `STATE.md` instead of `AGENTS.md` prints nothing, because state files stay open.

The hook does not see shell writes (`cat > AGENTS.md`, `sed -i`). For unattended runs, set `DOCTRINE_GUARD_MODE=deny` so no edit waits on a prompt nobody will answer.

## Step 3. Close sessions into the project (5 minutes)

The session-end skill writes what happened into the project's own state file, so the next session of any model starts from the folder and not from chat history.

| Claude Code | Codex |
|---|---|
| `mkdir -p .claude/skills`<br>`cp -R "$OM/core/skills/session-end" .claude/skills/` | `mkdir -p ~/.codex/skills`<br>`cp -R "$OM/core/skills/session-end" ~/.codex/skills/` |
| Installs it for this project. For all projects use `~/.claude/skills/` instead. | Installs it for your user. |

Replace the five double-brace placeholders in the copied `SKILL.md` (they sit in the steps below its Setup table) with this list. Use the same state file name you put in `AGENTS.md`; if it is not `STATE.md`, change the first line.

| Placeholder | Replace with |
|---|---|
| `{{OWNER_FILE}}` | `STATE.md` |
| `{{HANDOFF_FILE}}` | `HANDOFF.md` |
| `{{DECISIONS_LOG}}` | `DECISIONS.md` |
| `{{LESSONS_DIR}}` | `knowledge/` |
| `{{PREFERENCES_FILE}}` | `knowledge/working-style.md` |

Do the replacement yourself, in an editor or with `sed`, not through the agent: after step 2 the guard asks before an agent edits a `SKILL.md`. With `sed`, set `F` to the copied file (Codex: `~/.codex/skills/session-end/SKILL.md`) and run the command for your system:

```sh
F=.claude/skills/session-end/SKILL.md
sed -i '' -e 's|{{OWNER_FILE}}|STATE.md|g' -e 's|{{HANDOFF_FILE}}|HANDOFF.md|g' -e 's|{{DECISIONS_LOG}}|DECISIONS.md|g' -e 's|{{LESSONS_DIR}}|knowledge/|g' -e 's|{{PREFERENCES_FILE}}|knowledge/working-style.md|g' "$F"   # macOS
sed -i -e 's|{{OWNER_FILE}}|STATE.md|g' -e 's|{{HANDOFF_FILE}}|HANDOFF.md|g' -e 's|{{DECISIONS_LOG}}|DECISIONS.md|g' -e 's|{{LESSONS_DIR}}|knowledge/|g' -e 's|{{PREFERENCES_FILE}}|knowledge/working-style.md|g' "$F"      # Linux
```

Run only one of the two. Each `-e` replaces one placeholder everywhere in the file, and `-i` edits the file in place (macOS needs the empty `''` after it). The command does not create `HANDOFF.md`, `DECISIONS.md` or `knowledge/`; the skill creates them when a session first needs them. The table at the top of `SKILL.md` lists the same names without braces, so it stays readable.

If you already use the `skills` command-line installer (`npx skills`), it can install from the published repository instead of copying. That is optional and gives the same folder.

**Expected result:**

```sh
python3 "$OM/scripts/validate_skill.py" .claude/skills/session-end   # Codex: ~/.codex/skills/session-end
grep -c '{{' .claude/skills/session-end/SKILL.md                   # Codex: ~/.codex/skills/session-end/SKILL.md
```

The validator prints `ok session-end` and `All 1 skill(s) valid`. The grep prints `0`; the validator does not check placeholders, so this grep is the check.

## Step 4. Watch a check fail (6 minutes)

gate-selftest runs each registered check on a known-bad and a known-good input. A check that accepts the known-bad input lands in CANNOT-FAIL. Start with the runner's own self-check:

```sh
python3 "$OM/core/gate-selftest/selftest.py" --meta-only
```

Run these from your project folder. Nothing is written there: the runner only reads the repository and prints a report.

**Expected result:** exit code 0 and the line

```
meta triangle holds: always_pass=CANNOT-FAIL, honest_gate=PASS, always_fail=FALSE-ALARM
```

The runner feeds three fake gates through itself: one that always passes, one honest, one that always fails. If it cannot sort those three correctly, it exits 3 and prints no report, because a broken judge would make every later verdict worthless.

Now the example registry, three checks shaped after real incidents, each in a naive and a fixed version:

```sh
python3 "$OM/core/gate-selftest/selftest.py" --registry "$OM/core/gate-selftest/registry.example.yaml"
echo "exit $?"
```

**Expected result:** `exit 1`, with this summary:

```
CANNOT-FAIL: 3
FALSE-ALARM: 0
HARNESS-ERROR: 0
NO-FIXTURE: 0
PASS: 3
```

Exit 1 is the correct result here. The three naive gates (`builtin_shadow_naive`, `status_counter_naive`, `word_split_naive`) accepted their known-bad fixture: each exited 0 on input it should have rejected. Those are the findings. The three fixed versions reject the bad input and accept the good one.

Read the last block of the output too. `status_counter_fixed` lands in PASS with the flag "exit code lies": it prints `open: 3` and still exits 0. Run from a scheduler or as `check && echo OK`, it would behave like a check that always passes. The selftest flags it so you either read its output or fix its exit code.

To register your own checks, copy the example registry and follow [core/gate-selftest/README.md](core/gate-selftest/README.md). Keep your real registry outside this repository's folder, or ignore it in git: it will hold your paths.

## Verify in a live session (about 3 minutes)

The shell checks above prove the files are right. These three prove the agent picks them up. Start a new session in your project, then:

1. Ask "Who decides in this project, and which actions always need my explicit approval?" The answer should name you and list the actions you filled in. If it gives a generic answer, the agent did not load the file: check that `AGENTS.md` sits in the folder you started the session from.
2. Claude Code only: run `/hooks`. It should list a `PreToolUse` hook with matcher `Edit|Write|MultiEdit`. Then ask the agent to add a line to `AGENTS.md`; a permission prompt that starts with `DOCTRINE FILE:` should appear.
3. Ask the agent to list its available skills: `session-end` should be among them. At the end of a real session, say "close the session" and check that your state file got a few new lines.

## Step 5. Your first real job (10 minutes)

The steps above set up rules and checks. This one puts an agent on real work: it turns 12 messy invoice and receipt files into an expense ledger, and a gate you run yourself decides whether the result is done. The data is fictional and the job runs offline.

```sh
rm -rf ~/first-job && mkdir ~/first-job   # starts clean: a leftover ledger.csv from an earlier try would be judged too
cp -R "$OM/examples/first-job/data" "$OM/examples/first-job/TASK.md" ~/first-job/
cd ~/first-job
```

Start Claude Code or Codex in `~/first-job` and paste the prompt from [examples/first-job/README.md](examples/first-job/README.md). The agent reads `TASK.md` and writes `ledger.csv` and `summary.md`. When it says it is done, run the gate in your own terminal. `$OM` must still point at the repository; if you opened a new terminal, run `export OM=/path/to/onemanarmy-ai-agents` first.

```sh
python3 "$OM/examples/first-job/gate/check_ledger.py" ~/first-job
echo "exit $?"
```

**Expected result:** `RESULT: PASS (10 rows, total 4383.30 PLN, duplicate and unreadable file reported)` and `exit 0`. If the gate prints `FAIL:` lines, paste them to the agent, let it fix the files and run the gate again. The data holds three traps: a phone invoice that arrived twice, an invoice in euros, and a scan nobody can read. The agent should not ask you for the exchange rate (`TASK.md` gives it) and should name `skan_0007.txt` in the summary instead of entering an amount for it. The agent saying "done" is a claim; the gate's exit code is the check.

## What next

- Delegating work to subagents or other CLIs: [core/docs/completion-control.md](core/docs/completion-control.md) and [core/docs/controller-worker-contract.md](core/docs/controller-worker-contract.md).
- Deciding what the agent may do without asking: [core/docs/authority-model.md](core/docs/authority-model.md).
- Choosing which check to run for a change: [core/docs/verification-ladder.md](core/docs/verification-ladder.md).
- Choosing how much an agent may do without a prompt, and testing that the limit holds: [tiers/README.md](tiers/README.md).
- Giving your agents the context of your own company in one interview: [onboarding/README.md](onboarding/README.md).
