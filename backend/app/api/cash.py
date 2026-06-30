"""
Cash Intelligence API — ReconET

The hero endpoints:
GET /api/cash/position/{company_id} — Real cash position across all banks
GET /api/cash/forecast/{company_id} — 30-day cash forecast
GET /api/cash/summary/{company_id}  — Quick summary for dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, timedelta

from app.database import get_db
from app.models import (
    BankAccount, BankTransaction, Cheque, User, Match
)
from app.api.auth import get_current_user
from app.engine.cash_position import CashPositionEngine
from app.engine.cash_forecast import CashForecastEngine, RecurringPattern
from app.engine.recurring_detector import RecurringDetector
from app.engine.anomaly_detector import AnomalyDetector

router = APIRouter(prefix="/api/cash", tags=["cash"])


@router.get("/position/{company_id}")
async def get_cash_position(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get real cash position across all bank accounts.
    
    Returns:
    - Per-account balances (raw + adjusted)
    - Outstanding cheques deducted
    - Uncleared deposits added
    - Total adjusted position
    - By-bank breakdown
    - Stale cheque alerts
    - Trend vs previous period
    """
    # Get all bank accounts for company
    accounts = db.query(BankAccount).filter(
        BankAccount.company_id == company_id
    ).all()
    
    if not accounts:
        return {
            "status": "no_accounts",
            "message": "No bank accounts configured. Add bank accounts first.",
            "accounts": [],
            "totals": {"adjusted_position": 0},
        }
    
    # Get transactions for all accounts
    account_ids = [a.id for a in accounts]
    transactions = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids)
    ).all()
    
    # Get cheques
    cheques = db.query(Cheque).filter(
        Cheque.company_id == company_id
    ).all()
    
    # Get previous period position (30 days ago)
    thirty_days_ago = date.today() - timedelta(days=30)
    old_txns = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids),
        BankTransaction.transaction_date <= thirty_days_ago,
    ).all()
    
    previous_position = None
    if old_txns:
        # Sum latest balances per account from old transactions
        acct_balances = {}
        for t in old_txns:
            if t.balance_after is not None:
                acct_balances[t.bank_account_id] = t.balance_after
        previous_position = sum(acct_balances.values()) if acct_balances else None
    
    # Convert to dicts
    account_dicts = [
        {
            "id": a.id,
            "company_id": a.company_id,
            "bank_name": a.bank_name,
            "account_number": a.account_number,
            "account_type": a.account_type,
            "currency": a.currency,
        }
        for a in accounts
    ]
    
    txn_dicts = [
        {
            "id": t.id,
            "bank_account_id": t.bank_account_id,
            "date": t.transaction_date,
            "amount": t.amount,
            "description": t.description,
            "reference": t.reference,
            "balance": t.balance_after,
            "fee_amount": t.fee_amount or 0,
        }
        for t in transactions
    ]
    
    cheque_dicts = [
        {
            "id": c.id,
            "bank_account_id": c.bank_account_id,
            "cheque_number": c.cheque_number,
            "amount": c.amount,
            "payee_name": c.payee_name,
            "issue_date": c.issue_date,
            "status": c.status,
        }
        for c in cheques
    ]
    
    # Compute cash position
    engine = CashPositionEngine()
    position = engine.compute(
        bank_accounts=account_dicts,
        transactions=txn_dicts,
        cheques=cheque_dicts,
        previous_position=previous_position,
    )
    
    return engine.to_dict(position)


