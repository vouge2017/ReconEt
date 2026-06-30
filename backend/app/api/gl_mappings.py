"""
GL Account Mappings API — ReconET

Configure fee_type → GL account mappings per company.
Auto-suggests journal entries for matched transactions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models import User, UserRole
from app.api.auth import get_current_user, require_role
from app.engine.gl_mapper import GLAccountMapper

router = APIRouter(prefix="/api/gl-mappings", tags=["gl_mappings"])


class MappingUpdate(BaseModel):
    fee_type: str
    gl_account_code: str
    gl_account_name: str
    description: str = ""


class JournalEntryRequest(BaseModel):
    amount: float
    description: str
    gross_amount: Optional[float] = None
    bank_charge: float = 0
    gov_tax: float = 0
    wht: float = 0
    expense_account: str = "5100"
    expense_name: str = "Operating Expense"


@router.get("/")
async def get_mappings(current_user: User = Depends(get_current_user)):
    """Get all GL account mappings"""
    mapper = GLAccountMapper()
    return {"mappings": mapper.get_all_mappings()}


@router.put("/")
async def update_mapping(
    req: MappingUpdate,
    current_user: User = Depends(require_role(UserRole.CFO.value, UserRole.MANAGER.value)),
):
    """Update a GL account mapping (CFO/Manager only)"""
    mapper = GLAccountMapper()
    mapper.update_mapping(
        fee_type=req.fee_type,
        gl_code=req.gl_account_code,
        gl_name=req.gl_account_name,
        description=req.description,
    )
    return {"status": "updated", "fee_type": req.fee_type}


@router.post("/suggest-journal")
async def suggest_journal_entries(
    req: JournalEntryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate suggested journal entries for a transaction with fees.
    
    Returns debit/credit entries for:
    - Expense (vendor payment)
    - Bank charges
    - Government tax (VAT)
    - Withholding tax
    - Cash at bank
    """
    mapper = GLAccountMapper()
    
    transaction = {
        "amount": req.amount,
        "description": req.description,
        "gross_amount": req.gross_amount or req.amount,
        "bank_charge": req.bank_charge,
        "gov_tax": req.gov_tax,
        "wht": req.wht,
        "expense_account": req.expense_account,
        "expense_name": req.expense_name,
    }
    
    entries = mapper.map_transaction(transaction)
    
    # Verify balance
    total_debit = sum(e["debit"] for e in entries)
    total_credit = sum(e["credit"] for e in entries)
    
    return {
        "journal_entries": entries,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "is_balanced": abs(total_debit - total_credit) < 0.01,
    }
