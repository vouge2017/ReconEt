"""
Matching Engine with Fee Extraction Integration

This is the core: fee-aware matching that returns explanations.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class Transaction:
    """Normalized transaction from bank or GL"""
    id: str
    date: date
    amount: float
    reference: Optional[str] = None
    description: Optional[str] = None
    balance_after: Optional[float] = None
    currency: str = "ETB"
    bank_name: Optional[str] = None
    # Fee fields
    fee_amount: float = 0.0
    bank_charge: float = 0.0
    gov_tax: float = 0.0
    gross_amount: Optional[float] = None
    net_amount: Optional[float] = None


@dataclass
class MatchResult:
    """A match result with fee breakdown"""
    match_type: str
    confidence: int
    explanation: str
    bank_transaction_ids: List[str]
    gl_entry_ids: Optional[List[str]] = None
    status: str = "pending"
    # Fee breakdown
    fee_breakdown: Optional[Dict] = None
    # Matching details
    amount_strategy: Optional[str] = None  # "net", "gross", "split"


class MatchingEngine:
    """
    Fee-aware matching engine.
    
    Strategies:
    1. NET MATCH: Bank net_amount (fees included) → GL lump entry
    2. GROSS MATCH: Bank gross_amount → GL vendor entry
    3. SPLIT MATCH: Bank gross → GL vendor + Bank fees → GL bank charges
    """

    def __init__(self, date_tolerance_days: int = 3, amount_tolerance: float = 1.0):
        self.date_tolerance = date_tolerance_days
        self.amount_tolerance = amount_tolerance

    def run(
        self,
        bank_transactions: List[Transaction],
        gl_entries: List[Transaction],
    ) -> List[MatchResult]:
        """Run all match types, return sorted by confidence"""
        
        matches = []
        matched_bank_ids = set()
        matched_gl_ids = set()

        # Phase 1: Exact matches (highest confidence)
        for bt in bank_transactions:
            if bt.id in matched_bank_ids:
                continue
            
            best_match = self._find_best_match(bt, gl_entries, matched_gl_ids)
            if best_match:
                matches.append(best_match)
                matched_bank_ids.add(bt.id)
                if best_match.gl_entry_ids:
                    matched_gl_ids.update(best_match.gl_entry_ids)

        # Phase 2: Date-shifted matches
        remaining_bank = [t for t in bank_transactions if t.id not in matched_bank_ids]
        remaining_gl = [t for t in gl_entries if t.id not in matched_gl_ids]
        
        for bt in remaining_bank:
            best_match = self._find_date_shifted_match(bt, remaining_gl, matched_gl_ids)
            if best_match:
                matches.append(best_match)
                matched_bank_ids.add(bt.id)
                if best_match.gl_entry_ids:
                    matched_gl_ids.update(best_match.gl_entry_ids)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        # Auto-post high confidence
        for m in matches:
            if m.confidence >= 85:
                m.status = "auto_posted"

        return matches

    def _find_best_match(
        self, bt: Transaction, gl_entries: List[Transaction], matched_gl_ids: set
    ) -> Optional[MatchResult]:
        """Find best match using all strategies"""
        
        candidates = []

        for gl in gl_entries:
            if gl.id in matched_gl_ids:
                continue

            # Strategy 1: NET MATCH (most common - fees included in amount)
            net_result = self._try_net_match(bt, gl)
            if net_result:
                candidates.append(net_result)
                continue

            # Strategy 2: GROSS MATCH (GL records gross, fees separate)
            gross_result = self._try_gross_match(bt, gl)
            if gross_result:
                candidates.append(gross_result)
                continue

            # Strategy 3: SPLIT MATCH (GL has separate fee entries)
            split_result = self._try_split_match(bt, gl, gl_entries, matched_gl_ids)
            if split_result:
                candidates.append(split_result)
                continue

        if candidates:
            return max(candidates, key=lambda c: c.confidence)
        return None

    def _try_net_match(self, bt: Transaction, gl: Transaction) -> Optional[MatchResult]:
        """
        NET MATCH: Bank net amount (fees included) → GL lump entry
        
        Bank: TRANSFER TO ABC FEE 25 TAX 15 | Debit: 100,040
        GL:   Vendor ABC | Debit: 100,040
        → Match because net amounts equal
        """
        bt_net = abs(bt.net_amount if bt.net_amount is not None else bt.amount)
        gl_amount = abs(gl.amount)
        
        if abs(bt_net - gl_amount) > self.amount_tolerance:
            return None
        
        if bt.date != gl.date:
            return None

        # Build explanation
        parts = [f"net amount ETB {bt_net:,.2f} matches GL"]
        parts.append(f"date same day ({bt.date})")
        
        if bt.fee_amount > 0:
            parts.append(f"fees of ETB {bt.fee_amount:,.2f} included in amount")
        
        ref_match = self._fuzzy_reference(bt.reference, gl.reference)
        if ref_match:
            parts.append(f"reference '{bt.reference}' found")
        
        confidence = 92 if bt.fee_amount > 0 else 95
        if not ref_match:
            confidence -= 5

        explanation = "Matched because: " + " · ".join(parts)

        return MatchResult(
            match_type="exact_1to1" if bt.fee_amount == 0 else "fee_net_match",
            confidence=confidence,
            explanation=explanation,
            bank_transaction_ids=[bt.id],
            gl_entry_ids=[gl.id],
            fee_breakdown={
                "strategy": "net",
                "gross_amount": bt.gross_amount or bt.amount,
                "bank_charge": bt.bank_charge,
                "gov_tax": bt.gov_tax,
                "total_fees": bt.fee_amount,
                "net_amount": bt_net
            } if bt.fee_amount > 0 else None,
            amount_strategy="net"
        )

    def _try_gross_match(self, bt: Transaction, gl: Transaction) -> Optional[MatchResult]:
        """
        GROSS MATCH: Bank gross → GL vendor entry
        
        Bank: TRANSFER TO ABC FEE 25 TAX 15 | Debit: 100,040
        GL:   Vendor ABC | Debit: 100,000 (fees recorded separately)
        → Match because gross amounts equal
        """
        bt_gross = abs(bt.gross_amount if bt.gross_amount is not None else bt.amount)
        gl_amount = abs(gl.amount)
        
        if abs(bt_gross - gl_amount) > self.amount_tolerance:
            return None
        
        if bt.date != gl.date:
            return None
        
        if bt.fee_amount == 0:
            return None  # No fees, this is just a regular match

        explanation = (
            f"Matched because: gross amount ETB {bt_gross:,.2f} matches GL · "
            f"date same day ({bt.date}) · "
            f"fees ETB {bt.fee_amount:,.2f} (charge: {bt.bank_charge:,.2f}, tax: {bt.gov_tax:,.2f}) "
            f"recorded separately"
        )

        return MatchResult(
            match_type="fee_gross_match",
            confidence=95,
            explanation=explanation,
            bank_transaction_ids=[bt.id],
            gl_entry_ids=[gl.id],
            fee_breakdown={
                "strategy": "gross",
                "gross_amount": bt_gross,
                "bank_charge": bt.bank_charge,
                "gov_tax": bt.gov_tax,
                "total_fees": bt.fee_amount,
                "net_amount": bt_gross + bt.fee_amount
            },
            amount_strategy="gross"
        )

    def _try_split_match(
        self, bt: Transaction, gl: Transaction, 
        all_gl: List[Transaction], matched_gl_ids: set
    ) -> Optional[MatchResult]:
        """
        SPLIT MATCH: Bank gross → GL vendor + Bank fees → GL bank charges
        
        Bank: TRANSFER TO ABC FEE 25 TAX 15 | Debit: 100,040
        GL 1: Vendor ABC | Debit: 100,000
        GL 2: Bank Charges (6500) | Debit: 40
        → Match because gross + fees = total
        """
        if bt.fee_amount == 0:
            return None
        
        bt_gross = abs(bt.gross_amount if bt.gross_amount is not None else bt.amount - bt.fee_amount)
        gl_amount = abs(gl.amount)
        
        # Check if this GL entry matches gross amount
        if abs(bt_gross - gl_amount) > self.amount_tolerance:
            return None
        
        # Find fee GL entry (Bank Charges account, usually 6500)
        fee_gl = None
        for other_gl in all_gl:
            if other_gl.id in matched_gl_ids or other_gl.id == gl.id:
                continue
            # Look for Bank Charges account or fee-related description
            if (hasattr(other_gl, 'account_code') and 
                ('6500' in str(other_gl.account_code) or 
                 'bank charge' in str(other_gl.description or '').lower() or
                 'fee' in str(other_gl.description or '').lower())):
                if abs(abs(other_gl.amount) - bt.fee_amount) <= self.amount_tolerance:
                    fee_gl = other_gl
                    break
        
        if not fee_gl:
            return None  # Can't complete split match

        explanation = (
            f"Matched because: gross amount ETB {bt_gross:,.2f} matches vendor GL · "
            f"fees ETB {bt.fee_amount:,.2f} (charge: {bt.bank_charge:,.2f}, tax: {bt.gov_tax:,.2f}) "
            f"match bank charges GL · "
            f"total ETB {bt_gross + bt.fee_amount:,.2f} reconciled"
        )

        return MatchResult(
            match_type="fee_split_match",
            confidence=97,
            explanation=explanation,
            bank_transaction_ids=[bt.id],
            gl_entry_ids=[gl.id, fee_gl.id],
            fee_breakdown={
                "strategy": "split",
                "gross_amount": bt_gross,
                "bank_charge": bt.bank_charge,
                "gov_tax": bt.gov_tax,
                "total_fees": bt.fee_amount,
                "net_amount": bt_gross + bt.fee_amount,
                "vendor_gl_id": gl.id,
                "fee_gl_id": fee_gl.id
            },
            amount_strategy="split"
        )

    def _find_date_shifted_match(
        self, bt: Transaction, gl_entries: List[Transaction], matched_gl_ids: set
    ) -> Optional[MatchResult]:
        """Same amount, date within tolerance (bank processing lag)"""
        
        for gl in gl_entries:
            if gl.id in matched_gl_ids:
                continue
            
            bt_amount = abs(bt.net_amount if bt.net_amount is not None else bt.amount)
            gl_amount = abs(gl.amount)
            
            if abs(bt_amount - gl_amount) > self.amount_tolerance:
                continue
            
            day_diff = abs((bt.date - gl.date).days)
            if day_diff == 0 or day_diff > self.date_tolerance:
                continue
            
            confidence = 82 - (day_diff * 3)
            
            fee_note = ""
            if bt.fee_amount > 0:
                fee_note = f" · fees ETB {bt.fee_amount:,.2f} included"
            
            explanation = (
                f"Matched because: amount ETB {bt_amount:,.2f} · "
                f"date {day_diff} day(s) after GL entry (bank processing lag){fee_note}"
            )
            
            return MatchResult(
                match_type="date_shifted",
                confidence=max(confidence, 60),
                explanation=explanation,
                bank_transaction_ids=[bt.id],
                gl_entry_ids=[gl.id],
                fee_breakdown={
                    "strategy": "net",
                    "total_fees": bt.fee_amount
                } if bt.fee_amount > 0 else None,
                amount_strategy="net"
            )
        
        return None

    def _fuzzy_reference(self, ref1: Optional[str], ref2: Optional[str]) -> bool:
        """Check if references match (fuzzy)"""
        if not ref1 or not ref2:
            return False
        ref1 = ref1.upper().strip()
        ref2 = ref2.upper().strip()
        return ref1 in ref2 or ref2 in ref1
