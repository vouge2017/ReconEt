"""
Balance Verifier — Pre-upload gate for bank statements.

Before any matching occurs, verify that the statement balances:
    opening_balance + sum(credits) - sum(debits) = closing_balance

If this fails, reject the upload and flag for review.
This catches:
- PDF parsing errors (missing rows, wrong amounts)
- Truncated statements
- Corrupted data
- Partial uploads
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class Transaction:
    """Transaction for balance verification"""
    date: str
    description: str
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None  # Running balance from statement
    reference: str = ""


@dataclass
class VerificationResult:
    """Result of balance verification"""
    status: VerificationStatus
    opening_balance: float
    closing_balance: float
    calculated_closing: float
    total_credits: float
    total_debits: float
    transaction_count: int
    difference: float
    message: str
    details: Optional[dict] = None


class BalanceVerifier:
    """
    Verify bank statement balances before reconciliation.
    
    The contract:
        opening_balance + sum(credits) - sum(debits) = closing_balance
    
    Tolerance: 0.01 ETB (to handle floating point rounding)
    """
    
    TOLERANCE = 0.01  # ETB
    
    def verify(
        self,
        transactions: List[Transaction],
        opening_balance: Optional[float] = None,
        closing_balance: Optional[float] = None,
    ) -> VerificationResult:
        """
        Verify statement balances.
        
        Args:
            transactions: List of parsed transactions
            opening_balance: Statement opening balance (from PDF header)
            closing_balance: Statement closing balance (from PDF footer)
        
        Returns:
            VerificationResult with status and details
        """
        if not transactions:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                opening_balance=0,
                closing_balance=0,
                calculated_closing=0,
                total_credits=0,
                total_debits=0,
                transaction_count=0,
                difference=0,
                message="No transactions found in statement.",
                details={"error": "empty_statement"}
            )
        
        # Calculate totals from transactions
        total_credits = sum(t.credit for t in transactions)
        total_debits = sum(t.debit for t in transactions)
        
        # Try to get opening/closing from statement data
        # If not provided, try to derive from first/last transaction balances
        if opening_balance is None:
            # Opening balance = first transaction's running balance - first transaction's net
            first = transactions[0]
            if first.balance is not None:
                # If first txn is debit: opening = balance + debit
                # If first txn is credit: opening = balance - credit
                opening_balance = first.balance + first.debit - first.credit
            else:
                opening_balance = 0.0
        
        if closing_balance is None:
            # Closing balance = last transaction's running balance
            last = transactions[-1]
            if last.balance is not None:
                closing_balance = last.balance
            else:
                closing_balance = opening_balance + total_credits - total_debits
        
        # Calculate expected closing balance
        calculated_closing = opening_balance + total_credits - total_debits
        
        # Check tolerance
        difference = abs(calculated_closing - closing_balance)
        
        if difference <= self.TOLERANCE:
            status = VerificationStatus.PASSED
            message = (
                f"Balance verified: Opening {opening_balance:,.2f} + "
                f"Credits {total_credits:,.2f} - Debits {total_debits:,.2f} = "
                f"{calculated_closing:,.2f} (statement: {closing_balance:,.2f})"
            )
        elif difference <= 1.0:
            # Small difference — might be rounding
            status = VerificationStatus.WARNING
            message = (
                f"⚠️ Small balance discrepancy ({difference:,.2f} ETB). "
                f"Opening {opening_balance:,.2f} + Credits {total_credits:,.2f} - "
                f"Debits {total_debits:,.2f} = {calculated_closing:,.2f}, "
                f"but statement shows {closing_balance:,.2f}. "
                f"Proceeding with caution."
            )
        else:
            status = VerificationStatus.FAILED
            message = (
                f"❌ Statement balance does not match. "
                f"Opening {opening_balance:,.2f} + Credits {total_credits:,.2f} - "
                f"Debits {total_debits:,.2f} = {calculated_closing:,.2f}, "
                f"but statement shows {closing_balance:,.2f}. "
                f"Difference: {difference:,.2f} ETB. "
                f"Possible extraction error. Please review or contact support."
            )
        
        return VerificationResult(
            status=status,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            calculated_closing=calculated_closing,
            total_credits=total_credits,
            total_debits=total_debits,
            transaction_count=len(transactions),
            difference=difference,
            message=message,
            details={
                "tolerance": self.TOLERANCE,
                "first_transaction_date": transactions[0].date if transactions else None,
                "last_transaction_date": transactions[-1].date if transactions else None,
                "transactions_with_balance": sum(1 for t in transactions if t.balance is not None),
            }
        )
    
    def verify_running_balances(
        self, transactions: List[Transaction], opening_balance: float
    ) -> List[dict]:
        """
        Verify each transaction's running balance.
        
        Returns list of discrepancies (empty if all match).
        """
        discrepancies = []
        expected_balance = opening_balance
        
        for i, txn in enumerate(transactions):
            expected_balance = expected_balance + txn.credit - txn.debit
            
            if txn.balance is not None:
                diff = abs(expected_balance - txn.balance)
                if diff > self.TOLERANCE:
                    discrepancies.append({
                        "index": i,
                        "date": txn.date,
                        "description": txn.description[:50],
                        "expected_balance": expected_balance,
                        "actual_balance": txn.balance,
                        "difference": diff,
                    })
        
        return discrepancies
