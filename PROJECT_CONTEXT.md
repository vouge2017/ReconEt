# ReconET — Project Context

## What is ReconET?

ReconET is an Ethiopian treasury reconciliation platform that matches bank transactions against GL (General Ledger) entries with **fee-aware matching** — the critical feature no competitor has.

**The Problem:** Ethiopian banks (CBE, Dashen, Awash, etc.) embed fees in transaction amounts. A transfer of ETB 100,040 actually = ETB 100,000 vendor payment + ETB 25 bank charge + ETB 15 gov't tax. Existing tools fail to match these because they compare raw amounts.

**The Solution:** ReconET extracts fees from transaction descriptions, then uses three matching strategies (NET, GROSS, SPLIT) to achieve >90% match rates.

**Critical Update (June 24, 2026):** CBE and other banks only provide PDF statements (not CSV) due to security policy. PDF parsing is now the primary ingestion path.

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
│  ├── adapters/cbe_pdf.py — CBE PDF parser (4 account types) │
│  ├── engine/pdf_extractor.py — PDF text/table extraction    │
│  ├── engine/balance_verifier.py — Pre-upload balance check  │
│  ├── engine/ethiopian_calendar.py — Ge'ez → Gregorian       │
│  ├── engine/fee_extractor.py — Extract fees from text       │
│  ├── engine/matching.py — Fee-aware matching engine         │
│  └── engine/explainer.py — Explainability Engine            │
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

## Key Components

### 1. CBE PDF Adapter (`adapters/cbe_pdf.py`)

Parses CBE PDF bank statements with auto-detection of account types:
- **Saving Account**: Balances | Credit | Debit | Value Date | Narrative | Reference | Particulars | Date
- **Current Account**: Date | Particulars | Reference | Narrative | Value Date | Debit | Credit | Balances
- **Current with Overdraft**: Same as Current, allows negative balances
- **Time Deposit**: Fixed-term, skip for now

Extracts: date, value_date, narrative, particulars, reference, debit, credit, balance, reference codes (FT, CHQ, CD, CPO, ECS, PKR, VPCH), cheque numbers.

### 2. Balance Verifier (`engine/balance_verifier.py`)

Pre-upload gate: `opening_balance + sum(credits) - sum(debits) = closing_balance`
- Tolerance: 0.01 ETB
- If fails: reject upload, show error message
- If warning (difference ≤ 1.0 ETB): proceed with caution

### 3. Ethiopian Calendar Converter (`engine/ethiopian_calendar.py`)

CBE statements may use Ethiopian (Ge'ez) calendar dates:
- Ethiopian year 2018 = Gregorian 2025/2026
- Auto-detects and converts before storing

### 4. PDF Extraction Wrapper (`engine/pdf_extractor.py`)

Handles extraction from bank PDFs using:
- pdfplumber (primary) — text-based PDFs with tables
- camelot-py (fallback) — complex table layouts
- Tesseract + amh language pack (scanned PDFs)
- PaddleOCR (messy scans fallback)

### 5. Fee Extraction Engine (`engine/fee_extractor.py`)

Extracts fees from transaction descriptions using regex patterns:
- `FEE 25 TAX 15` → bank_charge=25, gov_tax=15
- `CHARGE 10 VAT 1.50` → bank_charge=10, gov_tax=1.50

### 6. Matching Engine (`engine/matching.py`)

Three fee-aware strategies:
- **NET MATCH** (92%): Bank net amount → GL lump entry
- **GROSS MATCH** (95%): Bank gross → GL vendor entry (fees separate)
- **SPLIT MATCH** (97%): Bank gross → GL vendor + fees → GL bank charges

### 7. Explainability Engine (`engine/explainer.py`)

Generates audit-ready explanations:
- English + Amharic summaries
- IFRS/IAS standard references
- Ethiopian compliance notes (VAT 15%, NBE, fiscal year Jul 7)
- Anomaly detection

### 8. Cheque Tracking (`api/cheques.py`)

- Track issued/received cheques
- Detect stale cheques (>90 days)
- Auto-match cheque clearing to bank transactions

---

## Reference Codes

| Code | Meaning | Match Behavior |
|------|---------|----------------|
| FT | Fund Transfer | Intercompany candidate |
| TT | Telegraphic Transfer | FX transaction, check NBE rate |
| CHQ | Cheque | Link to cheque register |
| CD | Cheque Deposit | Deposit in transit candidate |
| CPO | Cash Payment Order | Payroll/vendor payment |
| ECS | Electronic Clearing | Salary/auto-debit |
| PKR | Payment to Supplier | Vendor payment, match to AP |
| VPCH | Voucher Payment | Government/institutional |

---

## Database Schema

Key tables: `companies`, `bank_accounts`, `bank_transactions` (with fee columns), `gl_entries`, `matches` (with fee_breakdown JSON), `cheques`, `periods`, `audit_trail`.

Seed data: One company (Ethiopian Trading Corp), two bank accounts (CBE + Dashen).

---

## Current Status (as of June 24, 2026)

### ✅ Built
- CBE PDF adapter with multi-account-type detection
- Balance verification (pre-upload gate)
- Ethiopian calendar converter
- PDF extraction wrapper (pdfplumber + camelot + OCR)
- Fee extraction engine
- Fee-aware matching engine (NET/GROSS/SPLIT)
- Explainability Engine with IFRS references
- Cheque tracking API and frontend
- PostgreSQL schema with all tables
- Docker Compose setup

### 🚧 In Progress
- Testing with real CBE PDF statements
- Integration with Peachtree GL exports

### 📋 Planned
- Multi-bank adapters (Dashen, Awash, Ecobank)
- Bilingual UI (Amharic interface)
- Correction learning loop
- Audit trail export to Excel
- FX rate auto-fetch from NBE
- Telegram notifications
- Pilot customer deployment

---

## How to Run

```bash
# Start everything
docker-compose up -d

# Create sample CBE PDF
cd backend && python create_sample_cbe_pdf.py && cd ..

# Test PDF upload
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@data/sample_cbe_statement.pdf"

# Test CSV upload (still works)
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@data/sample_cbe_with_fees.csv"

# Run integration test
chmod +x test_cbe_pdf.sh && ./test_cbe_pdf.sh

# Open frontend
open http://localhost:5173
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/adapters/cbe_pdf.py` | CBE PDF parser (4 account types) |
| `backend/app/engine/pdf_extractor.py` | PDF text/table extraction |
| `backend/app/engine/balance_verifier.py` | Pre-upload balance check |
| `backend/app/engine/ethiopian_calendar.py` | Ge'ez → Gregorian conversion |
| `backend/app/engine/fee_extractor.py` | Fee extraction from descriptions |
| `backend/app/engine/matching.py` | Fee-aware matching engine |
| `backend/app/engine/explainer.py` | Explainability Engine |
| `backend/app/api/reconciliation.py` | Reconciliation API (PDF + CSV) |
| `backend/app/api/cheques.py` | Cheque tracking API |
| `backend/app/models/__init__.py` | SQLAlchemy models |
| `backend/create_sample_cbe_pdf.py` | Generate sample CBE PDF |
| `frontend/src/pages/Reconciliation.tsx` | Reconciliation UI |
| `frontend/src/pages/Cheques.tsx` | Cheques UI |
| `test_cbe_pdf.sh` | PDF integration test |
| `init.sql` | PostgreSQL schema |
| `docker-compose.yml` | Infrastructure |
