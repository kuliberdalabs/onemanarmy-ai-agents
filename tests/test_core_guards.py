"""Regression tests for three bugs found in core/ before release (stdlib unittest).

    python3 -m unittest discover tests -p test_core_guards.py -v

1. gate-selftest filed a gate that was killed by a signal, or crashed, on the
   bad fixture as PASS: the non-zero exit counted as a rejection. The same
   held when a shell wrapper reported the death (exit 126, 127 or 128+N) and
   when the traceback went to stdout.
2. doctrine-guard checked its ALLOW list first, so `*/scratchpad/*` and
   `*-log.md` switched protection off for AGENTS.md, CLAUDE.md, settings
   files and .claude/rules/ files.
3. The dash-arg-help reproducer needs Python 3.11 argparse; on older
   interpreters it printed raw return codes instead of saying so.
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
import textwrap
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELFTEST = os.path.join(REPO, "core", "gate-selftest", "selftest.py")
HOOK = os.path.join(REPO, "core", "hooks", "doctrine-guard", "doctrine-guard.sh")
DASH_ARG = os.path.join(REPO, "core", "pitfalls", "dash-arg-help.sh")

_spec = importlib.util.spec_from_file_location("selftest_core_guards", SELFTEST)
selftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(selftest)


def write(path, text, mode=None):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text))
    if mode is not None:
        os.chmod(path, mode)


class GateThatDiesIsNotARejection(unittest.TestCase):
    """A gate that dies on the bad fixture has not caught anything."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        write(os.path.join(self.tmp, "bad.txt"), "BROKEN\n")
        write(os.path.join(self.tmp, "good.txt"), "fine\n")
        # Kills itself on the bad input, accepts the good one.
        write(os.path.join(self.tmp, "sig_gate.sh"), """\
            if grep -q BROKEN "$1"; then kill -TERM $$; fi
            echo "PASS: clean"
            exit 0
            """)
        # Crashes on the bad input with an unhandled exception.
        write(os.path.join(self.tmp, "crash_gate.py"), """\
            import sys
            if "BROKEN" in open(sys.argv[1]).read():
                raise RuntimeError("parser Error: unexpected token")
            print("PASS: clean")
            """)
        # Rejects the bad input honestly, crashes on the good one.
        write(os.path.join(self.tmp, "crash_on_good.py"), """\
            import sys
            if "BROKEN" in open(sys.argv[1]).read():
                print("FAIL: input contains BROKEN")
                sys.exit(1)
            raise KeyError("missing column")
            """)
        # A log checker that quotes a traceback found in its input on stdout.
        write(os.path.join(self.tmp, "quotes_traceback.sh"), """\
            if grep -q BROKEN "$1"; then
              echo "FAIL: the log has a crash:"
              echo "Traceback (most recent call last):"
              exit 1
            fi
            echo "PASS: clean"
            """)
        write(os.path.join(self.tmp, "honest.sh"), """\
            if grep -q BROKEN "$1"; then echo "FAIL: BROKEN"; exit 1; fi
            echo "PASS: clean"
            """)

    def check(self, **entry):
        base = {"id": "x", "bad": "bad.txt", "good": "good.txt"}
        return selftest.check_entry({**base, **entry}, self.tmp, 30)

    def test_signal_on_bad_fixture_is_harness_error(self):
        r = self.check(cmd=["sh", "{here}/sig_gate.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertEqual(r["detail"], "bad fixture: killed by signal 15 (SIGTERM); "
                                      "a gate that dies has not rejected anything")

    def test_crash_on_bad_fixture_is_harness_error(self):
        r = self.check(cmd=[sys.executable, "{here}/crash_gate.py", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("bad fixture: crashed with an unhandled exception (exit=1, "
                      "RuntimeError: parser Error: unexpected token)", r["detail"])

    def test_crash_matching_a_broad_detect_pattern_is_harness_error(self):
        r = self.check(cmd=[sys.executable, "{here}/crash_gate.py", "{input}"],
                       expect_bad="detect", detect_bad="Error")
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)

    def test_crash_on_good_fixture_is_harness_error(self):
        r = self.check(cmd=[sys.executable, "{here}/crash_on_good.py", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertTrue(r["detail"].startswith("good fixture: crashed"), r["detail"])

    def test_honest_rejection_still_passes(self):
        self.assertEqual(self.check(cmd=["sh", "{here}/honest.sh", "{input}"])["bucket"], "PASS")

    def test_traceback_on_stdout_is_harness_error_in_exit_mode(self):
        r = self.check(cmd=["sh", "{here}/quotes_traceback.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("traceback on stdout", r["detail"])

    def test_traceback_after_the_verdict_line_passes_in_detect_mode(self):
        r = self.check(cmd=["sh", "{here}/quotes_traceback.sh", "{input}"],
                       expect_bad="detect", detect_bad="^FAIL: the log has a crash")
        self.assertEqual(r["bucket"], "PASS", r)

    def test_cli_exit_code_and_report_line(self):
        reg = os.path.join(self.tmp, "reg.json")
        with open(reg, "w", encoding="utf-8") as fh:
            json.dump({"instruments": [{"id": "sig_gate", "bad": "bad.txt", "good": "good.txt",
                                        "cmd": ["sh", "{here}/sig_gate.sh", "{input}"]}]}, fh)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = selftest.main(["--registry", reg])
        out = buf.getvalue()
        self.assertEqual(code, 1, out)
        self.assertIn("[HARNESS-ERROR] 1\n  - sig_gate  <?>\n      -> bad fixture: killed by "
                      "signal 15 (SIGTERM); a gate that dies has not rejected anything\n", out)
        self.assertIn("  PASS: 0\n", out)


class WrapperThatReportsADeathIsNotARejection(unittest.TestCase):
    """A shell or Python wrapper can turn a crash into an ordinary exit code."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        write(os.path.join(self.tmp, "bad.txt"), "BROKEN\n")
        write(os.path.join(self.tmp, "good.txt"), "fine\n")
        # The child dies of SIGTERM; the wrapper passes on 143 as its own exit.
        write(os.path.join(self.tmp, "wrapped_signal.sh"), """\
            if grep -q BROKEN "$1"; then sh -c 'kill -TERM $$'; exit $?; fi
            echo "PASS: clean"
            """)
        # The helper the gate needs is not installed: the shell exits 127.
        write(os.path.join(self.tmp, "missing_helper.sh"), """\
            if grep -q BROKEN "$1"; then gate_helper_that_is_not_installed_4f1c "$1"; exit $?; fi
            echo "PASS: clean"
            """)
        # The helper exists without its executable bit: the shell exits 126.
        write(os.path.join(self.tmp, "helper.sh"), "echo helper\n", 0o644)
        write(os.path.join(self.tmp, "noexec_helper.sh"), """\
            if grep -q BROKEN "$1"; then "$(dirname "$0")/helper.sh" "$1"; exit $?; fi
            echo "PASS: clean"
            """)
        # The traceback of an unhandled exception goes to stdout, not stderr.
        write(os.path.join(self.tmp, "stdout_crash.py"), """\
            import sys
            sys.stderr = sys.stdout
            if "BROKEN" in open(sys.argv[1]).read():
                raise RuntimeError("broken gate")
            print("PASS: clean")
            """)
        # Rejects the bad input, dies of a wrapped SIGTERM on the good one.
        write(os.path.join(self.tmp, "wrapped_signal_on_good.sh"), """\
            if grep -q BROKEN "$1"; then echo "FAIL: BROKEN"; exit 1; fi
            sh -c 'kill -TERM $$'; exit $?
            """)
        # Rejects on purpose with a traceback: the verdict line comes first.
        write(os.path.join(self.tmp, "verdict_then_traceback.py"), """\
            import sys, traceback
            if "BROKEN" in open(sys.argv[1]).read():
                try:
                    raise ValueError("validation rejection: BROKEN")
                except ValueError:
                    print("FAIL: input contains BROKEN", flush=True)
                    traceback.print_exc()
                    sys.exit(1)
            print("PASS: clean")
            """)
        # Rejects on purpose with nothing but the traceback.
        write(os.path.join(self.tmp, "traceback_only.py"), """\
            import sys, traceback
            if "BROKEN" in open(sys.argv[1]).read():
                try:
                    raise ValueError("validation rejection: BROKEN")
                except ValueError:
                    traceback.print_exc()
                    sys.exit(1)
            print("PASS: clean")
            """)
        # Prints its finding, then dies of a wrapped SIGTERM.
        write(os.path.join(self.tmp, "finding_then_signal.sh"), """\
            if grep -q BROKEN "$1"; then echo "FAIL: BROKEN"; sh -c 'kill -TERM $$'; exit $?; fi
            echo "PASS: clean"
            """)
        # Honest gates with exit codes other than 1, and one whose rejection
        # message says "Error" on stderr without any traceback.
        for code in (2, 3, 255):
            write(os.path.join(self.tmp, "exit_%d.sh" % code), """\
                if grep -q BROKEN "$1"; then echo "FAIL: BROKEN"; exit %d; fi
                echo "PASS: clean"
                """ % code)
        write(os.path.join(self.tmp, "error_word.sh"), """\
            if grep -q BROKEN "$1"; then echo "Error: input contains BROKEN" >&2; exit 1; fi
            echo "PASS: clean"
            """)

    def check(self, **entry):
        base = {"id": "x", "bad": "bad.txt", "good": "good.txt"}
        return selftest.check_entry({**base, **entry}, self.tmp, 30)

    def test_wrapped_signal_on_bad_fixture_is_harness_error(self):
        r = self.check(cmd=["sh", "{here}/wrapped_signal.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertEqual(r["detail"], "bad fixture: exit 143 = 128+15: a shell reported a child "
                                      "killed by signal 15 (SIGTERM); a gate that dies has not "
                                      "rejected anything")

    def test_missing_helper_on_bad_fixture_is_harness_error(self):
        r = self.check(cmd=["sh", "{here}/missing_helper.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertEqual(r["detail"], "bad fixture: exit 127: a shell could not find a command; "
                                      "a gate that could not run has not rejected anything")

    def test_helper_without_exec_bit_on_bad_fixture_is_harness_error(self):
        r = self.check(cmd=["sh", "{here}/noexec_helper.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertEqual(r["detail"], "bad fixture: exit 126: a shell found a command it could "
                                      "not execute; a gate that could not run has not rejected "
                                      "anything")

    def test_traceback_on_stdout_is_harness_error(self):
        r = self.check(cmd=[sys.executable, "{here}/stdout_crash.py", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertEqual(r["detail"], "bad fixture: crashed with an unhandled exception (exit=1, "
                                      "RuntimeError: broken gate), traceback on stdout; a crash "
                                      "is not a verdict")

    def test_traceback_on_stdout_matching_a_detect_pattern_is_harness_error(self):
        r = self.check(cmd=[sys.executable, "{here}/stdout_crash.py", "{input}"],
                       expect_bad="detect", detect_bad="broken gate")
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)

    def test_wrapped_signal_on_good_fixture_is_harness_error(self):
        r = self.check(cmd=["sh", "{here}/wrapped_signal_on_good.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertTrue(r["detail"].startswith("good fixture: exit 143 = 128+15"), r["detail"])

    def test_traceback_with_exit_0_on_good_fixture_is_harness_error(self):
        write(os.path.join(self.tmp, "swallows_crash.py"), """\
            import sys, traceback
            if "BROKEN" in open(sys.argv[1]).read():
                print("FAIL: input contains BROKEN")
                sys.exit(1)
            try:
                {}["missing column"]
            except KeyError:
                traceback.print_exc()
            print("PASS: clean")
            """)
        r = self.check(cmd=[sys.executable, "{here}/swallows_crash.py", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertEqual(r["detail"], "good fixture: printed a Python traceback (exit=0, "
                                      "KeyError: 'missing column'), traceback on stderr; "
                                      "a crash is not a verdict")

    def test_wrapped_signal_counts_even_when_the_finding_was_printed(self):
        r = self.check(cmd=["sh", "{here}/finding_then_signal.sh", "{input}"],
                       expect_bad="detect", detect_bad="^FAIL: BROKEN")
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)

    def test_rejection_with_a_traceback_is_harness_error_in_exit_mode(self):
        r = self.check(cmd=[sys.executable, "{here}/verdict_then_traceback.py", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("ValueError: validation rejection: BROKEN), traceback on stderr", r["detail"])

    def test_rejection_with_a_traceback_passes_in_detect_mode(self):
        r = self.check(cmd=[sys.executable, "{here}/verdict_then_traceback.py", "{input}"],
                       expect_bad="detect", detect_bad="^FAIL: input contains BROKEN")
        self.assertEqual(r["bucket"], "PASS", r)

    def test_detect_match_inside_the_traceback_is_not_a_verdict(self):
        r = self.check(cmd=[sys.executable, "{here}/traceback_only.py", "{input}"],
                       expect_bad="detect", detect_bad="validation rejection")
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)

    def test_declared_exit_codes_count_as_rejections(self):
        for code in (2, 3, 255):
            with self.subTest(code=code):
                r = self.check(cmd=["sh", "{here}/exit_%d.sh" % code, "{input}"], reject_exit=[code])
                self.assertEqual(r["bucket"], "PASS", r)
                self.assertEqual(r["bad_evidence"], "exit=%d" % code)

    def test_undeclared_exit_codes_are_harness_errors(self):
        for code in (2, 3, 255):
            with self.subTest(code=code):
                r = self.check(cmd=["sh", "{here}/exit_%d.sh" % code, "{input}"])
                self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
                self.assertIn("exit %d is not a declared rejection code" % code, r["detail"])


    def test_error_word_without_a_traceback_is_a_verdict(self):
        r = self.check(cmd=["sh", "{here}/error_word.sh", "{input}"])
        self.assertEqual(r["bucket"], "PASS", r)
        r = self.check(cmd=["sh", "{here}/error_word.sh", "{input}"],
                       expect_bad="detect", detect_bad="Error")
        self.assertEqual(r["bucket"], "PASS", r)

    def test_cli_report_names_each_cause(self):
        reg = os.path.join(self.tmp, "reg.json")
        gates = {"wrapped_signal": ["sh", "{here}/wrapped_signal.sh", "{input}"],
                 "missing_helper": ["sh", "{here}/missing_helper.sh", "{input}"],
                 "stdout_crash": [sys.executable, "{here}/stdout_crash.py", "{input}"]}
        with open(reg, "w", encoding="utf-8") as fh:
            json.dump({"instruments": [{"id": k, "bad": "bad.txt", "good": "good.txt", "cmd": v}
                                       for k, v in gates.items()]}, fh)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = selftest.main(["--registry", reg])
        out = buf.getvalue()
        self.assertEqual(code, 1, out)
        self.assertIn("[HARNESS-ERROR] 3\n", out)
        self.assertIn("  - wrapped_signal  <?>\n      -> bad fixture: exit 143 = 128+15: a shell "
                      "reported a child killed by signal 15 (SIGTERM)", out)
        self.assertIn("  - missing_helper  <?>\n      -> bad fixture: exit 127: a shell could not "
                      "find a command", out)
        self.assertIn("  - stdout_crash  <?>\n      -> bad fixture: crashed with an unhandled "
                      "exception (exit=1, RuntimeError: broken gate), traceback on stdout", out)
        self.assertIn("  PASS: 0\n", out)

class GateThatErrorsIsNotARejection(unittest.TestCase):
    """A gate a user would write can error before it decides anything."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        write(os.path.join(self.tmp, "bad.txt"), "5 0\n")
        write(os.path.join(self.tmp, "good.txt"), "5 10\n")

    def check(self, **entry):
        base = {"id": "ratio", "bad": "bad.txt", "good": "good.txt",
                "cmd": ["awk", "{ if ($1/$2 > 0.9) bad=1 } END { exit bad }", "{input}"]}
        return selftest.check_entry({**base, **entry}, self.tmp, 30)

    def test_awk_division_by_zero_on_the_bad_fixture_is_harness_error(self):
        probe = subprocess.run(["awk", "BEGIN { x = 1 / 0 }"], capture_output=True, text=True)
        if probe.returncode == 0:
            self.skipTest("this awk (mawk) treats division by zero as infinity, not as an error")
        r = self.check()
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        # The wording differs between awk builds (macOS: "awk: division by zero",
        # gawk: "awk: cmd. line:1: ... fatal: division by zero attempted").
        self.assertIn("bad fixture: exit 2 after the interpreter's own error (awk: ", r["detail"])
        self.assertIn("division by zero", r["detail"])

    def test_zsh_division_by_zero_exiting_1_is_harness_error(self):
        r = self.check(cmd=["zsh", "-f", "-c",
                            'read -r n d < "$1"; ratio=$(( n / d )); (( ratio <= 1 ))', "gate", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("exit 1 after the interpreter's own error", r["detail"])
        self.assertIn("division by zero", r["detail"])

    def test_bash_script_with_an_unbound_variable_is_harness_error(self):
        write(os.path.join(self.tmp, "gate.sh"), """\
            set -u
            if grep -q ' 0$' "$1"; then echo "$undefined_name"; fi
            exit 0
            """)
        r = self.check(cmd=["bash", "{here}/gate.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("undefined_name", r["detail"])

    def test_zsh_crash_with_stderr_sent_to_stdout_is_harness_error(self):
        r = self.check(cmd=["zsh", "-f", "-c",
                            'exec 2>&1; read -r n d < "$1"; ratio=$(( n / d )); (( ratio <= 1 ))',
                            "gate", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("division by zero", r["detail"])

    def test_zsh_script_in_a_folder_with_a_space_is_harness_error(self):
        folder = os.path.join(self.tmp, "my project")
        os.makedirs(folder)
        write(os.path.join(folder, "gate.zsh"), """\
            read -r n d < "$1"
            ratio=$(( n / d ))
            (( ratio <= 1 ))
            """)
        r = self.check(cmd=["zsh", "-f", os.path.join(folder, "gate.zsh"), "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("gate.zsh", r["detail"])
        self.assertIn("division by zero", r["detail"])

    def test_detect_pattern_matching_only_the_crash_is_harness_error(self):
        r = self.check(cmd=["zsh", "-f", "-c",
                            'read -r n d < "$1"; ratio=$(( n / d )); (( ratio <= 1 ))', "gate", "{input}"],
                       expect_bad="detect", detect_bad="division by zero")
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)
        self.assertIn("the only match for /division by zero/ is the interpreter's own error", r["detail"])

    def test_detect_pattern_matching_a_verdict_line_still_passes(self):
        write(os.path.join(self.tmp, "verdict.sh"), """\
            read -r n d < "$1"
            if [ "$d" = 0 ]; then echo "REJECT: division by zero in the input"; exit 1; fi
            echo "ok"
            """)
        r = self.check(cmd=["sh", "{here}/verdict.sh", "{input}"],
                       expect_bad="detect", detect_bad="REJECT: division by zero")
        self.assertEqual(r["bucket"], "PASS", r)

    def test_crash_inside_a_zsh_function_is_harness_error(self):
        script = 'check_ratio() {\n  read -r n d < "$1"\n  ratio=$(( n / d ))\n  (( ratio <= 1 ))\n}\ncheck_ratio "$1"'
        for extra in ({}, {"expect_bad": "detect", "detect_bad": "division by zero"}):
            with self.subTest(**extra):
                r = self.check(cmd=["zsh", "-f", "-c", script, "gate", "{input}"], **extra)
                self.assertEqual(r["bucket"], "HARNESS-ERROR", r)

    def test_crash_inside_a_helper_script_is_harness_error(self):
        write(os.path.join(self.tmp, "ratio_helper.zsh"), """\
            read -r n d < "$1"
            ratio=$(( n / d ))
            (( ratio <= 1 ))
            """)
        write(os.path.join(self.tmp, "wrapper.sh"), """\
            zsh -f "$(dirname "$0")/ratio_helper.zsh" "$1"
            """)
        r = self.check(cmd=["sh", "{here}/wrapper.sh", "{input}"])
        self.assertEqual(r["bucket"], "HARNESS-ERROR", r)

    def test_the_zsh_gate_rejecting_for_real_passes(self):
        write(os.path.join(self.tmp, "bad.txt"), "10 5\n")
        r = self.check(cmd=["zsh", "-f", "-c",
                            'read -r n d < "$1"; ratio=$(( n / d )); (( ratio <= 1 ))', "gate", "{input}"])
        self.assertEqual(r["bucket"], "PASS", r)

    def test_a_rejection_naming_the_input_file_and_line_is_still_a_verdict(self):
        write(os.path.join(self.tmp, "named.sh"), """\
            if grep -q ' 0$' "$1"; then echo "$1:1: denominator is zero" >&2; exit 1; fi
            echo "ok"
            """)
        r = self.check(cmd=["sh", "{here}/named.sh", "{input}"])
        self.assertEqual(r["bucket"], "PASS", r)

    def test_a_lint_style_rejection_on_stderr_is_still_a_verdict(self):
        write(os.path.join(self.tmp, "lint.sh"), """\
            if grep -q ' 0$' "$1"; then echo "ledger.csv:3: denominator is zero" >&2; exit 1; fi
            echo "ok"
            """)
        r = self.check(cmd=["sh", "{here}/lint.sh", "{input}"])
        self.assertEqual(r["bucket"], "PASS", r)

    def test_the_same_gate_rejecting_for_real_passes(self):
        write(os.path.join(self.tmp, "bad.txt"), "10 5\n")
        self.assertEqual(self.check()["bucket"], "PASS")

    def test_registry_rejects_a_bad_reject_exit(self):
        for value in ("[0]", "[256]", '"one"', "[]"):
            with self.subTest(value=value):
                path = os.path.join(self.tmp, "registry.yaml")
                write(path, "instruments:\n  - id: x\n    cmd: [sh, x]\n    reject_exit: %s\n" % value)
                with self.assertRaises(selftest.RegistryError):
                    selftest.load_registry(path)


def hook(path, **env):
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": path}})
    clean = {k: v for k, v in os.environ.items() if not k.startswith("DOCTRINE_GUARD_")}
    p = subprocess.run(["bash", HOOK], input=payload, capture_output=True, text=True,
                       env={**clean, **env}, timeout=30)
    return p.returncode, p.stdout


class DoctrineGuardProtectWins(unittest.TestCase):
    PROTECTED = (
        "/repo/scratchpad/AGENTS.md",
        "/srv/work/scratchpad/proj/AGENTS.md",
        "/srv/work/scratchpad/proj/CLAUDE.md",
        "/srv/work/scratchpad/proj/.claude/settings.json",
        "/srv/work/scratchpad/proj/.claude/settings.local.json",
        "/srv/work/scratchpad/proj/.claude/hooks/doctrine-guard.sh",
        "/srv/work/scratchpad/proj/.claude/skills/x/SKILL.md",
        "/repo/.claude/rules/audit-log.md",
        "/repo/.claude/rules/STATE.md",
        "/repo/scratchpad/../CLAUDE.md",
        "/repo/.claude/hooks/../settings.json",
    )
    OPEN = (
        "/repo/scratchpad/notes.md",
        "/repo/STATE.md",
        "/repo/notes/audit-log.md",
        "/repo/runs/events.jsonl",
        "/repo/src/app.py",
    )

    def test_protected_files_ask_even_below_a_scratchpad_folder(self):
        for path in self.PROTECTED:
            with self.subTest(path=path):
                rc, out = hook(path)
                self.assertEqual(rc, 0)
                self.assertIn('"permissionDecision": "ask"', out)

    def test_deny_mode_applies_below_a_scratchpad_folder(self):
        rc, out = hook("/srv/work/scratchpad/proj/AGENTS.md", DOCTRINE_GUARD_MODE="deny")
        self.assertIn('"permissionDecision": "deny"', out)

    def test_state_files_stay_open(self):
        for path in self.OPEN:
            with self.subTest(path=path):
                self.assertEqual(hook(path), (0, ""))

    def test_old_allow_variable_cannot_exempt_doctrine(self):
        rc, out = hook("/repo/AGENTS.md", DOCTRINE_GUARD_ALLOW="*/AGENTS.md:*")
        self.assertIn('"permissionDecision": "ask"', out)

    def test_selftest_covers_the_new_cases(self):
        p = subprocess.run(["bash", HOOK, "--selftest"], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("ok   AGENTS.md in scratchpad -> ask", p.stdout)
        self.assertIn("ok   rules file named like a log -> ask", p.stdout)
        self.assertIn("selftest: all cases passed", p.stdout)


def python_version(exe):
    try:
        p = subprocess.run([exe, "-I", "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    major, minor = p.stdout.strip().split(".")
    return int(major), int(minor)


def old_python():
    """An installed interpreter older than 3.11, or None."""
    candidates = [shutil.which(n) for n in ("python3.10", "python3.9", "python3.8")]
    candidates.append("/usr/bin/python3")
    if shutil.which("uv"):
        try:
            p = subprocess.run(["uv", "python", "find", "3.10"], capture_output=True, text=True,
                               timeout=30, stdin=subprocess.DEVNULL)
            if p.returncode == 0:
                candidates.insert(0, p.stdout.strip())
        except (OSError, subprocess.TimeoutExpired):
            pass
    for exe in candidates:
        if exe and os.path.exists(exe):
            v = python_version(exe)
            if v and v < (3, 11):
                return exe, v
    return None


class DashArgHelpNeedsPython311(unittest.TestCase):
    def run_with(self, exe):
        """Run the reproducer with `python3` on PATH resolving to exe."""
        with tempfile.TemporaryDirectory() as tmp:
            write(os.path.join(tmp, "python3"), f'#!/bin/sh\nexec "{exe}" "$@"\n', 0o755)
            env = {**os.environ, "PATH": tmp + os.pathsep + "/usr/bin:/bin"}
            p = subprocess.run([shutil.which("bash") or "bash", DASH_ARG], capture_output=True,
                               text=True, env=env, timeout=60)
        return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1]

    def test_older_python_says_what_it_needs(self):
        found = old_python()
        if not found:
            self.skipTest("no python3 older than 3.11 installed")
        exe, (major, minor) = found
        rc, last = self.run_with(exe)
        self.assertEqual(rc, 1)
        self.assertEqual(last, f"NOT REPRODUCED: needs python3 >= 3.11 (found {major}.{minor})")

    @unittest.skipIf(sys.version_info < (3, 11), "needs python 3.11 or newer")
    def test_supported_python_reproduces(self):
        rc, last = self.run_with(sys.executable)
        self.assertEqual(rc, 0, last)
        self.assertTrue(last.startswith("REPRODUCED: '-hVtqK8Aq0E' printed help"), last)


if __name__ == "__main__":
    unittest.main()
