"""
Exception Reporter — ReconET

Categorizes unmatched transactions and generates exception reports.
The goal: when something doesn't match, tell the accountant WHY and WHAT TO DO.

Categories:
1. Amount mismatch — fees not extracted?
2. Date mismatch — >3 day lag
3. Missing GL entry — bank has no matching GL
4. Missing bank transaction — GL has no matching bank
5. Duplicate — same amount, same day
6. Stale cheque — cheque not cleared
7. FX mismatch — currency conversion difference
8. Period mismatch — dates cross period boundary
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date
from enum import Enum


class ExceptionCategory(str, Enum):
    AMOUNT_MISMATCH = "amount_mismatch"
    DATE_MISMATCH = "date_mismatch"
    MISSING_GL = "missing_gl"
    MISSING_BANK = "missing_bank"
    DUPLICATE = "duplicate"
    STALE_CHEQUE = "stale_cheque"
    FX_MISMATCH = "fx_mismatch"
    PERIOD_MISMATCH = "period_mismatch"
    FEE_NOT_EXTRACTED = "fee_not_extracted"
    REVIEW_REQUIRED = "review_required"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExceptionItem:
    category: ExceptionCategory
    severity: Severity
    description: str
    description_am: str  # Amharic
    suggested_action: str
    suggested_action_am: str  # Amharic
    transaction_id: Optional[str] = None
    amount: float = 0.0
    transaction_date: Optional[str] = None
    reference: Optional[str] = None
    details: Dict = field(default_factory=dict)


@dataclass
class ExceptionReport:
    total_exceptions: int
    by_category: Dict[str, List[ExceptionItem]]
    by_severity: Dict[str, int]
    summary: List[Dict]
    items: List[ExceptionItem]


class ExceptionReporter:
    """
    Categorize and report on unmatched/exception transactions.
    
    Usage:
        reporter = ExceptionReporter()
        report = reporter.generate(
            unmatched_bank=[...],
            unmatched_gl=[...],
            matches=[...],
            all_transactions=[...]
        )
    """
    
    def generate(
        self,
        unmatched_bank: List[Dict] = None,
        unmatched_gl: List[Dict] = None,
        matches: List[Dict] = None,
        all_transactions: List[Dict] = None,
    ) -> ExceptionReport:
        """Generate exception report from reconciliation results"""
        items = []
        
        # Analyze unmatched bank transactions
        for txn in (unmatched_bank or []):
            items.extend(self._analyze_unmatched_bank(txn, all_transactions or []))
        
        # Analyze unmatched GL entries
        for entry in (unmatched_gl or []):
            items.append(self._analyze_unmatched_gl(entry))
        
        # Analyze matches with low confidence
        for match in (matches or []):
            if match.get("confidence", 100) < 70:
                items.append(self._analyze_low_confidence(match))
        
        # Analyze fee extraction issues
        for txn in (all_transactions or []):
            if self._might_have_fee_issue(txn):
                items.append(self._analyze_fee_issue(txn))
        
        # Build summary
        by_category = {}
        by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for item in items:
            cat = item.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)
            by_severity[item.severity.value] += 1
        
        summary = []
        for cat, cat_items in by_category.items():
            total_amount = sum(i.amount for i in cat_items)
            summary.append({
                "category": cat,
                "count": len(cat_items),
                "total_amount": total_amount,
                "severity": max((i.severity for i in cat_items), key=lambda s: 
                    {"low": 0, "medium": 1, "high": 2, "critical": 3}[s.value]).value,
                "suggested_action": cat_items[0].suggested_action,
            })
        
        return ExceptionReport(
            total_exceptions=len(items),
            by_category=by_category,
            by_severity=by_severity,
            summary=summary,
            items=items,
        )
    
    def _analyze_unmatched_bank(self, txn: Dict, all_transactions: List[Dict]) -> List[ExceptionItem]:
        """Analyze an unmatched bank transaction"""
        items = []
        amount = abs(txn.get("amount", 0) or txn.get("debit", 0) or txn.get("credit", 0))
        desc = (txn.get("description") or txn.get("narrative") or "").upper()
        ref = txn.get("reference", "")
        txn_date = txn.get("date", "")
        
        # Check for ATM/Cash
        if any(kw in desc for kw in ["ATM", "CASH WITHDRAWAL", "CASH DEPOSIT"]):
            items.append(ExceptionItem(
                category=ExceptionCategory.MISSING_GL,
                severity=Severity.LOW,
                description=f"ATM/Cash transaction of ETB {amount:,.2f} — may be petty cash",
                description_am=f"የATM/ጥሬ ገንዘብ ግብይት {amount:,.2f} ብር — የጥሬ ገንዘብ ሊሆን ይችላል",
                suggested_action="Reconcile with petty cash account or create manual journal entry",
                suggested_action_am="ከጥሬ ገንዘብ ሂሳብ ጋር ያስታረቁ ወይም በእጅ የመዝገብ ግቤት ይፍጠሩ",
                transaction_id=txn.get("id"),
                amount=amount,
                transaction_date=txn_date,
                reference=ref,
            ))
        
        # Check for interest/Tax
        elif any(kw in desc for kw in ["INTEREST", "TAX AMOUNT"]):
            items.append(ExceptionItem(
                category=ExceptionCategory.MISSING_GL,
                severity=Severity.MEDIUM,
                description=f"Interest/Tax of ETB {amount:,.2f} — verify GL account",
                description_am=f"ወለድ/ታክስ {amount:,.2f} ብር — የGL ሂሳብ ያረጋግጡ",
                suggested_action="Map to Interest Income (4200) or Tax Expense (7100)",
                suggested_action_am="ወደ የወለድ ገቢ (4200) ወይም የታክስ ወጪ (7100) ያ 매핑 ያድርጉ",
                transaction_id=txn.get("id"),
                amount=amount,
                transaction_date=txn_date,
                reference=ref,
            ))
        
        # Check for fee transactions
        elif any(kw in desc for kw in ["FEE", "CHARGE", "COMMISSION"]):
            items.append(ExceptionItem(
                category=ExceptionCategory.FEE_NOT_EXTRACTED,
                severity=Severity.MEDIUM,
                description=f"Fee transaction of ETB {amount:,.2f} — verify extraction",
                description_am=f"የክፍያ ግብይት {amount:,.2f} ብር — ማውጫን ያረጋግጡ",
                suggested_action="Verify fee extraction accuracy, may need separate GL entry",
                suggested_action_am="የክፍያ ማውጫን ትክክለኛነት ያረጋግጡ፣ ልዩ የGL ግቤት ሊያስፈልግ ይችላል",
                transaction_id=txn.get("id"),
                amount=amount,
                transaction_date=txn_date,
                reference=ref,
            ))
        
        # Check for transfers
        elif any(kw in desc for kw in ["TRANSFER", "FT"]):
            items.append(ExceptionItem(
                category=ExceptionCategory.MISSING_GL,
                severity=Severity.HIGH,
                description=f"Transfer of ETB {amount:,.2f} — no GL entry found",
                description_am=f"ሽግግር {amount:,.2f} ብር — የGL ግቤት አልተገኘም",
                suggested_action="Check if intercompany transfer or create GL entry for this payment",
                suggested_action_am="የውስጥ ሽግግር መሆኑን ይፈትሹ ወይም ለዚህ ክፍያ የGL ግቤት ይፍጠሩ",
                transaction_id=txn.get("id"),
                amount=amount,
                transaction_date=txn_date,
                reference=ref,
            ))
        
        # Generic unmatched
        else:
            items.append(ExceptionItem(
                category=ExceptionCategory.MISSING_GL,
                severity=Severity.HIGH,
                description=f"Unmatched bank transaction of ETB {amount:,.2f}: {desc[:60]}",
                description_am=f"ያልተገናኘ የባንክ ግብይት {amount:,.2f} ብር",
                suggested_action="Review and create matching GL entry or identify reason for mismatch",
                suggested_action_am="ይገምግሙ እና የሚዛመድ የGL ግቤት ይፍጠሩ ወይም ያልመዛኙን ምክንያት ይለዩ",
                transaction_id=txn.get("id"),
                amount=amount,
                transaction_date=txn_date,
                reference=ref,
            ))
        
        return items
    
    def _analyze_unmatched_gl(self, entry: Dict) -> ExceptionItem:
        """Analyze an unmatched GL entry"""
        amount = abs(entry.get("amount", 0) or entry.get("debit_amount", 0))
        desc = entry.get("description", "")
        ref = entry.get("reference", "")
        
        return ExceptionItem(
            category=ExceptionCategory.MISSING_BANK,
            severity=Severity.HIGH,
            description=f"GL entry of ETB {amount:,.2f} has no bank match: {desc[:60]}",
            description_am=f"የGL ግቤት {amount:,.2f} ብር የባንክ ግባና የለውም",
            suggested_action="Check if bank transaction exists or if GL entry is incorrect",
            suggested_action_am="የባንክ ግብይት መኖሩን ይፈትሹ ወይም የGL ግቤት ስህተት እንደሆነ ያረጋግጡ",
            transaction_id=entry.get("id"),
            amount=amount,
            transaction_date=entry.get("date"),
            reference=ref,
        )
    
    def _analyze_low_confidence(self, match: Dict) -> ExceptionItem:
        """Analyze a low-confidence match"""
        txn = match.get("bank_transaction", {})
        amount = abs(txn.get("amount", 0))
        confidence = match.get("confidence", 0)
        
        severity = Severity.MEDIUM if confidence >= 60 else Severity.HIGH
        
        return ExceptionItem(
            category=ExceptionCategory.REVIEW_REQUIRED,
            severity=severity,
            description=f"Low confidence match ({confidence}%) for ETB {amount:,.2f}",
            description_am=f"ዝቅተኛ መተማመን ግባና ({confidence}%) ለ{amount:,.2f} ብር",
            suggested_action=f"Review match manually. Confidence {confidence}% is below threshold.",
            suggested_action_am=f"ግባናውን በእጅ ይገምግሙ። መተማመን {confidence}% ከመደበኛው በታች ነው።",
            transaction_id=txn.get("id"),
            amount=amount,
            transaction_date=txn.get("date"),
            details={"confidence": confidence, "match_type": match.get("match_type")},
        )
    
    def _might_have_fee_issue(self, txn: Dict) -> bool:
        """Check if transaction might have fee extraction issues"""
        amount = abs(txn.get("amount", 0))
        fee_amount = txn.get("fee_amount", 0)
        
        # Round numbers that might have hidden fees
        if amount > 1000 and amount % 100 == 0 and fee_amount == 0:
            desc = (txn.get("description") or "").upper()
            if any(kw in desc for kw in ["TRANSFER", "PAYMENT", "FT"]):
                return True
        return False
    
    def _analyze_fee_issue(self, txn: Dict) -> ExceptionItem:
        """Analyze potential fee extraction issue"""
        amount = abs(txn.get("amount", 0))
        
        return ExceptionItem(
            category=ExceptionCategory.FEE_NOT_EXTRACTED,
            severity=Severity.LOW,
            description=f"Round amount ETB {amount:,.2f} may have embedded fees",
            description_am=f"የተጠጋጋ መጠን {amount:,.2f} ብር የተደበቁ ክፍያዎች ሊኖሩት ይችላል",
            suggested_action="Verify if bank fees are embedded in the amount",
            suggested_action_am="የባንክ ክፍያዎች በመጠኑ ውስጥ መደበቃቸውን ያረጋግጡ",
            transaction_id=txn.get("id"),
            amount=amount,
            transaction_date=txn.get("date"),
        )
    
    def to_dict(self, report: ExceptionReport) -> Dict:
        """Convert report to dict for API response"""
        return {
            "total_exceptions": report.total_exceptions,
            "by_severity": report.by_severity,
            "summary": report.summary,
            "items": [
                {
                    "category": item.category.value,
                    "severity": item.severity.value,
                    "description": item.description,
                    "description_am": item.description_am,
                    "suggested_action": item.suggested_action,
                    "suggested_action_am": item.suggested_action_am,
                    "transaction_id": item.transaction_id,
                    "amount": item.amount,
                    "transaction_date": item.transaction_date,
                    "reference": item.reference,
                    "details": item.details,
                }
                for item in report.items
            ]
        }
