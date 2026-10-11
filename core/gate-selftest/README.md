# gate-selftest

Answers one question about each check you rely on: **can it fail at all?**

Each registered gate runs twice, once on a known-bad fixture it must reject and once on a known-good fixture it must accept. Gates that pass the bad fixture land in CANNOT-FAIL. The reasoning and the incidents behind it are in [`docs/negative-controls.md`](../docs/negative-controls.md).

Python 3.11+, standard library only. The example gates need `sh` and `zsh`.

## Run it

The runner checks itself first (the meta triangle) and exits 0 or 3:

```sh
python3 core/gate-selftest/selftest.py --meta-only
```

The example registry holds three naive gates that cannot fail and three fixed ones, so it exits 1 on purpose:

```sh
python3 core/gate-selftest/selftest.py --registry core/gate-selftest/registry.example.yaml
```

Your own gates:

```sh
python3 core/gate-selftest/selftest.py --registry path/to/registry.yaml
```

A gate that died has not rejected anything. That run lands in HARNESS-ERROR on either fixture, with a report line naming the cause: the gate was killed by a signal, it exited 126 or 127 (a shell could not run a command), it exited 128+N where N is a signal number (a shell reporting a child killed by signal N), or it printed a Python traceback (`Traceback (most recent call last):`) on stdout or stderr. A `detect_bad` pattern that matches the crash output does not change that. In exit mode only exit 1 counts as a rejection; any other non-zero exit lands in HARNESS-ERROR as a gate that errored before it judged its input (awk, grep and diff exit 2 on trouble). A gate that rejects with another code declares it with `reject_exit`, for example `reject_exit: [1, 2]`. Even a declared code is not a rejection when the output (stderr or stdout) carries the interpreter's own error line, such as `zsh:1: division by zero`, `gate.sh: line 2: x: unbound variable` or `awk: division by zero`: that gate crashed before it judged its input. In detect mode the same lines are never a verdict: a pattern whose only match is the interpreter's own error lands in HARNESS-ERROR. The runner recognises error lines that name the shell, a script (named in `cmd` or ending in `.sh`, `.zsh`, `.bash` or `.ksh`), a zsh function with its line number, or awk. A crash that exits with the rejection code and prints none of these (a gate that discards stderr, a one-line shell function) still looks like a rejection, so use `expect_bad: detect` with a pattern for a verdict line only your gate prints, never an interpreter message, whenever a crash and a rejection can share an exit code. A gate that prints a traceback on purpose when it rejects should use detect mode, with a pattern for a verdict line it prints before the traceback (stdout is read before stderr); a match inside the traceback is not a verdict.

| Flag | Value | What it does |
| --- | --- | --- |
| `--registry` | path to a `.yaml` or `.json` registry | Gates to test. Default: `registry.yaml` next to `selftest.py`. Fixture paths resolve against the registry's directory. |
| `--only` | comma-separated gate ids | Runs only those gates. The meta triangle always runs. |
| `--protects` | a tag used in the registry | Runs only gates with that `protects` value. |
| `--json` | output file path | Writes every result, including the meta legs, as JSON. |
| `--timeout` | seconds, default 60 | Per run of a gate. A timeout lands in HARNESS-ERROR. |
| `--meta-only` | none | Checks the runner and stops. |

The runner does not modify fixtures or gates; each run gets a scratch directory (`{tmp}`) that is deleted afterwards. It does not schedule itself or install anything.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Every selected gate is PASS and the meta triangle holds. |
| 1 | At least one gate is CANNOT-FAIL, FALSE-ALARM, NO-FIXTURE or HARNESS-ERROR. |
| 2 | Usage or registry error: unreadable file, unknown key, empty selection. |
| 3 | The meta triangle failed. The runner is broken; no report is printed. |

## What the example registry shows

| Gate | Incident class | Bucket |
| --- | --- | --- |
| `builtin_shadow_naive` | zsh's builtin `log` runs instead of the project's `log` helper; zero lines read, zero errors reported | CANNOT-FAIL |
| `builtin_shadow_fixed` | `command log`, helper exit checked, zero lines is unknown | PASS |
| `status_counter_naive` | counts status `pending`, which the queue never uses | CANNOT-FAIL |
| `status_counter_fixed` | counts READY and BLOCKED, stops on unknown statuses | PASS, exit code lies |
| `word_split_naive` | `set -- $row` under zsh, so the status field is always empty | CANNOT-FAIL |
| `word_split_fixed` | splits with `read`, empty manifest is unknown | PASS |

`word_split_naive` lands in PASS when run with `bash` or `sh`. The defect belongs to the shell the script runs under, which is why the registry names the interpreter in `cmd`. Writing `word_split_fixed` produced one more receipt: the first draft named a variable `status`, which is read-only in zsh. That draft dies on every input under zsh. The runner of that day filed it as FALSE-ALARM; the current runner recognises zsh's own error line (`read-only variable: status`) and files it as HARNESS-ERROR.

## Registry format

A small YAML subset, parsed with the standard library so the tool has no dependencies. The original version of this runner used PyYAML; this one does not.

- top-level keys `version` and `instruments` only
- one flat mapping per gate (`- key: value`, then `  key: value`)
- plain scalars, `"double-quoted"` strings with JSON escapes, `'single-quoted'` strings (use these for regexes)
- flow lists of scalars: `[zsh, -f, "{here}/gate.zsh", "{input}"]`

Nested blocks, anchors, multi-line strings, unknown keys and duplicate ids are errors (exit 2). A file ending in `.json` is read as JSON with the same fields.

Fields: `id`, `what`, `protects`, `cmd`, `bad`, `good`, `expect_bad`, `expect_good`, `detect_bad`, `detect_good`, `reject_exit`, `timeout`, `notes`, `no_fixture_reason`. Placeholders in `cmd`: `{input}`, `{here}`, `{root}`, `{tmp}`. Field details are in the header of [`registry.example.yaml`](registry.example.yaml).

## Gates without a CLI

Some checks are library functions, or have their input path hard-coded. Wrap them in a small adapter script that takes the fixture path as its first argument, calls the check, and exits non-zero when the check rejects the input. If the check writes files, the adapter copies the check and its input into `{tmp}` and runs the copy, so a selftest run never touches live state. If the adapter has to patch a path inside the check, it verifies the patch took and exits 2 when it did not, so a changed check shows up as an error instead of a silent PASS.

## Layout

```
selftest.py              runner
registry.example.yaml    three example gates, naive and fixed
fixtures/_meta/          fake gates for the meta triangle, plus their good/bad input
fixtures/examples/       the example gates and their fixture pairs
```

Tests: `python3 -m unittest discover -s tests` from the repository root.
