"""first-job gate: vendor, document_no and original_amount checks, the duplicate
in the summary, and the total written in English or Polish number format
(stdlib unittest).

    python3 -m unittest discover tests -p 'test_first_job_gate.py' -v
"""
from __future__ import annotations

import csv
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOB = os.path.join(REPO, "examples", "first-job")
DATA = os.path.join(JOB, "data")
GATE = os.path.join(JOB, "gate", "check_ledger.py")
FIXTURES = os.path.join(JOB, "gate", "fixtures")
RECORDED_RUN = os.path.join(JOB, "runs", "2026-10-11-claude-code-haiku")

GOOD_DUPLICATE_LINE = ("Duplicate skipped: fwd_faktura_telefon.txt repeats invoice "
                       "FV/T/2026/88412; kept telefon_wrzesien_faktura.txt.")
GOOD_TOTAL_LINE = "Total for September 2026: 4383.30 PLN in 10 ledger rows."


def run_gate(folder):
    p = subprocess.run([sys.executable, GATE, folder], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    return p.returncode, p.stdout + p.stderr


class GateCase(unittest.TestCase):
    def copy_good(self):
        tmp = tempfile.mkdtemp(prefix="first-job-fix-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in ("ledger.csv", "summary.md"):
            shutil.copy(os.path.join(FIXTURES, "good", name), tmp)
        return tmp

    def edit(self, path, old, new):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new))

    def rewrite_ledger(self, folder, change, quoting=csv.QUOTE_MINIMAL):
        """Apply change(row) to every data row of ledger.csv (rows as dicts)."""
        path = os.path.join(folder, "ledger.csv")
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]), quoting=quoting)
            writer.writeheader()
            for row in rows:
                change(row)
                writer.writerow(row)

    def write_summary(self, folder, lines):
        with open(os.path.join(folder, "summary.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def assertFails(self, folder, *needles):
        code, out = run_gate(folder)
        self.assertEqual(code, 1, out)
        self.assertNotIn("RESULT: PASS", out)
        for needle in needles:
            self.assertIn(needle, out)
        return out

    def assertPasses(self, folder):
        code, out = run_gate(folder)
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: PASS", out)
        return out


class VendorAndDocumentNo(GateCase):
    def test_every_vendor_wrong_and_every_document_no_empty_fails(self):
        tmp = self.copy_good()
        path = os.path.join(tmp, "ledger.csv")
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerows([rows[0]] + [[r[0], "WRONG", "", *r[3:]] for r in rows[1:]])
        out = self.assertFails(tmp)
        lines = out.splitlines()
        self.assertEqual(sum("): vendor 'WRONG'" in ln for ln in lines), 10, out)
        # IMG_4471.txt shows no number, so an empty cell is right there.
        self.assertEqual(sum("): document_no is empty" in ln for ln in lines), 9, out)

    def test_bad_fields_fixture_fails_on_both_columns(self):
        out = self.assertFails(os.path.join(FIXTURES, "bad-fields"))
        self.assertRegex(out, r"(?m)^FAIL: line 2 \(faktura_biuro_wrzesien\.txt\): vendor 'WRONG'")
        self.assertRegex(out, r"(?m)^FAIL: line 2 \(faktura_biuro_wrzesien\.txt\): document_no is "
                              r"empty, document shows FV 09/2026/31$")
        self.assertIn("RESULT: FAIL (19 findings)", out)

    def test_buyer_named_as_vendor_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), "Rejestr Domen PL", "Twoja Firma")
        self.assertFails(tmp, "(domena_odnowienie.txt): vendor 'Twoja Firma'", "'Rejestr Domen'")

    def test_wrong_document_number_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), "RD/2026/52771", "RD/2026/52772")
        self.assertFails(tmp, "(domena_odnowienie.txt): document_no 'RD/2026/52772', "
                              "document shows RD/2026/52771")

    def test_number_invented_for_receipt_without_one_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), "Papiernik Kowalczyk,,", "Papiernik Kowalczyk,4471,")
        self.assertFails(tmp, "(IMG_4471.txt): document_no '4471', but the document shows no")

    def test_vendor_as_printed_in_capitals_or_without_diacritics_passes(self):
        tmp = self.copy_good()
        path = os.path.join(tmp, "ledger.csv")
        self.edit(path, '"Stacja Paliw ""Zakręt"""', '"STACJA PALIW ""ZAKRĘT"""')
        self.edit(path, "Papiernik Kowalczyk", "PAPIERNIK  KOWALCZYK")
        self.edit(path, "Telekom Mazowsze S.A.", "TELEKOM MAZOWSZE S.A.")
        self.edit(path, "Serwerownia Północ sp. z o.o.", "Serwerownia Polnoc")
        self.edit(path, "Przejazdy Wiślane", "Przejazdy Wislane")
        self.edit(path, "AdTools OU", "AdTools OÜ")
        self.assertPasses(tmp)

    def test_document_number_variants_pass(self):
        tmp = self.copy_good()
        path = os.path.join(tmp, "ledger.csv")
        self.edit(path, "MF26-00318", "MF/2026/0318")      # the announced invoice number
        self.edit(path, ",4471,", ",nr wydr. 4471,")       # the label printed on the receipt
        self.edit(path, "FV 09/2026/31", "fv09/2026/31")    # case and spacing
        self.assertPasses(tmp)


