# Eval ledger schema

Every folder under `evals/` is one dated field note: a `README.md` with the reading and a `ledger.csv` with one row per worker run. The CSV is the evidence. The prose is an interpretation of it, and a reader should be able to recompute every number in the prose from the CSV.

## Columns

Fixed, in this order. A ledger with a missing, renamed or reordered column is not comparable with the others and gets fixed before it ships.

| Column | Meaning | Allowed values |
|---|---|---|
| `date` | Day the run happened | `YYYY-MM-DD` |
| `task` | What the worker was asked to do, as `<task-class>/<slug>` | e.g. `labelling/blind-70` |
| `model_id` | Model id exactly as the CLI reported it | e.g. `gpt-6-sol` |
| `effort` | Reasoning effort passed to the CLI | `low`, `medium`, `high`, or what the CLI accepts |
| `cli` | CLI name and exact version | e.g. `codex-cli 0.157.1` |
| `sandbox` | Sandbox mode the run used | e.g. `workspace-write`, `read-only` |
| `wall_s` | Wall-clock seconds from start to exit | integer |
| `input_tokens` | Input tokens as the CLI reported them, cached included | integer |
| `cached_input_tokens` | The cached part of `input_tokens` | integer |
| `output_tokens` | Output tokens as the CLI reported them | integer |
| `result` | What the controller decided after checking the real artifact | `accepted`, `corrected`, `rejected`, `superseded` |
| `controller_corrections` | Items the controller changed or overruled before using the output | integer, `n/a` for `rejected`, or `unknown` |
| `accepted_unchanged` | Was the output used exactly as the worker delivered it | `yes`, `no` |

`result` values:

- `accepted`: checked on the real artifact and used as delivered.
- `corrected`: used after the controller fixed or overruled specific items; the count goes in `controller_corrections`.
- `rejected`: not used. `controller_corrections` is `n/a`, and the README says why.
- `superseded`: correct as far as it went, then replaced by a later run that builds on it. The later run is its own row.

A note may append extra columns after these thirteen when it needs them, for example `run_id` and `score` in a note that grades many runs. The thirteen stay first and in order, the extra columns are named in the note's README, and ledgers without them stay valid. Summing code skips `unknown` and `n/a` cells instead of reading them as zero.

No cell is ever blank. A value nobody measured is written `unknown`. A blank reads as zero or as "fine" once it reaches a spreadsheet, and that is the same mistake as a worker reporting done without evidence.

Fields the CLI reports but the schema leaves out (reasoning tokens, command counts, exit codes) can be quoted in the README when they explain a result. They stay out of the CSV so that ledgers from different tools keep the same shape.

## Rules

**The result column holds the controller's verdict.** A worker's own test suite can be green while the real system regresses: in the first eval here a worker's fix passed 35/35 of its own tests and caused 8 regressions on 25 protected cases when run against the real model. Recording the worker's claim would have logged that as a success.

**Tokens from different CLIs are not 1:1 comparable.** Claude Code and Codex CLI do not report cached input, per-call overhead and reasoning tokens the same way, and the fixed overhead depends on what each tool loads per call (instruction files, hooks). In the Codex runs here that overhead was about 24k input tokens per call before any work started. Compare token counts between models on the same CLI and version only. Comparing totals across CLIs produces confident cost conclusions that are wrong.

**Cached and uncached input are both recorded.** Most input on long agent runs is cached: 14.9M input tokens in one model's runs here were 0.54M once the cached part is removed. Reporting only the total overstates cost wherever cached input is billed lower, and reporting only the uncached part hides how much context a worker re-read and how long that took.

**Every README opens with an as-of header.** It carries the date measured, CLI name and version, model ids, the domain, `n`, a confidence level, and one line of unknowns. Model and CLI behaviour changes within weeks. A note without a date and version gets read as current long after it stopped being true.

**`n` is stated, and so is how pairs are counted.** One run per cell on one day is an anecdote with numbers. Saying so lets the reader weigh it; leaving it out lets a single run pass for a measurement.

**Confidence is one of `low`, `medium`, `high`, with the reason.** `high` needs repeated runs across more than one domain. Nothing in this folder qualifies yet.

**The unknowns line names what was not measured.** For example: one run per cell so no variance, one language, effort not swept. Without it, the absence of a problem in the data reads as evidence that there is none.

**The conclusion is "which worker for which task class". No leaderboards.** A ranking gets quoted without its `n`, domain and date, and then decides model choice for task classes nobody measured. Write per task class: which model, at which effort, with which controller check, and where neither should be used.

**Raw rows ship beside the prose.** Totals in the README are recomputed from `ledger.csv` and the README says they were. A summary that cannot be recomputed is a claim, and this repo does not trust claims.

## Recomputing totals

```sh
python3 -c '
import csv, collections, sys
t = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for r in csv.DictReader(open(sys.argv[1])):
    s = t[r["model_id"]]
    s[0] += 1; s[1] += int(r["wall_s"]); s[2] += int(r["input_tokens"])
    s[3] += int(r["input_tokens"]) - int(r["cached_input_tokens"]); s[4] += int(r["output_tokens"])
for m, (n, w, i, u, o) in sorted(t.items()):
    print(f"{m}: runs={n} wall_s={w} input={i} uncached={u} output={o}")
' evals/2026-09-27-codex-workers/ledger.csv
```
