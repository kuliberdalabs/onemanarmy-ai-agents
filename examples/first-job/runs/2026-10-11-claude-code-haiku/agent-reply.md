I wrote `ledger.csv` and `summary.md` in the first-job folder. The ledger has 10 rows totalling 4383.30 PLN. I read all 12 files in `data/` and did not run any checker.

**Files written**
- `ledger.csv`
- `summary.md`

**Unsure about**
- **Skipped file:** `skan_0007.txt` is left out. The OCR is too poor to read the issuer, date, invoice number or total. The summary tells the owner to get a clean copy.
- **Duplicate:** `fwd_faktura_telefon.txt` is the forwarded email copy of Telekom Mazowsze invoice FV/T/2026/88412. I kept `telefon_wrzesien_faktura.txt` (the attached invoice) and skipped the forward. Both show 123.00 PLN.
- **Category `rent`:** the coworking desk (`faktura_biuro_wrzesien.txt`) is coded as `rent`, not `office`. Change it if your accountant prefers `office`.
- **Mixed fuel receipt:** `paragon_stacja.txt` includes a hot dog and coffee (20.29 PLN) with the fuel. I recorded the whole receipt as `travel`.
- **OCR receipt:** `IMG_4471.txt` is OCR text from a photo. Its line items and total add up, so I included it, but it is worth checking against the paper. It has no receipt number, so `document_no` is empty.
- **Vendor for the conference ticket:** the ticket names the organiser, Fundacja Przykładowa Wiedza, as the seller, so I used that rather than the event name. The invoice `MF/2026/0318` is "sent separately" and is not in the folder, so `document_no` is the order number MF26-00318.
- **Accounting invoice period:** the bookkeeping invoice from Biuro Rachunkowe "Bilans" (`ksiegowa_wrzesien.txt`) is dated 15.09.2026 but covers August 2026 services. I kept it as a September row because the task says all files are September costs.
