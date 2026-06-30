# ReconET — The Rebuild Plan

**Date:** June 30, 2026
**Goal:** Build THE financial intelligence platform for Ethiopian businesses
**Not:** Another reconciliation tool

---

## FIRST PRINCIPLES — What Do We Actually Need?

### The Ethiopian Business Reality

1. A company has 2-5 bank accounts across CBE, Dashen, Awash, etc.
2. The accountant exports bank PDFs once a month
3. They spend 2-3 days manually matching transactions in Excel
4. Nobody knows the real cash position across all banks
5. Bank fees are opaque — nobody tracks them
6. Cheques clear in 3-7 days — nobody tracks outstanding ones properly
7. Fraud/dupe payments are caught in annual audits, if at all
8. The CFO asks "how much cash do we have?" and gets "around X million"

### What We Need to Solve (Priority Order)

| # | Problem | Value | Today's Solution |
|---|---------|-------|-----------------|
| 1 | Real cash position across all banks | CRITICAL | Mental math |
| 2 | Where did my money go? | HIGH | Manual Excel |
| 3 | Can I pay payroll Friday? | HIGH | Hope |
| 4 | Are my accounts clean? | HIGH | Annual audit |
| 5 | Am I overpaying bank fees? | MEDIUM | Nobody knows |
| 6 | Am I tax compliant? | MEDIUM | Manual tracking |
| 7 | Reconciliation matching | MEDIUM | 2-3 days in Excel |

