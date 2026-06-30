"""
GL Account Mapping Engine — ReconET

Maps fee types and transaction types to GL account codes.
Auto-suggests GL accounts for extracted fees.

Ethiopian Chart of Accounts (based on IFRS/SME adapted):
- 6500: Bank Charges
- 6501: Bank Commission
- 6502: Stamp Duty
- 7100: Government Tax (VAT on bank services)
- 7101: Withholding Tax
- 1100: Cash at Bank
- 2100: Accounts Payable
- 4100: Revenue
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class FeeCategory(str, Enum):
    BANK_CHARGE = "bank_charge"
    COMMISSION = "commission"
    STAMP_DUTY = "stamp_duty"
    GOV_TAX = "gov_tax"
    WHT = "wht"
    TRANSFER_FEE = "transfer_fee"
    CHEQUE_FEE = "cheque_fee"
    FX_COMMISSION = "fx_commission"


@dataclass
class GLMapping:
    fee_type: str
    gl_account_code: str
    gl_account_name: str
    description: str
    is_default: bool = True


# Default Ethiopian GL mappings (Chart of Accounts)
DEFAULT_MAPPINGS: List[GLMapping] = [
    GLMapping("bank_charge", "6500", "Bank Charges", "Service fees charged by banks", True),
    GLMapping("commission", "6501", "Bank Commission", "Commission on transactions", True),
    GLMapping("stamp_duty", "6502", "Stamp Duty", "Government stamp duty on financial instruments", True),
    GLMapping("gov_tax", "7100", "Government Tax (VAT)", "15% VAT on bank services", True),
    GLMapping("wht", "7101", "Withholding Tax", "2% WHT on bank fees", True),
    GLMapping("transfer_fee", "6500", "Bank Charges", "Fund transfer fees", True),
    GLMapping("cheque_fee", "6500", "Bank Charges", "Cheque-related fees", True),
    GLMapping("fx_commission", "6503", "FX Commission", "Foreign exchange commission", True),
    GLMapping("interest_income", "4200", "Interest Income", "Interest earned on deposits", True),
    GLMapping("interest_expense", "8100", "Interest Expense", "Interest paid on loans", True),
]


class GLAccountMapper:
    """
    Maps transaction fee types to GL accounts.
    
    Usage:
        mapper = GLAccountMapper()
        result = mapper.map_fee("bank_charge", 25.00)
        # → {"gl_code": "6500", "gl_name": "Bank Charges", "debit": 25.00}
    """
    
    def __init__(self, custom_mappings: Optional[List[Dict]] = None):
        self.mappings = {m.fee_type: m for m in DEFAULT_MAPPINGS}
        
        if custom_mappings:
            for cm in custom_mappings:
                self.mappings[cm["fee_type"]] = GLMapping(
                    fee_type=cm["fee_type"],
                    gl_account_code=cm["gl_account_code"],
                    gl_account_name=cm["gl_account_name"],
                    description=cm.get("description", ""),
                    is_default=False,
                )
    
    def map_fee(self, fee_type: str, amount: float) -> Dict:
        """Map a fee type to a GL account"""
        mapping = self.mappings.get(fee_type)
        if not mapping:
            # Try partial match
            for key, m in self.mappings.items():
                if key in fee_type or fee_type in key:
                    mapping = m
                    break
        
        if not mapping:
            return {
                "gl_code": None,
                "gl_name": "Unknown",
                "debit": amount,
                "needs_review": True,
                "suggestion": f"No mapping for fee type '{fee_type}'. Review and assign GL account."
            }
        
        return {
            "gl_code": mapping.gl_account_code,
            "gl_name": mapping.gl_account_name,
            "debit": amount,
            "needs_review": not mapping.is_default,
            "description": mapping.description,
        }
    
    def map_transaction(self, transaction: Dict) -> List[Dict]:
        """
        Generate GL journal entries for a transaction with fees.
        
        Returns list of journal entries:
        - Vendor/payment entry (debit)
        - Fee entries (debit)
        - Bank account entry (credit)
        """
        entries = []
        
        gross = abs(transaction.get("gross_amount", transaction.get("amount", 0)))
        bank_charge = transaction.get("bank_charge", 0)
        gov_tax = transaction.get("gov_tax", 0)
        wht = transaction.get("wht", 0)
        total_fees = bank_charge + gov_tax + wht
        
        # 1. Vendor/payment entry (debit)
        entries.append({
            "account_code": transaction.get("expense_account", "5100"),
            "account_name": transaction.get("expense_name", "Operating Expense"),
            "debit": gross,
            "credit": 0,
            "description": f"Payment: {transaction.get('description', '')}",
            "type": "expense"
        })
        
        # 2. Bank charge entry (debit)
        if bank_charge > 0:
            fee_map = self.map_fee("bank_charge", bank_charge)
            entries.append({
                "account_code": fee_map["gl_code"],
                "account_name": fee_map["gl_name"],
                "debit": bank_charge,
                "credit": 0,
                "description": f"Bank charge on transaction",
                "type": "fee"
            })
        
        # 3. Government tax entry (debit)
        if gov_tax > 0:
            fee_map = self.map_fee("gov_tax", gov_tax)
            entries.append({
                "account_code": fee_map["gl_code"],
                "account_name": fee_map["gl_name"],
                "debit": gov_tax,
                "credit": 0,
                "description": "15% VAT on bank services",
                "type": "tax"
            })
        
        # 4. WHT entry (debit)
        if wht > 0:
            fee_map = self.map_fee("wht", wht)
            entries.append({
                "account_code": fee_map["gl_code"],
                "account_name": fee_map["gl_name"],
                "debit": wht,
                "credit": 0,
                "description": "2% Withholding tax on bank fees",
                "type": "tax"
            })
        
        # 5. Bank account entry (credit) — total outflow
        entries.append({
            "account_code": "1100",
            "account_name": "Cash at Bank",
            "debit": 0,
            "credit": gross + total_fees,
            "description": f"Bank outflow for {transaction.get('description', '')}",
            "type": "bank"
        })
        
        return entries
    
    def get_all_mappings(self) -> List[Dict]:
        """Get all current mappings"""
        return [
            {
                "fee_type": m.fee_type,
                "gl_account_code": m.gl_account_code,
                "gl_account_name": m.gl_account_name,
                "description": m.description,
                "is_default": m.is_default,
            }
            for m in self.mappings.values()
        ]
    
    def update_mapping(self, fee_type: str, gl_code: str, gl_name: str, description: str = ""):
        """Update or add a mapping"""
        self.mappings[fee_type] = GLMapping(
            fee_type=fee_type,
            gl_account_code=gl_code,
            gl_account_name=gl_name,
            description=description,
            is_default=False,
        )
