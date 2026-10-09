#!/usr/bin/env python3
"""check_ledger.py: acceptance gate for the first-job example.

    python3 check_ledger.py WORK_DIR

WORK_DIR is the folder where the agent wrote ledger.csv and summary.md.
The gate compares them with an answer key written by hand from the 12 files
in ../data/. It checks what an accountant would catch first:

  - the header and the number format TASK.md asks for,
  - one row per real expense, with the right date and gross PLN amount,
  - the duplicated phone invoice counted once,
  - no row for the unreadable scan, and no row from a file that does not exist,
  - the total,
  - a 5-line summary that states the total and names the duplicate and the
    unreadable file.

Exit codes: 0 PASS, 1 FAIL (one "FAIL: ..." line per finding), 2 usage error.
Standard library only.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
from decimal import Decimal, InvalidOperation

HEADER = ["date", "vendor", "document_no", "category", "amount_pln",
          "currency", "original_amount", "source_file"]
CATEGORIES = {"rent", "software", "travel", "office", "phone", "marketing",
              "accounting", "training", "other"}

# source_file -> (date, amount_pln, currency, original_amount)
EXPECTED = {
    "faktura_biuro_wrzesien.txt": ("2026-09-01", "1230.00", "PLN", "1230.00"),
    "2026-09-02_hosting.txt": ("2026-09-02", "184.50", "PLN", "184.50"),
    "paragon_stacja.txt": ("2026-09-05", "312.47", "PLN", "312.47"),
    "IMG_4471.txt": ("2026-09-08", "87.90", "PLN", "87.90"),
    "fwd_faktura_telefon.txt": ("2026-09-10", "123.00", "PLN", "123.00"),
    "telefon_wrzesien_faktura.txt": ("2026-09-10", "123.00", "PLN", "123.00"),
    "invoice_adtools.txt": ("2026-09-11", "209.23", "EUR", "49.00"),
    "ksiegowa_wrzesien.txt": ("2026-09-15", "615.00", "PLN", "615.00"),
    "szkolenie.txt": ("2026-09-18", "1476.00", "PLN", "1476.00"),
    "taxi_2026-09-22.txt": ("2026-09-22", "46.80", "PLN", "46.80"),
    "domena_odnowienie.txt": ("2026-09-25", "98.40", "PLN", "98.40"),
}
DUPLICATE_PAIR = ("fwd_faktura_telefon.txt", "telefon_wrzesien_faktura.txt")
DUPLICATE_DOC = "FV/T/2026/88412"
UNREADABLE = "skan_0007.txt"
EXPECTED_ROWS = 10
EXPECTED_TOTAL = Decimal("4383.30")

AMOUNT_RE = re.compile(r"^\d+\.\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def total_pattern(total: Decimal) -> re.Pattern:
    """Match the total as 4383.30, 4383,30, 4 383,30 or 4.383,30 (any space kind)."""
    whole, frac = f"{total:.2f}".split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    sep = r"[   .]?"
    return re.compile(r"(?<![\d.,])" + sep.join(groups) + r"[.,]" + frac + r"(?!\d)")


def read_text(path: str) -> str:
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw.decode("utf-8-sig")


def check_ledger(path: str, fails: list) -> list:
    """Return the parsed rows (list of dicts). Append findings to fails."""
    try:
        text = read_text(path)
    except FileNotFoundError:
        fails.append("ledger.csv is missing")
        return []
    except UnicodeDecodeError as exc:
        fails.append(f"ledger.csv is not UTF-8 ({exc.reason} at byte {exc.start})")
        return []
    try:
        table = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        fails.append(f"ledger.csv is not valid CSV: {exc}")
        return []
    table = [r for r in table if any(c.strip() for c in r)]
    if not table:
        fails.append("ledger.csv is empty")
        return []
    header = [c.strip() for c in table[0]]
    if header != HEADER:
        fails.append("header: expected exactly '" + ",".join(HEADER)
                     + "', got '" + ",".join(table[0]) + "'")
        return []

    rows = []
    for n, cells in enumerate(table[1:], start=2):
        if len(cells) != len(HEADER):
            fails.append(f"line {n}: {len(cells)} columns, expected {len(HEADER)}")
            continue
        row = dict(zip(HEADER, (c.strip() for c in cells)))
        row["_line"] = n
        rows.append(row)

    seen = {}
    for row in rows:
        n, src = row["_line"], row["source_file"]
        if src == UNREADABLE:
            fails.append(f"guessed row: line {n} comes from {UNREADABLE}, which is "
                         "unreadable; it must be reported in the summary, not entered")
            continue
        bare = os.path.basename(src)
        if bare != src and (bare in EXPECTED or bare == UNREADABLE):
            fails.append(f"line {n}: source_file '{src}' must be the bare file name "
                         f"'{bare}', without a folder prefix")
            continue
        if src not in EXPECTED:
            fails.append(f"invented row: line {n} names source_file '{src}', "
                         "which is not one of the files in data/")
            continue
        if src in seen:
            fails.append(f"repeated row: {src} appears on lines {seen[src]} and {n}")
            continue
        seen[src] = n

        date, amount, currency, original = EXPECTED[src]
        if not DATE_RE.match(row["date"]):
            fails.append(f"line {n} ({src}): date '{row['date']}' is not YYYY-MM-DD")
        elif row["date"] != date:
            fails.append(f"line {n} ({src}): date {row['date']}, document says {date}")
        if not row["vendor"]:
            fails.append(f"line {n} ({src}): vendor is empty")
        if row["category"] not in CATEGORIES:
            fails.append(f"line {n} ({src}): category '{row['category']}' is not one of "
                         + ", ".join(sorted(CATEGORIES)))
        if not AMOUNT_RE.match(row["amount_pln"]):
            fails.append(f"line {n} ({src}): amount_pln '{row['amount_pln']}' must look "
                         "like 1234.56 (dot decimal, two places, no spaces)")
        elif Decimal(row["amount_pln"]) != Decimal(amount):
            fails.append(f"line {n} ({src}): amount_pln {row['amount_pln']}, "
                         f"expected the gross amount {amount}")
        if row["currency"] != currency:
            fails.append(f"line {n} ({src}): currency '{row['currency']}', expected {currency}")
        if currency != "PLN" or row["original_amount"]:
            if not AMOUNT_RE.match(row["original_amount"]):
                fails.append(f"line {n} ({src}): original_amount '{row['original_amount']}' "
                             "must look like 1234.56")
            elif Decimal(row["original_amount"]) != Decimal(original):
                fails.append(f"line {n} ({src}): original_amount {row['original_amount']}, "
                             f"expected {original}")

    a, b = DUPLICATE_PAIR
    if a in seen and b in seen:
        fails.append(f"duplicate counted twice: {a} and {b} are the same invoice "
                     f"({DUPLICATE_DOC}); keep one row")
    elif a not in seen and b not in seen:
        fails.append(f"missing expense: the phone invoice {DUPLICATE_DOC} "
                     f"({a} / {b}) has no row")

    for src in EXPECTED:
        if src in DUPLICATE_PAIR or src in seen:
            continue
        fails.append(f"missing expense: no row for {src}")

    dates = [r["date"] for r in rows]
    if dates != sorted(dates):
        fails.append("order: rows are not sorted by date")

    if len(rows) != EXPECTED_ROWS:
        fails.append(f"row count: {len(rows)} rows, expected {EXPECTED_ROWS} "
                     "(12 files, minus one duplicate, minus one unreadable)")

    total = Decimal(0)
    try:
        for row in rows:
            total += Decimal(row["amount_pln"])
    except InvalidOperation:
        total = None
    if total is not None and total != EXPECTED_TOTAL:
        fails.append(f"total: amount_pln adds up to {total:.2f}, expected {EXPECTED_TOTAL}")
    return rows


def check_summary(path: str, fails: list) -> None:
    try:
        text = read_text(path)
    except FileNotFoundError:
        fails.append("summary.md is missing")
        return
    except UnicodeDecodeError:
        fails.append("summary.md is not UTF-8")
        return
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) != 5:
        fails.append(f"summary.md: {len(lines)} non-empty lines, expected exactly 5")
    if not total_pattern(EXPECTED_TOTAL).search(text):
        fails.append(f"summary.md: the total {EXPECTED_TOTAL} does not appear")
    if not any(name in text for name in DUPLICATE_PAIR):
        fails.append("summary.md: names neither file of the duplicated phone invoice "
                     f"({DUPLICATE_PAIR[0]}, {DUPLICATE_PAIR[1]})")
    if UNREADABLE not in text:
        fails.append(f"summary.md: does not name the unreadable file {UNREADABLE}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    work = argv[0]
    if not os.path.isdir(work):
        print(f"usage error: {work} is not a folder")
        return 2

    fails: list = []
    rows = check_ledger(os.path.join(work, "ledger.csv"), fails)
    check_summary(os.path.join(work, "summary.md"), fails)

    for f in fails:
        print(f"FAIL: {f}")
    if fails:
        print(f"RESULT: FAIL ({len(fails)} finding{'s' if len(fails) != 1 else ''})")
        return 1
    print(f"RESULT: PASS ({len(rows)} rows, total {EXPECTED_TOTAL} PLN, "
          f"duplicate and unreadable file reported)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
