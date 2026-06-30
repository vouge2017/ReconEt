"""
Fee Intelligence API — ReconET

GET /api/fees/{company_id}/summary    — Fee breakdown for current period
GET /api/fees/{company_id}/trend      — Month-over-month trend
GET /api/fees/{company_id}/benchmark  — Peer benchmarking
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.models import BankAccount, BankTransaction, User
from app.api.auth import get_current_user
from app.engine.fee_intelligence import FeeIntelligenceEngine

router = APIRouter(prefix="/api/fees", tags=["fees"])


@router.get("/{company_id}/summary")
async def get_fee_summary(
    company_id: str,
    month: int = Query(None),
    year: int = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fee breakdown for a specific period"""
    today = date.today()
    month = month or today.month
    year = year or today.year
    
    accounts = db.query(BankAccount).filter(BankAccount.company_id == company_id).all()
    if not accounts:
        return {"status": "no_data"}
    
    account_ids = [a.id for a in accounts]
    transactions = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids)
    ).all()
    
    txn_dicts = [
        {"id": t.id, "date": t.transaction_date, "amount": t.amount,
         "fee_amount": t.fee_amount or 0, "bank_charge": t.bank_charge or 0,
         "gov_tax": t.gov_tax or 0, "description": t.description,
         "bank_name": "Unknown"}
        for t in transactions
    ]
    
    engine = FeeIntelligenceEngine()
    breakdown = engine.analyze_period(txn_dicts, month, year)
    
    return engine.to_breakdown_dict(breakdown)


@router.get("/{company_id}/trend")
async def get_fee_trend(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Month-over-month fee trend"""
    today = date.today()
    curr_month, curr_year = today.month, today.year
    
    if curr_month == 1:
        prev_month, prev_year = 12, curr_year - 1
    else:
        prev_month, prev_year = curr_month - 1, curr_year
    
    accounts = db.query(BankAccount).filter(BankAccount.company_id == company_id).all()
    if not accounts:
        return {"status": "no_data"}
    
    account_ids = [a.id for a in accounts]
    transactions = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids)
    ).all()
    
    txn_dicts = [
        {"id": t.id, "date": t.transaction_date, "amount": t.amount,
         "fee_amount": t.fee_amount or 0, "bank_charge": t.bank_charge or 0,
         "gov_tax": t.gov_tax or 0, "description": t.description}
        for t in transactions
    ]
    
    engine = FeeIntelligenceEngine()
    trend = engine.analyze_trend(
        txn_dicts, txn_dicts, curr_month, curr_year, prev_month, prev_year
    )
    
    return engine.to_trend_dict(trend)


@router.get("/{company_id}/benchmark")
async def get_fee_benchmark(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Benchmark fees against peers"""
    today = date.today()
    
    accounts = db.query(BankAccount).filter(BankAccount.company_id == company_id).all()
    if not accounts:
        return {"status": "no_data"}
    
    account_ids = [a.id for a in accounts]
    transactions = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids)
    ).all()
    
    total_fees = sum(t.fee_amount or 0 for t in transactions)
    total_volume = sum(abs(t.amount or 0) for t in transactions)
    
    engine = FeeIntelligenceEngine()
    benchmark = engine.benchmark(total_fees, total_volume)
    
    return engine.to_benchmark_dict(benchmark)
