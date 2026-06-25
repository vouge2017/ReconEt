# ReconET — Project Context

## What is ReconET?

ReconET is an Ethiopian treasury reconciliation platform that matches bank transactions against GL entries with **fee-aware matching** — the critical feature no competitor has.

**The Problem:** Ethiopian banks embed fees in transaction amounts. A transfer of ETB 100,040 = ETB 100,000 vendor payment + ETB 25 bank charge + ETB 15 gov't tax. Existing tools fail to match these.

**The Solution:** ReconET extracts fees from transaction descriptions, then uses three matching strategies (NET, GROSS, SPLIT) to achieve >90% match rates.

**Critical Update (June 25, 2026):** CBE PDFs are text-based with custom fonts (DEVEXP+), not scanned images. CMap-based extraction replaces OCR as primary method. Real CBE statements analyzed — 8-column format confirmed across savings and current accounts.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Tailwind)                         │
│  ├── Reconciliation page (upload PDF/CSV → view matches)    │
│  ├── Cheques page (track outstanding/stale cheques)         │
│  ├── Dashboard page (executive summary)                     │
│  └── Excel export (download .xlsx reports)                  │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLAlchemy)                              │
│  ├── /api/reconciliation/run — Upload PDF/CSV, get matches  │
│  ├── /api/reconciliation/export/{id} — Export to Excel      │
│  ├── /api/cheques/ — CRUD for cheque tracking               │
│  ├── adapters/cbe_pdf.py — CBE PDF parser (CMap primary)    │
│  ├── engine/cmap_extractor.py — CMap text extraction        │
│  ├── engine/pdf_extractor.py — PDF extraction + OCR (fallback│
│  ├── engine/excel_exporter.py — Excel export engine         │
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
├─────────────────────────────────────────────────────────────┤
│  Tests (pytest — 38 tests, all passing)                     │
│  ├── test_cmap_extractor.py — 13 tests                      │
│  ├── test_fee_extractor.py — 14 tests                       │
│  └── test_excel_exporter.py — 11 tests                      │
└─────────────────────────────────────────────────────────────┘
```

---

## CBE Statement Format (Real Data — June 2026)

**8 Columns (confirmed across 3 real statements):**

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

**Account Types Confirmed:**
- Saving Account (Nael Hailemariam, Sara Birmeka)
- Current Account (Ahimed Kedir Fright Transport)

**Reference Codes:**
- **FT** = Fund Transfer (account to account)
- **TT** = Cash Transaction (cash deposit/withdrawal)
- **CHQ** = Cheque
- **CD** = Cheque Deposit
- **CPO** = Cash Payment Order
- **ECS** = Electronic Clearing (salary)
- **PKR** = Payment to Supplier
- **VPCH** = Voucher Payment

**Important:** PDFs use custom font encoding (DEVEXP+), not scanned images. CMap-based text extraction works — no OCR needed for CBE.

---

## Fee Extraction — 4 Patterns

| Pattern | Example | Status |
|---------|---------|--------|
| 1. Embedded in description | `TRANSFER FEE 25 TAX 15` | ✅ Built |
| 2. Separate line item | `SERVICE CHARGE 25` | ✅ Built |
| 3. Separate row in table | Fee as own transaction row | ✅ Built |
| 4. Deducted but not itemized | Tariff database lookup | ✅ Built |

**Fee Patterns Found in Real Statements:**
- 1,002 = 1,000 + 2 fee
- 2,004 = 2,000 + 4 fee
- 1,005 = 1,000 + 5 fee
- 2,010 = 2,000 + 10 fee
- 502.50 = 500 + 2.50 fee
- 4,008 = 4,000 + 8 fee
- 6,030 = 6,000 + 30 fee

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
| CBE | `cbe_pdf.py` | ✅ Built (CMap primary, OCR fallback) |
| Dashen | `dashen_pdf.py` | 📋 Next |
| Awash | `awash_pdf.py` | 📋 Next |

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/engine/cmap_extractor.py` | CMap PDF text extractor (DEVEXP+ fonts) |
| `backend/app/engine/excel_exporter.py` | Excel export engine (6 sheets) |
| `backend/app/adapters/cbe_pdf.py` | CBE PDF parser (CMap primary, OCR fallback) |
| `backend/app/engine/fee_extractor.py` | 4 fee patterns + tariff DB |
| `backend/app/engine/matching.py` | 3-phase matching engine |
| `backend/app/engine/fuzzy_matcher.py` | Splink fuzzy matching |
| `backend/app/engine/explainer.py` | IFRS/Amharic explanations |
| `backend/app/engine/tariff_db.py` | CBE fee tariff database |
| `backend/app/engine/ethiopian_calendar.py` | Ge'ez → Gregorian |
| `backend/app/engine/balance_verifier.py` | Pre-upload balance check |
| `backend/app/engine/pdf_extractor.py` | PDF extraction + OCR (fallback) |
| `backend/app/main.py` | FastAPI app (CORS, logging) |
| `backend/app/api/reconciliation.py` | Reconciliation + Excel export API |
| `backend/app/api/cheques.py` | Cheque tracking API |
| `backend/tests/` | Test suite (38 tests) |
| `data/real_cbe_samples/` | Real CBE PDF statements |
| `ACCOUNTANT_QUESTIONS.md` | Interview questions |
| `MARKET_RESEARCH_AND_AUDIT.md` | Market research & expert audit |
| `EXECUTION_PLAN.md` | 3-phase execution plan |
| `SESSION_HANDOFF.md` | This file |

---

## How to Run

```bash
# Start everything
docker-compose up -d

# Run tests
python3 -m pytest backend/tests/ -v

# Test PDF upload
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@data/real_cbe_samples/Nael_Hailemariam.pdf"

# Export to Excel
curl -X GET http://localhost:8000/api/reconciliation/export/{run_id} \
  -o reconciliation.xlsx

# Open frontend
open http://localhost:5173
```

---

## Current Status (June 25, 2026)

### ✅ Built (Ready for Testing)
- CMap PDF extractor (DEVEXP+ font decoding)
- CBE PDF adapter (8-column format, CMap primary, OCR fallback)
- Balance verification (hard gate)
- Fee extraction (4 patterns + tariff DB)
- Matching engine (3 phases)
- Explainability engine (IFRS references, Amharic)
- Cheque tracking (API + UI)
- Ethiopian calendar (library + fallback)
- Fuzzy matching (Splink)
- Excel export (6 sheets, professional styling)
- Test suite (38 tests, all passing)
- Security basics (CORS, file limits, logging)

### 🔴 Critical Gaps (Phase 1 — Week 1-2)
- [ ] JWT authentication
- [x] Excel export — DONE
- [x] Automated tests — DONE (38 tests)
- [x] Error handling — DONE

### 🟡 Should-Fix (Phase 2 — Week 3-4)
- [ ] GL account mapping
- [ ] WHT tracking
- [ ] Exception reporting
- [ ] Period lock
- [ ] Executive dashboard

### 🟢 Nice-to-Have (Phase 3 — Week 5-6)
- [ ] Dashen/Awash adapters
- [ ] Reconciliation PDF report
- [ ] User roles (clerk/CFO/auditor)
- [ ] Onboarding wizard

---

## Friday Test Criteria

| Test | Pass | Fail |
|------|------|------|
| Upload real CBE PDF | Parse without errors | Crashes or no data |
| Balance verification | Passes | Rejects valid statement |
| Fee extraction | Extracts fees | Misses fees |
| Matching | Matches transactions | No matches |
| Explainability | Shows IFRS refs | No explanations |
| Excel export | Downloads .xlsx | Fails or empty |
| Tests | 38/38 pass | Any failure |
