"""
Cheque Tracking API

GET  /api/cheques/outstanding — List outstanding cheques
GET  /api/cheques/stale — List stale cheques
POST /api/cheques — Register a new cheque
PUT  /api/cheques/{id}/status — Update cheque status
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import date, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models import Cheque, BankAccount

router = APIRouter(prefix="/api/cheques", tags=["cheques"])


class ChequeCreate(BaseModel):
    bank_account_id: str
    cheque_number: str
    cheque_type: str  # "issued" or "received"
    amount: float
    payee_name: Optional[str] = None
    payer_name: Optional[str] = None
    issue_date: date
    expected_clear_date: Optional[date] = None
    stale_days: int = 90


class ChequeUpdate(BaseModel):
    status: str
    actual_clear_date: Optional[date] = None
    notes: Optional[str] = None


@router.get("/outstanding/{company_id}")
async def get_outstanding_cheques(company_id: str, db: Session = Depends(get_db)):
    """List all cheques that haven't cleared yet"""
    
    cheques = db.query(Cheque).join(BankAccount).filter(
        and_(
            BankAccount.company_id == company_id,
            Cheque.status.in_(["issued", "deposited", "clearing"])
        )
    ).all()
    
    total_outstanding = sum(c.amount for c in cheques)
    
    return {
        "count": len(cheques),
        "total_amount": total_outstanding,
        "cheques": [
            {
                "id": c.id,
                "cheque_number": c.cheque_number,
                "cheque_type": c.cheque_type,
                "amount": c.amount,
                "payee_name": c.payee_name,
                "payer_name": c.payer_name,
                "issue_date": str(c.issue_date),
                "expected_clear_date": str(c.expected_clear_date) if c.expected_clear_date else None,
                "days_outstanding": (date.today() - c.issue_date).days,
                "status": c.status
            }
            for c in cheques
        ]
    }


@router.get("/stale/{company_id}")
async def get_stale_cheques(company_id: str, db: Session = Depends(get_db)):
    """List cheques that have exceeded the stale threshold"""
    
    cheques = db.query(Cheque).join(BankAccount).filter(
        and_(
            BankAccount.company_id == company_id,
            Cheque.status.in_(["issued", "deposited", "clearing"]),
            Cheque.issue_date < date.today() - timedelta(days=90)  # Default 90 days
        )
    ).all()
    
    total_stale = sum(c.amount for c in cheques)
    
    return {
        "count": len(cheques),
        "total_amount": total_stale,
        "warning": f"{len(cheques)} cheque(s) outstanding for more than 90 days",
        "cheques": [
            {
                "id": c.id,
                "cheque_number": c.cheque_number,
                "amount": c.amount,
                "payee_name": c.payee_name,
                "issue_date": str(c.issue_date),
                "days_outstanding": (date.today() - c.issue_date).days,
                "status": c.status
            }
            for c in cheques
        ]
    }


@router.post("/")
async def create_cheque(cheque: ChequeCreate, db: Session = Depends(get_db)):
    """Register a new cheque"""
    
    # Verify bank account exists
    account = db.query(BankAccount).filter(BankAccount.id == cheque.bank_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    
    db_cheque = Cheque(
        bank_account_id=cheque.bank_account_id,
        company_id=account.company_id,
        cheque_number=cheque.cheque_number,
        cheque_type=cheque.cheque_type,
        amount=cheque.amount,
        payee_name=cheque.payee_name,
        payer_name=cheque.payer_name,
        issue_date=cheque.issue_date,
        expected_clear_date=cheque.expected_clear_date,
        stale_days=cheque.stale_days,
        status="issued"
    )
    
    db.add(db_cheque)
    db.commit()
    db.refresh(db_cheque)
    
    return {
        "id": db_cheque.id,
        "message": f"Cheque #{cheque.cheque_number} registered",
        "status": "issued"
    }


@router.put("/{cheque_id}/status")
async def update_cheque_status(
    cheque_id: str, 
    update: ChequeUpdate, 
    db: Session = Depends(get_db)
):
    """Update cheque status (cleared, bounced, stale, cancelled)"""
    
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(status_code=404, detail="Cheque not found")
    
    cheque.status = update.status
    if update.actual_clear_date:
        cheque.actual_clear_date = update.actual_clear_date
    if update.notes:
        cheque.notes = update.notes
    
    db.commit()
    
    return {
        "id": cheque.id,
        "cheque_number": cheque.cheque_number,
        "status": cheque.status,
        "message": f"Cheque #{cheque.cheque_number} status updated to {update.status}"
    }
