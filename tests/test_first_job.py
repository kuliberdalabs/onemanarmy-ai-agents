"""Tests for examples/first-job (stdlib unittest; pytest also runs them).

    python3 -m unittest discover tests -p 'test_first_job.py' -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOB = os.path.join(REPO, "examples", "first-job")
DATA = os.path.join(JOB, "data")
GATE = os.path.join(JOB, "gate", "check_ledger.py")
FIXTURES = os.path.join(JOB, "gate", "fixtures")
REGISTRY = os.path.join(JOB, "gate", "registry.yaml")
SELFTEST = os.path.join(REPO, "core", "gate-selftest", "selftest.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load("check_ledger", GATE)
selftest = _load("selftest_for_first_job", SELFTEST)


def run_gate(folder):
    p = subprocess.run([sys.executable, GATE, folder], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    return p.returncode, p.stdout + p.stderr


def pl_amount(value: str) -> re.Pattern:
    """1476.00 -> matches 1476,00 / 1 476,00 / 1.476,00 (any space kind); 49.00 also as 49.00."""
    whole, frac = value.split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    return re.compile(r"(?<![\d,.])" + r"[  .]?".join(groups) + r"[.,]" + frac + r"(?!\d)")


class Gate(unittest.TestCase):
    def test_good_fixture_passes(self):
        code, out = run_gate(os.path.join(FIXTURES, "good"))
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: PASS", out)
        self.assertNotIn("FAIL:", out)

    def test_duplicate_counted_twice_fails_with_reason(self):
        code, out = run_gate(os.path.join(FIXTURES, "bad"))
        self.assertEqual(code, 1, out)
        line = next((ln for ln in out.splitlines() if ln.startswith("FAIL: duplicate")), "")
        for needle in ("fwd_faktura_telefon.txt", "telefon_wrzesien_faktura.txt",
                       "FV/T/2026/88412"):
            self.assertIn(needle, line, out)
        self.assertIn("adds up to 4506.30", out)

    def test_guessed_row_for_unreadable_scan_fails(self):
        code, out = run_gate(os.path.join(FIXTURES, "bad-guessed"))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^FAIL: guessed row: .*skan_0007\.txt")

    def _copy_good(self):
        tmp = tempfile.mkdtemp(prefix="first-job-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in ("ledger.csv", "summary.md"):
            shutil.copy(os.path.join(FIXTURES, "good", name), tmp)
        return tmp

    def _edit(self, path, old, new):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new))

    def test_missing_ledger_fails_cleanly(self):
        tmp = self._copy_good()
        os.remove(os.path.join(tmp, "ledger.csv"))
        code, out = run_gate(tmp)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL: ledger.csv is missing", out)
        self.assertNotIn("Traceback", out)

    def test_four_line_summary_fails(self):
        tmp = self._copy_good()
        path = os.path.join(tmp, "summary.md")
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines[:4]) + "\n")
        code, out = run_gate(tmp)
        self.assertEqual(code, 1, out)
        self.assertIn("4 non-empty lines, expected exactly 5", out)

    def test_netto_instead_of_brutto_fails(self):
        tmp = self._copy_good()
        self._edit(os.path.join(tmp, "ledger.csv"), "rent,1230.00,PLN,1230.00",
                   "rent,1000.00,PLN,1000.00")
        code, out = run_gate(tmp)
        self.assertEqual(code, 1, out)
        self.assertIn("expected the gross amount 1230.00", out)

    def test_polish_number_format_in_csv_fails_with_hint(self):
        tmp = self._copy_good()
        self._edit(os.path.join(tmp, "ledger.csv"), ",98.40,PLN,98.40,", ',"98,40",PLN,98.40,')
        code, out = run_gate(tmp)
        self.assertEqual(code, 1, out)
        self.assertIn("must look like 1234.56", out)
        self.assertNotIn("Traceback", out)

    def test_folder_prefix_in_source_file_gets_a_clear_message(self):
        tmp = self._copy_good()
        self._edit(os.path.join(tmp, "ledger.csv"), ",szkolenie.txt", ",data/szkolenie.txt")
        code, out = run_gate(tmp)
        self.assertEqual(code, 1, out)
        self.assertIn("must be the bare file name 'szkolenie.txt'", out)
        self.assertNotIn("invented row", out)

    def test_summary_total_in_polish_format_passes(self):
        tmp = self._copy_good()
        self._edit(os.path.join(tmp, "summary.md"), "4383.30 PLN", "4 383,30 zł")
        code, out = run_gate(tmp)
        self.assertEqual(code, 0, out)

    def test_bom_and_crlf_ledger_passes(self):
        tmp = self._copy_good()
        path = os.path.join(tmp, "ledger.csv")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write(text)
        code, out = run_gate(tmp)
        self.assertEqual(code, 0, out)

    def test_not_a_folder_is_usage_error(self):
        code, _ = run_gate(os.path.join(FIXTURES, "does-not-exist"))
        self.assertEqual(code, 2)


class AnswerKeyMatchesData(unittest.TestCase):
    """A typo in data/ or in the answer key must not pass silently."""

    def read(self, name):
        with open(os.path.join(DATA, name), encoding="utf-8") as fh:
            return fh.read()

    def test_twelve_input_files(self):
        names = sorted(n for n in os.listdir(DATA) if not n.startswith("."))
        self.assertEqual(len(names), 12, names)
        self.assertEqual(set(names), set(gate.EXPECTED) | {gate.UNREADABLE})

    def test_every_expected_amount_is_in_its_source_file(self):
        for src, (date, amount, currency, original) in gate.EXPECTED.items():
            with self.subTest(src=src):
                text = self.read(src)
                self.assertRegex(text, pl_amount(original))
                y, m, d = date.split("-")
                months = {"09": "Sep"}
                forms = (date, f"{d}.{m}.{y}", f"{months[m]} {int(d)}, {y}")
                self.assertTrue(any(f in text for f in forms), f"{date} not in {src}")

    def test_eur_conversion_uses_task_rate_without_rounding_tie(self):
        with open(os.path.join(JOB, "TASK.md"), encoding="utf-8") as fh:
            rate = Decimal(re.search(r"1 EUR = (\d+\.\d+) PLN", fh.read()).group(1))
        _, amount, currency, original = gate.EXPECTED["invoice_adtools.txt"]
        self.assertEqual(currency, "EUR")
        exact = Decimal(original) * rate
        self.assertEqual(exact, exact.quantize(Decimal("0.01")), "rate lands on a half grosz")
        self.assertEqual(exact.quantize(Decimal("0.01")), Decimal(amount))

    def test_duplicate_pair_shares_invoice_number_but_not_bytes(self):
        a, b = (self.read(n) for n in gate.DUPLICATE_PAIR)
        self.assertIn(gate.DUPLICATE_DOC, a)
        self.assertIn(gate.DUPLICATE_DOC, b)
        self.assertNotEqual(a, b)

    def test_unreadable_scan_has_no_legible_amount_or_date(self):
        text = self.read(gate.UNREADABLE)
        self.assertNotRegex(text, r"\d+,\d{2}")
        self.assertNotRegex(text, r"\d{2}\.\d{2}\.\d{4}")

    def test_total_matches_answer_key(self):
        total = sum(Decimal(v[1]) for k, v in gate.EXPECTED.items()
                    if k != gate.DUPLICATE_PAIR[0])
        self.assertEqual(total, gate.EXPECTED_TOTAL)
        self.assertEqual(len(gate.EXPECTED) - 1, gate.EXPECTED_ROWS)

    def test_no_real_domains(self):
        for name in os.listdir(DATA):
            with self.subTest(name=name):
                for host in re.findall(r"@([\w.-]+)", self.read(name)):
                    self.assertTrue(host.endswith(".invalid"), host)


class SelftestRegistry(unittest.TestCase):
    def test_registry_entries_land_in_pass(self):
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            out_json = os.path.join(tmp, "r.json")
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                code = selftest.main(["--registry", REGISTRY, "--json", out_json])
            with open(out_json, encoding="utf-8") as fh:
                results = json.load(fh)["results"]
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual({r["id"]: r["bucket"] for r in results},
                         {"first_job_duplicate": "PASS", "first_job_guessed": "PASS",
                          "first_job_vendor": "PASS", "first_job_document_no": "PASS",
                          "first_job_summary_duplicate": "PASS"})

    def test_registry_catches_a_gate_that_cannot_fail(self):
        """Swap the real gate for one that always passes: the registry must say CANNOT-FAIL."""
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "check_ledger.py")
            with open(stub, "w", encoding="utf-8") as fh:
                fh.write("print('RESULT: PASS')\n")
            shutil.copytree(os.path.join(JOB, "gate", "fixtures"), os.path.join(tmp, "fixtures"))
            shutil.copy(REGISTRY, os.path.join(tmp, "registry.yaml"))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                code = selftest.main(["--registry", os.path.join(tmp, "registry.yaml")])
        self.assertEqual(code, 1, buf.getvalue())
        self.assertIn("CANNOT-FAIL: 5", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
