"""Tests for onboarding/check_placeholders.py and the onboarding files (stdlib unittest).

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONBOARDING = os.path.join(REPO, "onboarding")
TEMPLATE = os.path.join(ONBOARDING, "context-template")
CHECKER = os.path.join(ONBOARDING, "check_placeholders.py")

_spec = importlib.util.spec_from_file_location("check_placeholders", CHECKER)
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

NAME_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")


def run_main(*argv):
    """Run check_placeholders.main in-process. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cp.main(list(argv))
        except SystemExit as exc:  # argparse errors
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def template_names():
    names = set()
    for root, _dirs, files in os.walk(TEMPLATE):
        for name in files:
            names.update(NAME_RE.findall(read(os.path.join(root, name))))
    return names


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="onboarding-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, rel, text, mode="w"):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        kwargs = {} if "b" in mode else {"encoding": "utf-8"}
        with open(path, mode, **kwargs) as fh:
            fh.write(text)
        return path


class CheckerTests(TempDirCase):
    def test_reports_name_line_and_file(self):
        path = self.write("a.md", "first\nName: {{OWNER_NAME}}\nthird\n")
        findings, scanned, _ = cp.scan([self.tmp])
        self.assertEqual(findings, [(path, 2, "OWNER_NAME")])
        self.assertEqual(scanned, 1)

    def test_every_occurrence_on_a_line_is_reported(self):
        self.write("a.md", "{{A}} and {{B}} and {{A}}\n")
        findings, _, _ = cp.scan([self.tmp])
        self.assertEqual([n for _, _, n in findings], ["A", "B", "A"])

    def test_spaces_inside_braces_still_count(self):
        self.write("a.md", "x {{ SPACED_NAME }} y\n")
        findings, _, _ = cp.scan([self.tmp])
        self.assertEqual([n for _, _, n in findings], ["SPACED_NAME"])

    def test_clean_folder_exits_zero(self):
        self.write("a.md", "all filled in\n")
        self.write("sub/b.md", "also filled, with { single } braces and {{}} empty\n")
        code, out, _ = run_main(self.tmp)
        self.assertEqual(code, 0)
        self.assertIn("ok:", out)
        self.assertIn("2 files scanned", out)

    def test_unfilled_exits_one_and_prints_each(self):
        self.write("a.md", "{{ONE}}\n")
        self.write("sub/b.md", "ok\n{{TWO}}\n")
        code, out, _ = run_main(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("a.md:1: {{ONE}}", out)
        self.assertIn("b.md:2: {{TWO}}", out)
        self.assertIn("2 unfilled in 2 file(s)", out)

    def test_ignore_allows_named_placeholders_only(self):
        self.write("a.md", "{{KEEP}} {{FIX}}\n")
        code, out, _ = run_main(self.tmp, "--ignore", "KEEP")
        self.assertEqual(code, 1)
        self.assertIn("{{FIX}}", out)
        self.assertNotIn("{{KEEP}}", out)
        code, _, _ = run_main(self.tmp, "--ignore", "KEEP", "--ignore", "FIX")
        self.assertEqual(code, 0)

    def test_missing_path_is_usage_error(self):
        code, _, err = run_main(os.path.join(self.tmp, "does-not-exist"))
        self.assertEqual(code, 2)
        self.assertIn("no such path", err)

    def test_empty_folder_is_error_not_pass(self):
        code, _, err = run_main(self.tmp)
        self.assertEqual(code, 2)
        self.assertIn("no text files", err)

    def test_hidden_and_archive_folders_are_skipped(self):
        self.write("a.md", "clean\n")
        self.write(".git/x.md", "{{HIDDEN}}\n")
        self.write("archive/20260101-000000/USER.md", "{{OLD}}\n")
        code, out, _ = run_main(self.tmp)
        self.assertEqual(code, 0, out)

    def test_binary_and_non_utf8_files_are_skipped_and_counted(self):
        self.write("a.md", "clean\n")
        self.write("img.bin", b"\x00\x01{{BIN}}\x02", mode="wb")
        self.write("latin.txt", b"caf\xe9 {{LATIN}}", mode="wb")
        code, out, _ = run_main(self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn("2 binary skipped", out)

    def test_single_file_path_works(self):
        path = self.write("a.md", "{{ONE}}\n")
        code, out, _ = run_main(path)
        self.assertEqual(code, 1)
        self.assertIn("{{ONE}}", out)

    def test_cli_exit_codes_match_main(self):
        self.write("a.md", "{{ONE}}\n")
        bad = subprocess.run([sys.executable, "-I", CHECKER, self.tmp],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        missing = subprocess.run([sys.executable, "-I", CHECKER, self.tmp + "-nope"],
                                 capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)


class TemplateTests(TempDirCase):
    EXPECTED_FILES = [
        "USER.md", "company.md", "decisions.md",
        "knowledge/README.md", "memory/README.md", "inbox/README.md",
    ]

    def test_template_files_exist(self):
        for rel in self.EXPECTED_FILES:
            self.assertTrue(os.path.isfile(os.path.join(TEMPLATE, rel)), rel)

    def test_unfilled_template_fails_the_check(self):
        """Negative control: the gate must be able to fail on the shipped template."""
        code, out, _ = run_main(TEMPLATE)
        self.assertEqual(code, 1)
        self.assertIn("{{OWNER_NAME}}", out)

    def test_filled_copy_passes_the_check(self):
        dest = os.path.join(self.tmp, "ctx")
        shutil.copytree(TEMPLATE, dest)
        for root, _dirs, files in os.walk(dest):
            for name in files:
                path = os.path.join(root, name)
                text = NAME_RE.sub("filled value", read(path))
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
        code, out, _ = run_main(dest)
        self.assertEqual(code, 0, out)

    def test_one_placeholder_left_behind_is_caught(self):
        dest = os.path.join(self.tmp, "ctx")
        shutil.copytree(TEMPLATE, dest)
        for root, _dirs, files in os.walk(dest):
            for name in files:
                path = os.path.join(root, name)
                text = NAME_RE.sub("filled value", read(path))
                if name == "company.md":
                    text += "\nLeft over: {{ACCEPTANCE_CASE_3}}\n"
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
        code, out, _ = run_main(dest)
        self.assertEqual(code, 1)
        self.assertIn("ACCEPTANCE_CASE_3", out)

    def test_fill_table_matches_template(self):
        """synthesize-profile.md lists exactly the placeholders the template contains."""
        table = set()
        for line in read(os.path.join(ONBOARDING, "synthesize-profile.md")).splitlines():
            if line.startswith("| `{{"):
                table.update(NAME_RE.findall(line.split("|")[1]))
        self.assertEqual(table, template_names())

    def test_fill_table_names_the_file_each_placeholder_lives_in(self):
        for line in read(os.path.join(ONBOARDING, "synthesize-profile.md")).splitlines():
            if not line.startswith("| `{{"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            names, files = NAME_RE.findall(cells[0]), cells[1]
            if files == "all":
                continue
            for name in names:
                for f in re.findall(r"`([^`]+)`", files):
                    self.assertIn("{{%s}}" % name, read(os.path.join(TEMPLATE, f)),
                                  "%s not in %s" % (name, f))


class QuestionnaireTests(unittest.TestCase):
    @staticmethod
    def parse(path):
        """Return {number: [placeholder names]} from '### N.' headings and Feeds lines."""
        result, current = {}, None
        for line in read(path).splitlines():
            heading = re.match(r"### (\d+)\. ", line)
            if heading:
                current = int(heading.group(1))
                result[current] = []
            elif current is not None and re.match(r"(Feeds|Zasila):", line):
                result[current] = NAME_RE.findall(line)
        return result

    def setUp(self):
        self.en = self.parse(os.path.join(ONBOARDING, "questionnaire.en.md"))
        self.pl = self.parse(os.path.join(ONBOARDING, "questionnaire.pl.md"))

    def test_eighteen_numbered_questions_in_both_languages(self):
        self.assertEqual(sorted(self.en), list(range(1, 19)))
        self.assertEqual(sorted(self.pl), list(range(1, 19)))

    def test_every_question_feeds_something(self):
        for number in range(1, 19):
            self.assertTrue(self.en[number], "EN question %d has no Feeds line" % number)
            self.assertTrue(self.pl[number], "PL question %d has no Zasila line" % number)

    def test_languages_agree_on_what_each_question_feeds(self):
        self.assertEqual(self.en, self.pl)

    def test_fed_placeholders_exist_in_template(self):
        fed = {n for names in self.en.values() for n in names}
        self.assertLessEqual(fed, template_names())

    def test_only_derived_placeholders_are_not_fed_by_questions(self):
        fed = {n for names in self.en.values() for n in names}
        derived = {"OWNER_NAME", "ONBOARDING_DATE", "FIRST_PLAYBOOKS",
                   "CONFIRMED_DECISIONS", "OPEN_ITEMS"}
        self.assertEqual(template_names() - fed, derived)


class HygieneTests(unittest.TestCase):
    def files(self):
        for root, _dirs, files in os.walk(ONBOARDING):
            if "__pycache__" in root:
                continue
            for name in files:
                yield os.path.join(root, name)

    def test_no_em_dashes(self):
        for path in self.files():
            self.assertNotIn(chr(0x2014), read(path), path)

    def test_no_absolute_home_paths(self):
        pattern = re.compile("(/" + "Users/|/home/[a-z])")
        for path in self.files():
            self.assertIsNone(pattern.search(read(path)), path)


if __name__ == "__main__":
    unittest.main()
