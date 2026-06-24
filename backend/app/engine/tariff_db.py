"""
CBE Fee Tariff Database

For fee pattern 4: "Deducted from balance but not itemized"
When the bank deducts a fee but doesn't describe it in the transaction,
we estimate from known tariff schedules.

Tariffs are configurable per bank and can be updated when tariffs change.

Source: CBE tariff schedule (as of 2025)
Note: Tariffs change periodically. Customers should verify and update.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class TransactionType(str, Enum):
    """Transaction types for tariff lookup"""
    TRANSFER_INTERNAL = "transfer_internal"      # Within CBE
    TRANSFER_INTERBANK = "transfer_interbank"    # To other banks
    CHEQUE_ISSUED = "cheque_issued"
    CHEQUE_DEPOSIT = "cheque_deposit"
    CASH_DEPOSIT = "cash_deposit"
    CASH_WITHDRAWAL = "cash_withdrawal"
    STANDING_ORDER = "standing_order"
    SALARY_PAYMENT = "salary_payment"
    DRAFT_ISSUANCE = "draft_issuance"
    BALANCE_CERTIFICATE = "balance_certificate"
    STATEMENT_REQUEST = "statement_request"
    FX_TRANSFER = "fx_transfer"


@dataclass
class TariffEntry:
    """A single tariff entry"""
    transaction_type: TransactionType
    min_amount: float
    max_amount: float
    fee: float
    tax_rate: float  # e.g., 0.15 for 15% VAT
    description: str
    effective_from: str = "2025-01-01"
    effective_to: Optional[str] = None


# CBE Tariff Schedule (approximate, as of 2025)
# These should be verified and updated when CBE changes tariffs
CBE_TARIFFS: List[TariffEntry] = [
    # Internal transfers (within CBE)
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERNAL,
        min_amount=0, max_amount=50000,
        fee=25.00, tax_rate=0.15,
        description="Transfer within CBE (up to 50,000 ETB)"
    ),
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERNAL,
        min_amount=50001, max_amount=100000,
        fee=50.00, tax_rate=0.15,
        description="Transfer within CBE (50,001 - 100,000 ETB)"
    ),
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERNAL,
        min_amount=100001, max_amount=500000,
        fee=100.00, tax_rate=0.15,
        description="Transfer within CBE (100,001 - 500,000 ETB)"
    ),
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERNAL,
        min_amount=500001, max_amount=float('inf'),
        fee=200.00, tax_rate=0.15,
        description="Transfer within CBE (above 500,000 ETB)"
    ),
    
    # Interbank transfers
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERBANK,
        min_amount=0, max_amount=50000,
        fee=50.00, tax_rate=0.15,
        description="Interbank transfer (up to 50,000 ETB)"
    ),
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERBANK,
        min_amount=50001, max_amount=100000,
        fee=100.00, tax_rate=0.15,
        description="Interbank transfer (50,001 - 100,000 ETB)"
    ),
    TariffEntry(
        transaction_type=TransactionType.TRANSFER_INTERBANK,
        min_amount=100001, max_amount=float('inf'),
        fee=150.00, tax_rate=0.15,
        description="Interbank transfer (above 100,000 ETB)"
    ),
    
    # Cheque operations
    TariffEntry(
        transaction_type=TransactionType.CHEQUE_ISSUED,
        min_amount=0, max_amount=float('inf'),
        fee=10.00, tax_rate=0.15,
        description="Cheque issuance fee"
    ),
    TariffEntry(
        transaction_type=TransactionType.CHEQUE_DEPOSIT,
        min_amount=0, max_amount=float('inf'),
        fee=5.00, tax_rate=0.15,
        description="Cheque deposit fee"
    ),
    
    # Cash operations
    TariffEntry(
        transaction_type=TransactionType.CASH_DEPOSIT,
        min_amount=0, max_amount=100000,
        fee=0.00, tax_rate=0.15,
        description="Cash deposit (no fee up to 100,000)"
    ),
    TariffEntry(
        transaction_type=TransactionType.CASH_WITHDRAWAL,
        min_amount=0, max_amount=float('inf'),
        fee=0.00, tax_rate=0.15,
        description="Cash withdrawal (no fee)"
    ),
    
    # Standing orders
    TariffEntry(
        transaction_type=TransactionType.STANDING_ORDER,
        min_amount=0, max_amount=float('inf'),
        fee=15.00, tax_rate=0.15,
        description="Standing order execution"
    ),
    
    # Salary payments
    TariffEntry(
        transaction_type=TransactionType.SALARY_PAYMENT,
        min_amount=0, max_amount=float('inf'),
        fee=10.00, tax_rate=0.15,
        description="Salary payment processing"
    ),
    
    # Draft issuance
    TariffEntry(
        transaction_type=TransactionType.DRAFT_ISSUANCE,
        min_amount=0, max_amount=50000,
        fee=50.00, tax_rate=0.15,
        description="Bank draft issuance (up to 50,000)"
    ),
    TariffEntry(
        transaction_type=TransactionType.DRAFT_ISSUANCE,
        min_amount=50001, max_amount=float('inf'),
        fee=100.00, tax_rate=0.15,
        description="Bank draft issuance (above 50,000)"
    ),
    
    # Balance certificate
    TariffEntry(
        transaction_type=TransactionType.BALANCE_CERTIFICATE,
        min_amount=0, max_amount=float('inf'),
        fee=100.00, tax_rate=0.15,
        description="Balance certificate"
    ),
    
    # Statement request
    TariffEntry(
        transaction_type=TransactionType.STATEMENT_REQUEST,
        min_amount=0, max_amount=float('inf'),
        fee=25.00, tax_rate=0.15,
        description="Statement request"
    ),
    
    # FX transfers
    TariffEntry(
        transaction_type=TransactionType.FX_TRANSFER,
        min_amount=0, max_amount=float('inf'),
        fee=200.00, tax_rate=0.15,
        description="Foreign exchange transfer"
    ),
]


class TariffDatabase:
    """
    Look up fees from known tariff schedules.
    
    Used for fee pattern 4: "Deducted but not itemized"
    When the bank deducts a fee but doesn't describe it,
    we estimate from this database.
    
    Usage:
        db = TariffDatabase()
        result = db.lookup(TransactionType.TRANSFER_INTERNAL, 100000)
        if result:
            print(f"Fee: {result.fee}, Tax: {result.fee * result.tax_rate}")
    """
    
    def __init__(self, bank: str = "cbe"):
        self.bank = bank.lower()
        self.tariffs = self._load_tariffs()
    
    def _load_tariffs(self) -> List[TariffEntry]:
        """Load tariffs for the specified bank"""
        # For now, all banks use CBE tariffs
        # TODO: Add bank-specific tariff databases
        return CBE_TARIFFS
    
    def lookup(
        self, 
        transaction_type: TransactionType, 
        amount: float
    ) -> Optional[TariffEntry]:
        """
        Look up the fee for a transaction type and amount.
        
        Returns the matching TariffEntry or None if not found.
        """
        for tariff in self.tariffs:
            if tariff.transaction_type == transaction_type:
                if tariff.min_amount <= amount <= tariff.max_amount:
                    return tariff
        
        return None
    
    def estimate_fee(
        self, 
        transaction_type: TransactionType, 
        amount: float
    ) -> Dict[str, float]:
        """
        Estimate the fee and tax for a transaction.
        
        Returns dict with fee, tax, and total, or zeros if not found.
        """
        tariff = self.lookup(transaction_type, amount)
        
        if tariff:
            tax = tariff.fee * tariff.tax_rate
            return {
                "fee": tariff.fee,
                "tax": tax,
                "total": tariff.fee + tax,
                "description": tariff.description,
            }
        
        return {
            "fee": 0.0,
            "tax": 0.0,
            "total": 0.0,
            "description": "Unknown transaction type",
        }
    
    def detect_transaction_type(self, description: str, reference: str = "") -> Optional[TransactionType]:
        """
        Detect transaction type from description and reference.
        
        Used to automatically look up the right tariff.
        """
        text = f"{description} {reference}".upper()
        
        # Check for known patterns
        if "TRANSFER" in text and ("DASHEN" in text or "AWASH" in text or "ECOBANK" in text):
            return TransactionType.TRANSFER_INTERBANK
        elif "TRANSFER" in text:
            return TransactionType.TRANSFER_INTERNAL
        elif "CHQ" in text or "CHEQUE" in text:
            return TransactionType.CHEQUE_ISSUED
        elif "SALARY" in text:
            return TransactionType.SALARY_PAYMENT
        elif "STANDING ORDER" in text or "SO-" in text:
            return TransactionType.STANDING_ORDER
        elif "DRAFT" in text:
            return TransactionType.DRAFT_ISSUANCE
        elif "CERTIFICATE" in text:
            return TransactionType.BALANCE_CERTIFICATE
        elif "STATEMENT" in text:
            return TransactionType.STATEMENT_REQUEST
        elif "FX" in text or "FOREIGN" in text:
            return TransactionType.FX_TRANSFER
        
        return None
    
    def get_all_tariffs(self) -> List[Dict]:
        """Get all tariffs as list of dicts (for API/UI)"""
        return [
            {
                "type": t.transaction_type.value,
                "min_amount": t.min_amount,
                "max_amount": t.max_amount if t.max_amount != float('inf') else None,
                "fee": t.fee,
                "tax_rate": t.tax_rate,
                "description": t.description,
            }
            for t in self.tariffs
        ]
