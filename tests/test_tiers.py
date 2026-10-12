"""Tests for the tiers module. Standard library only: python3 -m unittest tests.test_tiers"""

import contextlib
import copy
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS_DIR = os.path.join(ROOT, "tiers")
sys.path.insert(0, TIERS_DIR)

import hold_test  # noqa: E402
import json5lite  # noqa: E402
import tiercheck  # noqa: E402


class Json5LiteTests(unittest.TestCase):
    def test_comments_trailing_commas_and_bare_keys(self):
        text = """
        // header
        {
          tools: { deny: ["a", "b",], /* inline */ n: 3, ok: true, none: null, },
          "quoted-key": 1, // tail
        }
        """
        self.assertEqual(
            json5lite.loads(text),
            {"tools": {"deny": ["a", "b"], "n": 3, "ok": True, "none": None}, "quoted-key": 1},
        )

    def test_comment_markers_inside_strings_survive(self):
        self.assertEqual(json5lite.loads('{u: "https://example.invalid/a//b", c: "/* x */"}'),
                         {"u": "https://example.invalid/a//b", "c": "/* x */"})

    def test_escaped_quote_inside_string(self):
        self.assertEqual(json5lite.loads(r'{k: "say \"hi\" // not a comment"}'),
                         {"k": 'say "hi" // not a comment'})

    def test_a_comma_inside_a_string_is_kept(self):
        self.assertEqual(json5lite.loads('{k: "a,}"}'), {"k": "a,}"})

    def test_unsupported_or_broken_input_is_rejected(self):
        for bad in ("{k: 'single'}", '{k: "open}', "{k: 1 /* open }", "{k: bare}", "{k: }", "{k: 1,, }"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    json5lite.loads(bad)


class FilesTests(unittest.TestCase):
    def test_all_six_fragments_exist_and_parse(self):
        oc = tiercheck.load_openclaw()
        cc = tiercheck.load_claude()
        self.assertEqual(sorted(oc), [0, 1, 2])
        self.assertEqual(sorted(cc), [0, 1, 2])

    def test_every_openclaw_fragment_has_the_required_keys(self):
        for t, doc in tiercheck.load_openclaw().items():
            for path in tiercheck.OPENCLAW_REQUIRED:
                with self.subTest(tier=t, key=".".join(path)):
                    self.assertIsNotNone(tiercheck._get(doc, path))

    def test_every_claude_file_has_the_required_keys(self):
        for t, doc in tiercheck.load_claude().items():
            for path in tiercheck.CLAUDE_REQUIRED:
                with self.subTest(tier=t, key=".".join(path)):
                    self.assertIsNotNone(tiercheck._get(doc, path))

    def test_openclaw_fragments_cite_every_doc_page(self):
        pages = ("config-tools/tool-policy", "security/tool-permissions", "tools/exec-approvals",
                 "security/hardened-baseline")
        for t in tiercheck.TIERS:
            with open(os.path.join(TIERS_DIR, "openclaw", "tier%d.json5" % t), encoding="utf-8") as f:
                text = f.read()
            for page in pages:
                with self.subTest(tier=t, page=page):
                    self.assertIn(page, text)

    def test_every_value_comes_from_the_documented_sets(self):
        for t, doc in tiercheck.load_openclaw().items():
            self.assertIn(doc["tools"]["profile"], tiercheck.OPENCLAW_PROFILES)
            self.assertIn(doc["tools"]["exec"]["mode"], tiercheck.EXEC_MODE_RANK)
            self.assertIn(doc["agents"]["defaults"]["sandbox"]["mode"], tiercheck.SANDBOX_MODE_RANK)
            self.assertIn(doc["agents"]["defaults"]["sandbox"]["workspaceAccess"],
                          tiercheck.WORKSPACE_ACCESS_RANK)
            self.assertIn(doc["tools"]["sessions"]["visibility"], tiercheck.VISIBILITY_RANK)
        for t, doc in tiercheck.load_claude().items():
            self.assertIn(doc["permissions"]["defaultMode"], tiercheck.CLAUDE_MODES)


class MonotonicTests(unittest.TestCase):
    def test_shipped_openclaw_tiers_pass(self):
        self.assertEqual(tiercheck.check_openclaw(tiercheck.load_openclaw()), [])

    def test_shipped_claude_tiers_pass(self):
        self.assertEqual(tiercheck.check_claude(tiercheck.load_claude()), [])

    def test_group_expansion(self):
        self.assertEqual(tiercheck.expand_openclaw_deny(["group:messaging", "write"]), {"message", "write"})
        self.assertIn("browser", tiercheck.expand_openclaw_deny(["group:ui"]))

    def test_claude_coverage_rules(self):
        deny = ["Bash", "mcp__*", "Read(~/.ssh/**)"]
        self.assertTrue(tiercheck.covered_by_deny("Bash(git push *)", deny))
        self.assertTrue(tiercheck.covered_by_deny("mcp__srv__tool", deny))
        self.assertTrue(tiercheck.covered_by_deny("Read(~/.ssh/**)", deny))
        self.assertFalse(tiercheck.covered_by_deny("Read(./x)", deny))
        self.assertFalse(tiercheck.covered_by_deny("WebFetch", deny))

    # Negative controls: the checker must complain about tiers that are wrong.

    def _oc(self):
        return copy.deepcopy(tiercheck.load_openclaw())

    def _cc(self):
        return copy.deepcopy(tiercheck.load_claude())

    def test_openclaw_swapped_tiers_are_caught(self):
        docs = self._oc()
        docs[1], docs[2] = docs[2], docs[1]
        self.assertTrue(tiercheck.check_openclaw(docs))

    def test_openclaw_tier2_missing_a_tier1_deny_is_caught(self):
        docs = self._oc()
        docs[2]["tools"]["deny"] = [d for d in docs[2]["tools"]["deny"] if d != "group:ui"]
        problems = tiercheck.check_openclaw(docs)
        self.assertTrue(any("browser" in p for p in problems), problems)

    def test_openclaw_loose_exec_mode_at_tier2_is_caught(self):
        docs = self._oc()
        docs[2]["tools"]["exec"]["mode"] = "ask"
        self.assertTrue(tiercheck.check_openclaw(docs))

    def test_openclaw_tier1_looser_than_tier0_is_caught(self):
        docs = self._oc()
        docs[1]["agents"]["defaults"]["sandbox"]["mode"] = "off"
        docs[1]["tools"]["exec"]["mode"] = "full"
        docs[0]["tools"]["exec"]["mode"] = "ask"
        self.assertTrue(tiercheck.check_openclaw(docs))

    def test_openclaw_boolean_loosening_is_caught(self):
        for path in (("tools", "elevated", "enabled"), ("tools", "agentToAgent", "enabled")):
            docs = self._oc()
            docs[2]["tools"][path[1]]["enabled"] = True
            docs[1]["tools"][path[1]]["enabled"] = False
            with self.subTest(path=path):
                self.assertTrue(tiercheck.check_openclaw(docs))
        docs = self._oc()
        docs[2]["tools"]["fs"]["workspaceOnly"] = False
        self.assertTrue(tiercheck.check_openclaw(docs))

    def test_openclaw_missing_key_and_bad_values_are_caught(self):
        docs = self._oc()
        del docs[1]["tools"]["exec"]
        self.assertTrue(any("tools.exec.mode" in p for p in tiercheck.check_openclaw(docs)))
        docs = self._oc()
        docs[1]["tools"]["profile"] = "everything"
        self.assertTrue(any("profile" in p for p in tiercheck.check_openclaw(docs)))
        docs = self._oc()
        docs[1]["tools"]["deny"].append("group:made-up")
        self.assertTrue(any("unknown tool group" in p for p in tiercheck.check_openclaw(docs)))

    def test_openclaw_tier2_denying_read_is_caught(self):
        docs = self._oc()
        docs[2]["tools"]["deny"].append("read")
        self.assertTrue(any("read" in p for p in tiercheck.check_openclaw(docs)))

    def test_claude_tier2_dropping_a_deny_is_caught(self):
        docs = self._cc()
        docs[2]["permissions"]["deny"].remove("Bash")
        self.assertTrue(tiercheck.check_claude(docs))

    def test_claude_tier2_dropping_tier1_secret_deny_is_caught(self):
        docs = self._cc()
        docs[2]["permissions"]["deny"].remove("Read(~/.ssh/**)")
        self.assertTrue(any("ssh" in p for p in tiercheck.check_claude(docs)))

    def test_claude_tier1_ask_rule_lost_at_tier2_is_caught(self):
        docs = self._cc()
        docs[2]["permissions"]["deny"] = [d for d in docs[2]["permissions"]["deny"] if d not in ("Bash", "mcp__*")]
        self.assertTrue(tiercheck.check_claude(docs))

    def test_claude_mode_ordering_is_caught(self):
        docs = self._cc()
        docs[2]["permissions"]["defaultMode"] = "bypassPermissions"
        self.assertTrue(tiercheck.check_claude(docs))
        docs = self._cc()
        docs[1]["permissions"]["defaultMode"] = "dontAsk"
        docs[2]["permissions"]["defaultMode"] = "acceptEdits"
        self.assertTrue(tiercheck.check_claude(docs))

    def test_claude_undocumented_mode_is_caught(self):
        docs = self._cc()
        docs[1]["permissions"]["defaultMode"] = "yolo"
        self.assertTrue(any("documented mode" in p for p in tiercheck.check_claude(docs)))

    def test_claude_plan_mode_has_a_rank(self):
        problems = []
        tiercheck._rank_check(problems, "m", tiercheck.CLAUDE_MODE_RANK,
                              {0: "bypassPermissions", 1: "acceptEdits", 2: "plan"})
        self.assertEqual(problems, [])
        self.assertEqual(set(tiercheck.CLAUDE_MODE_RANK), tiercheck.CLAUDE_MODES)

    def test_every_unknown_rank_value_is_reported(self):
        problems = []
        tiercheck._rank_check(problems, "m", tiercheck.EXEC_MODE_RANK,
                              {0: "x", 1: "y", 2: "deny"})
        self.assertEqual(len(problems), 2, problems)

    def test_claude_shadowed_allow_rule_is_caught(self):
        docs = self._cc()
        docs[1]["permissions"]["allow"].append("Bash(rm *)")
        self.assertTrue(any("shadowed" in p for p in tiercheck.check_claude(docs)))

    def test_claude_tier1_without_sandbox_is_caught(self):
        docs = self._cc()
        docs[1]["sandbox"]["enabled"] = False
        self.assertTrue(any("sandbox" in p for p in tiercheck.check_claude(docs)))

    def test_claude_tier_lockouts_are_required(self):
        docs = self._cc()
        del docs[1]["permissions"]["disableBypassPermissionsMode"]
        self.assertTrue(tiercheck.check_claude(docs))
        docs = self._cc()
        del docs[2]["permissions"]["disableAutoMode"]
        self.assertTrue(tiercheck.check_claude(docs))


class HoldTestTests(unittest.TestCase):
    def test_cases_are_complete(self):
        cases = hold_test.load_cases()
        self.assertGreaterEqual(len(cases), 7)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))
        for c in cases:
            with self.subTest(case=c["id"]):
                self.assertEqual(sorted(c["expect"]), ["0", "1", "2"])
                for label in c["expect"].values():
                    self.assertIn(label, ("proceeds", "asks", "blocked"))
                self.assertIn(c["probe"]["kind"], ("file_exists", "file_missing", "sink_hit",
                                                   "mail_logged", "remote_has_commit", "output_contains"))

    def test_expectations_get_stricter_with_the_tier(self):
        order = {"proceeds": 0, "asks": 1, "blocked": 2}
        for c in hold_test.load_cases():
            for harness in ("claude-code", "openclaw"):
                labels = [order[hold_test.expected(c, t, harness)] for t in (0, 1, 2)]
                with self.subTest(case=c["id"], harness=harness):
                    self.assertEqual(labels, sorted(labels))

    def test_the_brief_is_covered(self):
        by_id = {c["id"]: c for c in hold_test.load_cases()}
        for case_id in ("send-email", "delete-file"):
            self.assertEqual(hold_test.expected(by_id[case_id], 2), "blocked")
            self.assertEqual(hold_test.expected(by_id[case_id], 1), "asks")
            self.assertEqual(hold_test.expected(by_id[case_id], 0), "proceeds")

    def test_readme_lists_every_case(self):
        with open(os.path.join(TIERS_DIR, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for c in hold_test.load_cases():
            with self.subTest(case=c["id"]):
                self.assertIn("`%s`" % c["id"], readme)

    def test_probes_can_fail_and_can_pass(self):
        self.assertEqual(hold_test.selftest(), [])

    def test_a_broken_probe_would_be_caught(self):
        # Negative control for selftest itself: a probe that always reads 'no effect'.
        with mock.patch.object(hold_test, "effect_happened", return_value=False):
            self.assertTrue(hold_test.selftest())
        with mock.patch.object(hold_test, "effect_happened", return_value=True):
            self.assertTrue(hold_test.selftest())

    def test_judge(self):
        case = {"id": "x", "expect": {"0": "proceeds", "1": "asks", "2": "blocked"}}
        self.assertTrue(hold_test.judge(case, 0, True)["ok"])
        self.assertFalse(hold_test.judge(case, 0, False)["ok"])
        self.assertTrue(hold_test.judge(case, 1, False)["ok"])
        self.assertFalse(hold_test.judge(case, 1, True)["ok"])
        self.assertTrue(hold_test.judge(case, 2, False)["ok"])
        self.assertFalse(hold_test.judge(case, 2, True)["ok"])

    def test_parse_claude_output(self):
        arr = json.dumps([{"type": "system"}, {"type": "result", "result": "hi", "permission_denials": [{}, {}]}])
        self.assertEqual(hold_test.parse_claude_output(arr), ("hi", 2))
        obj = json.dumps({"type": "result", "result": "yo", "permission_denials": []})
        self.assertEqual(hold_test.parse_claude_output(obj), ("yo", 0))
        self.assertEqual(hold_test.parse_claude_output("not json"), ("not json", None))
        self.assertEqual(hold_test.parse_claude_output(json.dumps([{"type": "system"}])), ("", None))

    def test_claude_command_uses_the_tier_file_and_isolates_settings(self):
        for tier in (0, 1, 2):
            cmd = hold_test.claude_command("p", tier, 8, "1", None)
            with self.subTest(tier=tier):
                self.assertIn(os.path.join(TIERS_DIR, "claude-code", "tier%d.settings.json" % tier), cmd)
                self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "project,local")
                self.assertIn("--safe-mode", cmd)
                self.assertEqual(cmd[cmd.index("--permission-prompts") + 1], "none")

    def test_tier0_run_requires_the_disposable_host_flag(self):
        with mock.patch.object(hold_test.subprocess, "run") as run, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(hold_test.main(["run", "--tier", "0"]), 2)
            run.assert_not_called()
        self.assertIn("refusing: tier 0", err.getvalue())

    def test_world_reads_clean_before_any_action(self):
        import shutil
        import tempfile
        root = tempfile.mkdtemp(prefix="tierhold-test-")
        try:
            hold_test.setup_world(root)
            for c in hold_test.load_cases():
                if c["probe"]["kind"] != "output_contains":
                    with self.subTest(case=c["id"]):
                        self.assertFalse(hold_test.effect_happened(c["probe"], root, ""))
        finally:
            shutil.rmtree(root, ignore_errors=True)


FAKE_PREAMBLE = "#!%s\nimport json, os, sys\n" % sys.executable

# Each body runs as a fake `claude` executable. It sees the same argv and working
# directory as the real CLI: the prompt follows -p, the working directory is the workspace.
FAKE_BODIES = {
    "crash": "sys.exit(1)\n",
    "garbage": "print('<<not json>> {{{')\n",
    "never_touches_canary": (
        "print(json.dumps([{'type': 'system'}, {'type': 'result', 'subtype': 'success', "
        "'is_error': False, 'result': 'all done', 'permission_denials': [{}]}]))\n"),
    "alive": (
        "prompt = sys.argv[sys.argv.index('-p') + 1]\n"
        "reply = 'ok'\n"
        "if 'canary/keep.txt' in prompt:\n"
        "    reply += ' ' + open('canary/keep.txt').read()\n"
        "if 'liveness.txt' in prompt:\n"
        "    reply += '\\n' + open('liveness.txt').read()\n"
        "print(json.dumps([{'type': 'result', 'subtype': 'success', 'is_error': False,\n"
        "                   'result': reply, 'permission_denials': [{}]}]))\n"),
    "alive_and_deletes": (
        "prompt = sys.argv[sys.argv.index('-p') + 1]\n"
        "os.remove('canary/keep.txt')\n"
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,\n"
        "                  'result': open('liveness.txt').read(), 'permission_denials': []}))\n"),
    "alive_but_exit_1": (
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,\n"
        "                  'result': open('liveness.txt').read()}))\nsys.exit(1)\n"),
    "alive_but_flagged_error": (
        "print(json.dumps({'type': 'result', 'subtype': 'error_max_turns', 'is_error': True,\n"
        "                  'result': open('liveness.txt').read()}))\n"),
    "guesses_token": (
        "print(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False,\n"
        "                  'result': 'LIVE-0000000000000000'}))\n"),
    "hangs": "import time\ntime.sleep(60)\n",
}


class FakeClaude:
    """A throwaway directory with a fake `claude` first on PATH."""

    def __init__(self, kind):
        self.dir = tempfile.mkdtemp(prefix="fakeclaude-")
        path = os.path.join(self.dir, "claude")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(FAKE_PREAMBLE + FAKE_BODIES[kind])
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        self._patch = mock.patch.dict(os.environ, {"PATH": self.dir + os.pathsep + os.environ["PATH"]})

    def __enter__(self):
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


def run_fake(kind, tier=2, case=None, timeout=30):
    with FakeClaude(kind):
        return hold_test.run_claude(tier, case, None, 8, "1", False, None, timeout)


class LivenessTests(unittest.TestCase):
    """A case may only PASS when the run is proven alive and complete.

    Before the fix, a tier 2 run whose agent crashed read PASS on every blocked case,
    because the forbidden file was still there. These tests reproduce that without a model.
    """

    def test_the_bug_a_crashed_agent_used_to_look_like_a_held_tier(self):
        # The world is untouched, which is exactly what judge() reads as 'the tier held'.
        case = next(c for c in hold_test.load_cases() if c["id"] == "delete-file")
        self.assertTrue(hold_test.judge(case, 2, observed_effect=False)["ok"])

    def test_agent_that_exits_1_immediately_is_error_on_every_case(self):
        results = run_fake("crash")
        self.assertEqual(len(results), len(hold_test.load_cases()))
        for r in results:
            with self.subTest(case=r["case"]):
                self.assertEqual(r["status"], "ERROR")
                self.assertFalse(r["ok"])
                self.assertIn("code 1", r["error"])

    def test_agent_that_prints_garbage_is_error(self):
        for r in run_fake("garbage"):
            with self.subTest(case=r["case"]):
                self.assertEqual(r["status"], "ERROR")
                self.assertIn("parseable", r["error"])

    def test_agent_that_exits_0_but_never_touches_the_canary_is_error(self):
        for r in run_fake("never_touches_canary"):
            with self.subTest(case=r["case"]):
                self.assertEqual(r["status"], "ERROR")
                self.assertIn("canary", r["error"])

    def test_a_guessed_token_does_not_count(self):
        for r in run_fake("guesses_token", case="delete-file"):
            self.assertEqual(r["status"], "ERROR")

    def test_clean_exit_is_required_even_with_the_token_present(self):
        for r in run_fake("alive_but_exit_1", case="delete-file"):
            self.assertEqual(r["status"], "ERROR")
            self.assertIn("code 1", r["error"])

    def test_a_result_flagged_as_error_is_error(self):
        for r in run_fake("alive_but_flagged_error", case="delete-file"):
            self.assertEqual(r["status"], "ERROR")
            self.assertIn("flagged", r["error"])

    def test_timeout_is_error_and_kills_the_agent(self):
        results = run_fake("hangs", case="delete-file", timeout=1)
        self.assertEqual([r["status"] for r in results], ["ERROR"])
        self.assertIn("timeout", results[0]["error"])

    def test_missing_claude_is_error_not_a_crash(self):
        code, out, err, timed_out = hold_test.run_agent(["claude-does-not-exist-here"], tempfile.gettempdir(),
                                                        dict(os.environ), 5)
        self.assertIsNone(code)
        self.assertTrue(hold_test.liveness_error(code, timed_out, out, "LIVE-x"))

    def test_positive_control_a_live_agent_that_holds_the_tier_passes(self):
        # Without this, the tests above could be satisfied by a runner that never passes anything.
        results = run_fake("alive", tier=2)
        self.assertEqual([r["status"] for r in results], ["PASS"] * len(results), results)

    def test_a_live_agent_that_breaks_the_tier_fails(self):
        results = run_fake("alive_and_deletes", tier=2, case="delete-file")
        self.assertEqual(results[0]["status"], "FAIL")
        self.assertTrue(results[0]["effect"])

    def test_cases_prompt_for_the_canary(self):
        # The fake 'alive' only echoes the token if the prompt names liveness.txt.
        self.assertIn("liveness.txt", hold_test.LIVENESS_REQUEST)
        results = run_fake("alive", case="read-in-workspace")
        self.assertEqual(results[0]["status"], "PASS")

    def test_run_exits_nonzero_on_error_and_fail_and_zero_on_clean_pass(self):
        def code(kind, case):
            with FakeClaude(kind), contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hold_test.main(["run", "--tier", "2", "--case", case, "--timeout", "30"])
            return rc, out.getvalue()

        rc, out = code("crash", "delete-file")
        self.assertEqual(rc, 3)
        self.assertIn("ERROR", out)
        self.assertNotIn("PASS", out)
        rc, out = code("never_touches_canary", "delete-file")
        self.assertEqual(rc, 3)
        rc, out = code("alive_and_deletes", "delete-file")
        self.assertEqual(rc, 1)
        rc, out = code("alive", "delete-file")
        self.assertEqual(rc, 0)
        self.assertIn("PASS", out)

    def test_an_unknown_case_filter_is_not_a_pass(self):
        with FakeClaude("alive"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(hold_test.main(["run", "--tier", "2", "--case", "no-such-case"]), 1)

    def test_liveness_error_unit(self):
        good = json.dumps([{"type": "result", "subtype": "success", "is_error": False,
                            "result": "x LIVE-abc y"}])
        self.assertIsNone(hold_test.liveness_error(0, False, good, "LIVE-abc"))
        self.assertTrue(hold_test.liveness_error(0, False, good, "LIVE-zzz"))
        self.assertTrue(hold_test.liveness_error(1, False, good, "LIVE-abc"))
        self.assertTrue(hold_test.liveness_error(None, False, good, "LIVE-abc"))
        self.assertTrue(hold_test.liveness_error(None, True, "", "LIVE-abc"))
        self.assertTrue(hold_test.liveness_error(0, False, "", "LIVE-abc"))
        self.assertTrue(hold_test.liveness_error(0, False, json.dumps([{"type": "system"}]), "LIVE-abc"))
        self.assertTrue(hold_test.liveness_error(0, False, json.dumps({"result": 5}), "LIVE-abc"))

    def test_each_world_gets_its_own_unguessable_token(self):
        tokens = []
        for _ in range(2):
            root = tempfile.mkdtemp(prefix="tierhold-test-")
            try:
                hold_test.setup_world(root)
                tokens.append(hold_test.read_canary(root))
                self.assertNotIn(tokens[-1], hold_test.render_prompt(hold_test.load_cases()[0], root, 1))
            finally:
                shutil.rmtree(root, ignore_errors=True)
        self.assertNotEqual(tokens[0], tokens[1])
        self.assertTrue(tokens[0].startswith("LIVE-"))

    def test_check_with_require_liveness(self):
        root = tempfile.mkdtemp(prefix="tierhold-test-")
        try:
            hold_test.setup_world(root)
            reply = os.path.join(root, "reply.txt")
            args = ["check", "--root", root, "--case", "delete-file", "--tier", "2",
                    "--agent-output-file", reply, "--require-liveness"]
            with open(reply, "w", encoding="utf-8") as fh:
                fh.write("I did nothing.")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(hold_test.main(args), 3)
                with open(reply, "w", encoding="utf-8") as fh:
                    fh.write("done " + hold_test.read_canary(root))
                self.assertEqual(hold_test.main(args), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class ScrubTests(unittest.TestCase):
    """The tiers module and its tests must carry no private trace."""

    # Generic patterns only. Private names are checked by a pre-publish scrub that
    # lives outside this repository.
    FORBIDDEN = [r"/Us" + r"ers/\w", r"/home/\w", chr(0x2014)]

    def _files(self):
        for dirpath, dirnames, filenames in os.walk(TIERS_DIR):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if name.endswith((".py", ".md", ".json", ".json5")):
                    yield os.path.join(dirpath, name)
        yield os.path.abspath(__file__)

    def test_no_private_trace(self):
        for path in self._files():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for pattern in self.FORBIDDEN:
                with self.subTest(path=os.path.relpath(path, ROOT), pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), "found %r" % pattern)

    def test_scrub_patterns_can_fail(self):
        for sample in ("/Us" + "ers/someone/x", "/ho" + "me/someone", "a" + chr(0x2014) + "b"):
            with self.subTest(sample=sample):
                self.assertTrue(any(re.search(p, sample) for p in self.FORBIDDEN))
        self.assertFalse(any(re.search(p, "a plain sentence about tiers") for p in self.FORBIDDEN))

    def test_example_domains_are_reserved(self):
        for path in self._files():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for host in re.findall(r"[\w.-]+@([\w.-]+)", text):
                if host.endswith((".invalid", "example.invalid")) or host in ("example.invalid",):
                    continue
                if re.match(r"^\w+\.(py|md|json)$", host):
                    continue
                with self.subTest(path=os.path.relpath(path, ROOT), host=host):
                    self.fail("email-like address on a non-.invalid domain: %s" % host)

    def test_json_files_are_strict_json(self):
        for path in self._files():
            if path.endswith(".json"):
                with self.subTest(path=os.path.relpath(path, ROOT)):
                    with open(path, encoding="utf-8") as f:
                        json.load(f)


if __name__ == "__main__":
    unittest.main()
