"""Tests for the overlay fixes: reads fenced at tier 1, mail asks, apply_patch, tiercheck pins.

Standard library only: python3 -m unittest discover tests -p "test_tier_overlays.py"
"""

import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS_DIR = os.path.join(ROOT, "tiers")
sys.path.insert(0, TIERS_DIR)

import hold_test  # noqa: E402
import tiercheck  # noqa: E402


class ShippedOverlayTests(unittest.TestCase):
    """The shipped files themselves, read as they are on disk."""

    def test_claude_tiers_1_and_2_refuse_reads_outside_the_working_directories(self):
        cc = tiercheck.load_claude()
        for t in (1, 2):
            with self.subTest(tier=t):
                self.assertIs(cc[t]["permissions"].get("blockReadsOutsideWorkingDirectories"), True)

    def test_claude_tiers_1_and_2_deny_env_variants(self):
        cc = tiercheck.load_claude()
        for t in (1, 2):
            for rule in ("Read(//**/.env)", "Read(//**/.env.*)"):
                with self.subTest(tier=t, rule=rule):
                    self.assertIn(rule, cc[t]["permissions"]["deny"])

    def test_claude_tier1_asks_before_every_mail_command_the_world_shims(self):
        cc = tiercheck.load_claude()
        for name in hold_test.MAIL_COMMANDS:
            rule = "Bash(%s *)" % name
            with self.subTest(rule=rule):
                self.assertIn(rule, cc[1]["permissions"]["ask"])
                self.assertTrue(tiercheck.covered_by_deny(rule, cc[2]["permissions"]["deny"]))

    def test_openclaw_tiers_1_and_2_deny_apply_patch(self):
        oc = tiercheck.load_openclaw()
        for t in (1, 2):
            with self.subTest(tier=t):
                self.assertIn("apply_patch", tiercheck.expand_openclaw_deny(oc[t]["tools"]["deny"]))

    def test_openclaw_tier1_comment_no_longer_says_apply_patch_cannot_delete(self):
        with open(os.path.join(TIERS_DIR, "openclaw", "tier1.json5"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("apply_patch cannot delete", text)
        self.assertIn("Delete File", text)


class TiercheckPinTests(unittest.TestCase):
    """Negative controls: each loosening below must make tiercheck complain."""

    def _oc(self):
        return copy.deepcopy(tiercheck.load_openclaw())

    def _cc(self):
        return copy.deepcopy(tiercheck.load_claude())

    def _assert_caught(self, problems, *needles):
        self.assertTrue(any(all(n in p for n in needles) for p in problems),
                        "no problem mentions %r: %r" % (needles, problems))

    def test_shipped_files_still_pass(self):
        self.assertEqual(tiercheck.check_openclaw(tiercheck.load_openclaw()), [])
        self.assertEqual(tiercheck.check_claude(tiercheck.load_claude()), [])

    def test_openclaw_full_profile_at_tier1_or_tier2_is_caught(self):
        for t in (1, 2):
            docs = self._oc()
            docs[t]["tools"]["profile"] = "full"
            with self.subTest(tier=t):
                self._assert_caught(tiercheck.check_openclaw(docs), "tools.profile", "tier %d" % t)

    def test_openclaw_tier1_sandbox_non_main_is_caught(self):
        docs = self._oc()
        docs[1]["agents"]["defaults"]["sandbox"]["mode"] = "non-main"
        self._assert_caught(tiercheck.check_openclaw(docs), "sandbox.mode", "tier 1")

    def test_openclaw_tier1_without_apply_patch_deny_is_caught(self):
        docs = self._oc()
        docs[1]["tools"]["deny"] = [d for d in docs[1]["tools"]["deny"] if d != "apply_patch"]
        self._assert_caught(tiercheck.check_openclaw(docs), "apply_patch", "tier 1")

    def test_claude_read_lock_removed_is_caught(self):
        for t in (1, 2):
            docs = self._cc()
            docs[t]["permissions"].pop("blockReadsOutsideWorkingDirectories", None)
            with self.subTest(tier=t):
                self._assert_caught(tiercheck.check_claude(docs),
                                    "blockReadsOutsideWorkingDirectories", "tier %d" % t)

    def test_claude_tier1_sandbox_network_opened_is_caught(self):
        docs = self._cc()
        docs[1]["sandbox"]["network"]["allowedDomains"] = ["*"]
        self._assert_caught(tiercheck.check_claude(docs), "allowedDomains")
        docs = self._cc()
        del docs[1]["sandbox"]["network"]
        self._assert_caught(tiercheck.check_claude(docs), "allowedDomains")

    def test_claude_tier1_unsandboxed_fallback_is_caught(self):
        docs = self._cc()
        docs[1]["sandbox"]["failIfUnavailable"] = False
        self._assert_caught(tiercheck.check_claude(docs), "failIfUnavailable")

    def test_claude_tier1_edit_or_write_allow_is_caught(self):
        for rule in ("Write(//**)", "Edit(//**)", "Edit"):
            docs = self._cc()
            docs[1]["permissions"]["allow"].append(rule)
            with self.subTest(rule=rule):
                self._assert_caught(tiercheck.check_claude(docs), "tier 1", rule)

    def test_claude_tier1_mode_other_than_accept_edits_is_caught(self):
        docs = self._cc()
        docs[1]["permissions"]["defaultMode"] = "auto"
        self._assert_caught(tiercheck.check_claude(docs), "tier 1", "acceptEdits")

    def test_claude_tier2_allow_rule_missing_at_tier1_is_caught(self):
        docs = self._cc()
        docs[2]["permissions"]["allow"].append("TodoWrite")
        self._assert_caught(tiercheck.check_claude(docs), "TodoWrite", "tier 2")

    def test_claude_tier1_dropping_a_mail_ask_is_caught(self):
        for name in hold_test.MAIL_COMMANDS:
            rule = "Bash(%s *)" % name
            docs = self._cc()
            docs[1]["permissions"]["ask"] = [r for r in docs[1]["permissions"]["ask"] if r != rule]
            with self.subTest(rule=rule):
                self._assert_caught(tiercheck.check_claude(docs), rule)

    def test_ok_report_names_what_is_compared(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tiercheck.main(), 0)
        text = out.getvalue()
        for needle in ("tools.profile", "sandbox.mode", "apply_patch",
                       "blockReadsOutsideWorkingDirectories", "allowedDomains",
                       "failIfUnavailable", "permissions.allow", "not checked"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


class TiercheckListTypeTests(unittest.TestCase):
    """A rule list written as one string must be an error: iterating a string
    compares single letters, and every letter passes the set checks."""

    def _assert_type_error(self, problems, label, tier):
        self.assertTrue(any(label in p and "must be a list of strings" in p and "tier %d" % tier in p
                            for p in problems),
                        "no type problem for %s at tier %d: %r" % (label, tier, problems))

    def test_claude_rule_list_written_as_a_string_is_caught(self):
        for kind, value in (("allow", "Read"), ("ask", "Bash(rm *)"), ("deny", "Edit")):
            for t in tiercheck.TIERS:
                docs = copy.deepcopy(tiercheck.load_claude())
                docs[t]["permissions"][kind] = value
                with self.subTest(kind=kind, tier=t):
                    self._assert_type_error(tiercheck.check_claude(docs),
                                            "permissions.%s" % kind, t)

    def test_claude_rule_list_written_as_an_object_or_with_a_number_is_caught(self):
        for value in ({"Read": True}, ["Read", 1]):
            docs = copy.deepcopy(tiercheck.load_claude())
            docs[2]["permissions"]["allow"] = value
            with self.subTest(value=value):
                self._assert_type_error(tiercheck.check_claude(docs), "permissions.allow", 2)

    def test_openclaw_deny_written_as_a_string_is_caught(self):
        for t, value in ((0, ""), (1, "message"), (2, "group:fs")):
            docs = copy.deepcopy(tiercheck.load_openclaw())
            docs[t]["tools"]["deny"] = value
            with self.subTest(tier=t, value=value):
                self._assert_type_error(tiercheck.check_openclaw(docs), "tools.deny", t)

    def test_empty_and_single_rule_lists_stay_clean(self):
        docs = copy.deepcopy(tiercheck.load_claude())
        docs[2]["permissions"]["allow"] = []
        self.assertEqual(tiercheck.check_claude(docs), [])
        docs[2]["permissions"]["allow"] = ["Read"]
        self.assertEqual(tiercheck.check_claude(docs), [])
        oc = copy.deepcopy(tiercheck.load_openclaw())
        self.assertEqual(oc[0]["tools"]["deny"], [])
        self.assertEqual(tiercheck.check_openclaw(oc), [])

    def test_cli_on_a_copy_with_allow_as_a_string_fails(self):
        """The command a reader runs, on overlay files edited on disk."""
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("tiercheck.py", "json5lite.py"):
                shutil.copy(os.path.join(TIERS_DIR, name), tmp)
            for sub in ("openclaw", "claude-code"):
                shutil.copytree(os.path.join(TIERS_DIR, sub), os.path.join(tmp, sub))
            clean = subprocess.run([sys.executable, os.path.join(tmp, "tiercheck.py")],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            for t in (1, 2):
                path = os.path.join(tmp, "claude-code", "tier%d.settings.json" % t)
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
                doc["permissions"]["allow"] = "Read"
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, indent=2)
            p = subprocess.run([sys.executable, os.path.join(tmp, "tiercheck.py")],
                               capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("tier check FAILED", p.stdout)
        self.assertIn("claude tier 1: permissions.allow must be a list of strings, got 'Read'",
                      p.stdout)
        self.assertNotIn("tier check ok", p.stdout)


if __name__ == "__main__":
    unittest.main()


class TiercheckBooleanTypeTests(unittest.TestCase):
    """A switch written as the string "false" is truthy to a reader and must be an error."""

    def test_openclaw_switch_written_as_a_string_is_caught(self):
        for path in (("tools", "fs", "workspaceOnly"), ("tools", "elevated", "enabled"),
                     ("tools", "agentToAgent", "enabled")):
            for t in tiercheck.TIERS:
                docs = copy.deepcopy(tiercheck.load_openclaw())
                node = docs[t]
                for key in path[:-1]:
                    node = node.setdefault(key, {})
                node[path[-1]] = "false"
                label = ".".join(path)
                with self.subTest(path=label, tier=t):
                    problems = tiercheck.check_openclaw(docs)
                    self.assertTrue(any(label in p and "must be true or false" in p and "tier %d" % t in p
                                        for p in problems), problems)

    def test_shipped_switches_stay_clean(self):
        self.assertEqual(tiercheck.check_openclaw(copy.deepcopy(tiercheck.load_openclaw())), [])
