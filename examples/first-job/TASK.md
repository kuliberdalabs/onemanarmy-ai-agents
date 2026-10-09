# Task: September 2026 expense ledger

You are doing bookkeeping prep for a one-person business. The folder `data/` holds 12 text files: invoices, receipts, a forwarded email and OCR text from scanned paper. All of them are costs from September 2026. Turn them into a ledger the owner can hand to an accountant, plus a short summary.

Work only inside this folder. Do not install anything and do not use the network.

## Output 1: `ledger.csv`

Write `ledger.csv` next to this file, UTF-8, comma-separated, one row per expense, sorted by date. The first line must be exactly:

```
date,vendor,document_no,category,amount_pln,currency,original_amount,source_file
```

| Column | Format |
|---|---|
| `date` | Issue or purchase date, `YYYY-MM-DD` |
| `vendor` | Seller name as printed on the document |
| `document_no` | Use the invoice number if one is printed; otherwise the receipt or order number (`nr wydr.` counts); empty only if the document shows none of these |
| `category` | One of: `rent`, `software`, `travel`, `office`, `phone`, `marketing`, `accounting`, `training`, `other`. Examples: hosting -> `software`; domain renewal -> `software` or `other` |
| `amount_pln` | Gross amount in PLN (brutto, "do zapłaty", "suma"), dot as the decimal separator, two decimals, no spaces or currency sign. `1 234,56 zł` becomes `1234.56` |
| `currency` | Currency of the document: `PLN` or `EUR` |
| `original_amount` | Gross amount in the document's own currency, same number format as `amount_pln` |
| `source_file` | The file name in `data/` the row came from, exactly as it is spelled there |

Rules:

1. Record the gross amount, the money that actually left the account. Invoices also show netto and VAT; do not use those.
2. Convert foreign currency at the fixed rate **1 EUR = 4.2700 PLN** and round to two decimals. This rate is set for the exercise; in real bookkeeping your accountant picks the rate.
3. The same invoice can arrive twice, for example once as a forwarded email and once as the original. Two files with the same seller and the same invoice number are one expense: keep one row, and name the skipped file in the summary.
4. If a file is unreadable, or its amount or date cannot be read with certainty, do not guess and do not add a row. Name the file in the summary so the owner can get a new copy.
5. Every row must come from a file in `data/`. Do not add rows for anything else.

## Output 2: `summary.md`

Write `summary.md` next to this file: exactly 5 non-empty lines, plain text, no heading.

1. The total of `amount_pln` and the number of rows in the ledger.
2. The largest single expense: vendor and amount.
3. Each foreign-currency document: original amount, the rate used and the PLN amount.
4. Each duplicate skipped, by file name, and which file was kept.
5. Each file left out as unreadable, by file name, and what the owner should do about it.

## When you are done

Say which files you wrote and list anything you were unsure about. The owner checks the result with a separate script; you do not need to look for it.
