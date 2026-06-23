# ReconET — Three Blockers Implementation Plan

**Date:** June 23, 2026
**Priority:** Fee Extraction → PostgreSQL → Cheque Tracking
**Goal:** Fix these before Explainability Engine

---

## BLOCKER 1: FEE EXTRACTION (This Week)

### Why It's Critical
Without fee extraction:
- 30% of transactions won't match (fees embedded in amount)
- CFO loses trust immediately
- "Why didn't it match?" → "Because the tool doesn't understand fees"

### What's Built ✅
- `FeeExtractor` class with 3 extraction methods
- `CBEAdapterWithFees` that integrates fee extraction
- Sample CBE CSV with realistic fee patterns
- Demo script showing extraction results

### What's Left to Build

| Task | Priority | Effort | Status |
|------|----------|--------|--------|
| Validate with real CBE CSV | P0 | 2 hours | ⏳ Waiting for customer data |
| Add CBE tariff database | P1 | 3 hours | 📝 Not started |
| Update matching engine for fee-aware matching | P0 | 4 hours | 📝 Not started |
| Build Fee Reconciliation Report | P1 | 3 hours | 📝 Not started |
| Add fee anomaly detection | P2 | 2 hours | 📝 Not started |
| Test with Dashen, Awash, Ecobank formats | P1 | 4 hours | 📝 Not started |

### Fee-Aware Matching Logic

```python
# Current matching: amount == amount (fails if fees embedded)
# New matching: Try 3 strategies

def match_with_fees(bank_txn, gl_entries):
    # Strategy 1: NET MATCH (fees included in amount)
    # Bank: 100,040 (includes 25 fee + 15 tax)
    # GL: 100,040 (lump sum)
    # → Match if net_amount == gl_amount
    
    # Strategy 2: SPLIT MATCH (GL separates fees)
    # Bank: gross 100,000 + fee 25 + tax 15 = 100,040
    # GL Entry 1: Vendor 100,000
    # GL Entry 2: Bank Charges 40
    # → Match if gross == vendor_gl AND fees == charges_gl
    
    # Strategy 3: GROSS MATCH (GL records gross only)
    # Bank: gross 100,000 (fees separate)
    # GL: 100,000
    # → Match if gross_amount == gl_amount
```

### Customer Discovery Questions

Before configuring fee handling for a new customer:

1. "When you pay a vendor ETB 100,000 and bank charges ETB 25 + tax ETB 15, what's the journal entry?"
2. "Do you have a 'Bank Charges' or 'Bank Fees' GL account? What number?"
3. "Show me your last bank statement — can you point to the fee line?"
4. "Do you reconcile fees separately or as part of the main transaction?"
5. "Has a fee amount ever changed without notice? How did you catch it?"

---

## BLOCKER 2: POSTGRESQL MIGRATION (This Week)

### Why It's Critical
SQLite limitations:
- Single writer = blocks multi-user
- No concurrent connections
- File locking = data corruption risk
- No replication/backup

### Migration Plan

#### Step 1: Database Schema Migration
```sql
-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    tin VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'clerk',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bank Accounts
CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    gl_account_code VARCHAR(20),
    is_intercompany BOOLEAN DEFAULT false,
    intercompany_pair_id UUID REFERENCES bank_accounts(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bank Transactions (with fee columns)
CREATE TABLE bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_account_id UUID REFERENCES bank_accounts(id),
    transaction_date DATE NOT NULL,
    value_date DATE,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    reference VARCHAR(255),
    description TEXT,
    transaction_type VARCHAR(50),
    fee_amount DECIMAL(15,2) DEFAULT 0,
    fee_type VARCHAR(50),
    gross_amount DECIMAL(15,2),
    net_amount DECIMAL(15,2),
    balance_after DECIMAL(15,2),
    raw_data JSONB,
    upload_batch_id VARCHAR(255),
    is_matched BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- GL Entries
CREATE TABLE gl_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    entry_date DATE NOT NULL,
    account_code VARCHAR(20) NOT NULL,
    account_name VARCHAR(255),
    description TEXT,
    reference VARCHAR(255),
    debit_amount DECIMAL(15,2) DEFAULT 0,
    credit_amount DECIMAL(15,2) DEFAULT 0,
    journal_number VARCHAR(50),
    source VARCHAR(50) DEFAULT 'peachtree_export',
    raw_data JSONB,
    upload_batch_id VARCHAR(255),
    is_matched BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Matches
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    match_type VARCHAR(50) NOT NULL,
    confidence_score INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    bank_transaction_ids JSONB NOT NULL,
    gl_entry_ids JSONB,
    loan_schedule_id UUID,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    override_reason TEXT,
    is_correction BOOLEAN DEFAULT false,
    correction_pattern JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Periods
CREATE TABLE periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    period_month INTEGER NOT NULL,
    period_year INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    locked_by UUID REFERENCES users(id),
    locked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit Trail
CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB NOT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_bank_txn_date ON bank_transactions(transaction_date);
CREATE INDEX idx_bank_txn_account ON bank_transactions(bank_account_id);
CREATE INDEX idx_bank_txn_matched ON bank_transactions(is_matched);
CREATE INDEX idx_gl_entry_date ON gl_entries(entry_date);
CREATE INDEX idx_gl_entry_account ON gl_entries(account_code);
CREATE INDEX idx_gl_entry_matched ON gl_entries(is_matched);
CREATE INDEX idx_match_company ON matches(company_id);
CREATE INDEX idx_match_status ON matches(status);
CREATE INDEX idx_audit_company ON audit_trail(company_id);
CREATE INDEX idx_audit_created ON audit_trail(created_at);
```

