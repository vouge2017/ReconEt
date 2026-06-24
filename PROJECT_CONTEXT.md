# ReconET — Project Context

## What is ReconET?

ReconET is an Ethiopian treasury reconciliation platform that matches bank transactions against GL entries with **fee-aware matching** — the critical feature no competitor has.

**The Problem:** Ethiopian banks embed fees in transaction amounts. A transfer of ETB 100,040 = ETB 100,000 vendor payment + ETB 25 bank charge + ETB 15 gov't tax. Existing tools fail to match these.

**The Solution:** ReconET extracts fees from transaction descriptions, then uses three matching strategies (NET, GROSS, SPLIT) to achieve >90% match rates.

**Critical Update (June 24, 2026):** CBE only provides PDF statements (not CSV). PDF is now the primary ingestion path. Real CBE statement analyzed — 8-column format confirmed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Tailwind)                         │
│  ├── Reconciliation page (upload PDF/CSV → view matches)    │
│  └── Cheques page (track outstanding/stale cheques)         │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLAlchemy)                              │
│  ├── /api/reconciliation/run — Upload PDF/CSV, get matches  │
│  ├── /api/cheques/ — CRUD for cheque tracking               │
│  ├── adapters/cbe_pdf.py — CBE PDF parser (8 columns)       │
│  ├── engine/pdf_extractor.py — PDF extraction + OCR         │
│  ├── engine/balance_verifier.py — Pre-upload balance check  │
│  ├── engine/ethiopian_calendar.py — Ge'ez → Gregorian       │
│  ├── engine/fee_extractor.py — 4 fee patterns + tariff DB   │
│  ├── engine/matching.py — 3-phase matching engine           │
│  ├── engine/fuzzy_matcher.py — Splink-based fuzzy matching  │
│  ├── engine/tariff_db.py — CBE fee tariff database          │
│  └── engine/explainer.py — IFRS/Amharic explanations        │
├─────────────────────────────────────────────────────────────┤
│  Database (PostgreSQL)                                       │
│  ├── bank_transactions (with fee columns)                   │
│  ├── gl_entries                                             │
│  ├── matches (with fee_breakdown JSON)                      │
│  ├── cheques                                                │
│  └── audit_trail                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## CBE Statement Format (Real Data — June 2026)

**8 Columns:**

| # | Column | Example |
|---|--------|---------|
| 1 | Date | 03/01/2023 |
| 2 | Particulars | CBE ATM WITHDRAWAL |
| 3 | Reference | 2301030000001 |
| 4 | Narrative | PORT SAID |
| 5 | Value Date | 03/01/2023 |
| 6 | Debit | 1,000.00 |
| 7 | Credit | - |
| 8 | Balance | 9,000.00 |

**Reference Codes:**
- **FT** = Fund Transfer (account to account)
- **TT** = Cash Transaction (cash deposit/withdrawal)
- **CHQ** = Cheque
- **CD** = Cheque Deposit
- **CPO** = Cash Payment Order
- **ECS** = Electronic Clearing (salary)
- **PKR** = Payment to Supplier
- **VPCH** = Voucher Payment

**Important:** PDF is scanned (image-based). Needs OCR (Tesseract) for extraction.

---

## Fee Extraction — 4 Patterns

| Pattern | Example | Status |
|---------|---------|--------|
| 1. Embedded in description | `TRANSFER FEE 25 TAX 15` | ✅ Built |
| 2. Separate line item | `SERVICE CHARGE 25` | ✅ Built |
| 3. Separate row in table | Fee as own transaction row | ✅ Built |
| 4. Deducted but not itemized | Tariff database lookup | ✅ Built |

---

## Matching Engine — 3 Phases

| Phase | Type | Confidence | Description |
|-------|------|------------|-------------|
| 1 | Exact | 90-95% | Amount + date + reference match |
| 2 | Date-shifted | 73-82% | Same amount, 1-3 day lag |
| 3 | Fuzzy | 50-70% | Splink-based probabilistic matching |

---

## Bank Scope — MVP

| Bank | Adapter | Status |
|------|---------|--------|
| CBE | `cbe_pdf.py` | ✅ Built |
| Dashen | `dashen_pdf.py` | 📋 Next |
| Awash | `awash_pdf.py` | 📋 Next |

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/adapters/cbe_pdf.py` | CBE PDF parser (8 columns) |
| `backend/app/engine/fee_extractor.py` | 4 fee patterns + tariff DB |
| `backend/app/engine/matching.py` | 3-phase matching engine |
| `backend/app/engine/fuzzy_matcher.py` | Splink fuzzy matching |
| `backend/app/engine/explainer.py` | IFRS/Amharic explanations |
| `backend/app/engine/tariff_db.py` | CBE fee tariff database |
| `backend/app/engine/ethiopian_calendar.py` | Ge'ez → Gregorian |
| `backend/app/engine/balance_verifier.py` | Pre-upload balance check |
| `backend/app/engine/pdf_extractor.py` | PDF extraction + OCR |
| `backend/app/main.py` | FastAPI app (CORS, logging) |
| `backend/app/api/reconciliation.py` | Reconciliation API |
| `backend/app/api/cheques.py` | Cheque tracking API |
| `frontend/src/pages/Reconciliation.tsx` | Reconciliation UI |
| `frontend/src/pages/Cheques.tsx` | Cheques UI |
| `data/real_cbe_samples/` | Real CBE PDF + images |

---

## How to Run

```bash
# Start everything
docker-compose up -d

# Test PDF upload
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@data/real_cbe_samples/cbe_statement.pdf"

# Test CSV upload
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@data/sample_cbe_with_fees.csv"

# Open frontend
open http://localhost:5173
```

---

## Current Status (June 24, 2026)

### ✅ Built (Ready for Testing)
- CBE PDF adapter (8-column format)
- Balance verification (hard gate)
- Fee extraction (4 patterns)
- Matching engine (3 phases)
- Explainability engine (IFRS references)
- Cheque tracking (API + UI)
- Ethiopian calendar (library + fallback)
- Fuzzy matching (Splink)
- Security quick wins (CORS, file limits, logging)

### 📋 TODO (After Friday)
- JWT authentication
- Rate limiting
- Input validation
- Alembic migrations
- Excel export
- Dashen/Awash adapters
- SOC 2 (if enterprise customers ask)

---

## Friday Test Criteria

| Test | Pass | Fail |
|------|------|------|
| Upload real CBE PDF | Parse without errors | Crashes or no data |
| Balance verification | Passes | Rejects valid statement |
| Fee extraction | Extracts fees | Misses fees |
| Matching | Matches transactions | No matches |
| Explainability | Shows IFRS refs | No explanations |
