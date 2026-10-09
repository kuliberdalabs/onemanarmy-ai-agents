#!/usr/bin/env python3
"""gate-selftest: negative controls for the checks you already trust.

WHY
  A check that has never failed on a known-bad input has not shown that it
  can fail. Three incidents of one class led to this runner:
    1. A verification step ran a command named `log` under zsh. zsh has a
       builtin `log`, which printed "too many arguments" and nothing else.
       The step counted zero matches and reported clean for three days.
    2. A queue report counted items whose status was "pending". The queue
       only ever used READY, DONE, BLOCKED and PARKED. The counter could not
       show anything except zero, and zero looked like information.
    3. A batch script written for bash ran under zsh. `set -- $row` does not
       split words in zsh, the renderer got an empty argument list, and the
       script exited 0 after producing zero files.
  A positive test never catches this class, because a positive test checks
  exactly the behaviour a check that can only pass already has.

WHAT IT DOES
  For every gate in the registry the runner:
    a) runs it on a KNOWN-BAD fixture and demands a rejection
       (non-zero exit, or a match of `detect_bad` in stdout/stderr),
    b) runs it on a KNOWN-GOOD fixture and demands acceptance.

  Buckets
    PASS           rejects the bad fixture and accepts the good one.
    CANNOT-FAIL    accepted the bad fixture. This is the finding.
    FALSE-ALARM    rejected the good fixture. People learn to ignore it.
    NO-FIXTURE     no command or no fixture pair, so nothing is known.
    HARNESS-ERROR  the gate could not be run (timeout, missing binary).

  A PASS gate in detect mode that printed the finding on the bad fixture and
  still exited 0 is flagged "exit code lies": anything that calls it with
  `&& echo OK`, from a scheduler or from a pipeline that ignores the output
  treats it exactly like a check that always passes.

WHO CHECKS THE CHECKER
  Before reading the registry the runner classifies three built-in fake gates
  from fixtures/_meta/. Each must land in one specific bucket:
    always_pass.sh   -> CANNOT-FAIL
    honest_gate.sh   -> PASS
    always_fail.sh   -> FALSE-ALARM
  One assertion is not enough. A runner that files everything as CANNOT-FAIL
  passes the first leg; a runner that only looks at the bad side passes the
  first two. If any leg fails, the runner exits 3 and reports nothing else.

EXIT CODES
  0  every gate is PASS and the meta triangle holds
  1  at least one gate is CANNOT-FAIL, FALSE-ALARM, NO-FIXTURE or HARNESS-ERROR
  2  usage or registry error
  3  the meta triangle failed: the runner is broken, do not trust any report

USAGE
  python3 selftest.py --registry registry.example.yaml
  python3 selftest.py --meta-only
  python3 selftest.py --registry my-gates.yaml --only status_counter_fixed
  python3 selftest.py --registry my-gates.yaml --json result.json

The registry is a small YAML subset parsed with the standard library (see
parse_registry_yaml), or plain JSON when the file name ends in .json.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(ROOT, "fixtures", "_meta")

PASS = "PASS"
CANNOT_FAIL = "CANNOT-FAIL"
FALSE_ALARM = "FALSE-ALARM"
NO_FIXTURE = "NO-FIXTURE"
HARNESS_ERROR = "HARNESS-ERROR"

ORDER = [CANNOT_FAIL, FALSE_ALARM, HARNESS_ERROR, NO_FIXTURE, PASS]
FAILING_BUCKETS = {CANNOT_FAIL, FALSE_ALARM, HARNESS_ERROR, NO_FIXTURE}

EXIT_OK, EXIT_FINDINGS, EXIT_USAGE, EXIT_RUNNER_BROKEN = 0, 1, 2, 3

KNOWN_KEYS = {
    "id", "what", "protects", "cmd", "bad", "good", "expect_bad", "expect_good",
    "detect_bad", "detect_good", "timeout", "notes", "no_fixture_reason",
}


class RegistryError(Exception):
    pass


# --------------------------------------------------------------- registry --

def _scalar(token: str, where: str):
    """Resolve a plain (unquoted) scalar the way YAML would for simple cases."""
    if token in ("true", "True"):
        return True
    if token in ("false", "False"):
        return False
    if token in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if token[0] in "{}[]&*!|>%@`\"'" or ": " in token or token.endswith(":"):
        raise RegistryError(f"{where}: quote this value: {token!r}")
    return token


def _read_value(s: str, i: int, where: str, in_list: bool = False):
    """Read one value starting at s[i]. Returns (value, next_index)."""
    if s[i] == '"':
        j = i + 1
        while j < len(s):
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == '"':
                try:
                    return json.loads(s[i:j + 1]), j + 1
                except json.JSONDecodeError as exc:
                    raise RegistryError(f"{where}: bad double-quoted string: {exc}") from None
            j += 1
        raise RegistryError(f"{where}: unterminated double-quoted string")
    if s[i] == "'":
        out, j = [], i + 1
        while j < len(s):
            if s[j] == "'":
                if j + 1 < len(s) and s[j + 1] == "'":
                    out.append("'")
                    j += 2
                    continue
                return "".join(out), j + 1
            out.append(s[j])
            j += 1
        raise RegistryError(f"{where}: unterminated single-quoted string")
    if s[i] == "[" and not in_list:
        items, j = [], i + 1
        while True:
            while j < len(s) and s[j] == " ":
                j += 1
            if j >= len(s):
                raise RegistryError(f"{where}: unterminated flow list")
            if s[j] == "]":
                return items, j + 1
            item, j = _read_value(s, j, where, in_list=True)
            items.append(item)
            while j < len(s) and s[j] == " ":
                j += 1
            if j < len(s) and s[j] == ",":
                j += 1
            elif j < len(s) and s[j] == "]":
                continue
            else:
                raise RegistryError(f"{where}: expected ',' or ']' in flow list")
    # plain scalar
    j = i
    stop = ",]" if in_list else ""
    while j < len(s):
        if s[j] in stop:
            break
        if s[j] == "#" and j > i and s[j - 1] == " ":
            break
        j += 1
    return _scalar(s[i:j].strip(), where), j


def _parse_value(text: str, where: str):
    value, j = _read_value(text, 0, where)
    rest = text[j:].strip()
    if rest and not rest.startswith("#"):
        raise RegistryError(f"{where}: unexpected text after value: {rest!r}")
    return value


_KEY = re.compile(r"([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$")


def parse_registry_yaml(text: str, source: str = "registry") -> dict:
    """Parse the YAML subset the registry uses. Anything else is an error.

    Supported: blank lines, comment lines, top-level `version: <int>` and
    `instruments:`, a list of flat mappings under `instruments:` written as
    "- key: value" followed by "  key: value" lines, plain scalars,
    "double-quoted" strings (JSON escapes), 'single-quoted' strings ('' is a
    quote; use these for regexes), and flow lists of scalars: [a, "b c"].
    Nested blocks, anchors and multi-line strings are rejected so the runner
    never guesses what an entry meant.
    """
    doc: dict = {}
    entries = None
    current = None
    item_indent = key_col = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        where = f"{source}:{lineno}"
        line = raw.rstrip()
        body = line.lstrip(" ")
        if not body or body.startswith("#"):
            continue
        if body.startswith("\t") or "\t" in line[: len(line) - len(body)]:
            raise RegistryError(f"{where}: tabs are not allowed for indentation")
        indent = len(line) - len(body)
        if indent == 0:
            m = _KEY.match(body)
            if not m:
                raise RegistryError(f"{where}: expected a top-level key")
            key, value = m.group(1), m.group(2)
            if key in doc:
                raise RegistryError(f"{where}: duplicate top-level key {key!r}")
            if key == "instruments":
                if value not in (None, ""):
                    raise RegistryError(f"{where}: `instruments:` takes a block list")
                entries = doc["instruments"] = []
            elif key == "version":
                doc["version"] = _parse_value(value or "", where)
            else:
                raise RegistryError(f"{where}: unknown top-level key {key!r}")
            current = None
            continue
        if entries is None or (doc and list(doc)[-1] != "instruments"):
            raise RegistryError(f"{where}: indented line outside `instruments:`")
        if body.startswith("- "):
            if item_indent is None:
                item_indent = indent
            elif indent != item_indent:
                raise RegistryError(f"{where}: list items must share one indentation")
            after = body[2:].lstrip(" ")
            key_col = indent + (len(body) - len(after))
            current = {}
            entries.append(current)
            body = after
        elif current is None or indent != key_col:
            raise RegistryError(f"{where}: key is not aligned with its list item")
        m = _KEY.match(body)
        if not m or m.group(2) in (None, ""):
            raise RegistryError(f"{where}: expected `key: value` (nested blocks are not supported)")
        key = m.group(1)
        if key in current:
            raise RegistryError(f"{where}: duplicate key {key!r}")
        current[key] = _parse_value(m.group(2), where)
    if entries is None:
        raise RegistryError(f"{source}: no `instruments:` list found")
    return doc


def load_registry(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    name = os.path.basename(path)
    if path.endswith(".json"):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RegistryError(f"{name}: {exc}") from None
    else:
        doc = parse_registry_yaml(text, name)
    entries = doc.get("instruments") if isinstance(doc, dict) else None
    if not isinstance(entries, list):
        raise RegistryError(f"{name}: `instruments` must be a list")
    seen = set()
    for n, e in enumerate(entries, 1):
        if not isinstance(e, dict) or not isinstance(e.get("id"), str):
            raise RegistryError(f"{name}: entry {n} has no string `id`")
        if e["id"] in seen:
            raise RegistryError(f"{name}: duplicate id {e['id']!r}")
        seen.add(e["id"])
        unknown = set(e) - KNOWN_KEYS
        if unknown:
            raise RegistryError(f"{name}: entry {e['id']!r} has unknown keys: {sorted(unknown)}")
        if "cmd" in e and not (isinstance(e["cmd"], list) and all(isinstance(a, str) for a in e["cmd"])):
            raise RegistryError(f"{name}: entry {e['id']!r}: `cmd` must be a list of strings")
    return entries


# ----------------------------------------------------------------- engine --

def subst(arg: str, mapping: dict) -> str:
    for k, v in mapping.items():
        arg = arg.replace("{" + k + "}", v)
    return arg


def run_once(cmd, workdir, timeout):
    """Run one command. Returns (rc, combined_output, harness_error_or_None)."""
    try:
        p = subprocess.run(
            cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        return p.returncode, (p.stdout or "") + (p.stderr or ""), None
    except subprocess.TimeoutExpired:
        return None, "", f"timeout after {timeout}s"
    except FileNotFoundError as exc:
        return None, "", f"missing binary: {exc.filename or exc}"
    except OSError as exc:
        return None, "", f"OSError: {exc}"


def judge(rc, out, mode, pattern, want_fail):
    """Did the gate behave the way this side of the pair demands?

    want_fail=True demands a rejection, want_fail=False demands acceptance.
    Returns (ok, evidence).
    """
    if mode == "exit":
        rejected = rc != 0
        return (rejected if want_fail else not rejected), f"exit={rc}"
    if mode == "detect":
        if not pattern:
            return False, "detect mode without a pattern in the registry"
        hit = re.search(pattern, out, re.MULTILINE) is not None
        return hit, f"exit={rc} pattern={'HIT' if hit else 'MISS'} /{pattern}/"
    return False, f"unknown judging mode: {mode!r}"


def check_entry(entry, base_dir, timeout_default):
    def fixture(key):
        p = entry.get(key)
        if p is None:
            return None
        return p if os.path.isabs(p) else os.path.join(os.path.abspath(base_dir), p)

    bad, good = fixture("bad"), fixture("good")
    res = {
        "id": entry["id"],
        "what": entry.get("what", ""),
        "protects": entry.get("protects", "?"),
        "notes": entry.get("notes", ""),
        "bucket": None,
        "bad_evidence": "",
        "good_evidence": "",
        "detail": "",
        "exit_code_lies": False,
    }
    if not entry.get("cmd") or bad is None or good is None:
        res["bucket"] = NO_FIXTURE
        res["detail"] = entry.get("no_fixture_reason", "no cmd or no fixture pair")
        return res
    for label, p in (("bad", bad), ("good", good)):
        if not os.path.exists(p):
            res["bucket"] = NO_FIXTURE
            res["detail"] = f"{label} fixture does not exist: {entry.get(label)}"
            return res

    timeout = entry.get("timeout", timeout_default)
    mode_bad = entry.get("expect_bad", "exit")
    mode_good = entry.get("expect_good", "exit")
    pat_bad, pat_good = entry.get("detect_bad"), entry.get("detect_good")

    workdir = tempfile.mkdtemp(prefix="gate-selftest-")
    try:
        common = {"root": ROOT, "here": base_dir, "tmp": workdir}
        outputs = {}
        for side, path, mode, pat, want_fail in (
            ("bad", bad, mode_bad, pat_bad, True),
            ("good", good, mode_good, pat_good, False),
        ):
            cmd = [subst(a, {**common, "input": path}) for a in entry["cmd"]]
            rc, out, err = run_once(cmd, workdir, timeout)
            if err:
                res["bucket"] = HARNESS_ERROR
                res["detail"] = f"{side} fixture: {err}"
                res[f"{side}_evidence"] = err
                return res
            ok, evidence = judge(rc, out, mode, pat, want_fail)
            res[f"{side}_evidence"] = evidence
            res[f"{side}_tail"] = out.strip().splitlines()[-3:]
            outputs[side] = (rc, out, ok)

        rc_bad, _, ok_bad = outputs["bad"]
        _, out_good, ok_good = outputs["good"]
        # A detect_bad pattern that also matches the good output separates nothing.
        nondiscriminating = bool(
            mode_bad == "detect" and pat_bad and re.search(pat_bad, out_good, re.MULTILINE)
        )
        if not ok_bad:
            res["bucket"], res["detail"] = CANNOT_FAIL, "accepted the known-bad fixture"
        elif not ok_good:
            res["bucket"], res["detail"] = FALSE_ALARM, "rejected the known-good fixture"
        elif nondiscriminating:
            res["bucket"] = CANNOT_FAIL
            res["detail"] = ("detect_bad also matches the good fixture's output; "
                             "the pattern separates nothing, so PASS would be fiction")
        else:
            res["bucket"], res["detail"] = PASS, "rejects bad, accepts good"
            res["exit_code_lies"] = mode_bad == "detect" and rc_bad == 0
        return res
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ------------------------------------------------------------ meta triangle --

def meta_entries():
    def gate(script):
        return {
            "cmd": ["sh", os.path.join(META_DIR, script), "{input}"],
            "bad": os.path.join(META_DIR, "bad_input.txt"),
            "good": os.path.join(META_DIR, "good_input.txt"),
        }
    return [
        ({"id": "_meta_always_pass", **gate("always_pass.sh")}, CANNOT_FAIL),
        ({"id": "_meta_honest_gate", **gate("honest_gate.sh")}, PASS),
        ({"id": "_meta_always_fail", **gate("always_fail.sh")}, FALSE_ALARM),
    ]


def run_meta(timeout):
    """Returns (results, broken) where broken lists every leg that missed."""
    results, broken = [], []
    for entry, want in meta_entries():
        r = check_entry(entry, META_DIR, timeout)
        results.append(r)
        if r["bucket"] != want:
            broken.append(f"{r['id']}: expected {want}, got {r['bucket']} ({r['detail']})")
    return results, broken


# ------------------------------------------------------------------ report --

def print_report(results, registry_label):
    print(f"=== gate-selftest: {len(results)} gates, registry {registry_label} ===\n")
    for b in ORDER:
        rows = [r for r in results if r["bucket"] == b]
        print(f"[{b}] {len(rows)}")
        for r in rows:
            flag = "  (exit code lies)" if r["exit_code_lies"] else ""
            print(f"  - {r['id']}  <{r['protects']}>{flag}")
            if r["what"]:
                print(f"      {r['what']}")
            if b in (PASS, CANNOT_FAIL, FALSE_ALARM):
                print(f"      bad fixture:  {r['bad_evidence']}")
                print(f"      good fixture: {r['good_evidence']}")
            if r["detail"]:
                print(f"      -> {r['detail']}")
            if r["notes"]:
                print(f"      note: {r['notes']}")
        print()

    print("=== SUMMARY ===")
    for b in ORDER:
        print(f"  {b}: {len([r for r in results if r['bucket'] == b])}")

    cf = [r for r in results if r["bucket"] == CANNOT_FAIL]
    if cf:
        print("\n### CANNOT-FAIL: gates that could not fail on a known failure ###")
        for r in cf:
            print(f"  * {r['id']}  [{r['protects']}]  evidence: {r['bad_evidence']}")
    lies = [r for r in results if r["exit_code_lies"]]
    if lies:
        print("\n### PASS, but the exit code lies ###")
        print("  These gates print the defect and still exit 0. Called with `&& echo OK`,")
        print("  from a scheduler or from a pipeline that ignores output, each behaves")
        print("  like a gate that always passes. Read the output or fix the exit code.")
        for r in lies:
            print(f"  * {r['id']}  [{r['protects']}]")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default=os.path.join(ROOT, "registry.yaml"),
                    help="registry file (.yaml subset or .json); default: registry.yaml here")
    ap.add_argument("--json", dest="json_out", default=None, help="write results as JSON")
    ap.add_argument("--only", default=None, help="comma-separated gate ids")
    ap.add_argument("--protects", default=None, help="filter on the `protects` field")
    ap.add_argument("--timeout", type=int, default=60, help="seconds per gate run")
    ap.add_argument("--meta-only", action="store_true",
                    help="run only the built-in meta triangle")
    args = ap.parse_args(argv)

    meta_results, broken = run_meta(args.timeout)
    if broken:
        print("!!! META TRIANGLE FAILED: the runner is broken. No report is trustworthy.")
        for m in broken:
            print(f"  - {m}")
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as fh:
                json.dump({"meta": meta_results, "meta_broken": broken, "results": []},
                          fh, indent=2, ensure_ascii=False)
        return EXIT_RUNNER_BROKEN
    print("meta triangle holds: always_pass=CANNOT-FAIL, honest_gate=PASS, always_fail=FALSE-ALARM")
    if args.meta_only:
        return EXIT_OK
    print()

    if not os.path.exists(args.registry):
        print(f"selftest: registry not found: {args.registry}\n"
              f"  copy registry.example.yaml to registry.yaml, or pass --registry",
              file=sys.stderr)
        return EXIT_USAGE
    try:
        entries = load_registry(args.registry)
    except (RegistryError, OSError) as exc:
        print(f"selftest: registry error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    only = {x.strip() for x in args.only.split(",")} if args.only else None
    if only:
        missing = only - {e["id"] for e in entries}
        if missing:
            print(f"selftest: unknown ids in --only: {sorted(missing)}", file=sys.stderr)
            return EXIT_USAGE
    selected = [e for e in entries
                if (not only or e["id"] in only)
                and (not args.protects or e.get("protects") == args.protects)]
    if not selected:
        print("selftest: no gates selected; an empty run proves nothing", file=sys.stderr)
        return EXIT_USAGE

    base_dir = os.path.dirname(os.path.abspath(args.registry))
    results = [check_entry(e, base_dir, args.timeout) for e in selected]
    print_report(results, os.path.basename(args.registry))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"meta": meta_results, "meta_broken": [], "results": results},
                      fh, indent=2, ensure_ascii=False)
        print(f"\njson -> {args.json_out}")

    return EXIT_FINDINGS if any(r["bucket"] in FAILING_BUCKETS for r in results) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
