# ReconET — Session Handoff

**Date:** June 24, 2026
**Previous Session:** Added Explainability Engine, Cheques UI, GL CSV upload, rich explanations
**This Session:** Added CBE PDF adapter, balance verification, Ethiopian calendar, PDF pipeline

---

## What Was Done This Session

### 1. Ethiopian Calendar Converter (`engine/ethiopian_calendar.py`)

Handles CBE's use of Ethiopian (Ge'ez) calendar dates:
- `ethiopian_to_gregorian()` — Converts Ge'ez dates to Gregorian
- `gregorian_to_ethiopian()` — Reverse conversion
- `parse_cbe_date()` — Auto-detects and converts CBE date formats
- `classify_reference_code()` — Extracts FT, CHQ, CD, CPO, ECS, PKR, VPCH codes
- `extract_cheque_number()` — Extracts cheque numbers from reference/description

### 2. Balance Verifier (`engine/balance_verifier.py`)

Pre-upload gate that verifies: `opening + credits - debits = closing`
- Tolerance: 0.01 ETB
- Three statuses: passed, warning (≤1.0 ETB diff), failed
- Rejects upload if balance doesn't match
- Also provides `verify_running_balances()` for per-transaction verification

### 3. PDF Extraction Wrapper (`engine/pdf_extractor.py`)

Unified interface for extracting text and tables from PDFs:
- **pdfplumber** (primary) — best for text-based PDFs with tables
- **camelot-py** (fallback) — better for complex table layouts
- **Tesseract + amh** (scanned PDFs) — Amharic OCR support
- **PaddleOCR** (messy scans) — last resort
- Auto-detects PDF type (text-based vs scanned)

### 4. CBE PDF Adapter (`adapters/cbe_pdf.py`)

Parses CBE PDF bank statements with auto-detection:
- **4 account types**: Savings, Current, Current with Overdraft, Time Deposit
- **Column layouts**: Different header orders per account type
- **Auto-detection**: Reads PDF content to determine account type
- **Fee extraction**: Integrates with FeeExtractor for each transaction
- **Reference codes**: Classifies FT, CHQ, CD, CPO, ECS, PKR, VPCH
- **Cheque numbers**: Extracts from CHQ references

### 5. Updated Reconciliation API

- Accepts both PDF and CSV uploads (auto-detected from filename/magic bytes)
- Parameter renamed from `bank_csv` to `bank_file`
- PDF flow: parse → balance verify → extract fees → match → explain
- Returns `balance_verification` and `pdf_info` in response
- Rejects with 422 if balance verification fails

### 6. Updated Frontend

- File input now accepts `.pdf,.csv`
- Button text changed to "Upload Bank Statement"
- Added `BalanceVerificationCard` component
- Shows balance verification status (✅ passed, ⚠️ warning, ❌ failed)
- Displays opening/closing balances, credits, debits

### 7. Updated Docker/Requirements

- `requirements.txt`: Added pdfplumber, camelot-py, pytesseract, pdf2image, Pillow
- `Dockerfile`: Added tesseract-ocr, tesseract-ocr-amh, poppler-utils, ghostscript

### 8. Sample PDF Generator (`create_sample_cbe_pdf.py`)

Creates realistic CBE-style PDF for testing:
- Uses reportlab or fpdf2
- Current Account layout (Date | Particulars | Reference | Narrative | ...)
- 10 transactions with fees, cheques, transfers
- Opening/closing balances that verify

### 9. Integration Test (`test_cbe_pdf.sh`)

Tests the full pipeline:
- API health check
- PDF upload + balance verification
- CSV backward compatibility
- Fee extraction from PDF
- Cheque detection from PDF

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/engine/ethiopian_calendar.py` | NEW | Ge'ez → Gregorian, reference codes |
| `backend/app/engine/balance_verifier.py` | NEW | Pre-upload balance verification |
| `backend/app/engine/pdf_extractor.py` | NEW | PDF text/table extraction wrapper |
| `backend/app/adapters/cbe_pdf.py` | NEW | CBE PDF parser (4 account types) |
| `backend/app/adapters/__init__.py` | MODIFIED | Export CBE PDF adapter |
| `backend/app/api/reconciliation.py` | REWRITTEN | PDF + CSV support |
| `backend/requirements.txt` | MODIFIED | Added PDF dependencies |
| `backend/Dockerfile` | MODIFIED | Added OCR system deps |
| `backend/create_sample_cbe_pdf.py` | NEW | Sample PDF generator |
| `frontend/src/pages/Reconciliation.tsx` | MODIFIED | PDF support, balance card |
| `test_cbe_pdf.sh` | NEW | Integration test |
| `PROJECT_CONTEXT.md` | UPDATED | PDF pipeline docs |
| `SESSION_HANDOFF.md` | UPDATED | This file |

---

## What's Next

### Immediate (this week — Friday demo)
1. **Test with real CBE PDF** — Validate on actual bank statement
2. **Verify balance verification** — Ensure it catches parsing errors
3. **Check fee extraction** — Confirm fees extracted from PDF-parsed data
4. **Deploy to staging** — Push with PostgreSQL for pilot testing

### Short-term (next week)
1. **Cheque matching** — Auto-match CHQ references to cheque register
2. **Audit trail export** — Export matches + explanations to Excel
3. **Multi-bank adapters** — Dashen, Awash, Ecobank PDF formats

### Medium-term (2-3 weeks)
1. **Bilingual UI** — Full Amharic interface
2. **Correction learning** — User overrides improve future confidence
3. **FX rate integration** — Auto-fetch NBE daily rates
4. **Telegram notifications** — Alert on stale cheques, anomalies

---

## Known Issues

1. **PDF parsing accuracy** — Depends on PDF quality; scanned PDFs need OCR
2. **Ethiopian calendar detection** — Heuristic-based; may need refinement with real data
3. **Column mapping** — Different CBE branches may have slightly different layouts
4. **No GL CSV upload in PDF mode** — GL still uses mock entries when PDF uploaded
5. **No auth** — No user authentication yet (planned for Phase 2)

---

## Critical Context for Next Session

- **CBE only provides PDF** — CSV is fallback for other banks/testing
- **Balance verification is a HARD gate** — If it fails, reject upload
- **Ethiopian calendar** — CBE dates may be Ge'ez; must convert to Gregorian
- **Reference codes drive matching** — FT=intercompany, CHQ=cheque register
- **4 CBE account types** — Auto-detect from PDF content
- **Friday is the deadline** — Must work with real CBE PDF

---

## The Contract

| Deliverable | Status |
|-------------|--------|
| CBE PDF adapter | ✅ Built |
| Balance verification | ✅ Built |
| Ethiopian calendar | ✅ Built |
| PDF extraction wrapper | ✅ Built |
| Frontend PDF support | ✅ Built |
| Integration test | ✅ Built |
| Sample CBE PDF | ✅ Built |
| Real CBE PDF test | ⏳ Friday |
| PostgreSQL migration | 🚧 In progress |
| Cheque tracking | ✅ API + UI built |
