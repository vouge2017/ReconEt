"""
Period Lock API — ReconET

Prevents backdating of reconciliation entries.
Only CFO/Admin can lock/unlock periods.

Ethiopian fiscal year: Jul 7 - Jul 6
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models import Period, PeriodStatus, User, UserRole, AuditTrail
from app.api.auth import get_current_user, require_role, log_audit

router = APIRouter(prefix="/api/periods", tags=["periods"])


class LockRequest(BaseModel):
    period_month: int
    period_year: int


class PeriodResponse(BaseModel):
    id: str
    period_month: int
    period_year: int
    status: str
    locked_by: Optional[str]
    locked_at: Optional[str]


@router.get("/{company_id}")
async def list_periods(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all periods for a company"""
    periods = db.query(Period).filter(
        Period.company_id == company_id
    ).order_by(Period.period_year.desc(), Period.period_month.desc()).all()
    
    return [
        {
            "id": p.id,
            "period_month": p.period_month,
            "period_year": p.period_year,
            "status": p.status,
            "locked_by": p.locked_by,
            "locked_at": str(p.locked_at) if p.locked_at else None,
        }
        for p in periods
    ]


@router.post("/{company_id}/lock")
async def lock_period(
    company_id: str,
    req: LockRequest,
    current_user: User = Depends(require_role(UserRole.CFO.value, UserRole.MANAGER.value)),
    db: Session = Depends(get_db)
):
    """Lock a period (CFO/Manager only)"""
    # Validate month/year
    if not (1 <= req.period_month <= 12):
        raise HTTPException(status_code=400, detail="Month must be 1-12")
    if not (2020 <= req.period_year <= 2030):
        raise HTTPException(status_code=400, detail="Year must be 2020-2030")
    
    # Find or create period
    period = db.query(Period).filter(
        Period.company_id == company_id,
        Period.period_month == req.period_month,
        Period.period_year == req.period_year,
    ).first()
    
    if not period:
        period = Period(
            company_id=company_id,
            period_month=req.period_month,
            period_year=req.period_year,
        )
        db.add(period)
    
    if period.status == PeriodStatus.LOCKED.value:
        raise HTTPException(status_code=409, detail="Period is already locked")
    
    period.status = PeriodStatus.LOCKED.value
    period.locked_by = current_user.id
    period.locked_at = datetime.utcnow()
    db.commit()
    
    # Audit
    log_audit(db, current_user.id, company_id, "lock_period", "period", period.id,
              {"month": req.period_month, "year": req.period_year})
    
    return {
        "status": "locked",
        "period": f"{req.period_month}/{req.period_year}",
        "locked_by": current_user.full_name,
    }


@router.post("/{company_id}/unlock")
async def unlock_period(
    company_id: str,
    req: LockRequest,
    current_user: User = Depends(require_role(UserRole.CFO.value)),
    db: Session = Depends(get_db)
):
    """Unlock a period (CFO only)"""
    period = db.query(Period).filter(
        Period.company_id == company_id,
        Period.period_month == req.period_month,
        Period.period_year == req.period_year,
    ).first()
    
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.status != PeriodStatus.LOCKED.value:
        raise HTTPException(status_code=409, detail="Period is not locked")
    
    period.status = PeriodStatus.OPEN.value
    period.locked_by = None
    period.locked_at = None
    db.commit()
    
    log_audit(db, current_user.id, company_id, "unlock_period", "period", period.id,
              {"month": req.period_month, "year": req.period_year})
    
    return {"status": "unlocked", "period": f"{req.period_month}/{req.period_year}"}


@router.get("/{company_id}/check/{year}/{month}")
async def check_period(
    company_id: str,
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if a period is locked"""
    period = db.query(Period).filter(
        Period.company_id == company_id,
        Period.period_month == month,
        Period.period_year == year,
    ).first()
    
    is_locked = period.status == PeriodStatus.LOCKED.value if period else False
    
    return {
        "period": f"{month}/{year}",
        "is_locked": is_locked,
        "status": period.status if period else "open",
    }
