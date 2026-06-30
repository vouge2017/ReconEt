"""
Executive Dashboard API — ReconET

One-glance view for CFOs:
- Match rate trend
- Fee summary
- Outstanding cheques
- Exception counts
- Period status
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta

from app.database import get_db
from app.models import (
    BankTransaction, GLEntry, Match, Cheque, Period, 
    AuditTrail, BankAccount, User, PeriodStatus
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/{company_id}")
async def get_dashboard(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get executive dashboard data"""
    
    # Date ranges
    today = date.today()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # === Transaction Stats ===
    total_txns = db.query(func.count(BankTransaction.id)).join(BankAccount).filter(
        BankAccount.company_id == company_id
    ).scalar() or 0
    
    matched_txns = db.query(func.count(BankTransaction.id)).join(BankAccount).filter(
        BankAccount.company_id == company_id,
        BankTransaction.is_matched == True
    ).scalar() or 0
    
    unmatched_txns = total_txns - matched_txns
    match_rate = (matched_txns / total_txns * 100) if total_txns > 0 else 0
    
    # This month's transactions
    month_txns = db.query(func.count(BankTransaction.id)).join(BankAccount).filter(
        BankAccount.company_id == company_id,
        BankTransaction.transaction_date >= month_start
    ).scalar() or 0
    
    month_matched = db.query(func.count(BankTransaction.id)).join(BankAccount).filter(
        BankAccount.company_id == company_id,
        BankTransaction.transaction_date >= month_start,
        BankTransaction.is_matched == True
    ).scalar() or 0
    
    # === Fee Summary ===
    fee_result = db.query(
        func.sum(BankTransaction.fee_amount),
        func.sum(BankTransaction.bank_charge),
        func.sum(BankTransaction.gov_tax),
        func.count(BankTransaction.id).filter(BankTransaction.fee_amount > 0)
    ).join(BankAccount).filter(
        BankAccount.company_id == company_id
    ).first()
    
    total_fees = fee_result[0] or 0
    total_bank_charges = fee_result[1] or 0
    total_gov_tax = fee_result[2] or 0
    txns_with_fees = fee_result[3] or 0
    
    # This month's fees
    month_fee_result = db.query(
        func.sum(BankTransaction.fee_amount),
    ).join(BankAccount).filter(
        BankAccount.company_id == company_id,
        BankTransaction.transaction_date >= month_start
    ).first()
    month_fees = month_fee_result[0] or 0
    
    # === Cheque Stats ===
    outstanding_cheques = db.query(func.count(Cheque.id)).filter(
        Cheque.company_id == company_id,
        Cheque.status.in_(["issued", "deposited", "clearing"])
    ).scalar() or 0
    
    outstanding_amount = db.query(func.sum(Cheque.amount)).filter(
        Cheque.company_id == company_id,
        Cheque.status.in_(["issued", "deposited", "clearing"])
    ).scalar() or 0
    
    stale_cheques = db.query(func.count(Cheque.id)).filter(
        Cheque.company_id == company_id,
        Cheque.status.in_(["issued", "deposited", "clearing"]),
        Cheque.issue_date < today - timedelta(days=90)
    ).scalar() or 0
    
    stale_amount = db.query(func.sum(Cheque.amount)).filter(
        Cheque.company_id == company_id,
        Cheque.status.in_(["issued", "deposited", "clearing"]),
        Cheque.issue_date < today - timedelta(days=90)
    ).scalar() or 0
    
    # === Period Status ===
    current_period = db.query(Period).filter(
        Period.company_id == company_id,
        Period.period_month == today.month,
        Period.period_year == today.year,
    ).first()
    
    locked_periods = db.query(func.count(Period.id)).filter(
        Period.company_id == company_id,
        Period.status == PeriodStatus.LOCKED.value
    ).scalar() or 0
    
    # === Recent Activity ===
    recent_audits = db.query(AuditTrail).filter(
        AuditTrail.company_id == company_id
    ).order_by(AuditTrail.created_at.desc()).limit(10).all()
    
    recent_activity = [
        {
            "action": a.action,
            "entity_type": a.entity_type,
            "details": a.details,
            "created_at": str(a.created_at),
        }
        for a in recent_audits
    ]
    
    # === Amount Summary ===
    amount_result = db.query(
        func.sum(BankTransaction.amount).filter(BankTransaction.amount > 0),
        func.sum(BankTransaction.amount).filter(BankTransaction.amount < 0),
    ).join(BankAccount).filter(
        BankAccount.company_id == company_id
    ).first()
    
    total_credits = amount_result[0] or 0
    total_debits = abs(amount_result[1] or 0)
    
    return {
        "match_stats": {
            "total_transactions": total_txns,
            "matched": matched_txns,
            "unmatched": unmatched_txns,
            "match_rate": round(match_rate, 1),
            "this_month": {
                "transactions": month_txns,
                "matched": month_matched,
            }
        },
        "fee_summary": {
            "total_fees": round(total_fees, 2),
            "bank_charges": round(total_bank_charges, 2),
            "gov_tax": round(total_gov_tax, 2),
            "transactions_with_fees": txns_with_fees,
            "this_month_fees": round(month_fees, 2),
        },
        "cheques": {
            "outstanding_count": outstanding_cheques,
            "outstanding_amount": round(outstanding_amount, 2),
            "stale_count": stale_cheques,
            "stale_amount": round(stale_amount, 2),
        },
        "periods": {
            "current_period": f"{today.month}/{today.year}",
            "current_status": current_period.status if current_period else "open",
            "locked_count": locked_periods,
        },
        "amounts": {
            "total_credits": round(total_credits, 2),
            "total_debits": round(total_debits, 2),
            "net_movement": round(total_credits - total_debits, 2),
        },
        "recent_activity": recent_activity,
    }


@router.get("/{company_id}/match-trend")
async def get_match_trend(
    company_id: str,
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get match rate trend over time"""
    today = date.today()
    trend = []
    
    for i in range(months - 1, -1, -1):
        # Calculate month start/end
        month_date = today - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
        
        total = db.query(func.count(BankTransaction.id)).join(BankAccount).filter(
            BankAccount.company_id == company_id,
            BankTransaction.transaction_date >= month_start,
            BankTransaction.transaction_date <= month_end,
        ).scalar() or 0
        
        matched = db.query(func.count(BankTransaction.id)).join(BankAccount).filter(
            BankAccount.company_id == company_id,
            BankTransaction.transaction_date >= month_start,
            BankTransaction.transaction_date <= month_end,
            BankTransaction.is_matched == True,
        ).scalar() or 0
        
        rate = (matched / total * 100) if total > 0 else 0
        
        trend.append({
            "month": month_start.strftime("%b %Y"),
            "total": total,
            "matched": matched,
            "rate": round(rate, 1),
        })
    
    return {"trend": trend}
