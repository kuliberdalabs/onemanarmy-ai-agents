"""Tests for core/gate-selftest/selftest.py (stdlib unittest; pytest also runs them).

    python3 -m unittest discover tests -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, "core", "gate-selftest")
SELFTEST = os.path.join(TOOL, "selftest.py")
EXAMPLE_REGISTRY = os.path.join(TOOL, "registry.example.yaml")

_spec = importlib.util.spec_from_file_location("selftest", SELFTEST)
selftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(selftest)


def run_main(*argv):
    """Run selftest.main in-process. Returns (exit_code, stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = selftest.main(list(argv))
    return code, buf.getvalue()


def run_cli(script, *argv):
    p = subprocess.run([sys.executable, script, *argv], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout + p.stderr


class MetaTriangle(unittest.TestCase):
    def test_intact_runner_exits_0(self):
        code, out = run_cli(SELFTEST, "--meta-only")
        self.assertEqual(code, 0, out)
        self.assertIn("meta triangle holds", out)

    def test_each_leg_lands_in_its_bucket(self):
        results, broken = selftest.run_meta(30)
        self.assertEqual(broken, [])
        self.assertEqual(
            {r["id"]: r["bucket"] for r in results},
            {"_meta_always_pass": "CANNOT-FAIL", "_meta_honest_gate": "PASS",
             "_meta_always_fail": "FALSE-ALARM"},
        )


class BrokenRunner(unittest.TestCase):
    """Each sabotage below is a plausible runner bug. Every one must exit 3."""

    def test_judge_that_always_approves(self):
        with mock.patch.object(selftest, "judge", lambda *a, **k: (True, "sabotaged")):
            code, out = run_main("--meta-only")
        self.assertEqual(code, 3, out)
        self.assertIn("_meta_always_pass: expected CANNOT-FAIL, got PASS", out)

    def test_judge_that_only_reads_the_bad_side(self):
        real = selftest.judge

        def bad_side_only(rc, out, mode, pattern, want_fail):
            return real(rc, out, mode, pattern, want_fail) if want_fail else (True, "skipped")

        with mock.patch.object(selftest, "judge", bad_side_only):
            code, out = run_main("--meta-only")
        self.assertEqual(code, 3, out)
        self.assertIn("_meta_always_fail: expected FALSE-ALARM, got PASS", out)

    def test_judge_that_inverts_exit_codes(self):
        def inverted(rc, out, mode, pattern, want_fail):
            rejected = rc == 0
            return (rejected if want_fail else not rejected), f"exit={rc}"

        with mock.patch.object(selftest, "judge", inverted):
            code, _ = run_main("--meta-only")
        self.assertEqual(code, 3)

    def test_sabotaged_copy_on_disk_exits_3(self):
        """A real process with a broken judge, not a mock: copy, break, run."""
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(os.path.join(TOOL, "fixtures", "_meta"),
                            os.path.join(tmp, "fixtures", "_meta"))
            with open(SELFTEST, encoding="utf-8") as fh:
                src = fh.read()
            sentinel = "rejected = rc != 0"
            # If the sentinel moved, this test must fail loudly, not pass on an unbroken copy.
            self.assertIn(sentinel, src)
            broken = os.path.join(tmp, "selftest.py")
            with open(broken, "w", encoding="utf-8") as fh:
                fh.write(src.replace(sentinel, "rejected = False"))
            code, out = run_cli(broken, "--meta-only")
        self.assertEqual(code, 3, out)
        self.assertIn("META TRIANGLE FAILED", out)

    def test_missing_meta_fixture_exits_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(os.path.join(TOOL, "fixtures", "_meta"),
                            os.path.join(tmp, "fixtures", "_meta"))
            os.remove(os.path.join(tmp, "fixtures", "_meta", "honest_gate.sh"))
            shutil.copy(SELFTEST, tmp)
            code, out = run_cli(os.path.join(tmp, "selftest.py"), "--meta-only")
        self.assertEqual(code, 3, out)


@unittest.skipUnless(shutil.which("zsh"), "the example gates reproduce zsh behaviour")
class ExampleRegistry(unittest.TestCase):
    EXPECTED = {
        "builtin_shadow_naive": "CANNOT-FAIL",
        "builtin_shadow_fixed": "PASS",
        "status_counter_naive": "CANNOT-FAIL",
        "status_counter_fixed": "PASS",
        "word_split_naive": "CANNOT-FAIL",
        "word_split_fixed": "PASS",
    }

    def test_classifies_every_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_json = os.path.join(tmp, "result.json")
            code, out = run_cli(SELFTEST, "--registry", EXAMPLE_REGISTRY, "--json", out_json)
            with open(out_json, encoding="utf-8") as fh:
                data = json.load(fh)
        self.assertEqual(code, 1, out)  # naive gates are findings by design
        buckets = {r["id"]: r["bucket"] for r in data["results"]}
        self.assertEqual(buckets, self.EXPECTED)
        lies = sorted(r["id"] for r in data["results"] if r["exit_code_lies"])
        self.assertEqual(lies, ["status_counter_fixed"])

    def test_fixed_gates_alone_exit_0(self):
        code, out = run_cli(SELFTEST, "--registry", EXAMPLE_REGISTRY,
                            "--only", "builtin_shadow_fixed,status_counter_fixed,word_split_fixed")
        self.assertEqual(code, 0, out)

    def test_word_split_naive_passes_under_bash(self):
        """The defect belongs to the shell: the same script is honest under bash."""
        gate = os.path.join(TOOL, "fixtures", "examples", "word-split", "gate_naive.sh")
        entry = {"id": "ws_bash", "cmd": ["bash", gate, "{input}"],
                 "bad": "fixtures/examples/word-split/bad_manifest.txt",
                 "good": "fixtures/examples/word-split/good_manifest.txt"}
        self.assertEqual(selftest.check_entry(entry, TOOL, 30)["bucket"], "PASS")


class Buckets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        for name, text in (("bad.txt", "BROKEN\n"), ("good.txt", "fine\n")):
            with open(os.path.join(self.tmp, name), "w") as fh:
                fh.write(text)

    def check(self, **entry):
        base = {"id": "x", "bad": "bad.txt", "good": "good.txt"}
        return selftest.check_entry({**base, **entry}, self.tmp, 10)

    def test_no_fixture(self):
        r = self.check(cmd=["true"], good=None, no_fixture_reason="no failing artifact kept")
        self.assertEqual(r["bucket"], "NO-FIXTURE")
        self.assertEqual(r["detail"], "no failing artifact kept")

    def test_missing_fixture_file(self):
        self.assertEqual(self.check(cmd=["true"], bad="gone.txt")["bucket"], "NO-FIXTURE")

    def test_harness_error_on_missing_binary(self):
        r = self.check(cmd=["definitely-not-a-binary-4f1c", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR")

    def test_nondiscriminating_pattern_is_cannot_fail(self):
        r = self.check(cmd=["cat", "{input}"], expect_bad="detect", detect_bad=".",
                       expect_good="exit")
        self.assertEqual(r["bucket"], "CANNOT-FAIL")
        self.assertIn("separates nothing", r["detail"])

    def gate_script(self, body):
        path = os.path.join(self.tmp, "gate.sh")
        with open(path, "w") as fh:
            fh.write(body)
        return ["sh", path, "{input}"]

    def test_detect_gate_that_crashed_without_a_verdict_is_harness_error(self):
        cmd = self.gate_script('echo checking\necho $((1/0))\n')
        r = self.check(cmd=cmd, expect_bad="detect", detect_bad="^open: [1-9]",
                       expect_good="exit")
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("no match", r["detail"])

    def test_verdict_without_final_newline_stays_apart_from_stderr(self):
        cmd = self.gate_script(
            'if grep -q BROKEN "$1"; then printf "open: 3"; echo $((1/0)); '
            'else echo "open: 0"; fi\n')
        r = self.check(cmd=cmd, expect_bad="detect", detect_bad="^open: [1-9][0-9]*$",
                       expect_good="exit")
        self.assertEqual(r["bucket"], "PASS", r)

    def test_join_streams(self):
        self.assertEqual(selftest.join_streams("a", "b\n"), "a\nb\n")
        self.assertEqual(selftest.join_streams("a\n", "b"), "a\nb")
        self.assertEqual(selftest.join_streams("", "b"), "b")
        self.assertEqual(selftest.join_streams("a", ""), "a")

    def test_registry_run_with_no_fixture_exits_1(self):
        reg = os.path.join(self.tmp, "reg.yaml")
        with open(reg, "w") as fh:
            fh.write("instruments:\n  - id: later\n    no_fixture_reason: \"not built yet\"\n")
        code, out = run_main("--registry", reg)
        self.assertEqual(code, 1, out)


class RegistryParser(unittest.TestCase):
    def test_parses_subset(self):
        doc = selftest.parse_registry_yaml(
            "# c\nversion: 1\ninstruments:\n"
            "  - id: a\n    cmd: [sh, \"{here}/x.sh\", '{input}']\n"
            "    detect_bad: '^open: [1-9]\\d*$'\n    timeout: 5  # seconds\n"
            "    what: \"say \\\"hi\\\"\"\n")
        self.assertEqual(doc["version"], 1)
        e = doc["instruments"][0]
        self.assertEqual(e["cmd"], ["sh", "{here}/x.sh", "{input}"])
        self.assertEqual(e["detect_bad"], r"^open: [1-9]\d*$")
        self.assertEqual(e["timeout"], 5)
        self.assertEqual(e["what"], 'say "hi"')

    def test_rejects_what_it_does_not_understand(self):
        for text in (
            "instruments:\n  - id: a\n    cmd:\n      - sh\n",       # nested block
            "instruments:\n  - id: a\n    bad: {input}\n",           # unquoted brace
            "instruments:\n  - id: a\n     what: misaligned\n",      # wrong indent
            "instruments:\n  - id: a\n    id: b\n",                  # duplicate key
            "stuff: 1\n",                                            # unknown top-level key
        ):
            with self.subTest(text=text):
                with self.assertRaises(selftest.RegistryError):
                    selftest.parse_registry_yaml(text)

    def test_registry_error_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = os.path.join(tmp, "reg.yaml")
            with open(reg, "w") as fh:
                fh.write("instruments:\n  - id: a\n    cmd: [sh\n")
            code, _ = run_main("--registry", reg)
        self.assertEqual(code, 2)

    def test_json_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = os.path.join(tmp, "reg.json")
            with open(reg, "w") as fh:
                json.dump({"instruments": [{"id": "a", "typo_key": 1}]}, fh)
            with self.assertRaises(selftest.RegistryError):
                selftest.load_registry(reg)


if __name__ == "__main__":
    unittest.main()
