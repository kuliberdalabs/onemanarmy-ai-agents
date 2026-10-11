"""Checkers must fail when they cannot see what they check (stdlib unittest).

Covers onboarding/check_placeholders.py on files it cannot read or decode, and
scripts/validate_skill.py on frontmatter that is not valid YAML.

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "onboarding", "check_placeholders.py")
VALIDATOR = os.path.join(REPO, "scripts", "validate_skill.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cp = load("check_placeholders_fix", CHECKER)
vs = load("validate_skill_fix", VALIDATOR)

IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


def run_checker(*argv):
    """Run check_placeholders.main in-process. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cp.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fix-checkers-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, rel, data):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        return path

    def lock(self, path):
        """Remove all permissions from `path`; skip when they still allow reading."""
        mode = os.stat(path).st_mode
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, mode)  # runs before the rmtree cleanup
        if os.access(path, os.R_OK):
            self.skipTest("permissions do not stop this user from reading")


class PlaceholderCheckerReadErrors(TempDirCase):
    def test_cp1250_file_with_placeholders_fails(self):
        self.write("clean.md", "all filled in\n")
        self.write("USER.md", "Właściciel: Grzegorz Żółć\nName: {{OWNER_NAME}}\n".encode("cp1250"))
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("ok:", out)
        self.assertIn("USER.md is not UTF-8 text (byte 0xb3 on line 1); save it as UTF-8", err)
        self.assertIn("could not check 1 path(s), so the result is incomplete (1 scanned)", err)
        self.assertNotIn("binary", out + err)

    def test_cp1250_single_file_names_the_reason(self):
        path = self.write("USER.md", "Zółć {{OWNER_NAME}}\n".encode("cp1250"))
        code, _, err = run_checker(path)
        self.assertEqual(code, 2)
        self.assertIn(f"error: {path} is not UTF-8 text", err)
        self.assertNotIn("no text files scanned", err)

    def test_utf16_text_is_not_treated_as_binary(self):
        self.write("clean.md", "all filled in\n")
        self.write("USER.md", "Name: {{OWNER_NAME}}\n".encode("utf-16"))
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 2, out + err)
        self.assertIn("USER.md is not UTF-8 text (it is UTF-16)", err)
        self.assertNotIn("binary", out + err)

    @unittest.skipIf(IS_ROOT, "root can read files without permissions")
    def test_unreadable_file_fails(self):
        self.write("clean.md", "all filled in\n")
        self.lock(self.write("USER.md", "Name: {{OWNER_NAME}}\n"))
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("ok:", out)
        self.assertIn("cannot read " + os.path.join(self.tmp, "USER.md") + ": ", err)

    @unittest.skipIf(IS_ROOT, "root can list folders without permissions")
    def test_unlistable_subfolder_fails(self):
        self.write("clean.md", "all filled in\n")
        self.write("sub/USER.md", "Name: {{OWNER_NAME}}\n")
        self.lock(os.path.join(self.tmp, "sub"))
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 2, out + err)
        self.assertNotIn("ok:", out)
        self.assertIn("cannot list " + os.path.join(self.tmp, "sub") + ": ", err)

    @unittest.skipIf(IS_ROOT, "root can list folders without permissions")
    def test_unlistable_folder_argument_fails_next_to_a_clean_one(self):
        clean = self.write("ok/clean.md", "all filled in\n")
        self.write("locked/USER.md", "Name: {{OWNER_NAME}}\n")
        locked = os.path.join(self.tmp, "locked")
        self.lock(locked)
        code, out, err = run_checker(locked, clean)
        self.assertEqual(code, 2, out + err)
        self.assertIn(f"cannot list {locked}: ", err)

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_dangling_symlink_fails(self):
        self.write("clean.md", "all filled in\n")
        try:
            os.symlink(os.path.join(self.tmp, "gone.md"), os.path.join(self.tmp, "USER.md"))
        except OSError:
            self.skipTest("cannot create symlinks here")
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 2, out + err)
        self.assertIn("cannot read " + os.path.join(self.tmp, "USER.md"), err)

    def test_findings_are_still_listed_when_a_file_is_unreadable(self):
        self.write("a.md", "{{ONE}}\n")
        self.write("b.md", b"caf\xe9 {{TWO}}\n")
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 2, out + err)
        self.assertIn("a.md:1: {{ONE}}", out)
        self.assertIn("b.md is not UTF-8 text (byte 0xe9 on line 1)", err)

    def test_scan_reports_errors(self):
        path = self.write("USER.md", b"caf\xe9 {{LATIN}}\n")
        findings, scanned, skipped, errors = cp.scan([self.tmp])
        self.assertEqual((findings, scanned, skipped), ([], 0, 0))
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith(f"{path} is not UTF-8 text"), errors)

    def test_nul_file_is_still_skipped_as_binary(self):
        self.write("clean.md", "all filled in\n")
        self.write("img.bin", b"\x00\x01{{BIN}}\x02")
        code, out, err = run_checker(self.tmp)
        self.assertEqual(code, 0, out + err)
        self.assertIn("ok: no unfilled placeholders (1 files scanned, 1 binary skipped)", out)

    def test_cli_exit_code_is_two(self):
        self.write("clean.md", "all filled in\n")
        self.write("USER.md", "Zółć {{OWNER_NAME}}\n".encode("cp1250"))
        result = subprocess.run([sys.executable, "-I", CHECKER, self.tmp],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("is not UTF-8 text", result.stderr)


DESCRIPTION = ("Checks the frontmatter and every referenced file so that a broken skill "
               "never reaches anyone who installs it.")


class SkillFrontmatter(TempDirCase):
    def skill(self, frontmatter, name="demo-skill"):
        self.write(f"{name}/SKILL.md", f"---\n{frontmatter}\n---\n\n# Demo\n")
        return os.path.join(self.tmp, name)

    def problems(self, frontmatter, name="demo-skill"):
        return vs.validate(Path(self.skill(frontmatter, name)))

    def assertRejected(self, frontmatter, expected, name="demo-skill"):
        problems = self.problems(frontmatter, name)
        self.assertTrue(any(expected in p for p in problems),
                        f"expected {expected!r} in {problems}")

    def test_description_is_long_enough(self):
        self.assertGreaterEqual(len(DESCRIPTION), 80)

    def test_plain_description_with_colon_space_is_rejected(self):
        self.assertRejected(
            f"name: demo-skill\ndescription: Validate this skill: {DESCRIPTION}",
            'SKILL.md line 3: description contains ": ", which YAML reads as the start of another key;'
            " put the whole value in double quotes")

    def test_plain_description_with_space_hash_is_rejected(self):
        self.assertRejected(
            f"name: demo-skill\ndescription: {DESCRIPTION} #beta",
            'SKILL.md line 3: description contains " #", which YAML reads as the start of a comment')

    def test_plain_value_ending_in_colon_is_rejected(self):
        self.assertRejected(f"description: {DESCRIPTION} Steps:\nname: demo-skill",
                            'SKILL.md line 2: description ends with ":"')

    def test_unclosed_double_quote_is_rejected(self):
        self.assertRejected(f'name: demo-skill\ndescription: "{DESCRIPTION}',
                            "SKILL.md line 3: description opens a double quote that is not closed")

    def test_mismatched_quotes_are_rejected(self):
        self.assertRejected(f"name: demo-skill\ndescription: \"{DESCRIPTION}'",
                            "SKILL.md line 3: description opens a double quote that is not closed")
        self.assertRejected(f"name: demo-skill\ndescription: '{DESCRIPTION}\"",
                            "SKILL.md line 3: description opens a single quote that is not closed")

    def test_text_after_closing_quote_is_rejected(self):
        self.assertRejected(f'name: demo-skill\ndescription: "Say "hi" first. {DESCRIPTION}"',
                            "description has text after the closing double quote")
        self.assertRejected(f"name: demo-skill\ndescription: 'It's here. {DESCRIPTION}'",
                            "description has text after the closing single quote")

    def test_unknown_escape_in_double_quotes_is_rejected(self):
        self.assertRejected(f'name: demo-skill\ndescription: "Reads C:\\Users. {DESCRIPTION}"',
                            "description uses the escape \\U inside double quotes")

    def test_value_starting_with_an_indicator_is_rejected(self):
        for value in ("> folded", "[a, b]", "&anchor text", "*alias", "!tag text", "- item"):
            with self.subTest(value=value):
                self.assertRejected(f"name: demo-skill\ndescription: {value} {DESCRIPTION}",
                                    f"description starts with {value[0]!r}")

    def test_key_without_space_after_colon_is_rejected(self):
        self.assertRejected(f"name:demo-skill\ndescription: {DESCRIPTION}",
                            "SKILL.md line 2: expected \"name: value\" or \"description: value\"")

    def test_duplicate_key_is_rejected(self):
        self.assertRejected(f"name: demo-skill\ndescription: {DESCRIPTION}\nname: demo-skill",
                            "SKILL.md line 4: duplicate key 'name'")

    def test_indented_continuation_is_rejected(self):
        self.assertRejected(f"name: demo-skill\ndescription: {DESCRIPTION}\n  and more text",
                            "SKILL.md line 4: indented line")

    def test_tab_is_rejected(self):
        self.assertRejected(f"name: demo-skill\ndescription:\t{DESCRIPTION}",
                            "SKILL.md line 3: character U+0009 is not allowed")

    def test_plain_value_yaml_reads_as_a_number_is_rejected(self):
        self.assertRejected(f"name: 2026\ndescription: {DESCRIPTION}",
                            "SKILL.md line 2: name is '2026', which YAML reads as a boolean, null,"
                            " number or date", name="2026")

    def test_quoted_values_are_read_as_yaml_reads_them(self):
        quoted = DESCRIPTION.replace("broken", "\\\"broken\\\"").replace("so that", "so that:")
        self.assertEqual(self.problems(f'name: "demo-skill"\ndescription: "{quoted}"'), [])
        single = DESCRIPTION.replace("broken", "user''s broken")
        self.assertEqual(self.problems(f"name: 'demo-skill'\ndescription: '{single}'"), [])
        self.assertEqual(self.problems(f'name: "2026"\ndescription: "{DESCRIPTION}"', name="2026"), [])

    def test_plain_quotes_and_apostrophes_inside_text_stay_valid(self):
        value = ('Close a session when the user says "wrap up" or "done", '
                 "using the project's owner file. " + DESCRIPTION)
        self.assertEqual(self.problems(f"name: demo-skill\ndescription: {value}"), [])

    def test_shipped_skill_still_validates(self):
        self.assertEqual(vs.validate(Path(REPO) / "core" / "skills" / "session-end"), [])

    def test_cli_exit_code_is_one(self):
        skill = self.skill(f"name: demo-skill\ndescription: Validate this skill: {DESCRIPTION}")
        result = subprocess.run([sys.executable, "-I", VALIDATOR, skill],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("INVALID demo-skill: SKILL.md line 3: description contains", result.stdout)
        self.assertIn("1 of 1 skill(s) invalid", result.stdout)


if __name__ == "__main__":
    unittest.main()


class SkillFilesTheValidatorCannotRead(TempDirCase):
    """"valid" must mean every file was checked; an unreadable folder is a problem."""

    def skill(self):
        self.write("demo-skill/SKILL.md", f"---\nname: demo-skill\ndescription: {DESCRIPTION}\n---\n\n# Demo\n")
        self.write("demo-skill/assets/private/bad.json", "{not json")
        return Path(self.tmp) / "demo-skill"

    def test_bad_json_is_found_when_the_folder_is_readable(self):
        problems = vs.validate(self.skill())
        self.assertTrue(any("invalid JSON" in p for p in problems), problems)

    def test_unreadable_assets_folder_is_reported_not_skipped(self):
        skill = self.skill()
        self.lock(str(skill / "assets" / "private"))
        problems = vs.validate(skill)
        self.assertTrue(any(p.startswith("cannot read ") and "private" in p for p in problems), problems)

    def test_cli_does_not_say_valid_when_a_folder_was_skipped(self):
        skill = self.skill()
        self.lock(str(skill / "assets" / "private"))
        out = subprocess.run([sys.executable, VALIDATOR, str(skill)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertNotIn("valid", out.stdout.splitlines()[-1].replace("invalid", ""))


class SkillInterfaceTheValidatorCannotRead(TempDirCase):
    def test_unreadable_agents_folder_is_reported_not_skipped(self):
        self.write("demo-skill/SKILL.md", f"---\nname: demo-skill\ndescription: {DESCRIPTION}\n---\n\n# Demo\n")
        self.write("demo-skill/agents/openai.yaml", "interface:\n  display_name: broken\n")
        skill = Path(self.tmp) / "demo-skill"
        self.assertTrue(any("needs a quoted" in p for p in vs.validate(skill)))
        self.lock(str(skill / "agents"))
        problems = vs.validate(skill)
        self.assertTrue(any(p.startswith("cannot read ") and "openai.yaml" in p for p in problems), problems)


class LinkedFoldersAreChecked(TempDirCase):
    def test_placeholder_in_a_linked_knowledge_folder_is_found(self):
        self.write("profile/USER.md", "Name: Grzegorz\n")
        self.write("shared/note.md", "Do not keep {{NEVER_STORE}} here\n")
        os.symlink(os.path.join(self.tmp, "shared"), os.path.join(self.tmp, "profile", "knowledge"))
        code, out, _ = run_checker(os.path.join(self.tmp, "profile"))
        self.assertEqual(code, 1, out)
        self.assertIn("NEVER_STORE", out)

    def test_a_link_cycle_is_walked_once(self):
        self.write("profile/USER.md", "Name: Grzegorz\n")
        os.symlink(os.path.join(self.tmp, "profile"), os.path.join(self.tmp, "profile", "loop"))
        code, out, _ = run_checker(os.path.join(self.tmp, "profile"))
        self.assertEqual(code, 0, out)
        self.assertIn("1 files scanned", out)


class SkillLinkedAssetsAreChecked(TempDirCase):
    def test_bad_json_in_a_linked_assets_folder_is_found(self):
        self.write("demo-skill/SKILL.md", f"---\nname: demo-skill\ndescription: {DESCRIPTION}\n---\n\n# Demo\n")
        self.write("shared/config.json", '{"brand": "Example",}')
        os.makedirs(os.path.join(self.tmp, "demo-skill", "assets"))
        os.symlink(os.path.join(self.tmp, "shared"), os.path.join(self.tmp, "demo-skill", "assets", "common"))
        problems = vs.validate(Path(self.tmp) / "demo-skill")
        self.assertTrue(any("invalid JSON" in p and "config.json" in p for p in problems), problems)


class SkillNestedScriptsAreChecked(TempDirCase):
    def test_syntax_error_in_a_nested_helper_is_found(self):
        self.write("demo-skill/SKILL.md", f"---\nname: demo-skill\ndescription: {DESCRIPTION}\n---\n\n# Demo\n")
        self.write("demo-skill/scripts/run.py", "from helpers import read_input\n")
        self.write("demo-skill/scripts/helpers/read_input.py", "def load()\n    return 1\n")
        problems = vs.validate(Path(self.tmp) / "demo-skill")
        self.assertTrue(any("invalid Python" in p and "read_input.py" in p for p in problems), problems)
