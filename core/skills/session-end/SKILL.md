---
name: session-end
description: Close a working session into the project that owns the work, with a short update to that project's owner file instead of a handoff document or a global diary. Use when the user says "session end", "wrap up", "close the session" or "done for today". Writes a full handoff only when asked or when state would otherwise be lost.
---

# Session end

Close the session where the work lives. The next agent, of any model, should be able to continue from the project folder alone.

## Setup

Replace the placeholders below once, for your setup. Each one is a path relative to the project root, or an absolute path for files shared across projects. The table writes each name without braces; in the steps below, the same name appears in double braces. Replace those, and the table stays readable.

| Placeholder | What it is | Example |
|---|---|---|
| `OWNER_FILE` | The file in each project that holds its current state | `STATE.md` |
| `HANDOFF_FILE` | One shared file for unfinished work that has no better home | `HANDOFF.md` in your notes folder |
| `DECISIONS_LOG` | Dated one-line decisions that change direction | `decisions.md` in your notes folder |
| `LESSONS_DIR` | Topic files for lessons that apply beyond one project | `knowledge/` in your notes folder |
| `PREFERENCES_FILE` | How the human wants to work with agents | `working-style.md` in your notes folder |

If a project's `AGENTS.md` names a different owner file, that wins.

## Steps

1. **Owner file first.** For each project touched, update `{{OWNER_FILE}}`: what changed, what is verified and how, the next step, and anything waiting on the human. A few lines. Do not restate history the file already holds.
   *Prevents:* the next session rebuilding context from chat logs it cannot see.

2. **Handoff only for loose ends.** `{{HANDOFF_FILE}}` gets an entry only for unfinished active work or an escalation that has no project to live in. Remove entries this session finished. Keep the file under 60 lines.
   *Prevents:* a handoff file that grows into a second, stale copy of every project's state.

3. **Decisions get one dated line.** A decision that changes direction goes to `{{DECISIONS_LOG}}` as one line: date, what, why, pointer to the detail. A cross-project or strategy session with no project owner closes here.
   *Prevents:* a later agent reversing a settled decision because it only found the old plan.

4. **Lessons go to one topic file.** A lesson that will recur goes to the one matching file in `{{LESSONS_DIR}}`. A one-off stays in the project. Nothing goes to a global diary.
   *Prevents:* lessons nobody finds again because they sit in a dated log instead of under their topic.

5. **Corrections about working style edit the old line.** A correction from the human about style, voice or preferences goes to `{{PREFERENCES_FILE}}` as one dated line. If it changes an existing rule, edit that line instead of adding a second one.
   *Prevents:* two contradictory rules where the agent picks whichever it read last.

6. **Stop what you started.** Shut down servers, browsers and background jobs this session launched, unless they are meant to keep running.
   *Prevents:* orphaned processes holding ports, locks or rate limits for the next session.

7. **Tell the human in a few lines:** done, verified how, what is next, what waits on them.

## Why the owner file

A single global session log looks tidy and fails in practice. It mixes every project, grows without bound, and a fresh agent has to read all of it to find the three lines that matter. The project's own owner file is where the next agent looks first, and it stays small because each session overwrites stale lines instead of appending.

## Continuity test

Before writing a handoff, ask: **could a fresh agent of any model continue this work from the project folder alone, after one sentence from the human?**

- If yes, no handoff. The owner file is enough.
- If no, state lives in your head and not on disk. Typical cases: work interrupted midway, an approval with conditions that a later session will act on, or a change of executor where nuance matters. Write the handoff.

A handoff covers: goal, scope, approved actions and their conditions, evidence collected so far, and the next step. It goes next to `{{OWNER_FILE}}` in that project.

## Options

- `--full`: write the project-local handoff described above, even if the continuity test passes.
- `--dry-run`: report where each note would go and write nothing.
