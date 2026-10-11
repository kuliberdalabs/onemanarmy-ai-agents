# Onboarding

Onboarding turns a company owner's answers into the agent's company context. That context is what makes a generic pack specific.

A pack for agents, such as a morning brief or a voice-note-to-report playbook, is written for nobody in particular. It says "summarize what matters". Whether that means three lines at 6 a.m. in a chat app or a table in a weekly document, which folder is the source of truth, which people are waiting on an answer and which data must never be stored, none of that is in the pack. It is in the owner's head. Onboarding gets it out in one conversation and writes it down in a form every agent can read.

## What is here

| Path | What it is |
|---|---|
| `questionnaire.en.md`, `questionnaire.pl.md` | The 18-question interview, in English and Polish. Each question lists the placeholders its answer fills. |
| `START.md` | The first-run script: one question at a time, a summary the owner accepts, and only then files. |
| `synthesize-profile.md` | How answers become files: a fill table, rules for what is a fact and what is a guess, and the archive-then-write procedure. |
| `context-template/` | Skeleton files with `{{PLACEHOLDER}}` markers: `USER.md`, `company.md`, `decisions.md`, and the `knowledge/`, `memory/` and `inbox/` READMEs. |
| `check_placeholders.py` | Lists every placeholder that is still unfilled. Stdlib only. |

## How to run it

1. Copy `context-template/` into your agent's workspace. This is the context folder.
2. Point your agent's instruction file (`AGENTS.md`, `CLAUDE.md`, or whatever your tool reads) at `USER.md` and `company.md`, and tell it to read both at the start of a session. Until the interview is done they contain placeholders, so the agent should treat them as empty.
3. Give the agent `START.md` and let it interview the owner in the owner's language.
4. The agent drafts the profile, shows a summary of at most twelve lines, and waits.
5. After an explicit accept it archives any existing files, writes the new ones, and runs:

   ```sh
   python3 onboarding/check_placeholders.py path/to/context-folder
   ```

   An exit code of 0 means every file was read and no placeholders are left. Exit 1 lists each unfilled placeholder as `<file>:<line>: {{NAME}}`. Exit 2 means the check could not finish: a path is missing, no text file was found, or a file or folder could not be read or is not UTF-8 text. Each one is named on stderr; fix it and run again. For a file saved in another encoding, such as cp1250, the checker prints:

   ```text
   error: <context folder>/USER.md is not UTF-8 text (byte 0xb3 on line 1); save it as UTF-8 and run again
   error: could not check 1 path(s), so the result is incomplete (N scanned)
   ```

   A file it cannot open gives `error: cannot read <file>: <reason>` (for example `Permission denied`), and a folder it cannot list gives `error: cannot list <folder>: <reason>`. Placeholders found in the readable files are still listed, but the exit code is 2, not 1.
6. The agent runs the five acceptance cases the owner gave in Q12. The owner judges each result.

The owner's name is the placeholder `{{OWNER_NAME}}`. Fill it once when you copy the template (a find and replace is enough; keep the files saved as UTF-8). The Polish text never inflects it, and addresses the owner in the second person instead.

## Why it is built this way

The same ideas as the rest of this repository, applied to the first hour of an agent's life.

- **A saved profile is a claim.** Nothing is written until the owner accepts a summary. Silence and partial corrections do not count as acceptance.
- **Facts and guesses are kept apart.** Every item is `said`, `inferred` or `unknown`. Inferences stay in their own section, marked, and are hypotheses until the owner confirms them. A guess that sits in a context file as a fact is read as a fact for the rest of the project.
- **The gate can fail.** The template ships with every placeholder unfilled, so `check_placeholders.py` exits 1 on it. The test suite asserts that, then fills every placeholder and asserts exit 0. A scan that finds nothing in a mistyped folder exits 2 instead of passing. An unreadable or non-UTF-8 file also exits 2.
- **Done means the owner's cases pass.** Q12 asks for five real cases and the result the owner expects for each. The first version of the assistant is judged on those, and the runs are logged in `decisions.md`.
- **Overwriting is reversible.** Existing files are copied to `archive/<timestamp>/` first, and the archive is not edited afterwards.
- **Sensitive data is a stated boundary.** Q9 records categories the agent must not store. Secrets pasted during the interview are not copied anywhere.

## Limits

- The interview records what the owner says. It does not check it.
- The never-store list is an instruction to the agent. It is not enforcement. If a category is truly off limits, also keep it out of the folders the agent can read.
- `check_placeholders.py` finds markers only. It cannot tell whether a filled value is good. That is what the acceptance cases are for.
- A file counts as binary, and is skipped and counted, only when it contains a NUL byte and does not start with a UTF-16 byte order mark. Text in any encoding other than UTF-8 is an error, not a skip. Linked folders, such as a shared `knowledge/` linked into a profile, are followed and checked, each real folder once.
- The questionnaire was written for one-person or very small companies. For a larger team, run it once per person and keep one `company.md`.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

This runs the whole suite. `tests/test_onboarding.py` (25 tests) covers the checker, the template against its fill table, and the consistency of the two questionnaires. `tests/test_checkers.py` (37 tests) covers the checker on files it cannot read or decode, and the skill validator in `scripts/validate_skill.py`.
