"""
Cheque Lifecycle Engine — ReconET

Tracks cheques from issuance to clearing (or staleness).
Auto-matches clearing cheques to bank transactions.

Lifecycle:
  ISSUED → DEPOSITED → CLEARING → CLEARED
                                         ↘ BOUNCED
  ISSUED → (90+ days) → STALE → CANCELLED

Ethiopian context:
- Cheques are still heavily used (CBE processes ~50K/day)
- Clearing takes 3-7 business days
- Stale threshold: 90 days (Ethiopian banking practice)
- Stale cheques must be cancelled and re-issued
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date, timedelta
from enum import Enum


class ChequeStatus(str, Enum):
    ISSUED = "issued"
    DEPOSITED = "deposited"
    CLEARING = "clearing"
    CLEARED = "cleared"
    BOUNCED = "bounced"
    STALE = "stale"
    CANCELLED = "cancelled"


@dataclass
class ChequeMatch:
    """A matched cheque clearing"""
    cheque_id: str
    cheque_number: str
    bank_transaction_id: str
    amount: float
    issue_date: str
    clear_date: str
    days_to_clear: int
    payee: str
    confidence: int


@dataclass
class ChequeSummary:
    """Summary of cheque status"""
    total_issued: int = 0
    total_cleared: int = 0
    total_outstanding: int = 0
    total_stale: int = 0
    total_bounced: int = 0
    total_cancelled: int = 0
    # Amounts
    outstanding_amount: float = 0.0
    stale_amount: float = 0.0
    cleared_amount: float = 0.0
    # Alerts
    stale_cheques: List[Dict] = field(default_factory=list)
    overdue_cheques: List[Dict] = field(default_factory=list)


class ChequeLifecycleEngine:
    """
    Track cheque lifecycle and auto-match clearing.
    
    Usage:
        engine = ChequeLifecycleEngine()
        matches = engine.match_clearing(cheques, transactions)
        summary = engine.get_summary(cheques)
        stale = engine.detect_stale(cheques)
    """
    
    STALE_DAYS = 90
    MAX_CLEAR_DAYS = 14  # Cheques should clear within 14 days
    
    def match_clearing(
        self, cheques: List[Dict], bank_transactions: List[Dict]
    ) -> List[ChequeMatch]:
        """
        Match issued cheques to bank transactions when they clear.
        
        Matching criteria:
        1. Amount matches (within tolerance)
        2. Cheque number found in transaction description
        3. Transaction date > cheque issue date
        """
        matches = []
        used_txn_ids = set()
        
        # Find outstanding cheques
        outstanding = [
            c for c in cheques
            if c.get("status") in ("issued", "deposited", "clearing")
        ]
        
        # Find CHQ/Cheque transactions in bank statement
        chq_transactions = [
            t for t in bank_transactions
            if self._is_cheque_transaction(t) and t.get("id") not in used_txn_ids
        ]
        
        for cheque in outstanding:
            chq_number = str(cheque.get("cheque_number", "")).strip()
            chq_amount = abs(float(cheque.get("amount", 0)))
            issue_date = cheque.get("issue_date")
            
            if isinstance(issue_date, str):
                try:
                    issue_date = date.fromisoformat(issue_date)
                except ValueError:
                    continue
            
            best_match = None
            best_score = 0
            
            for txn in chq_transactions:
                if txn.get("id") in used_txn_ids:
                    continue
                
                txn_amount = abs(float(txn.get("amount", 0)))
                txn_desc = (txn.get("description") or txn.get("narrative") or "").upper()
                txn_ref = (txn.get("reference") or "").upper()
                txn_date = txn.get("date")
                
                if isinstance(txn_date, str):
                    try:
                        txn_date = date.fromisoformat(txn_date)
                    except ValueError:
                        continue
                
                if not isinstance(txn_date, date):
                    continue
                
                # Must be after issue date
                if issue_date and txn_date < issue_date:
                    continue
                
                score = 0
                
                # Amount match (weight: 50)
                if abs(chq_amount - txn_amount) < 1.0:
                    score += 50
                elif abs(chq_amount - txn_amount) < chq_amount * 0.01:
                    score += 30
                
                # Cheque number in description/reference (weight: 40)
                if chq_number and (chq_number in txn_desc or chq_number in txn_ref):
                    score += 40
                elif chq_number:
                    # Partial match (last 4 digits)
                    if chq_number[-4:] in txn_desc or chq_number[-4:] in txn_ref:
                        score += 20
                
                # CHQ/Cheque keyword (weight: 10)
                if any(kw in txn_desc or kw in txn_ref for kw in ["CHQ", "CHEQUE", "CHECK"]):
                    score += 10
                
                if score > best_score and score >= 50:
                    best_score = score
                    best_match = txn
            
            if best_match:
                txn_date = best_match.get("date")
                if isinstance(txn_date, str):
                    txn_date = date.fromisoformat(txn_date)
                
                days_to_clear = (txn_date - issue_date).days if issue_date else 0
                
                matches.append(ChequeMatch(
                    cheque_id=cheque.get("id", ""),
                    cheque_number=chq_number,
                    bank_transaction_id=best_match.get("id", ""),
                    amount=chq_amount,
                    issue_date=str(issue_date) if issue_date else "",
                    clear_date=str(txn_date),
                    days_to_clear=days_to_clear,
                    payee=cheque.get("payee_name", ""),
                    confidence=best_score,
                ))
                
                used_txn_ids.add(best_match["id"])
        
        return matches
    
    def detect_stale(self, cheques: List[Dict]) -> List[Dict]:
        """Find stale cheques (>90 days outstanding)"""
        today = date.today()
        stale = []
        
        for chq in cheques:
            if chq.get("status") not in ("issued", "deposited", "clearing"):
                continue
            
            issue_date = chq.get("issue_date")
            if isinstance(issue_date, str):
                try:
                    issue_date = date.fromisoformat(issue_date)
                except ValueError:
                    continue
            if not isinstance(issue_date, date):
                continue
            
            days_outstanding = (today - issue_date).days
            if days_outstanding > self.STALE_DAYS:
                stale.append({
                    "id": chq.get("id"),
                    "cheque_number": chq.get("cheque_number"),
                    "amount": chq.get("amount", 0),
                    "payee": chq.get("payee_name", ""),
                    "issue_date": str(issue_date),
                    "days_outstanding": days_outstanding,
                    "status": "stale",
                    "action": "Cancel and re-issue, or contact payee",
                    "action_am": "ይሰርዙ እና እንደገና ይስጡ፣ ወይም ተቀባዩን ያግኙ",
                })
        
        return stale
    
    def detect_overdue(self, cheques: List[Dict]) -> List[Dict]:
        """Find cheques that should have cleared but haven't"""
        today = date.today()
        overdue = []
        
        for chq in cheques:
            if chq.get("status") not in ("issued", "deposited"):
                continue
            
            expected_clear = chq.get("expected_clear_date")
            if isinstance(expected_clear, str):
                try:
                    expected_clear = date.fromisoformat(expected_clear)
                except ValueError:
                    continue
            
            if not isinstance(expected_clear, date):
                # Estimate from issue date + max clear days
                issue_date = chq.get("issue_date")
                if isinstance(issue_date, str):
                    try:
                        issue_date = date.fromisoformat(issue_date)
                    except ValueError:
                        continue
                if isinstance(issue_date, date):
                    expected_clear = issue_date + timedelta(days=self.MAX_CLEAR_DAYS)
                else:
                    continue
            
            if expected_clear < today:
                days_overdue = (today - expected_clear).days
                overdue.append({
                    "id": chq.get("id"),
                    "cheque_number": chq.get("cheque_number"),
                    "amount": chq.get("amount", 0),
                    "payee": chq.get("payee_name", ""),
                    "expected_clear_date": str(expected_clear),
                    "days_overdue": days_overdue,
                    "action": "Follow up with bank or payee",
                    "action_am": "ከባንክ ወይም ከተቀባይ ጋር ይከታተሉ",
                })
        
        return overdue
    
    def get_summary(self, cheques: List[Dict]) -> ChequeSummary:
        """Get cheque status summary"""
        summary = ChequeSummary()
        today = date.today()
        
        for chq in cheques:
            status = chq.get("status", "issued")
            amount = float(chq.get("amount", 0))
            
            if status == "issued":
                summary.total_issued += 1
                summary.total_outstanding += 1
                summary.outstanding_amount += amount
            elif status in ("deposited", "clearing"):
                summary.total_outstanding += 1
                summary.outstanding_amount += amount
            elif status == "cleared":
                summary.total_cleared += 1
                summary.cleared_amount += amount
            elif status == "bounced":
                summary.total_bounced += 1
            elif status == "stale":
                summary.total_stale += 1
                summary.stale_amount += amount
            elif status == "cancelled":
                summary.total_cancelled += 1
        
        # Detect stale
        summary.stale_cheques = self.detect_stale(cheques)
        summary.total_stale = len(summary.stale_cheques)
        summary.stale_amount = sum(c["amount"] for c in summary.stale_cheques)
        
        # Detect overdue
        summary.overdue_cheques = self.detect_overdue(cheques)
        
        return summary
    
    def _is_cheque_transaction(self, txn: Dict) -> bool:
        """Check if a bank transaction is a cheque clearing"""
        desc = (txn.get("description") or txn.get("narrative") or "").upper()
        ref = (txn.get("reference") or "").upper()
        
        return any(kw in desc or kw in ref for kw in ["CHQ", "CHEQUE", "CHECK", "CD"])
    
    def to_match_dict(self, match: ChequeMatch) -> Dict:
        return {
            "cheque_id": match.cheque_id,
            "cheque_number": match.cheque_number,
            "bank_transaction_id": match.bank_transaction_id,
            "amount": match.amount,
            "issue_date": match.issue_date,
            "clear_date": match.clear_date,
            "days_to_clear": match.days_to_clear,
            "payee": match.payee,
            "confidence": match.confidence,
        }
    
    def to_summary_dict(self, summary: ChequeSummary) -> Dict:
        return {
            "counts": {
                "total_issued": summary.total_issued,
                "total_cleared": summary.total_cleared,
                "total_outstanding": summary.total_outstanding,
                "total_stale": summary.total_stale,
                "total_bounced": summary.total_bounced,
                "total_cancelled": summary.total_cancelled,
            },
            "amounts": {
                "outstanding": round(summary.outstanding_amount, 2),
                "stale": round(summary.stale_amount, 2),
                "cleared": round(summary.cleared_amount, 2),
            },
            "stale_cheques": summary.stale_cheques,
            "overdue_cheques": summary.overdue_cheques,
        }
