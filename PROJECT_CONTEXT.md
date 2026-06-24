# ReconET — Project Context

## What is ReconET?

ReconET is an Ethiopian treasury reconciliation platform that matches bank transactions against GL (General Ledger) entries with **fee-aware matching** — the critical feature no competitor has.

**The Problem:** Ethiopian banks (CBE, Dashen, Awash, etc.) embed fees in transaction amounts. A transfer of ETB 100,040 actually = ETB 100,000 vendor payment + ETB 25 bank charge + ETB 15 gov't tax. Existing tools fail to match these because they compare raw amounts.

**The Solution:** ReconET extracts fees from transaction descriptions, then uses three matching strategies (NET, GROSS, SPLIT) to achieve >90% match rates.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Tailwind)                         │
│  ├── Reconciliation page (upload CSV → view matches)        │
│  └── Cheques page (track outstanding/stale cheques)         │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLAlchemy)                              │
│  ├── /api/reconciliation/run — Upload bank CSV, get matches │
│  ├── /api/cheques/ — CRUD for cheque tracking               │
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

### 1. Fee Extraction Engine (`engine/fee_extractor.py`)

Extracts fees from transaction descriptions using regex patterns:
- `FEE 25 TAX 15` → bank_charge=25, gov_tax=15
- `CHARGE 10 VAT 1.50` → bank_charge=10, gov_tax=1.50
- Handles Amharic column names from CBE exports

### 2. Matching Engine (`engine/matching.py`)

Three fee-aware strategies:
- **NET MATCH** (92% confidence): Bank net amount → GL lump entry
- **GROSS MATCH** (95%): Bank gross → GL vendor entry (fees separate)
- **SPLIT MATCH** (97%): Bank gross → GL vendor + fees → GL bank charges

Plus: date-shifted matching for bank processing lag (1-3 days).

### 3. Explainability Engine (`engine/explainer.py`)

Generates audit-ready explanations for every match:
- Plain-language English + Amharic explanations
- IFRS/IAS standard references (IFRS 9, 10, 15; IAS 1, 7, 12, 21, 32, 39)
- Ethiopian compliance notes (VAT 15%, NBE directives, fiscal year Jul 7)
- Anomaly detection (weekend txns, round amounts, amount spikes)
- Confidence classification (auto-post / review / manual)

### 4. Cheque Tracking (`api/cheques.py`)

Ethiopian companies process ~50,000 cheques/day at CBE alone:
- Track issued/received cheques
- Detect stale cheques (>90 days outstanding)
- Auto-match cheque clearing to bank transactions

---

## Database Schema

Key tables: `companies`, `bank_accounts`, `bank_transactions` (with fee columns), `gl_entries`, `matches` (with fee_breakdown JSON), `cheques`, `periods`, `audit_trail`.

Seed data: One company (Ethiopian Trading Corp), two bank accounts (CBE + Dashen).

---

## Frontend Pages

1. **Reconciliation** — Upload bank CSV → view matches with fee breakdowns, confidence badges, IFRS references, anomaly flags
2. **Cheques** — View outstanding/stale cheques, register new cheques, stale alerts

---

## Current Status (as of June 24, 2026)

### ✅ Built
- Fee extraction engine with regex patterns
- Fee-aware matching engine (NET/GROSS/SPLIT strategies)
- Explainability Engine with IFRS references and Amharic support
- Cheque tracking API and frontend
- PostgreSQL schema with all tables
- Docker Compose setup
- Sample CBE CSV data

### 🚧 In Progress
- Real GL CSV upload (parser exists, needs testing with real data)
- Integration with Peachtree GL exports

### 📋 Planned
- Bilingual UI (Amharic interface)
- Correction learning loop (user overrides improve future matches)
- Audit trail export to Excel
- FX rate auto-fetch from NBE
- Telegram notifications
- Multi-bank adapters (Dashen, Awash, Ecobank formats)
- Pilot customer deployment

---

## How to Run

```bash
# Start everything
docker-compose up -d

# Test API
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_csv=@data/sample_cbe_with_fees.csv"

# Open frontend
open http://localhost:5173
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/engine/fee_extractor.py` | Fee extraction from descriptions |
| `backend/app/engine/matching.py` | Fee-aware matching engine |
| `backend/app/engine/explainer.py` | Explainability Engine |
| `backend/app/api/reconciliation.py` | Reconciliation API |
| `backend/app/api/cheques.py` | Cheque tracking API |
| `backend/app/models/__init__.py` | SQLAlchemy models |
| `frontend/src/pages/Reconciliation.tsx` | Reconciliation UI |
| `frontend/src/pages/Cheques.tsx` | Cheques UI |
| `init.sql` | PostgreSQL schema |
| `docker-compose.yml` | Infrastructure |
