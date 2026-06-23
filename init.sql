-- ReconET PostgreSQL Schema
-- Run on container init

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    tin VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bank_account_id UUID REFERENCES bank_accounts(id),
    transaction_date DATE NOT NULL,
    value_date DATE,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    reference VARCHAR(255),
    description TEXT,
    transaction_type VARCHAR(50),
    -- Fee columns (the critical addition)
    fee_amount DECIMAL(15,2) DEFAULT 0,
    fee_type VARCHAR(50),
    gross_amount DECIMAL(15,2),
    net_amount DECIMAL(15,2),
    bank_charge DECIMAL(15,2) DEFAULT 0,
    gov_tax DECIMAL(15,2) DEFAULT 0,
    -- Standard columns
    balance_after DECIMAL(15,2),
    raw_data JSONB,
    upload_batch_id VARCHAR(255),
    is_matched BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- GL Entries
CREATE TABLE gl_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    match_type VARCHAR(50) NOT NULL,
    confidence_score INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    bank_transaction_ids JSONB NOT NULL,
    gl_entry_ids JSONB,
    -- Fee breakdown in match
    fee_breakdown JSONB,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    override_reason TEXT,
    is_correction BOOLEAN DEFAULT false,
    correction_pattern JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cheques (new table for cheque tracking)
CREATE TABLE cheques (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    bank_account_id UUID REFERENCES bank_accounts(id),
    cheque_number VARCHAR(20) NOT NULL,
    cheque_type VARCHAR(10) NOT NULL CHECK (cheque_type IN ('issued', 'received')),
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ETB',
    payee_name VARCHAR(255),
    payer_name VARCHAR(255),
    issue_date DATE NOT NULL,
    expected_clear_date DATE,
    actual_clear_date DATE,
    status VARCHAR(20) DEFAULT 'issued' CHECK (status IN ('issued', 'deposited', 'clearing', 'cleared', 'bounced', 'stale', 'cancelled')),
    gl_entry_id UUID REFERENCES gl_entries(id),
    bank_transaction_id UUID REFERENCES bank_transactions(id),
    stale_days INTEGER DEFAULT 90,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Periods
CREATE TABLE periods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB NOT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_bank_txn_date ON bank_transactions(transaction_date);
CREATE INDEX idx_bank_txn_account ON bank_transactions(bank_account_id);
CREATE INDEX idx_bank_txn_matched ON bank_transactions(is_matched);
CREATE INDEX idx_gl_entry_date ON gl_entries(entry_date);
CREATE INDEX idx_gl_entry_account ON gl_entries(account_code);
CREATE INDEX idx_gl_entry_matched ON gl_entries(is_matched);
CREATE INDEX idx_match_company ON matches(company_id);
CREATE INDEX idx_match_status ON matches(status);
CREATE INDEX idx_cheque_number ON cheques(cheque_number);
CREATE INDEX idx_cheque_status ON cheques(status);
CREATE INDEX idx_cheque_company ON cheques(company_id);
CREATE INDEX idx_audit_company ON audit_trail(company_id);
CREATE INDEX idx_audit_created ON audit_trail(created_at);

-- Seed data for testing
INSERT INTO companies (id, name, tin) VALUES 
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Ethiopian Trading Corp', 'ETH-00123456');

INSERT INTO bank_accounts (id, company_id, bank_name, account_number, account_type, gl_account_code) VALUES
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'CBE', '1000123456789', 'Current', '1100'),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Dashen', '2000987654321', 'Current', '1101');