#### Step 2: Data Migration Script
```python
# migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

def migrate_data(sqlite_path, pg_conn_str):
    # Connect to both
    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = psycopg2.connect(pg_conn_str)
    
    # Migrate each table
    tables = ['companies', 'users', 'bank_accounts', 'bank_transactions',
              'gl_entries', 'matches', 'periods', 'audit_trail']
    
    for table in tables:
        # Read from SQLite
        cursor = sqlite_conn.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        # Write to PostgreSQL
        with pg_conn.cursor() as pg_cursor:
            insert_sql = f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES %s
                ON CONFLICT (id) DO NOTHING
            """
            execute_values(pg_cursor, insert_sql, rows)
    
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
```

#### Step 3: Update Database Connection
```python
# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use PostgreSQL in production, SQLite in development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reconet.db")

# Fix for Render's postgres:// URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Step 4: Render Deployment
```yaml
# render.yaml
services:
  - type: web
    name: reconet-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: reconet-db
          property: connectionString

databases:
  - name: reconet-db
    plan: free
    databaseName: reconet
    user: reconet_user
```

### Migration Checklist

- [ ] Create PostgreSQL database on Render
- [ ] Run schema migration
- [ ] Write data migration script
- [ ] Test migration with sample data
- [ ] Update connection strings
- [ ] Deploy updated backend
- [ ] Verify all endpoints work
- [ ] Load test with concurrent users

---

## BLOCKER 3: CHEQUE TRACKING (Next Week)

### Why It's Critical
Ethiopian companies still rely heavily on cheques:
- CBE processes ~50,000 cheques/day
- Average cheque clearing: 3-7 days
- Stale cheques = unreconciled items = audit findings
- "Where is cheque #1234?" = manual phone call to bank

### Cheque Lifecycle

```
ISSUED → DEPOSITED → CLEARING → CLEARED/BOUNCED → STALE
   ↓         ↓          ↓            ↓              ↓
 GL Entry  Bank CSV   Pending     Matched      Exception
```

### Database Schema

```sql
CREATE TABLE cheques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    bank_account_id UUID REFERENCES bank_accounts(id),
    
    -- Cheque details
    cheque_number VARCHAR(20) NOT NULL,
    cheque_type VARCHAR(10) NOT NULL, -- 'issued' or 'received'
    
    -- Amounts
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    
    -- Parties
    payee_name VARCHAR(255), -- Who we're paying
    payer_name VARCHAR(255), -- Who's paying us
    
    -- Dates
    issue_date DATE NOT NULL,
    expected_clear_date DATE, -- Based on bank SLA
    actual_clear_date DATE, -- When it actually cleared
    
    -- Status
    status VARCHAR(20) DEFAULT 'issued',
    -- issued, deposited, clearing, cleared, bounced, stale, cancelled
    
    -- Reconciliation
    gl_entry_id UUID REFERENCES gl_entries(id),
    bank_transaction_id UUID REFERENCES bank_transactions(id),
    match_id UUID REFERENCES matches(id),
    
    -- Stale detection
    stale_days INTEGER DEFAULT 90, -- Days until considered stale
    stale_warning_sent BOOLEAN DEFAULT false,
    
    -- Notes
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cheque_number ON cheques(cheque_number);
CREATE INDEX idx_cheque_status ON cheques(status);
CREATE INDEX idx_cheque_account ON cheques(bank_account_id);
CREATE INDEX idx_cheque_clear_date ON cheques(expected_clear_date);
```

### Stale Cheque Detection

```python
class ChequeTracker:
    """Track and detect stale cheques"""
    
    STALE_THRESHOLD_DAYS = 90  # Ethiopian standard
    
    def get_stale_cheques(self, company_id: str) -> List[dict]:
        """Find all cheques that haven't cleared within threshold"""
        
        query = """
            SELECT 
                c.cheque_number,
                c.amount,
                c.payee_name,
                c.issue_date,
                c.expected_clear_date,
                CURRENT_DATE - c.issue_date as days_outstanding,
                c.status
            FROM cheques c
            WHERE c.company_id = :company_id
            AND c.status IN ('issued', 'deposited', 'clearing')
            AND c.issue_date < CURRENT_DATE - INTERVAL '%s days'
            ORDER BY c.issue_date ASC
        """ % self.STALE_THRESHOLD_DAYS
        
        return execute(query, {"company_id": company_id})
    
    def get_clearing_exceptions(self, company_id: str) -> List[dict]:
        """Find cheques that should have cleared but haven't"""
        
        query = """
            SELECT 
                c.cheque_number,
                c.amount,
                c.payee_name,
                c.expected_clear_date,
                CURRENT_DATE - c.expected_clear_date as days_overdue
            FROM cheques c
            WHERE c.company_id = :company_id
            AND c.status IN ('issued', 'deposited')
            AND c.expected_clear_date < CURRENT_DATE
            ORDER BY days_overdue DESC
        """
        
        return execute(query, {"company_id": company_id})
    
    def auto_match_cheque(self, cheque, bank_txn):
        """Auto-match cheque to bank transaction when it clears"""
        
        # Check if amounts match
        if abs(cheque.amount - abs(bank_txn.amount)) > 1.0:
            return None
        
        # Check if cheque number in description
        if cheque.cheque_number not in str(bank_txn.description):
            return None
        
        # Update cheque status
        cheque.status = "cleared"
        cheque.actual_clear_date = bank_txn.transaction_date
        cheque.bank_transaction_id = bank_txn.id
        
        return MatchResult(
            match_type="cheque_clearing",
            confidence=98,
            explanation=f"Cheque #{cheque.cheque_number} for ETB {cheque.amount:,.2f} "
                       f"cleared on {bank_txn.transaction_date} "
                       f"(issued {cheque.issue_date}, "
                       f"{(bank_txn.transaction_date - cheque.issue_date).days} days to clear)"
        )
