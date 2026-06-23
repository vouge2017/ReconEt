"""Core data models — ReconET"""
from sqlalchemy import (
    Column, String, Integer, Float, Date, DateTime, Boolean, Text, JSON,
    ForeignKey, CheckConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    CLERK = "clerk"
    MANAGER = "manager"
    CFO = "cfo"
    AUDITOR = "auditor"


class MatchStatus(str, enum.Enum):
    PENDING = "pending"
    AUTO_POSTED = "auto_posted"
    CONFIRMED = "confirmed"
    OVERRIDDEN = "overridden"
    ANOMALY = "anomaly"


class PeriodStatus(str, enum.Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    LOCKED = "locked"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    tin = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    bank_accounts = relationship("BankAccount", back_populates="company")
    users = relationship("User", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.CLERK)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(50), nullable=False)
    account_type = Column(String(50), nullable=False)
    currency = Column(String(3), default="ETB")
    gl_account_code = Column(String(20))
    is_intercompany = Column(Boolean, default=False)
    intercompany_pair_id = Column(String, ForeignKey("bank_accounts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="bank_accounts")
    transactions = relationship("BankTransaction", back_populates="bank_account")


class BankTransaction(Base):
    """Bank transactions with fee extraction"""
    __tablename__ = "bank_transactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"))
    transaction_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="ETB")
    reference = Column(String(255))
    description = Column(Text)
    transaction_type = Column(String(50))
    # Fee columns
    fee_amount = Column(Float, default=0)
    fee_type = Column(String(50))
    bank_charge = Column(Float, default=0)
    gov_tax = Column(Float, default=0)
    gross_amount = Column(Float)
    net_amount = Column(Float)
    # Standard columns
    balance_after = Column(Float)
    raw_data = Column(JSON)
    upload_batch_id = Column(String)
    is_matched = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    bank_account = relationship("BankAccount", back_populates="transactions")


class GLEntry(Base):
    """GL entries from Peachtree"""
    __tablename__ = "gl_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    entry_date = Column(Date, nullable=False)
    account_code = Column(String(20), nullable=False)
    account_name = Column(String(255))
    description = Column(Text)
    reference = Column(String(255))
    debit_amount = Column(Float, default=0)
    credit_amount = Column(Float, default=0)
    journal_number = Column(String(50))
    source = Column(String(50), default="peachtree_export")
    raw_data = Column(JSON)
    upload_batch_id = Column(String)
    is_matched = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Match(Base):
    """Match results with fee breakdown"""
    __tablename__ = "matches"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    match_type = Column(String(50), nullable=False)
    confidence_score = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    status = Column(String(20), default=MatchStatus.PENDING)
    bank_transaction_ids = Column(JSON, nullable=False)
    gl_entry_ids = Column(JSON)
    fee_breakdown = Column(JSON)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    override_reason = Column(Text, nullable=True)
    is_correction = Column(Boolean, default=False)
    correction_pattern = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Cheque(Base):
    """Cheque tracking"""
    __tablename__ = "cheques"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"))
    cheque_number = Column(String(20), nullable=False)
    cheque_type = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="ETB")
    payee_name = Column(String(255))
    payer_name = Column(String(255))
    issue_date = Column(Date, nullable=False)
    expected_clear_date = Column(Date)
    actual_clear_date = Column(Date)
    status = Column(String(20), default="issued")
    gl_entry_id = Column(String, ForeignKey("gl_entries.id"))
    bank_transaction_id = Column(String, ForeignKey("bank_transactions.id"))
    stale_days = Column(Integer, default=90)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Period(Base):
    """Period lock"""
    __tablename__ = "periods"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    status = Column(String(20), default=PeriodStatus.OPEN)
    locked_by = Column(String, ForeignKey("users.id"), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditTrail(Base):
    """Audit trail — immutable"""
    __tablename__ = "audit_trail"

    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String)
    details = Column(JSON, nullable=False)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
