# First job: a month of receipts into a ledger

The job, in five lines:

- 12 text files from September 2026: invoices, receipts, a forwarded email, OCR text from scans. The data is fictional.
- Amounts are written the Polish way (`1 230,00 zł`, `1.476,00 zł`, `312,47`), with netto, VAT and brutto lines side by side.
- One phone invoice arrived twice, one invoice is in euros, and one scan cannot be read.
- The agent writes `ledger.csv` (one row per real expense) and `summary.md` (five lines for the owner).
- A gate you run yourself decides whether it is done.

Expected time: about 10 minutes, most of it the agent working. It runs offline with Claude Code or Codex.

## Why this job

It is the kind of work a one-person business hands an agent on day one, and it has the three traps that make agent output costly when nobody checks it: a duplicate that inflates the total, a number in a foreign format, and a file where the honest answer is "I cannot read this". The agent's own report can sound finished either way. The gate is what tells you.

## Run it

**1. Copy the job into a fresh folder** outside this repository, so the agent cannot read the answer key in `gate/`:

```sh
rm -rf ~/first-job && mkdir ~/first-job   # starts clean: a leftover ledger.csv from an earlier try would be judged too
cp -R "$OM/examples/first-job/data" "$OM/examples/first-job/TASK.md" ~/first-job/
cd ~/first-job
```

`OM` is the path to this repository, as in [START-HERE.md](../../START-HERE.md). The answer key lives in `gate/`, which stays in the repository and is not copied; the prompt below also tells the agent to stay in the new folder.

**2. Start your agent in that folder** (`claude` or `codex`) and paste this prompt:

```
Read TASK.md in this folder and do the task it describes. Work only in this
folder; do not read folders outside it. Write ledger.csv and summary.md in this
folder. Do not guess values you cannot read; report them as TASK.md says. When you finish, list the files you wrote and anything you were
unsure about.
```

**3. Run the gate yourself** when the agent says it is done. `$OM` must still point at the repository; after opening a new terminal, run `export OM=/path/to/onemanarmy-ai-agents` first:

```sh
python3 "$OM/examples/first-job/gate/check_ledger.py" ~/first-job
echo "exit $?"
```

## What "done" means

Done is the gate printing `RESULT: PASS` and `exit 0` when you run it, not the agent saying it finished. A pass means: 10 rows, a total of 4383.30 PLN, the phone invoice counted once, no row for the unreadable scan, and a five-line summary that names both problems.

A failed run prints one `FAIL:` line per problem, for example:

```
FAIL: duplicate counted twice: fwd_faktura_telefon.txt and telefon_wrzesien_faktura.txt are the same invoice (FV/T/2026/88412); keep one row
FAIL: total: amount_pln adds up to 4506.30, expected 4383.30
RESULT: FAIL (4 findings)
```

Paste those lines back to the agent and ask it to fix the files, then run the gate again. What you should not see: the agent asking you for the exchange rate (TASK.md gives it) or entering an amount for `skan_0007.txt` (it should name that file in the summary and leave it out).

## Recorded runs

On 2026-10-10 the job ran once with Codex CLI 0.160.0 (`codex exec`, default model, about 70 seconds) and once with Claude Code (`claude -p --model haiku`), each with the prompt above in a fresh copy of the folder. Both passed the gate on the first round. Both runs were on the maintainer's machine, with its global agent instructions loaded, so a clean setup may behave differently. n is 1 per agent.

## Check the checker

A gate that has never failed on a known-bad input has not shown it can fail. This one ships with two such inputs in `gate/fixtures/`: `bad/` books the forwarded phone invoice as a second expense, and `bad-guessed/` enters a made-up amount for the unreadable scan. `good/` is a reference solution. Run gate-selftest on them:

```sh
python3 "$OM/core/gate-selftest/selftest.py" --registry "$OM/examples/first-job/gate/registry.yaml"
echo "exit $?"
```

**Expected result:** `exit 0` and `PASS: 2`. That is the opposite of Step 4 in START-HERE, where exit 1 was correct because the example registry holds naive gates on purpose. Here both entries should reject their bad fixture by its specific finding line and accept the good one.

## Make it yours

The pattern carries over to any repeatable job: a folder of inputs, a brief the agent reads (`TASK.md`), an output format strict enough to check, and a gate with a known-good and a known-bad example registered in gate-selftest. For your own receipts the gate cannot hold an answer key, so check what does not depend on the month: every row points to a real file, no invoice number appears twice, the total equals the sum of rows, and every file is either in the ledger or named in the summary.

## Files

| Path | What it is |
|---|---|
| `TASK.md` | The brief the agent reads: output format, rules, fixed EUR rate |
| `data/` | The 12 input files |
| `gate/check_ledger.py` | The acceptance gate, standard library only |
| `gate/fixtures/good/` | Reference `ledger.csv` and `summary.md` |
| `gate/fixtures/bad/`, `gate/fixtures/bad-guessed/` | Known-bad outputs the gate must reject |
| `gate/registry.yaml` | gate-selftest entries for those fixtures |
