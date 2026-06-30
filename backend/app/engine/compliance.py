"""
Compliance Tracker — ReconET

Tracks VAT, WHT, and generates compliance reports for Ethiopian tax law.

Ethiopian tax rules on bank services:
- 15% VAT on all bank service fees (since 2020)
- 2% WHT on certain bank fees (withholding tax)
- Monthly VAT return filing
- Quarterly WHT certificate

This engine computes compliance data from bank transactions.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date


@dataclass
class ComplianceSummary:
    """Monthly compliance summary"""
    period_month: int
    period_year: int
    # VAT
    total_vatable_fees: float = 0.0
    total_vat: float = 0.0
    vat_rate: float = 0.15
    # WHT
    total_wht_base: float = 0.0
    total_wht: float = 0.0
    wht_rate: float = 0.02
    # By bank
    by_bank: Dict[str, Dict] = field(default_factory=dict)
    # Filing status
    vat_filed: bool = False
    wht_filed: bool = False
    filing_due_date: Optional[str] = None


class ComplianceEngine:
    """
    Compute VAT and WHT on bank fees.
    
    Usage:
        engine = ComplianceEngine()
        summary = engine.compute_monthly(transactions, month=6, year=2026)
    """
    
    VAT_RATE = 0.15    # 15% VAT on bank services
    WHT_RATE = 0.02    # 2% WHT on bank fees
    
    def compute_monthly(
        self, transactions: List[Dict], month: int, year: int
    ) -> ComplianceSummary:
        """
        Compute monthly VAT and WHT from bank transactions.
        
        Args:
            transactions: Transaction dicts with date, fee_amount, bank_charge, gov_tax, description
            month: Period month
            year: Period year
        """
        summary = ComplianceSummary(period_month=month, period_year=year)
        
        by_bank = {}
        
        for txn in transactions:
            txn_date = txn.get("date")
            if isinstance(txn_date, str):
                try:
                    txn_date = date.fromisoformat(txn_date)
                except ValueError:
                    continue
            if not isinstance(txn_date, date):
                continue
            if txn_date.month != month or txn_date.year != year:
                continue
            
            fee_amount = txn.get("fee_amount", 0) or 0
            bank_charge = txn.get("bank_charge", 0) or 0
            gov_tax = txn.get("gov_tax", 0) or 0
            
            if fee_amount <= 0:
                continue
            
            # VAT: 15% on bank charges
            summary.total_vatable_fees += bank_charge
            summary.total_vat += gov_tax if gov_tax > 0 else bank_charge * self.VAT_RATE
            
            # WHT: 2% on bank charges (not on VAT)
            summary.total_wht_base += bank_charge
            summary.total_wht += bank_charge * self.WHT_RATE
            
            # By bank
            bank_name = txn.get("bank_name", "Unknown")
            if bank_name not in by_bank:
                by_bank[bank_name] = {"fees": 0, "vat": 0, "wht": 0, "count": 0}
            by_bank[bank_name]["fees"] += bank_charge
            by_bank[bank_name]["vat"] += gov_tax if gov_tax > 0 else bank_charge * self.VAT_RATE
            by_bank[bank_name]["wht"] += bank_charge * self.WHT_RATE
            by_bank[bank_name]["count"] += 1
        
        summary.by_bank = by_bank
        
        # Filing due date (15th of next month for VAT)
        if month == 12:
            summary.filing_due_date = f"{year + 1}-01-15"
        else:
            summary.filing_due_date = f"{year}-{month + 1:02d}-15"
        
        return summary
    
    def compute_quarterly_wht(
        self, transactions: List[Dict], quarter: int, year: int
    ) -> Dict:
        """
        Compute quarterly WHT for certificate generation.
        
        Quarter 1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec
        """
        start_month = (quarter - 1) * 3 + 1
        months = [start_month, start_month + 1, start_month + 2]
        
        total_wht = 0.0
        total_base = 0.0
        
        for month in months:
            summary = self.compute_monthly(transactions, month, year)
            total_wht += summary.total_wht
            total_base += summary.total_wht_base
        
        return {
            "quarter": quarter,
            "year": year,
            "months": months,
            "total_wht_base": round(total_base, 2),
            "total_wht": round(total_wht, 2),
            "wht_rate": self.WHT_RATE,
            "certificate_data": {
                "description": f"WHT on bank fees Q{quarter} {year}",
                "amount": round(total_wht, 2),
                "base_amount": round(total_base, 2),
            },
        }
    
    def to_dict(self, summary: ComplianceSummary) -> Dict:
        return {
            "period": f"{summary.period_month}/{summary.period_year}",
            "vat": {
                "vatable_fees": round(summary.total_vatable_fees, 2),
                "vat_amount": round(summary.total_vat, 2),
                "vat_rate": summary.vat_rate,
            },
            "wht": {
                "wht_base": round(summary.total_wht_base, 2),
                "wht_amount": round(summary.total_wht, 2),
                "wht_rate": summary.wht_rate,
            },
            "by_bank": {
                bank: {
                    "fees": round(data["fees"], 2),
                    "vat": round(data["vat"], 2),
                    "wht": round(data["wht"], 2),
                    "count": data["count"],
                }
                for bank, data in summary.by_bank.items()
            },
            "filing": {
                "due_date": summary.filing_due_date,
                "vat_filed": summary.vat_filed,
                "wht_filed": summary.wht_filed,
            },
        }