@router.get("/forecast/{company_id}")
async def get_cash_forecast(
    company_id: str,
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get 30-day cash forecast based on recurring patterns.
    
    Returns:
    - Daily predicted balance
    - Expected inflows/outflows
    - Critical days (below safety threshold)
    - Alerts
    """
    # Get current cash position first
    accounts = db.query(BankAccount).filter(
        BankAccount.company_id == company_id
    ).all()
    
    if not accounts:
        return {"status": "no_data", "message": "No bank accounts found."}
    
    account_ids = [a.id for a in accounts]
    transactions = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids)
    ).all()
    
    cheques = db.query(Cheque).filter(Cheque.company_id == company_id).all()
    
    # Compute current position
    pos_engine = CashPositionEngine()
    position = pos_engine.compute(
        bank_accounts=[
            {"id": a.id, "company_id": a.company_id, "bank_name": a.bank_name,
             "account_number": a.account_number, "account_type": a.account_type}
            for a in accounts
        ],
        transactions=[
            {"id": t.id, "bank_account_id": t.bank_account_id, "date": t.transaction_date,
             "amount": t.amount, "description": t.description, "reference": t.reference,
             "balance": t.balance_after}
            for t in transactions
        ],
        cheques=[
            {"id": c.id, "bank_account_id": c.bank_account_id, "cheque_number": c.cheque_number,
             "amount": c.amount, "payee_name": c.payee_name, "issue_date": c.issue_date,
             "status": c.status}
            for c in cheques
        ],
    )
    
    # Detect recurring patterns
    detector = RecurringDetector()
    patterns = detector.detect([
        {"id": t.id, "date": t.transaction_date, "amount": t.amount,
         "description": t.description, "reference": t.reference}
        for t in transactions
    ])
    
    # Convert patterns to forecast format
    forecast_patterns = [
        RecurringPattern(
            pattern_id=str(i),
            pattern_type=p.pattern_type,
            description=p.description,
            amount=p.amount,
            frequency=p.frequency,
            next_expected_date=p.next_expected_date,
            day_of_month=p.day_of_month,
            day_of_week=p.day_of_week,
            confidence=p.confidence,
            occurrences=p.occurrences,
        )
        for i, p in enumerate(patterns)
    ]
    
    # Generate forecast
    forecast_engine = CashForecastEngine()
    forecast = forecast_engine.forecast(
        current_balance=position.adjusted_position,
        patterns=forecast_patterns,
        days=days,
        company_id=company_id,
    )
    
    result = forecast_engine.to_dict(forecast)
    result["detected_patterns"] = [
        {
            "type": p.pattern_type,
            "description": p.description,
            "amount": p.amount,
            "frequency": p.frequency,
            "next_date": p.next_expected_date,
            "confidence": p.confidence,
            "occurrences": p.occurrences,
        }
        for p in patterns
    ]
    
    return result


@router.get("/anomalies/{company_id}")
async def get_anomalies(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scan for anomalies in recent transactions.
    
    Returns alerts for:
    - Duplicate payments
    - Weekend transactions
    - Amount spikes
    - New payees
    - Stale cheques
    - Fee anomalies
    """
    accounts = db.query(BankAccount).filter(
        BankAccount.company_id == company_id
    ).all()
    
    if not accounts:
        return {"alerts": [], "total": 0}
    
    account_ids = [a.id for a in accounts]
    
    # Current month transactions
    month_start = date.today().replace(day=1)
    current_txns = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids),
        BankTransaction.transaction_date >= month_start,
    ).all()
    
    # Historical transactions (for baseline)
    historical_txns = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(account_ids),
        BankTransaction.transaction_date < month_start,
    ).all()
    
    # Cheques
    cheques = db.query(Cheque).filter(Cheque.company_id == company_id).all()
    
    # Run anomaly detection
    detector = AnomalyDetector()
    alerts = detector.scan(
        transactions=[
            {"id": t.id, "date": t.transaction_date, "amount": t.amount,
             "description": t.description, "reference": t.reference,
             "fee_amount": t.fee_amount or 0}
            for t in current_txns
        ],
        cheques=[
            {"id": c.id, "cheque_number": c.cheque_number, "amount": c.amount,
             "payee_name": c.payee_name, "issue_date": c.issue_date, "status": c.status}
            for c in cheques
        ],
        historical_transactions=[
            {"id": t.id, "date": t.transaction_date, "amount": t.amount,
             "description": t.description, "reference": t.reference}
            for t in historical_txns
        ],
    )
    
    return {
        "alerts": [
            {
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "description_am": a.description_am,
                "transaction_ids": a.transaction_ids,
                "amount": a.amount,
                "date": a.transaction_date,
                "details": a.details,
            }
            for a in alerts
        ],
        "total": len(alerts),
        "by_severity": {
            "critical": sum(1 for a in alerts if a.severity == "critical"),
            "warning": sum(1 for a in alerts if a.severity == "warning"),
            "info": sum(1 for a in alerts if a.severity == "info"),
        },
    }


@router.get("/summary/{company_id}")
async def get_cash_summary(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick cash summary for dashboard widget.
    Lighter version of /position — returns only totals.
    """
    accounts = db.query(BankAccount).filter(
        BankAccount.company_id == company_id
    ).all()
    
    if not accounts:
        return {"status": "no_accounts", "adjusted_position": 0}
    
    account_ids = [a.id for a in accounts]
    
    # Get latest balance per account
    total_raw = 0.0
    for acct in accounts:
        latest = db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == acct.id
        ).order_by(BankTransaction.transaction_date.desc()).first()
        
        if latest and latest.balance_after:
            total_raw += latest.balance_after
    
    # Outstanding cheques
    outstanding = db.query(Cheque).filter(
        Cheque.company_id == company_id,
        Cheque.status.in_(["issued", "deposited", "clearing"]),
    ).all()
    
    outstanding_total = sum(c.amount for c in outstanding)
    stale_count = sum(1 for c in outstanding if (date.today() - c.issue_date).days > 90)
    
    adjusted = total_raw - outstanding_total
    
    return {
        "adjusted_position": round(adjusted, 2),
        "raw_balance": round(total_raw, 2),
        "outstanding_cheques": round(outstanding_total, 2),
        "outstanding_cheque_count": len(outstanding),
        "stale_cheque_count": stale_count,
        "account_count": len(accounts),
        "by_bank": {},  # Simplified
    }
