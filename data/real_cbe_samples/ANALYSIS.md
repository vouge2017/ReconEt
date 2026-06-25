# CBE Statement Analysis — June 25, 2026

## Summary

Three real CBE bank statements analyzed. **Critical discovery: PDFs are NOT scanned images.** They are text-based PDFs with custom font encodings (DEVEXP+ prefix). Text can be extracted programmatically using CMap decoding — no OCR needed.

This changes the architecture: `pdf_extractor.py` should use CMap-based text extraction, not Tesseract OCR.

---

## Statement 1: Nael Hailemariam

| Field | Value |
|-------|-------|
| Account Holder | NAEL HAILEMARIAM TEKLEHAIMANOT |
| Account Number | 1000066001079 |
| Account Type | Saving Account |
| Currency | ETB |
| Branch | BERHANNA SELAM BRANCH |
| Period | 01 JAN 2022 – 05 APR 2022 |
| Pages | 4 |
| Opening Balance | ETB 5,127.54 |
| Closing Balance | ETB 1,352.43 |

**Transaction Types:**
- ATM Cash Withdrawal (dominant)
- Fund Transfer (FT references)
- Cash Transaction (TT references)
- Credit Interest (quarterly)
- Tax Amount Due (on interest)
- Inward Telex Payment

**Fee Patterns Observed:**
- Withdrawal of 1,002 → likely 1,000 + 2 fee
- Withdrawal of 2,004 → likely 2,000 + 4 fee
- Withdrawal of 1,005 → likely 1,000 + 5 fee
- Withdrawal of 502.50 → likely 500 + 2.50 fee

---

## Statement 2: Ahimed Kedir Fright Transport

| Field | Value |
|-------|-------|
| Account Holder | AHIMED KEDIR FRIGHT TRANSPORT |
| Account Number | 1000357122717 |
| Account Type | CURRENT ACCOUNT |
| Currency | ETB |
| Branch | ASSEFA TSEGAYE BRANCH |
| Period | 01 JAN 2021 – 18 APR 2022 |
| Pages | 8 |
| Opening Balance | ETB 64,700.00 |
| Closing Balance | ETB 278,683.64 |

**Transaction Types:**
- Transfer (FT references)
- Cheque (CHQ references)
- Cheque Deposit (CD references)
- Cash Transaction (TT references)
- Inward Telex Payment
- Mobile money transfers ("done via Mob")
- Post Office payments (Post S./Post A.)
- DStv payments

**Fee Patterns Observed:**
- Post Office deductions: 595.22, 430.80, 550.08, 478.33, 240.15, 404.98, 578.54, 226.40, 499.00, 898.61, 714.76, 499.00
- These are postal service fees deducted from the account
- Cheque transactions: CHQ NO.35703206, 35703207, etc.

**Business Characteristics:**
- Transport company with high transaction volume
- Many small mobile payments (school, fuel, transport, spare parts)
- Regular large deposits (cheque deposits, transfers)
- Cheque-based payments to suppliers

---

## Statement 3: Yoseph Statement (Sara Birmeka Mohammed)

| Field | Value |
|-------|-------|
| Account Holder | SARA BIRMEKA MOHAMMED |
| Account Number | 1000009464658 |
| Account Type | Saving Account |
| Currency | ETB |
| Branch | Gofa Sefer Branch |
| Period | 01 MAR 2023 – 31 MAY 2023 |
| Pages | 6 |
| Opening Balance | ETB 142,983.02 |
| Closing Balance | ETB 12,230.27 |

**Transaction Types:**
- ATM Cash Withdrawal (dominant)
- Fund Transfer (FT references)
- Cash Transaction (TT references)
- Credit Interest (monthly)
- Tax Amount Due (on interest)
- ATM Charges

