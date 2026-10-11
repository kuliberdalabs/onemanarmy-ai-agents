# Negative controls: a check must fail once before its green counts

*Updated: 2026-10-11 | scope: every gate, lint, audit or report an agent or a person relies on to say "clean" | tool: [`core/gate-selftest/`](../gate-selftest/)*

A check that has only ever passed has told you nothing about whether it can fail. Before we trust a gate's "clean", we run it on an input we know is broken and require it to say so. That run is the negative control. This page explains why, shows three incidents where the missing control cost us days, and describes how to register a gate.

## The failure class

All three incidents below share one shape: a check that could only pass. Each ran, exited 0 and printed something that looked like a result. None of them had looked at the thing it was supposed to check.

A positive test cannot catch this. A positive test feeds the check good input and expects green, and a check that can only pass produces green every time. The only test that separates an honest check from a blind one is a known-bad input.

## Three incidents

**1. A shell builtin shadowed the command.** A verification step ran `log show ... | grep ...` to confirm that a fix had stopped a class of system prompts. It ran under zsh, which has its own builtin `log`. The builtin printed `too many arguments` to stderr and nothing to stdout, `grep` found zero matches, and the step exited 0. The fix was reported working for three days. It had never been checked.
Reproducer: [`core/pitfalls/zsh-log-builtin.sh`](../pitfalls/zsh-log-builtin.sh). Example gate: `builtin_shadow_naive`.

**2. A counter counted a status that never existed.** A queue index counted open items with `awk '$7 == "pending"'`. Items in that queue only ever carried READY, DONE, BLOCKED or PARKED. With three open items (READY, READY, BLOCKED), the index line read `0 pending`. The counter could not show anything but zero, and zero looked like information.
Example gate: `status_counter_naive`.

**3. Word splitting that bash does and zsh does not.** A batch render script, written with bash habits, ran under zsh. `set -- $row` does not split an unquoted variable in zsh, so the renderer received an empty argument list. The script exited 0 after rendering zero files.
Reproducer: [`core/pitfalls/zsh-no-wordsplit.sh`](../pitfalls/zsh-no-wordsplit.sh). Example gate: `word_split_naive`.

When we first ran negative controls across our own gates (2026-07-31, 21 gates), 13 had a fixture pair. Of those 13, one could not fail at all: the counter from incident 2, reproduced exactly. Four detected the defect and printed it, then exited 0 anyway. The other eight passed cleanly. The remaining eight gates had no fixture pair, so we knew nothing about them.

## Rules

| Rule | Failure it prevents |
| --- | --- |
| Every gate gets two fixtures: a known-bad input it must reject and a known-good input it must accept. | A gate that always passes, which looks identical to a working gate on good days. |
| The bad fixture comes from an artifact that really failed. Keep the broken file, log or manifest when the incident happens. | A made-up fixture tests the author's imagination. The real failure usually has a shape nobody would invent (a status nobody used, a builtin nobody knew about). |
| The good fixture differs from the bad one only by the defect. | A PASS that tells you the gate reacts to something, without telling you it reacts to the defect. |
| A gate that rejects the good fixture is a finding too (FALSE-ALARM). | A gate that always complains gets switched off, and then nothing checks that path. |
| A detect pattern must not match the good output. | A regex broad enough to match both sides looks like evidence and separates nothing. |
| A gate whose output reports the defect but whose exit code is 0 gets flagged. | `gate && deploy`, a scheduler or a pipeline that ignores output treats it as a gate that always passes. |
| A gate with no fixture pair counts as unknown, never as clean. | Coverage numbers that include gates nobody has ever seen fail. |
| The runner proves itself first, on fake gates with known outcomes. | A broken runner reporting every gate as PASS, which looks like a good day. |

## Buckets

`gate-selftest` puts every gate into one bucket:

| Bucket | Meaning | Exit |
| --- | --- | --- |
| PASS | Rejects the bad fixture, accepts the good one. | 0 |
| CANNOT-FAIL | Accepted the known-bad fixture. This is what the tool exists to find. | 1 |
| FALSE-ALARM | Rejected the known-good fixture. | 1 |
| NO-FIXTURE | No command or no fixture pair. Nothing is known. | 1 |
| HARNESS-ERROR | The gate could not run or died without a verdict: missing binary, timeout, killed by a signal, exit 126 or 127 (a shell could not run a command), exit 128+N (a shell reporting a child killed by signal N), a Python traceback on stdout or stderr, or in exit mode a non-zero exit that the registry does not declare as a rejection (`reject_exit`, default 1) or that follows the interpreter's own error line (`zsh:1: division by zero`); in detect mode a pattern whose only match is that line. A gate that dies has not rejected anything, even when its output matches a detect pattern; in detect mode only a match printed before the traceback counts. | 1 |

PASS gates can carry an **exit code lies** flag: in detect mode, the gate printed the finding on the bad fixture and still exited 0. The detection works, and whatever called the gate never hears about it. The flag does not change the exit code, because some reports are meant to exit 0. It tells you not to chain them with `&&`.

## Who checks the checker

The runner's own logic can be wrong in ways that make every report look healthy. Before it reads your registry, it classifies three fake gates whose correct buckets are fixed:

| Fake gate | Behaviour | Must land in |
| --- | --- | --- |
| `always_pass.sh` | exits 0 on everything | CANNOT-FAIL |
| `honest_gate.sh` | rejects input containing `BROKEN` | PASS |
| `always_fail.sh` | exits 1 on everything | FALSE-ALARM |

One leg is not enough. A runner that files everything as CANNOT-FAIL passes the first. A runner that only judges the bad side of each pair passes the first two. If any leg lands wrong, the runner exits 3 and prints no report. The test suite breaks the runner on purpose (a judge that always approves, one that only reads the bad side, one with inverted exit codes, a missing meta fixture) and requires exit 3 every time.

## How to add a gate

1. **Keep the failure.** When a gate misses something, or something breaks that a gate should have caught, save the real broken artifact before it is fixed or deleted. Trim it to the smallest file that still shows the defect.
2. **Make the good twin.** Copy the bad fixture and remove only the defect.
3. **Register it.** Add an entry to your registry (copy `core/gate-selftest/registry.example.yaml`):

   ```yaml
   instruments:
     - id: invoice_total_check
       what: "Reject invoices whose line items do not add up to the total."
       protects: money
       cmd: [python3, "{here}/checks/invoice_total.py", "{input}"]
       bad: fixtures/invoice-total/bad_rounding.json
       good: fixtures/invoice-total/good_rounding.json
   ```

   Use `expect_bad: detect` with a `detect_bad` regex when the gate reports findings in its output instead of its exit code. Use it too when a crash and a rejection share an exit code: in exit mode, a plain non-zero exit counts as a rejection.
4. **Run it and read the bucket.**

   ```sh
   python3 core/gate-selftest/selftest.py --registry path/to/registry.yaml
   ```

   A new gate that lands in CANNOT-FAIL on its first run is the expected outcome surprisingly often. Fix the gate, keep the fixture.
5. **No fixture yet?** Register the gate anyway with `no_fixture_reason`. It shows up as NO-FIXTURE and keeps the run at exit 1 until someone supplies the pair, so the gap stays visible.

## Limits

- The runner checks the gate against the fixtures you give it. A gate can pass every fixture and still miss a failure shape nobody has recorded yet.
- Shell behaviour depends on the shell. Run the selftest under the same shell and versions the gate uses in production; the example gates call `zsh` explicitly for that reason.
- Gates that need network, credentials or live services need an adapter that feeds them a fixture. Point the adapter at a copy, never at live state.