class AnswerKeyFieldsMatchData(unittest.TestCase):
    """A typo in the vendor or document_no answer key must not pass silently."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("check_ledger_fix", GATE)
        cls.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gate)

    def test_fields_cover_every_expected_file(self):
        self.assertEqual(set(self.gate.FIELDS), set(self.gate.EXPECTED))

    def test_vendor_words_and_numbers_are_in_the_source_file(self):
        for src, (words, numbers) in self.gate.FIELDS.items():
            with self.subTest(src=src):
                with open(os.path.join(DATA, src), encoding="utf-8") as fh:
                    text = fh.read()
                self.assertIn(f" {self.gate.fold(words)} ", f" {self.gate.fold(text)} ")
                for number in numbers:
                    self.assertTrue(self.gate.document_no_matches(text, number), number)

    def test_good_fixture_agrees_with_the_key(self):
        with open(os.path.join(FIXTURES, "good", "ledger.csv"), encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                words, numbers = self.gate.FIELDS[row["source_file"]]
                with self.subTest(src=row["source_file"]):
                    self.assertTrue(self.gate.vendor_matches(row["vendor"], words))
                    self.assertEqual(bool(numbers), bool(row["document_no"]))


class SummaryNamesTheSkippedDuplicate(GateCase):
    def test_no_duplicates_found_naming_the_kept_file_fails(self):
        tmp = self.copy_good()
        self.write_summary(tmp, [
            "Total for September 2026: 4383.30 PLN in 10 ledger rows.",
            "Largest expense: Fundacja Przykładowa Wiedza, 1476.00 PLN.",
            "Foreign currency: invoice_adtools.txt, EUR 49.00 at 4.2700 = 209.23 PLN.",
            "No duplicates found; the phone bill is telefon_wrzesien_faktura.txt.",
            "All files were readable except skan_0007.txt, which I booked nowhere.",
        ])
        out = self.assertFails(tmp, "summary.md: does not name the skipped duplicate "
                                    "fwd_faktura_telefon.txt",
                               "summary.md: says there were no duplicates")
        self.assertNotIn("duplicate and unreadable file reported", out)

    def test_summary_silent_about_the_duplicate_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "Phone: Telekom Mazowsze, 123.00 PLN, from telefon_wrzesien_faktura.txt.")
        self.assertFails(tmp, "does not name the skipped duplicate fwd_faktura_telefon.txt")

    def test_naming_both_files_while_denying_the_duplicate_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "No duplicates found; fwd_faktura_telefon.txt and telefon_wrzesien_faktura.txt "
                  "are both on file.")
        self.assertFails(tmp, "summary.md: says there were no duplicates")

    def test_polish_denial_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "Brak duplikatów: fwd_faktura_telefon.txt i telefon_wrzesien_faktura.txt "
                  "to osobne pliki.")
        self.assertFails(tmp, "summary.md: says there were no duplicates")

    def test_bare_polish_denial_still_fails(self):
        for line in ("Brak duplikatów; pominięto telefon_wrzesien_faktura.txt.",
                     "Nie znaleziono duplikatów (fwd_faktura_telefon.txt i telefon_wrzesien_faktura.txt)."):
            with self.subTest(line=line):
                tmp = self.copy_good()
                self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE, line)
                self.assertFails(tmp, "summary.md:")

    def test_bad_summary_fixture_fails(self):
        out = self.assertFails(os.path.join(FIXTURES, "bad-summary"))
        self.assertRegex(out, r"(?m)^FAIL: summary\.md: does not name the skipped duplicate "
                              r"fwd_faktura_telefon\.txt")

    def test_ledger_keeping_the_forwarded_copy_needs_the_other_name(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), ",telefon_wrzesien_faktura.txt",
                  ",fwd_faktura_telefon.txt")
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "Duplicate: kept fwd_faktura_telefon.txt (invoice FV/T/2026/88412).")
        self.assertFails(tmp, "does not name the skipped duplicate telefon_wrzesien_faktura.txt")

    def test_correct_wordings_pass(self):
        wordings = [
            "Kept telefon_wrzesien_faktura.txt; skipped fwd_faktura_telefon.txt (same invoice "
            "FV/T/2026/88412), so no duplicate row is booked.",
            "Duplicate skipped: fwd_faktura_telefon.txt; kept telefon_wrzesien_faktura.txt. "
            "No other duplicates.",
            "Pominięty duplikat: fwd_faktura_telefon.txt; zachowano telefon_wrzesien_faktura.txt "
            "(FV/T/2026/88412).",
            "Brak duplikatów w zestawieniu; pominięto fwd_faktura_telefon.txt, zostawiono "
            "telefon_wrzesien_faktura.txt.",
            "No duplicates in the ledger: skipped fwd_faktura_telefon.txt, kept "
            "telefon_wrzesien_faktura.txt.",
            "No duplicates remain in the ledger; skipped fwd_faktura_telefon.txt, kept "
            "telefon_wrzesien_faktura.txt.",
        ]
        for line in wordings:
            with self.subTest(line=line):
                tmp = self.copy_good()
                self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE, line)
                self.assertPasses(tmp)


class OriginalAmount(GateCase):
    def test_empty_original_amount_on_every_pln_row_fails(self):
        tmp = self.copy_good()

        def empty_pln(row):
            if row["currency"] == "PLN":
                row["original_amount"] = ""

        self.rewrite_ledger(tmp, empty_pln)
        out = self.assertFails(tmp, "(faktura_biuro_wrzesien.txt): original_amount is empty, "
                                    "expected the gross amount in PLN, 1230.00")
        lines = out.splitlines()
        self.assertEqual(sum("): original_amount is empty" in ln for ln in lines), 9, out)
        self.assertNotIn("(invoice_adtools.txt): original_amount", out)
        self.assertIn("RESULT: FAIL (9 findings)", out)

    def test_empty_original_amount_on_the_euro_invoice_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), ",EUR,49.00,", ",EUR,,")
        self.assertFails(tmp, "(invoice_adtools.txt): original_amount is empty, "
                              "expected the gross amount in EUR, 49.00")

    def test_pln_amount_in_the_euro_column_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), ",EUR,49.00,", ",EUR,209.23,")
        self.assertFails(tmp, "(invoice_adtools.txt): original_amount 209.23, "
                              "expected the gross amount in EUR, 49.00")

    def test_original_amount_differing_from_the_pln_gross_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), ",615.00,PLN,615.00,", ",615.00,PLN,500.00,")
        self.assertFails(tmp, "(ksiegowa_wrzesien.txt): original_amount 500.00, "
                              "expected the gross amount in PLN, 615.00")

    def test_original_amount_in_polish_format_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), ",1476.00,PLN,1476.00,",
                  ',1476.00,PLN,"1 476,00",')
        self.assertFails(tmp, "(szkolenie.txt): original_amount '1 476,00' must look like 1234.56")

    def test_every_cell_quoted_passes(self):
        tmp = self.copy_good()
        self.rewrite_ledger(tmp, lambda row: None, quoting=csv.QUOTE_ALL)
        with open(os.path.join(tmp, "ledger.csv"), encoding="utf-8") as fh:
            self.assertIn('"PLN","1230.00"', fh.read())
        self.assertPasses(tmp)

    def test_recorded_agent_run_passes(self):
        self.assertPasses(RECORDED_RUN)


class SummaryCountedTwiceWording(GateCase):
    """'No duplicates counted twice' describes a correct ledger; 'no duplicates found' denies one."""

    def test_counted_twice_wordings_that_name_the_skipped_file_pass(self):
        wordings = [
            "No duplicates counted twice; skipped fwd_faktura_telefon.txt, "
            "kept telefon_wrzesien_faktura.txt.",
            "No duplicate was counted twice: skipped fwd_faktura_telefon.txt (same invoice "
            "FV/T/2026/88412), kept telefon_wrzesien_faktura.txt.",
            "No duplicates double-counted: fwd_faktura_telefon.txt is a forwarded copy of "
            "FV/T/2026/88412, kept telefon_wrzesien_faktura.txt.",
            "Brak duplikatów policzonych dwa razy: pominięto fwd_faktura_telefon.txt, "
            "zachowano telefon_wrzesien_faktura.txt.",
            "Skipped fwd_faktura_telefon.txt as a duplicate of telefon_wrzesien_faktura.txt; "
            "nothing is counted twice.",
        ]
        for line in wordings:
            with self.subTest(line=line):
                tmp = self.copy_good()
                self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE, line)
                self.assertPasses(tmp)

    def test_counted_twice_wording_passes_when_the_ledger_keeps_the_forwarded_copy(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "ledger.csv"), ",telefon_wrzesien_faktura.txt",
                  ",fwd_faktura_telefon.txt")
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "No duplicates counted twice; skipped telefon_wrzesien_faktura.txt, "
                  "kept fwd_faktura_telefon.txt.")
        self.assertPasses(tmp)

    def test_counted_twice_wording_that_swaps_the_files_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "No duplicates counted twice; skipped telefon_wrzesien_faktura.txt, "
                  "kept fwd_faktura_telefon.txt.")
        self.assertFails(tmp, "summary.md: names telefon_wrzesien_faktura.txt as the skipped "
                              "duplicate, but the ledger keeps it",
                         "summary.md: says fwd_faktura_telefon.txt was kept, but the ledger "
                         "has no row for it")

    def test_counted_twice_wording_without_the_skipped_file_fails(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "No duplicates counted twice; the phone bill is telefon_wrzesien_faktura.txt.")
        self.assertFails(tmp, "does not name the skipped duplicate fwd_faktura_telefon.txt")

    def test_no_duplicates_found_fails_even_when_both_files_are_named(self):
        tmp = self.copy_good()
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "No duplicates found; skipped fwd_faktura_telefon.txt, "
                  "kept telefon_wrzesien_faktura.txt.")
        self.assertFails(tmp, "summary.md: says there were no duplicates")

    def test_counted_twice_wording_fails_when_the_ledger_books_both_copies(self):
        tmp = self.copy_good()
        shutil.copy(os.path.join(FIXTURES, "bad", "ledger.csv"), tmp)
        self.edit(os.path.join(tmp, "summary.md"), GOOD_DUPLICATE_LINE,
                  "No duplicates counted twice; fwd_faktura_telefon.txt and "
                  "telefon_wrzesien_faktura.txt are both in the ledger.")
        self.assertFails(tmp, "FAIL: duplicate counted twice:",
                         "summary.md: says there were no duplicates")


class SummaryTotalFormats(GateCase):
    def test_common_total_formats_pass(self):
        for line in ("Total: PLN 4,383.30 across 10 ledger rows.",
                     "Total: 4,383.30 PLN in 10 rows.",
                     "Total: 4 383,30 zł across 10 ledger rows.",
                     "Total: 4 383,30 zł across 10 ledger rows.",
                     "Total: 4.383,30 zł across 10 ledger rows.",
                     "Total: 4383,30 zł across 10 ledger rows.",
                     "Total: 4 383.30 PLN across 10 ledger rows."):
            with self.subTest(line=line):
                tmp = self.copy_good()
                self.edit(os.path.join(tmp, "summary.md"), GOOD_TOTAL_LINE, line)
                self.assertPasses(tmp)

    def test_wrong_total_in_english_format_still_fails(self):
        for line in ("Total: PLN 4,506.30 across 11 ledger rows.",
                     "Total: PLN 14,383.30 across 10 ledger rows."):
            with self.subTest(line=line):
                tmp = self.copy_good()
                self.edit(os.path.join(tmp, "summary.md"), GOOD_TOTAL_LINE, line)
                self.assertFails(tmp, "summary.md: the total 4383.30 does not appear")


if __name__ == "__main__":
    unittest.main()
