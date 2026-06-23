# ReconET — Integrated System

## Quick Start

```bash
# Start PostgreSQL + API
docker-compose up -d

# Run the test
chmod +x test_integration.sh
./test_integration.sh
```

## What's Integrated

### 1. Fee Extraction → Matching Engine
The matching engine now handles three fee scenarios:

**NET MATCH** (most common):
```
Bank: TRANSFER TO ABC FEE 25 TAX 15 | Debit: 100,040
GL:   Vendor ABC | Debit: 100,040
→ Match because: net amount ETB 100,040.00 matches GL · fees of ETB 40.00 included
```

**GROSS MATCH** (when GL splits fees):
```
Bank: TRANSFER TO ABC FEE 25 TAX 15 | Debit: 100,040
GL:   Vendor ABC | Debit: 100,000
→ Match because: gross amount ETB 100,000.00 matches GL · fees ETB 40.00 recorded separately
```

**SPLIT MATCH** (GL has separate fee entry):
```
Bank: TRANSFER TO ABC FEE 25 TAX 15 | Debit: 100,040
GL 1: Vendor ABC | Debit: 100,000
GL 2: Bank Charges (6500) | Debit: 40
→ Match because: gross amount matches vendor · fees match bank charges
```

### 2. PostgreSQL Migration
```bash
# docker-compose.yml handles everything
docker-compose up -d

# PostgreSQL at localhost:5432
# API at localhost:8000
```

### 3. Cheque Tracking
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

## API Response Example

```json
{
  "summary": {
    "total_bank_transactions": 10,
    "total_matched": 5,
    "total_unmatched": 5,
    "match_rate": "50.0%",
    "fee_summary": {
      "total_fees_extracted": 362.0,
      "total_bank_charges": 250.0,
      "total_gov_tax": 112.0,
      "transactions_with_fees": 6
    }
  },
  "matches": [
    {
      "match_id": "abc-123",
      "match_type": "fee_net_match",
      "confidence": 92,
      "explanation": "Matched because: net amount ETB 100,040.00 matches GL · date same day (2026-06-15) · fees of ETB 40.00 included in amount · reference 'INV-2026-0089' found",
      "status": "auto_posted",
      "amount_strategy": "net",
      "bank_transaction": {
        "id": "bank-1",
        "date": "2026-06-15",
        "amount": -100040.0,
        "reference": "INV-2026-0089",
        "description": "TRANSFER TO ABC TRADING FEE 25 TAX 15"
      },
      "fee_breakdown": {
        "strategy": "net",
        "gross_amount": 100040.0,
        "bank_charge": 25.0,
        "gov_tax": 15.0,
        "total_fees": 40.0,
        "net_amount": 100040.0
      }
    }
  ]
}
```

## File Structure

```
reconet/
├── docker-compose.yml          # PostgreSQL + API
├── init.sql                    # Database schema
├── test_integration.sh         # Integration test
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI entry
│       ├── database.py         # PostgreSQL connection
│       ├── models/
│       │   └── __init__.py     # All models including Cheque
│       ├── engine/
│       │   ├── fee_extractor.py
│       │   └── matching.py     # Fee-aware matching
│       └── api/
│           ├── reconciliation.py
│           └── cheques.py
```

## Next Steps

1. **Friday**: Get real CBE CSV from pilot customer
2. **Validate**: Test fee extraction on real data
3. **Deploy**: Push to Render with PostgreSQL
4. **Next week**: Cheque tracking UI
5. **Week after**: Explainability Engine
