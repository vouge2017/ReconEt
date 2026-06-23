# ReconET — Integrated System (v2)

## What's Built

### 1. Fee Extraction → Matching Engine → UI

**The Flow:**
```
CBE CSV → Fee Extractor → Matching Engine → API Response → Frontend Display
```

**What the CFO sees:**
- Match rate: 92%
- Total fees extracted: ETB 362.00
- Bank charges: ETB 250.00
- Government tax (VAT): ETB 112.00
- Each match shows: confidence, explanation, fee breakdown

---

## Quick Start

```bash
# Start everything (PostgreSQL + API + Frontend)
docker-compose up -d

# Wait for services to be healthy
sleep 10

# Test the API
./test_integration.sh

# Open frontend
open http://localhost:5173
```

---

## What You'll See

### Frontend (http://localhost:5173)

1. **Upload Button** — Select CBE CSV file
2. **Fee Summary Dashboard** — 4 cards showing:
   - Match Rate (e.g., "50%")
   - Total Fees Extracted (e.g., "ETB 362.00")
   - Bank Charges (e.g., "ETB 250.00")
   - Gov't Tax (e.g., "ETB 112.00")
3. **Match Cards** — Each transaction shows:
   - Confidence badge (92%, 85%, etc.)
   - Status (Auto-Posted, Review)
   - Explanation: "Matched because: net amount ETB 100,040.00 matches GL · fees of ETB 40.00 included"
   - **Fee Breakdown Panel** (expandable):
     - Gross Amount: ETB 100,040.00
     - Bank Charge: ETB 25.00
     - Gov't Tax (15%): ETB 15.00
     - Total Fees: ETB 40.00
     - Net Amount (GL): ETB 100,040.00

---

## API Endpoints

### Reconciliation
```bash
# Run matching with fee extraction
curl -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_csv=@data/sample_cbe_with_fees.csv"

# Get fee summary
curl http://localhost:8000/api/reconciliation/summary/{company_id}
```

### Cheques
```bash
# List outstanding cheques
curl http://localhost:8000/api/cheques/outstanding/{company_id}

# List stale cheques (>90 days)
curl http://localhost:8000/api/cheques/stale/{company_id}

# Register new cheque
curl -X POST http://localhost:8000/api/cheques/ \
  -H "Content-Type: application/json" \
  -d '{
    "bank_account_id": "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "cheque_number": "CHQ-001235",
    "cheque_type": "issued",
    "amount": 50000,
    "payee_name": "Supplier ABC",
    "issue_date": "2026-06-01"
  }'
```

---

## Fee Matching Strategies

| Strategy | When | Example | Confidence |
|----------|------|---------|------------|
| **NET** | Fees embedded in GL | Bank 100,040 → GL 100,040 | 92% |
| **GROSS** | GL records vendor only | Bank 100,040 → GL 100,000 | 95% |
| **SPLIT** | GL has separate fee entry | Bank 100,040 → GL 100,000 + GL 40 | 97% |

---

## File Structure

```
reconet/
├── docker-compose.yml
├── init.sql                    # PostgreSQL schema
├── test_integration.sh
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── database.py
│       ├── models/__init__.py
│       ├── engine/
│       │   ├── fee_extractor.py
│       │   └── matching.py
│       └── api/
│           ├── reconciliation.py
│           └── cheques.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       └── pages/Reconciliation.tsx
└── data/
    └── sample_cbe_with_fees.csv
```

---

## Testing Checklist

- [ ] `docker-compose up -d` starts without errors
- [ ] PostgreSQL is healthy (check with `docker-compose ps`)
- [ ] API responds at http://localhost:8000/health
- [ ] Frontend loads at http://localhost:5173
- [ ] Upload sample CSV shows matches
- [ ] Fee breakdown displays for transactions with fees
- [ ] Cheque endpoints return data

---

## What's NOT Built (Intentionally)

- Telegram notifications
- FX rate auto-fetch
- Explainability Engine
- Amharic interface
- Correction learning loop

**Focus: Test, fix, validate. Next week: pilot customer demo.**