```

### Cheque Dashboard Widget

```
┌─────────────────────────────────────────────────────────┐
│ CHEQUE STATUS SUMMARY                        [View All] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Outstanding: 23 cheques    │  Stale: 3 cheques        │
│  ETB 1,450,000              │  ETB 125,000              │
│                                                         │
│  ⚠️ STALE ALERTS                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ CHQ-001234 │ ETB 45,000 │ 120 days │ ABC Trading│   │
│  │ CHQ-001235 │ ETB 30,000 │ 95 days  │ XYZ Ltd    │   │
│  │ CHQ-001236 │ ETB 50,000 │ 91 days  │ Supplier A │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Cancel Stale] [Request Replacement] [Add Notes]       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Cheque Matching in Reconciliation

When processing bank CSV:
1. Check if description contains "CHQ" or "CHEQUE"
2. Extract cheque number from description
3. Look up cheque in `cheques` table
4. If found and amount matches → auto-match (98% confidence)
5. Update cheque status to "cleared"

---

## IMPLEMENTATION TIMELINE

### Week 1: Fee Extraction + PostgreSQL

| Day | Task | Output |
|-----|------|--------|
| Mon | Get real CBE CSV from pilot customer | Validated fee patterns |
| Tue | Build fee-aware matching engine | Updated matching logic |
| Wed | Create PostgreSQL schema | Database ready |
| Thu | Write migration script | Data migration ready |
| Fri | Deploy to Render + test | Production deployment |

### Week 2: Cheque Tracking + Testing

| Day | Task | Output |
|-----|------|--------|
| Mon | Build cheque database schema | Tables created |
| Tue | Implement stale detection | Alert system |
| Wed | Build cheque matching | Auto-match logic |
| Thu | Create cheque dashboard | UI widget |
| Fri | End-to-end testing | All 3 blockers working |

### Week 3: Explainability Engine

| Day | Task | Output |
|-----|------|--------|
| Mon | Implement explanation templates | All 6 match types |
| Tue | Add accounting treatment | IFRS references |
| Wed | Build bilingual output | Amharic support |
| Thu | Audit trail integration | Export format |
| Fri | CFO review + feedback | Iterate |

---

## SUCCESS METRICS

| Blocker | Metric | Target |
|---------|--------|--------|
| Fee Extraction | Match rate improvement | >90% (from ~70%) |
| Fee Extraction | Fee detection accuracy | >95% |
| PostgreSQL | Concurrent users | >10 simultaneous |
| PostgreSQL | Query performance | <100ms p95 |
| Cheque Tracking | Stale detection | 100% of stale cheques |
| Cheque Tracking | Auto-match rate | >80% of clearing cheques |

---

## WHAT TO ASK THE CUSTOMER NOW

1. **"Can you send us your last month's CBE bank statement CSV?"**
   → We need real data to validate fee extraction

2. **"How do you record bank fees in Peachtree?"**
   → Lump sum or split to Bank Charges account?

3. **"Do you use cheques? How many per month?"**
   → Determines priority of cheque tracking

4. **"How many users need simultaneous access?"**
   → Confirms PostgreSQL urgency

5. **"What's your biggest reconciliation pain point right now?"**
   → May reveal other blockers we missed
