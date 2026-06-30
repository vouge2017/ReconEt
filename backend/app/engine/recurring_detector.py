"""
Recurring Pattern Detector — ReconET

Finds patterns in transaction history:
- Payroll (biweekly or monthly, same amount, same description)
- Rent (monthly, same amount, same payee)
- Loan payments (monthly, decreasing slightly over time)
- Standing orders (weekly/monthly, same amount, same reference)
- Vendor payments (recurring, similar amounts)
- Subscriptions (monthly, same amount)

Used by Cash Forecast Engine to predict future cash flows.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict, Counter
import re
import statistics


@dataclass
class DetectedPattern:
    """A recurring pattern found in transaction history"""
    pattern_type: str       # payroll, rent, loan, standing_order, vendor, subscription, utility
    description: str
    amount: float
    frequency: str          # weekly, biweekly, monthly, quarterly
    next_expected_date: str
    day_of_month: Optional[int] = None
    day_of_week: Optional[int] = None
    confidence: float = 0.0
    occurrences: int = 0
    last_seen: Optional[str] = None
    avg_amount: float = 0.0
    amount_variance: float = 0.0
    sample_references: List[str] = field(default_factory=list)


class RecurringDetector:
    """
    Detect recurring patterns from transaction history.
    
    Usage:
        detector = RecurringDetector()
        patterns = detector.detect(transactions)
        # Returns list of DetectedPattern with next expected dates
    """
    
    # Keywords for classification
    PAYROLL_KEYWORDS = ["SALARY", "PAYROLL", "WAGE", "BONUS", "ALLOWANCE"]
    RENT_KEYWORDS = ["RENT", "LEASE", "OFFICE SPACE", "WAREHOUSE"]
    LOAN_KEYWORDS = ["LOAN", "INSTALLMENT", "EMI", "REPAYMENT", "PRINCIPAL", "INTEREST"]
    STANDING_ORDER_KEYWORDS = ["STANDING ORDER", "SO-", "RECURRING", "AUTO DEBIT"]
    UTILITY_KEYWORDS = ["ELECTRIC", "WATER", "TELECOM", "ETHIO TELECOM", "SAFARICOM", "UTILITY"]
    SUBSCRIPTION_KEYWORDS = ["SUBSCRIPTION", "LICENSE", "SOFTWARE", "CLOUD", "SaaS"]
    
    def detect(self, transactions: List[Dict], min_occurrences: int = 2) -> List[DetectedPattern]:
        """
        Detect recurring patterns from transaction history.
        
        Args:
            transactions: List of transaction dicts with date, amount, description, reference
            min_occurrences: Minimum times a pattern must repeat to be detected
        
        Returns:
            List of DetectedPattern sorted by confidence
        """
        if not transactions:
            return []
        
        # Parse and group transactions
        parsed = self._parse_transactions(transactions)
        
        # Group by similar description (fuzzy grouping)
        groups = self._group_by_description(parsed)
        
        patterns = []
        
        for group_key, group_txns in groups.items():
            if len(group_txns) < min_occurrences:
                continue
            
            pattern = self._analyze_group(group_key, group_txns)
            if pattern and pattern.confidence >= 0.5:
                patterns.append(pattern)
        
        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return patterns
    
    def _parse_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Parse and normalize transactions"""
        parsed = []
        for txn in transactions:
            d = txn.get("date")
            if isinstance(d, str):
                try:
                    d = date.fromisoformat(d)
                except ValueError:
                    continue
            if not isinstance(d, date):
                continue
            
            parsed.append({
                "date": d,
                "amount": float(txn.get("amount", 0)),
                "description": (txn.get("description") or txn.get("narrative") or "").upper().strip(),
                "reference": (txn.get("reference") or "").upper().strip(),
                "raw": txn,
            })
        
        parsed.sort(key=lambda t: t["date"])
        return parsed
    
    def _group_by_description(self, transactions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group transactions by similar description"""
        groups = defaultdict(list)
        
        for txn in transactions:
            desc = txn["description"]
            ref = txn["reference"]
            
            # Normalize description for grouping
            key = self._normalize_description(desc, ref)
            groups[key].append(txn)
        
        return dict(groups)
    
    def _normalize_description(self, desc: str, ref: str = "") -> str:
        """Normalize description for grouping similar transactions"""
        # Remove dates, amounts, reference numbers
        desc = re.sub(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', '', desc)
        desc = re.sub(r'\d{10,}', '', desc)  # Long numbers (references)
        desc = re.sub(r'ETB\s*[\d,]+\.?\d*', '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()
        
        # Use reference prefix if available (FT, CHQ, SO, etc.)
        if ref:
            ref_prefix = re.match(r'^([A-Z]+)', ref)
            if ref_prefix:
                return f"{ref_prefix.group(1)}:{desc[:30]}"
        
        return desc[:40]
    
    def _analyze_group(self, group_key: str, transactions: List[Dict]) -> Optional[DetectedPattern]:
        """Analyze a group of similar transactions to find pattern"""
        
        if len(transactions) < 2:
            return None
        
        dates = [t["date"] for t in transactions]
        amounts = [abs(t["amount"]) for t in transactions]
        descriptions = [t["description"] for t in transactions]
        references = [t["reference"] for t in transactions]
        
        # Calculate amount stats
        avg_amount = statistics.mean(amounts)
        amount_variance = statistics.stdev(amounts) if len(amounts) > 1 else 0
        amount_cv = amount_variance / avg_amount if avg_amount > 0 else 0  # Coefficient of variation
        
        # Detect frequency
        frequency, day_of_month, day_of_week, interval_days = self._detect_frequency(dates)
        
        if not frequency:
            return None
        
        # Classify pattern type
        pattern_type = self._classify_pattern(descriptions, references, avg_amount)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            len(transactions), amount_cv, interval_days, pattern_type, descriptions
        )
        
        # Generate description
        desc = self._generate_description(pattern_type, descriptions, avg_amount)
        
        # Predict next occurrence
        next_date = self._predict_next_date(dates[-1], frequency, day_of_month, day_of_week, interval_days)
        
        return DetectedPattern(
            pattern_type=pattern_type,
            description=desc,
            amount=round(avg_amount, 2),
            frequency=frequency,
            next_expected_date=str(next_date),
            day_of_month=day_of_month,
            day_of_week=day_of_week,
            confidence=round(confidence, 2),
            occurrences=len(transactions),
            last_seen=str(dates[-1]),
            avg_amount=round(avg_amount, 2),
            amount_variance=round(amount_variance, 2),
            sample_references=list(set(references[:3])),
        )
    
    def _detect_frequency(
        self, dates: List[date]
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[int]]:
        """Detect frequency from a list of dates"""
        if len(dates) < 2:
            return None, None, None, None
        
        intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        
        if not intervals:
            return None, None, None, None
        
        avg_interval = statistics.mean(intervals)
        
        # Classify frequency
        if 5 <= avg_interval <= 9:
            return "weekly", None, dates[-1].weekday(), 7
        elif 12 <= avg_interval <= 16:
            return "biweekly", None, dates[-1].weekday(), 14
        elif 25 <= avg_interval <= 35:
            return "monthly", dates[-1].day, None, 30
        elif 80 <= avg_interval <= 100:
            return "quarterly", dates[-1].day, None, 90
        elif 350 <= avg_interval <= 380:
            return "yearly", dates[-1].day, dates[-1].month, 365
        else:
            # Try monthly by day-of-month
            days_of_month = [d.day for d in dates]
            if len(set(days_of_month)) <= 2:  # Same day each month (±1)
                return "monthly", statistics.mode(days_of_month), None, 30
            return None, None, None, int(avg_interval)
    
    def _classify_pattern(
        self, descriptions: List[str], references: List[str], avg_amount: float
    ) -> str:
        """Classify pattern type from description keywords"""
        all_text = " ".join(descriptions + references).upper()
        
        if any(kw in all_text for kw in self.PAYROLL_KEYWORDS):
            return "payroll"
        if any(kw in all_text for kw in self.RENT_KEYWORDS):
            return "rent"
        if any(kw in all_text for kw in self.LOAN_KEYWORDS):
            return "loan"
        if any(kw in all_text for kw in self.STANDING_ORDER_KEYWORDS):
            return "standing_order"
        if any(kw in all_text for kw in self.UTILITY_KEYWORDS):
            return "utility"
        if any(kw in all_text for kw in self.SUBSCRIPTION_KEYWORDS):
            return "subscription"
        
        # Amount-based heuristics
        if avg_amount > 100000 and any(kw in all_text for kw in ["TRANSFER", "FT"]):
            return "vendor"
        
        return "recurring"
    
    def _calculate_confidence(
        self, occurrences: int, amount_cv: float, interval_days: int,
        pattern_type: str, descriptions: List[str]
    ) -> float:
        """Calculate confidence score for a pattern"""
        score = 0.0
        
        # More occurrences = higher confidence
        if occurrences >= 6:
            score += 0.3
        elif occurrences >= 4:
            score += 0.2
        elif occurrences >= 2:
            score += 0.1
        
        # Consistent amount = higher confidence
        if amount_cv < 0.01:  # Almost identical amounts
            score += 0.3
        elif amount_cv < 0.05:
            score += 0.2
        elif amount_cv < 0.1:
            score += 0.1
        
        # Known pattern type = higher confidence
        if pattern_type in ("payroll", "rent", "loan", "standing_order"):
            score += 0.25
        elif pattern_type in ("utility", "subscription"):
            score += 0.15
        
        # Consistent description = higher confidence
        unique_descs = len(set(descriptions))
        if unique_descs <= 2:
            score += 0.15
        elif unique_descs <= len(descriptions) * 0.3:
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_description(
        self, pattern_type: str, descriptions: List[str], avg_amount: float
    ) -> str:
        """Generate human-readable description for the pattern"""
        # Get most common description
        desc_counter = Counter(descriptions)
        common_desc = desc_counter.most_common(1)[0][0] if descriptions else "Unknown"
        
        # Truncate
        if len(common_desc) > 50:
            common_desc = common_desc[:47] + "..."
        
        type_labels = {
            "payroll": "Payroll",
            "rent": "Rent Payment",
            "loan": "Loan Repayment",
            "standing_order": "Standing Order",
            "utility": "Utility Payment",
            "subscription": "Subscription",
            "vendor": "Vendor Payment",
            "recurring": "Recurring Payment",
        }
        
        label = type_labels.get(pattern_type, "Recurring")
        return f"{label}: {common_desc}"
    
    def _predict_next_date(
        self, last_date: date, frequency: str, day_of_month: Optional[int],
        day_of_week: Optional[int], interval_days: int
    ) -> date:
        """Predict next occurrence date"""
        if frequency == "weekly" and day_of_week is not None:
            # Next occurrence of this weekday
            days_ahead = (day_of_week - last_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return last_date + timedelta(days=days_ahead)
        
        elif frequency == "biweekly":
            return last_date + timedelta(days=14)
        
        elif frequency == "monthly" and day_of_month is not None:
            # Next month, same day
            if last_date.month == 12:
                next_month = last_date.replace(year=last_date.year + 1, month=1, day=1)
            else:
                next_month = last_date.replace(month=last_date.month + 1, day=1)
            
            # Handle months with fewer days
            try:
                return next_month.replace(day=day_of_month)
            except ValueError:
                return next_month.replace(day=28)
        
        elif frequency == "quarterly":
            return last_date + timedelta(days=90)
        
        else:
            return last_date + timedelta(days=interval_days)