**Key insight:** Reconciliation (#7) is the LOWEST priority problem. We built it first. That's backwards.

---

## WHAT WE'RE BUILDING

### The Product: ReconET — Cash Intelligence for Ethiopian Business

**One sentence:** ReconET tells Ethiopian CFOs how much cash they have, where it's going, and what's wrong — in real time.

**The daily experience:** A CFO opens ReconET every morning. Sees:
- Real cash position (all banks, adjusted for cheques/transfers)
- Yesterday's movements
- Upcoming obligations (payroll, rent, loan payments)
- Anomaly alerts (dupes, unusual transactions, stale cheques)
- Fee summary (what the bank charged yesterday)

**The monthly experience:** An accountant uploads bank statements. ReconET:
- Auto-categorizes every transaction
- Matches against GL (existing engine)
- Flags exceptions with explanations
- Generates reconciliation report for CFO sign-off
- Tracks fees, VAT, WHT for compliance

**The quarterly experience:** The CFO sees:
- Fee benchmarking vs similar companies
- Cash flow trends
- Bank relationship insights
- Compliance status (VAT, WHT, NBE)

---

## ARCHITECTURE — What We Need

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite + Tailwind)            │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Dashboard │ │ Cash     │ │ Fees &   │ │Anomalies │           │
│  │(Morning  │ │ Position │ │Compliance│ │& Alerts  │           │
│  │ Check)   │ │          │ │          │ │          │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Reconcile │ │ Cheques  │ │ Reports  │ │ Settings │           │
│  │(Upload → │ │          │ │(PDF/XLSX)│ │(Users,   │           │
│  │ Review)  │ │          │ │          │ │ Banks)   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ API Layer (REST)                                      │       │
│  │ /api/auth/*  /api/cash/*  /api/recon/*  /api/cheques/*│       │
│  │ /api/fees/*  /api/anomalies/*  /api/reports/*         │       │
│  └──────────────────────────────────────────────────────┘       │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Engine Layer                                          │       │
│  │                                                      │       │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │       │
│  │ │ PDF Parser  │ │ Cash Engine │ │ Fee Engine  │     │       │
│  │ │ (CMap+OCR)  │ │ (Position,  │ │ (Extract,   │     │       │
│  │ │             │ │  Forecast)  │ │  Benchmark) │     │       │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │       │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │       │
│  │ │ Match Engine│ │ Anomaly     │ │ Compliance  │     │       │
│  │ │ (3-phase)   │ │ Detector    │ │ (VAT, WHT,  │     │       │
│  │ │             │ │             │ │  NBE)       │     │       │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │       │
│  │ ┌─────────────┐ ┌─────────────┐                      │       │
│  │ │ Cheque      │ │ Report      │                      │       │
│  │ │ Tracker     │ │ Generator   │                      │       │
│  │ └─────────────┘ └─────────────┘                      │       │
│  └──────────────────────────────────────────────────────┘       │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Data Layer                                            │       │
│  │ PostgreSQL (primary)  │  Redis (cache, queues)        │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## WHAT WE NEED TO BUILD — 6 Engines

### Engine 1: Data Ingestion (The Front Door)

**What it does:** Accepts bank data in any format and normalizes it.

**Must handle:**
- CBE PDF (✅ built — CMap extraction)
- Dashen PDF (📋 need samples)
- Awash PDF (📋 need samples)
- Any bank CSV (✅ basic)
- Peachtree CSV export (📋 need to build)
- Manual entry (📋 need to build)

**What to build:**
- `backend/app/ingestion/peachtree_parser.py` — Parse Peachtree exports
- `backend/app/ingestion/csv_normalizer.py` — Normalize any CSV format
- `backend/app/ingestion/bank_detector.py` — Auto-detect bank (✅ built)
- `backend/app/ingestion/batch_processor.py` — Process multiple files at once

**Key feature:** Upload 5 bank PDFs from 3 different banks → all normalized in one go.

---

### Engine 2: Cash Intelligence (The Core Value)

**What it does:** Shows real cash position across all banks, adjusted for pending items.

**Must compute:**
- Raw balance per account (from latest bank statement)
- Adjusted position (minus outstanding cheques, plus uncleared deposits)
- Pending items (transfers in flight, expected payments)
- 30-day forecast (based on recurring patterns)
- Safety threshold alerts

**What to build:**
- `backend/app/engine/cash_position.py` — Multi-bank cash aggregator
- `backend/app/engine/cash_forecast.py` — 30-day rolling forecast
- `backend/app/engine/recurring_detector.py` — Find standing orders, rent, payroll patterns
- `backend/app/api/cash.py` — Cash position + forecast API

**Data model:**
```sql
CREATE TABLE cash_snapshots (
    id UUID PRIMARY KEY,
    company_id UUID,
    snapshot_date DATE,
    -- Per-account balances
    cbe_balance DECIMAL(15,2),
    dashen_balance DECIMAL(15,2),
    awash_balance DECIMAL(15,2),
    -- Adjustments
    outstanding_cheques DECIMAL(15,2),
    uncleared_deposits DECIMAL(15,2),
    pending_transfers DECIMAL(15,2),
    -- Result
    raw_total DECIMAL(15,2),
    adjusted_total DECIMAL(15,2),
    -- Forecast
    forecast_7day DECIMAL(15,2),
    forecast_30day DECIMAL(15,2),
    safety_threshold DECIMAL(15,2),
    below_threshold BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE recurring_patterns (
    id UUID PRIMARY KEY,
    company_id UUID,
    pattern_type VARCHAR(50), -- payroll, rent, loan, standing_order
    description TEXT,
    amount DECIMAL(15,2),
    frequency VARCHAR(20), -- weekly, biweekly, monthly
    next_expected_date DATE,
    confidence FLOAT,
    source_transaction_ids JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**The killer feature:** Upload bank statement → immediately see real cash position. No GL data needed.

---

### Engine 3: Fee Intelligence (The Money Saver)

**What it does:** Tracks every bank fee, categorizes them, benchmarks against peers.

**Must compute:**
- Total fees by type (transfer, cheque, commission, VAT, WHT)
- Fee trend (month-over-month)
- Fee as % of transaction volume
- Per-transaction fee analysis
- Peer benchmarking (when we have enough data)

**What to build:**
- `backend/app/engine/fee_intelligence.py` — Fee analytics engine
- `backend/app/engine/fee_benchmark.py` — Peer comparison
- `backend/app/api/fees.py` — Fee analytics API

**Data model:**
```sql
CREATE TABLE fee_analysis (
    id UUID PRIMARY KEY,
    company_id UUID,
    period_month INTEGER,
    period_year INTEGER,
    -- Totals
    total_fees DECIMAL(15,2),
    total_bank_charges DECIMAL(15,2),
    total_vat DECIMAL(15,2),
    total_wht DECIMAL(15,2),
    -- By type
    transfer_fees DECIMAL(15,2),
    cheque_fees DECIMAL(15,2),
    commission_fees DECIMAL(15,2),
    other_fees DECIMAL(15,2),
    -- Metrics
    fee_to_volume_ratio FLOAT,
    month_over_month_change FLOAT,
    -- Benchmarks
    peer_median_fees DECIMAL(15,2),
    percentile_rank INTEGER, -- 1-100
    potential_savings DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE fee_schedules (
    id UUID PRIMARY KEY,
    bank_name VARCHAR(100),
    fee_type VARCHAR(50),
    min_amount DECIMAL(15,2),
    max_amount DECIMAL(15,2),
    fee_amount DECIMAL(15,2),
    tax_rate FLOAT,
    effective_from DATE,
    effective_to DATE,
    source VARCHAR(255), -- URL or document reference
    verified BOOLEAN DEFAULT FALSE
);
```

**The killer feature:** "You paid ETB 45,000 in bank fees this quarter. Similar companies pay ETB 32,000. Here's why you're overpaying."

---

### Engine 4: Anomaly Detection (The Guardian)

**What it does:** Finds problems before humans do.

**Must detect:**
- Duplicate payments (same amount, same payee, close dates)
- Weekend/holiday transactions (Ethiopian banks don't process)
- Unusual amounts (spikes vs historical average)
- New payees (first payment to unknown entity)
- Round numbers (potential estimates or errors)
- Stale cheques (>90 days uncashed)
- Missing expected transactions (payroll didn't process)
- Fee anomalies (sudden fee increase)

**What to build:**
- `backend/app/engine/anomaly_detector.py` — Pattern-based anomaly detection
- `backend/app/api/anomalies.py` — Alerts API

**Data model:**
```sql
CREATE TABLE anomaly_alerts (
    id UUID PRIMARY KEY,
    company_id UUID,
    alert_type VARCHAR(50), -- duplicate, weekend, spike, new_payee, stale, missing, fee_anomaly
    severity VARCHAR(20),   -- critical, warning, info
    title TEXT,
    description TEXT,
    description_am TEXT,    -- Amharic
    -- Related entities
    transaction_ids JSONB,
    amount DECIMAL(15,2),
    -- Status
    status VARCHAR(20) DEFAULT 'new', -- new, acknowledged, resolved, false_positive
    resolved_by UUID,
    resolved_at TIMESTAMP,
    resolution_note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**The killer feature:** "Duplicate payment detected: ETB 250,000 to ABC Trading on Jun 12 AND Jun 13. Verify immediately."

---

### Engine 5: Reconciliation (Already Built — Polish It)

**What we have:** 3-phase matching engine, fee extraction, explainability.

**What to add:**
- Peachtree GL import (auto-detect columns, handle Amharic headers)
- Review workflow (approve/reject/override matches)
- Batch processing (upload 3 months at once)
- Exception report as PDF (signable)
- Auto-learning from accountant corrections

**What to build:**
- `backend/app/ingestion/peachtree_parser.py` — Parse Peachtree exports
- `backend/app/engine/review_workflow.py` — Approve/reject/override
- `backend/app/engine/report_generator.py` — PDF reconciliation report

---

### Engine 6: Compliance (The Tax Helper)

**What it does:** Tracks VAT, WHT, and generates compliance reports.

**Must compute:**
- VAT on bank fees (15% — Ethiopian law)
- WHT on bank fees (2%)
- Monthly VAT return data
- Quarterly WHT certificate data
- NBE reporting format

**What to build:**
- `backend/app/engine/compliance.py` — VAT/WHT/NBE tracking
- `backend/app/api/compliance.py` — Compliance API

---

## WHAT WE NEED TO HAVE (Tools & Data)

### Technical Tools (Already Have)

| Tool | Status | Purpose |
|------|--------|---------|
| Python 3.12 | ✅ | Backend language |
| FastAPI | ✅ | API framework |
| SQLAlchemy | ✅ | ORM |
| PostgreSQL | ✅ | Primary database |
| Redis | 📋 | Caching, queues |
| pdfplumber | ✅ | PDF parsing |
| openpyxl | ✅ | Excel export |
| React + Vite | ✅ | Frontend |
| Tailwind CSS | ✅ | Styling |
| JWT auth | ✅ | Authentication |

### Technical Tools (Need to Add)

| Tool | Purpose | Priority |
|------|---------|----------|
| Celery + Redis | Background jobs (forecast, anomaly scan) | P0 |
| WeasyPrint or ReportLab | PDF report generation | P1 |
| Chart.js or Recharts | Frontend charts | P1 |
| APScheduler | Scheduled tasks (daily anomaly scan) | P2 |
| Sentry | Error tracking | P2 |

### Data We Need (Critical)

| Data | Status | How to Get |
|------|--------|-----------|
| CBE PDF samples | ✅ Have 4 | Already in repo |
| Dashen PDF samples | ❌ None | Ask Dashen branch or find online |
| Awash PDF samples | ❌ None | Ask Awash branch or find online |
| CBE fee schedule | 📋 Approximate | Verify at CBE branch |
| Dashen fee schedule | ❌ None | Ask Dashen |
| Awash fee schedule | ❌ None | Ask Awash |
| Peachtree export sample | ❌ None | Ask any accountant |
| Sage export sample | ❌ None | Ask any accountant |
| NBE reporting format | ❌ None | NBE website or accountant |

### Human Access We Need

| Who | Why | How |
|-----|-----|-----|
| 1 Ethiopian accountant | Validate workflow, test UI, Peachtree samples | LinkedIn, personal network |
| 1 CFO | Validate dashboard, approve workflow | Through accountant |
| CBE branch contact | Verify fee schedule, get statement samples | Walk in |
| Dashen branch contact | Statement samples, fee schedule | Walk in |

---

## BUILD ORDER — What to Build First

### Phase 0: Foundation (Week 1) — "Make It Ingest"

Goal: Upload any bank statement → see cash position immediately.

**Build:**
1. Cash Position Engine — multi-bank aggregation, cheque adjustment
2. Peachtree Parser — auto-detect columns from Peachtree CSV export
3. CSV Normalizer — handle any CSV format
4. Batch Upload — upload multiple PDFs at once
5. Dashboard redesign — cash position as hero widget

**Result:** Upload 3 bank PDFs → see total cash position across all banks. No GL data needed. Immediate value.

### Phase 1: Intelligence (Week 2-3) — "Make It Think"

Goal: The platform tells you things you didn't know.

**Build:**
1. Cash Forecast Engine — 30-day rolling forecast from recurring patterns
2. Anomaly Detector — duplicates, weekend txns, spikes, new payees
3. Fee Intelligence — categorize, trend, per-transaction analysis
4. Cheque Lifecycle — auto-match clearing cheques, stale alerts
5. Alert System — real-time notifications for critical anomalies

**Result:** "Your cash drops below safety threshold in 8 days." "Duplicate payment detected." "You're overpaying bank fees by 34%."

### Phase 2: Polish (Week 4) — "Make It Professional"

Goal: A CFO can use this daily. An accountant can replace Excel.

**Build:**
1. Review Workflow — approve/reject/override matches with notes
2. PDF Reconciliation Report — printable, signable
3. Excel Export (enhanced) — professional formatting, all sheets
4. User Management — CFO invites team, role assignment
5. Period Lock — month-end close workflow
6. Compliance Tracker — VAT, WHT summary

**Result:** A complete month-end reconciliation workflow. Upload → match → review → approve → report → sign.

### Phase 3: Network (Week 5-6) — "Make It Indispensable"

Goal: The platform gets better with more users.

**Build:**
1. Fee Benchmarking — aggregate anonymous fee data, compare peers
2. Cash Flow Patterns — learn from transaction history
3. Multi-period Analysis — quarter-over-quarter, year-over-year
4. Onboarding Wizard — first-use experience
5. Mobile-responsive — CFO checks on phone

**Result:** "Companies like yours pay ETB X in fees. You pay ETB Y." The platform becomes a financial advisor.

---

## THE MOAT — Why Can't Someone Copy This?

| Layer | What | Defensible? |
|-------|------|------------|
| CMap PDF extraction | Engineering | ❌ Anyone can build |
| Fee-aware matching | Engineering | ❌ Anyone can build |
| Ethiopian fee database | Data | ✅ Hard to compile |
| Multi-bank format support | Data + Engineering | ✅ Need real samples |
| Peer fee benchmarks | Network | ✅ Need critical mass |
| Anomaly patterns | Data + ML | ✅ Gets better with data |
| Accountant workflow | UX + Domain | ✅ Hard to copy without domain knowledge |
| Daily CFO habit | Product | ✅ Hardest to replicate |

**The real moat is data + habit.** Once 100 companies are feeding data, the benchmarks, anomaly patterns, and forecasts become impossible to replicate without that data. And once a CFO checks ReconET every morning, switching costs are high.

---

## SUCCESS METRICS

### Phase 0 (Week 1)
- [ ] Upload 3 CBE PDFs → see aggregated cash position in <30 seconds
- [ ] Cash position accounts for outstanding cheques
- [ ] No GL data required for immediate value

### Phase 1 (Week 2-3)
- [ ] Cash forecast within 20% accuracy for 7-day window
- [ ] Anomaly detector catches known duplicates in test data
- [ ] Fee analysis shows breakdown by type with trend

### Phase 2 (Week 4)
- [ ] Full workflow: upload → match → review → approve → report
- [ ] PDF report generated in <5 seconds
- [ ] 3 user roles working (clerk, CFO, auditor)

### Phase 3 (Week 5-6)
- [ ] Fee benchmarks available for CBE users
- [ ] Onboarding wizard completes in <5 minutes
- [ ] Mobile dashboard loads in <3 seconds

---

## FILES TO CREATE/REWRITE

### New Engine Files
```
backend/app/engine/cash_position.py        — Multi-bank cash aggregator
backend/app/engine/cash_forecast.py        — 30-day rolling forecast
backend/app/engine/recurring_detector.py   — Standing order/payroll detection
backend/app/engine/anomaly_detector.py     — Duplicate, spike, weekend detection
backend/app/engine/fee_intelligence.py     — Fee analytics + benchmarking
backend/app/engine/compliance.py           — VAT/WHT/NBE tracking
backend/app/engine/review_workflow.py      — Approve/reject/override
backend/app/engine/report_generator.py     — PDF report generation
```

### New Ingestion Files
```
backend/app/ingestion/peachtree_parser.py  — Peachtree CSV parser
backend/app/ingestion/csv_normalizer.py    — Universal CSV normalizer
backend/app/ingestion/batch_processor.py   — Multi-file upload handler
```

### New API Files
```
backend/app/api/cash.py                    — Cash position + forecast
backend/app/api/fees.py                    — Fee analytics
backend/app/api/anomalies.py               — Alert management
backend/app/api/compliance.py              — VAT/WHT reports
backend/app/api/reports.py                 — PDF/XLSX report generation
```

### Frontend Rewrite
```
frontend/src/App.tsx                       — New navigation + auth
frontend/src/pages/Dashboard.tsx           — Cash position hero
frontend/src/pages/CashPosition.tsx        — Multi-bank view + forecast
frontend/src/pages/Reconciliation.tsx      — Upload + review workflow
frontend/src/pages/Fees.tsx                — Fee analytics + benchmarks
frontend/src/pages/Anomalies.tsx           — Alert management
frontend/src/pages/Cheques.tsx             — Cheque lifecycle
frontend/src/pages/Compliance.tsx          — VAT/WHT tracking
frontend/src/pages/Reports.tsx             — Generate/download reports
frontend/src/pages/Settings.tsx            — Users, banks, preferences
```

### Test Files
```
backend/tests/test_cash_position.py
backend/tests/test_cash_forecast.py
backend/tests/test_anomaly_detector.py
backend/tests/test_fee_intelligence.py
backend/tests/test_peachtree_parser.py
backend/tests/test_compliance.py
```

---

## THE DAILY EXPERIENCE (What the User Sees)

### Morning (CFO opens ReconET on phone)

```
┌─────────────────────────────────────┐
│  ReconET                  👤 CFO    │
├─────────────────────────────────────┤
│                                     │
│  Cash Position          ETB 1.83M   │
│  ▲ 12% vs last week                │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ ■ CBE    1,247,330          │   │
│  │ ■ Dashen   456,200          │   │
│  │ ■ Awash    892,100          │   │
│  │ Adjusted: 1,826,630         │   │
│  └─────────────────────────────┘   │
│                                     │
│  ⚠️ 2 Alerts                        │
│  • Stale cheque: ETB 45,000 (120d) │
│  • Duplicate: ETB 250K to ABC Co   │
│                                     │
│  📊 This Month                      │
│  Inflow:  +ETB 5.2M                │
│  Outflow: -ETB 4.8M                │
│  Fees:    ETB 12,400               │
│                                     │
│  📅 Upcoming                        │
│  Jul 4: Payroll ETB 1.2M           │
│  Jul 7: Loan payment ETB 180K      │
│                                     │
└─────────────────────────────────────┘
```

### Month-End (Accountant reconciles)

```
1. Upload 3 bank PDFs (CBE, Dashen, Awash)
2. ReconET auto-categorizes + matches (30 seconds)
3. Review: 45 auto-matched, 5 need review
4. Approve/reject each with notes
5. Generate PDF report → CFO signs
6. Lock period
Total time: 2 hours (vs 2-3 days in Excel)
```

---

## WHAT CHANGES FROM CURRENT CODEBASE

| Current | New |
|---------|-----|
| Reconciliation-centric | Cash-centric |
| Upload → match → export | Upload → understand → act |
| Single bank focus | Multi-bank aggregation |
| Static matching | Learning from corrections |
| Excel export as primary output | Dashboard as primary output |
| No cash visibility | Real-time cash position |
| No anomaly detection | Proactive alerts |
| No fee intelligence | Fee benchmarking |
| No forecast | 30-day cash forecast |
| No compliance tracking | VAT/WHT/NBE |

---

## NEXT STEP

Build Engine 2: Cash Intelligence.

It's the core value. Upload bank PDF → see real cash position. No GL data needed. Immediate value.

That's what makes someone open ReconET every morning.