**Fee Patterns Observed:**
- Withdrawal of 2,004 → likely 2,000 + 4 fee
- Withdrawal of 2,010 → likely 2,000 + 10 fee
- Withdrawal of 1,002 → likely 1,000 + 2 fee
- Withdrawal of 1,005 → likely 1,000 + 5 fee
- Withdrawal of 501 → likely 500 + 1 fee
- Withdrawal of 301.50 → likely 300 + 1.50 fee
- ATM Charges: ETB 0.50 (separate line item)
- Withdrawal of 603 → likely 600 + 3 fee
- Withdrawal of 4,008 → likely 4,000 + 8 fee
- Withdrawal of 6,012 → likely 6,000 + 12 fee
- Withdrawal of 6,030 → likely 6,000 + 30 fee

**Key Observations:**
- Fees are consistently embedded in withdrawal amounts
- Fee amounts follow patterns: 2, 4, 5, 8, 10, 12, 30
- ATM charges appear as separate line items (ETB 0.50)
- Credit Interest and Tax Amount Due are separate entries

---

## CBE Statement Format (Confirmed)

**8 Columns:**
1. Date (DD MM YYYY)
2. Particulars (transaction type)
3. Reference (FT/TT/CHQ/CD codes)
4. Narrative (description)
5. Value Date (DD MM YYYY)
6. Debit (negative amounts)
7. Credit (positive amounts)
8. Balance (running balance)

**Reference Code Patterns:**
- FTYYDDDXXXXX\CODE → Fund Transfer (YY=year, DDD=day, XXXXX=random, CODE=branch/terminal)
- TTYYDDDXXXXX\CODE → Cash Transaction
- CHQ → Cheque number in narrative
- CD → Cheque Deposit

**Header Format:**
```
COMMERCIAL BANK OF ETHIOPIA
Account Statement
[BRANCH NAME]
Account : [number]
Currency : ETB
Account Type : [type]
From [date] to [date]
Statement of Transactions For the period
```

**Footer Format:**
```
*Please examine this statement promptly and immediately advice our Auditing Dept of any errors. If no error is reported with in fifteen days, this statement will be considered correct.*
Page : X/Y
```

---

## Technical Notes

### PDF Encoding
- Uses custom fonts: DEVEXP+Arial, DEVEXP+ArialRoundedMTBold, DEVEXP+TimesNewRoman, DEVEXP+ArialNarrow
- Encoding: Identity-H with ToUnicode CMaps
- Text is extractable via CMap decoding (no OCR needed)
- Font objects: F1-F6 mapped to objects 11, 16, 21, 26, 31, 36

### Extraction Method
1. Parse all objects in PDF
2. Find font objects with ToUnicode CMaps
3. Decompress and parse CMap bfchar/bfrange mappings
4. For each page, find content stream
5. Use font CMaps to decode hex-encoded text
6. Reconstruct text lines from PDF operators

### Implications for ReconET
- **OCR (Tesseract) is NOT needed** for these PDFs
- The `pdf_extractor.py` should be updated to use CMap-based extraction
- This is faster, more accurate, and doesn't require image processing
- The existing `cbe_pdf.py` adapter needs to handle the custom font encoding

---

## Fee Extraction Patterns (For ReconET)

### Pattern 1: Embedded Fees (Most Common)
Withdrawal amounts include fees:
- 1,002 = 1,000 + 2
- 2,004 = 2,000 + 4
- 1,005 = 1,000 + 5
- 502.50 = 500 + 2.50
- 2,010 = 2,000 + 10
- 4,008 = 4,000 + 8
- 6,012 = 6,000 + 12
- 6,030 = 6,000 + 30

### Pattern 2: Separate Line Items
- ATM CHARGES: ETB 0.50
- Tax Amount Due: varies
- Post Office fees: 595.22, 430.80, etc.

### Pattern 3: Interest & Tax
- Credit Interest: quarterly credit
- Tax Amount Due: debit on interest (usually 2% of interest)

### Fee Detection Strategy
1. Check if amount has common fee patterns (X,002; X,004; X,005; X,010)
2. Look for "ATM CHARGES" or "SERVICE CHARGE" in narrative
3. Check for "Tax Amount Due" entries
4. Use CBE tariff database as fallback
