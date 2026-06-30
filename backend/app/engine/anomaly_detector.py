"""
Anomaly Detector — ReconET

Finds problems before humans do:
- Duplicate payments (same amount, same payee, close dates)
- Weekend/holiday transactions (Ethiopian banks don't process)
- Unusual amounts (spikes vs historical average)
- New payees (first payment to unknown entity)
- Round numbers (potential estimates or errors)
- Stale cheques (>90 days uncashed)
- Missing expected transactions (payroll didn't process)
- Fee anomalies (sudden fee increase)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date, timedelta
from collections import defaultdict
import statistics


class AlertSeverity:
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class AnomalyAlert:
    """A detected anomaly"""
    alert_type: str         # duplicate, weekend, spike, new_payee, round_amount, stale, missing, fee_anomaly
    severity: str           # critical, warning, info
    title: str
    description: str
    description_am: str     # Amharic
    transaction_ids: List[str] = field(default_factory=list)
    amount: float = 0.0
    transaction_date: Optional[str] = None
    details: Dict = field(default_factory=dict)


class AnomalyDetector:
    """
    Detect anomalies in bank transactions.
    
    Usage:
        detector = AnomalyDetector()
        alerts = detector.scan(transactions, cheques=cheques)
    """
    
    # Ethiopian public holidays (approximate, major ones)
    ETHIOPIAN_HOLIDAYS_MONTHS = [1, 3, 4, 9, 10]  # Jan (Genna), Mar (Adwa), Apr (Siklet), Sep (Meskel), Oct (Gena)
    
    def scan(
        self,
        transactions: List[Dict],
        cheques: List[Dict] = None,
        historical_transactions: List[Dict] = None,
        expected_patterns: List[Dict] = None,
    ) -> List[AnomalyAlert]:
        """
        Scan transactions for anomalies.
        
        Args:
            transactions: Current period transactions
            cheques: Outstanding cheques
            historical_transactions: Past transactions for baseline
            expected_patterns: Expected recurring payments
        """
        alerts = []
        
        # Parse transactions
        parsed = self._parse_transactions(transactions)
        
        # 1. Duplicate detection
        alerts.extend(self._detect_duplicates(parsed))
        
        # 2. Weekend/holiday transactions
        alerts.extend(self._detect_weekend_transactions(parsed))
        
        # 3. Amount spikes
        if historical_transactions:
            alerts.extend(self._detect_spikes(parsed, historical_transactions))
        
        # 4. New payees
        if historical_transactions:
            alerts.extend(self._detect_new_payees(parsed, historical_transactions))
        
        # 5. Round amounts on transfers
        alerts.extend(self._detect_round_amounts(parsed))
        
        # 6. Stale cheques
        if cheques:
            alerts.extend(self._detect_stale_cheques(cheques))
        
        # 7. Missing expected transactions
        if expected_patterns:
            alerts.extend(self._detect_missing_transactions(parsed, expected_patterns))
        
        # 8. Fee anomalies
        alerts.extend(self._detect_fee_anomalies(parsed))
        
        # Sort by severity
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
        
        return alerts
    
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
                "id": txn.get("id", ""),
                "date": d,
                "amount": float(txn.get("amount", 0)),
                "description": (txn.get("description") or txn.get("narrative") or "").upper().strip(),
                "reference": (txn.get("reference") or "").upper().strip(),
                "fee_amount": float(txn.get("fee_amount", 0)),
                "raw": txn,
            })
        
        return parsed
    
    def _detect_duplicates(self, transactions: List[Dict]) -> List[AnomalyAlert]:
        """Detect potential duplicate payments"""
        alerts = []
        
        # Group by amount
        by_amount = defaultdict(list)
        for txn in transactions:
            by_amount[abs(txn["amount"])].append(txn)
        
        for amount, txns in by_amount.items():
            if len(txns) < 2 or amount < 1000:  # Skip small amounts
                continue
            
            # Check pairs
            for i in range(len(txns)):
                for j in range(i + 1, len(txns)):
                    t1, t2 = txns[i], txns[j]
                    days_diff = abs((t1["date"] - t2["date"]).days)
                    
                    if days_diff <= 3:  # Within 3 days
                        # Check if same payee (description similarity)
                        desc1_words = set(t1["description"].split())
                        desc2_words = set(t2["description"].split())
                        overlap = len(desc1_words & desc2_words)
                        
                        if overlap >= 2 or t1["description"][:20] == t2["description"][:20]:
                            alerts.append(AnomalyAlert(
                                alert_type="duplicate",
                                severity=AlertSeverity.CRITICAL,
                                title=f"Possible duplicate: ETB {amount:,.0f}",
                                description=(
                                    f"Two payments of ETB {amount:,.0f} to similar payees "
                                    f"within {days_diff} day(s). Verify if duplicate."
                                ),
                                description_am=(
                                    f"ሁለት ክፍያዎች {amount:,.0f} ብር ለተመሳሳይ ተቀባዮች "
                                    f"በ{days_diff} ቀን(ዎች) ውስጥ። ተደጋጋሚ መሆኑን ያረጋግጡ።"
                                ),
                                transaction_ids=[t1["id"], t2["id"]],
                                amount=amount,
                                transaction_date=str(t1["date"]),
                                details={
                                    "date_1": str(t1["date"]),
                                    "date_2": str(t2["date"]),
                                    "desc_1": t1["description"][:50],
                                    "desc_2": t2["description"][:50],
                                    "days_between": days_diff,
                                }
                            ))
        
        return alerts
    
    def _detect_weekend_transactions(self, transactions: List[Dict]) -> List[AnomalyAlert]:
        """Detect transactions on weekends (unusual for Ethiopian banks)"""
        alerts = []
        
        for txn in transactions:
            d = txn["date"]
            if d.weekday() == 5:  # Saturday
                alerts.append(AnomalyAlert(
                    alert_type="weekend",
                    severity=AlertSeverity.WARNING,
                    title=f"Saturday transaction: ETB {abs(txn['amount']):,.0f}",
                    description=(
                        f"Transaction on Saturday ({d}). Ethiopian banks typically "
                        f"don't process on Saturdays. Verify if legitimate."
                    ),
                    description_am=(
                        f"ቅዳሜ ግብይት ({d})። የኢትዮጵያ ባንኮች በቅዳሜ አይሰሩም። "
                        f"እውነተኛ መሆኑን ያረጋግጡ።"
                    ),
                    transaction_ids=[txn["id"]],
                    amount=abs(txn["amount"]),
                    transaction_date=str(d),
                ))
            elif d.weekday() == 6:  # Sunday
                alerts.append(AnomalyAlert(
                    alert_type="weekend",
                    severity=AlertSeverity.WARNING,
                    title=f"Sunday transaction: ETB {abs(txn['amount']):,.0f}",
                    description=(
                        f"Transaction on Sunday ({d}). Ethiopian banks are closed on Sundays."
                    ),
                    description_am=f"እሁድ ግብይት ({d})። የኢትዮጵያ ባንኮች በእሁድ ይዘጋሉ።",
                    transaction_ids=[txn["id"]],
                    amount=abs(txn["amount"]),
                    transaction_date=str(d),
                ))
        
        return alerts
    
    def _detect_spikes(
        self, current: List[Dict], historical: List[Dict]
    ) -> List[AnomalyAlert]:
        """Detect amount spikes vs historical average"""
        alerts = []
        
        # Calculate historical average by description group
        hist_amounts = defaultdict(list)
        for txn in historical:
            key = txn["description"][:20]
            hist_amounts[key].append(abs(txn["amount"]))
        
        hist_avg = {}
        for key, amounts in hist_amounts.items():
            if len(amounts) >= 3:
                hist_avg[key] = statistics.mean(amounts)
        
        # Check current transactions
        for txn in current:
            key = txn["description"][:20]
            if key in hist_avg:
                avg = hist_avg[key]
                amount = abs(txn["amount"])
                
                if avg > 0 and amount > avg * 3:  # 3x the average
                    alerts.append(AnomalyAlert(
                        alert_type="spike",
                        severity=AlertSeverity.WARNING,
                        title=f"Amount spike: ETB {amount:,.0f} (avg: {avg:,.0f})",
                        description=(
                            f"Transaction of ETB {amount:,.0f} is {amount/avg:.1f}x the "
                            f"historical average of ETB {avg:,.0f}. Verify if legitimate."
                        ),
                        description_am=(
                            f"ግብይት {amount:,.0f} ብር ከታሪክ በይዘር {avg:,.0f} ብር "
                            f"በ{amount/avg:.1f} እጥፍ ነው። እውነተኛ መሆኑን ያረጋግጡ።"
                        ),
                        transaction_ids=[txn["id"]],
                        amount=amount,
                        transaction_date=str(txn["date"]),
                        details={"historical_average": avg, "multiplier": round(amount/avg, 1)},
                    ))
        
        return alerts
    
    def _detect_new_payees(
        self, current: List[Dict], historical: List[Dict]
    ) -> List[AnomalyAlert]:
        """Detect first-time payments to new entities"""
        alerts = []
        
        # Build set of known payees from history
        known_payees = set()
        for txn in historical:
            # Normalize payee name (first 20 chars of description)
            payee = txn["description"][:20].strip()
            if payee:
                known_payees.add(payee)
        
        # Check current transactions for new payees
        for txn in current:
            if txn["amount"] < 0:  # Only outgoing payments
                payee = txn["description"][:20].strip()
                amount = abs(txn["amount"])
                
                if payee and payee not in known_payees and amount >= 50000:
                    alerts.append(AnomalyAlert(
                        alert_type="new_payee",
                        severity=AlertSeverity.WARNING,
                        title=f"New payee: ETB {amount:,.0f}",
                        description=(
                            f"First payment of ETB {amount:,.0f} to new entity: "
                            f"'{txn['description'][:40]}'. Verify vendor legitimacy."
                        ),
                        description_am=(
                            f"የመጀመሪያ ክፍያ {amount:,.0f} ብር ለአዲስ ተቀባይ: "
                            f"'{txn['description'][:40]}'. የሻጭ ሕጋዊነትን ያረጋግጡ።"
                        ),
                        transaction_ids=[txn["id"]],
                        amount=amount,
                        transaction_date=str(txn["date"]),
                    ))
        
        return alerts
    
    def _detect_round_amounts(self, transactions: List[Dict]) -> List[AnomalyAlert]:
        """Detect suspiciously round amounts on transfers"""
        alerts = []
        
        for txn in transactions:
            amount = abs(txn["amount"])
            desc = txn["description"]
            
            # Only flag for transfers/payments
            if not any(kw in desc for kw in ["TRANSFER", "FT", "PAYMENT"]):
                continue
            
            # Check if round (exact thousands)
            if amount >= 10000 and amount % 1000 == 0:
                alerts.append(AnomalyAlert(
                    alert_type="round_amount",
                    severity=AlertSeverity.INFO,
                    title=f"Round amount: ETB {amount:,.0f}",
                    description=(
                        f"Exact round amount of ETB {amount:,.0f}. "
                        f"Verify if this matches an actual invoice."
                    ),
                    description_am=f"የተጠጋጋ መጠን {amount:,.0f} ብር። ከክፍያ ጋር ይዛመዳል ያረጋግጡ።",
                    transaction_ids=[txn["id"]],
                    amount=amount,
                    transaction_date=str(txn["date"]),
                ))
        
        return alerts
    
    def _detect_stale_cheques(self, cheques: List[Dict]) -> List[AnomalyAlert]:
        """Detect stale cheques (>90 days outstanding)"""
        alerts = []
        today = date.today()
        
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
            
            if days_outstanding > 120:
                severity = AlertSeverity.CRITICAL
            elif days_outstanding > 90:
                severity = AlertSeverity.WARNING
            else:
                continue
            
            alerts.append(AnomalyAlert(
                alert_type="stale_cheque",
                severity=severity,
                title=f"Stale cheque: ETB {chq.get('amount', 0):,.0f} ({days_outstanding} days)",
                description=(
                    f"Cheque #{chq.get('cheque_number', 'N/A')} for ETB {chq.get('amount', 0):,.0f} "
                    f"issued {days_outstanding} days ago to '{chq.get('payee_name', 'Unknown')}'. "
                    f"Not yet cleared. Consider cancellation."
                ),
                description_am=(
                    f"ቼክ #{chq.get('cheque_number', 'N/A')} ለ{chq.get('amount', 0):,.0f} ብር "
                    f"ከ{days_outstanding} ቀናት በፊት ተሰጥቷል። አልተፈረሰም። መሰረዝን ያስቡ።"
                ),
                amount=chq.get("amount", 0),
                transaction_date=str(issue_date),
                details={
                    "cheque_number": chq.get("cheque_number"),
                    "payee": chq.get("payee_name"),
                    "days_outstanding": days_outstanding,
                }
            ))
        
        return alerts
    
    def _detect_missing_transactions(
        self, current: List[Dict], expected: List[Dict]
    ) -> List[AnomalyAlert]:
        """Detect missing expected transactions (e.g., payroll didn't process)"""
        alerts = []
        today = date.today()
        
        for exp in expected:
            expected_date = exp.get("expected_date")
            if isinstance(expected_date, str):
                try:
                    expected_date = date.fromisoformat(expected_date)
                except ValueError:
                    continue
            
            if not isinstance(expected_date, date):
                continue
            
            # Check if expected date has passed
            if expected_date > today:
                continue
            
            days_overdue = (today - expected_date).days
            if days_overdue < 3:
                continue  # Give 3 days grace
            
            # Check if matching transaction exists
            found = False
            for txn in current:
                if abs((txn["date"] - expected_date).days) <= 3:
                    if abs(abs(txn["amount"]) - exp.get("amount", 0)) < exp.get("amount", 0) * 0.1:
                        found = True
                        break
            
            if not found:
                alerts.append(AnomalyAlert(
                    alert_type="missing",
                    severity=AlertSeverity.WARNING,
                    title=f"Missing: {exp.get('description', 'Expected payment')}",
                    description=(
                        f"Expected payment of ETB {exp.get('amount', 0):,.0f} "
                        f"on {expected_date} not found. {days_overdue} days overdue."
                    ),
                    description_am=(
                        f"የሚጠበቅ ክፍያ {exp.get('amount', 0):,.0f} ብር "
                        f"በ{expected_date} አልተገኘም። በ{days_overdue} ቀናት አልፏል።"
                    ),
                    amount=exp.get("amount", 0),
                    transaction_date=str(expected_date),
                    details={"expected_date": str(expected_date), "days_overdue": days_overdue},
                ))
        
        return alerts
    
    def _detect_fee_anomalies(self, transactions: List[Dict]) -> List[AnomalyAlert]:
        """Detect unusual fee amounts"""
        alerts = []
        
        fee_txns = [t for t in transactions if t.get("fee_amount", 0) > 0]
        if len(fee_txns) < 3:
            return alerts
        
        fees = [t["fee_amount"] for t in fee_txns]
        avg_fee = statistics.mean(fees)
        
        for txn in fee_txns:
            fee = txn["fee_amount"]
            if avg_fee > 0 and fee > avg_fee * 5:  # 5x average
                alerts.append(AnomalyAlert(
                    alert_type="fee_anomaly",
                    severity=AlertSeverity.WARNING,
                    title=f"High fee: ETB {fee:,.0f} (avg: {avg_fee:,.0f})",
                    description=(
                        f"Bank fee of ETB {fee:,.0f} is {fee/avg_fee:.1f}x the average "
                        f"of ETB {avg_fee:,.0f}. Verify transaction type."
                    ),
                    description_am=(
                        f"የባንክ ክፍያ {fee:,.0f} ብር ከበይዘር {avg_fee:,.0f} ብር "
                        f"በ{fee/avg_fee:.1f} እጥፍ ነው። የግብይት ዓይነትን ያረጋግጡ።"
                    ),
                    transaction_ids=[txn["id"]],
                    amount=fee,
                    transaction_date=str(txn["date"]),
                    details={"average_fee": avg_fee, "multiplier": round(fee/avg_fee, 1)},
                ))
        
        return alerts
