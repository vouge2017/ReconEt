"""
Awash Bank PDF Adapter — ReconET (Stub)

Awash Bank is Ethiopia's largest private bank by assets.
This adapter handles their PDF statement format.

Status: STUB — needs real Awash statement samples to implement.
Priority: Medium (after CBE is validated with real users)

Awash statement format (to be confirmed with samples):
- Likely uses standard PDF encoding (not DEVEXP+ like CBE)
- May use Amharic column headers
- Column layout unknown — need real samples
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class AwashTransaction:
    """Parsed Awash Bank transaction"""
    date: date
    value_date: Optional[date]
    description: str
    reference: str
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None
    fee_amount: float = 0.0
    bank_charge: float = 0.0
    gov_tax: float = 0.0
    row_index: int = 0


@dataclass
class AwashParseResult:
    """Result of parsing an Awash Bank PDF"""
    account_number: Optional[str]
    account_name: Optional[str]
    statement_period: Optional[str]
    opening_balance: Optional[float]
    closing_balance: Optional[float]
    transactions: List[AwashTransaction]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "stub"  # stub until real samples are analyzed


class AwashPDFAdapter:
    """
    Parse Awash Bank PDF statements.
    
    Status: STUB — awaiting real statement samples.
    
    To implement:
    1. Get 3+ real Awash PDF statements
    2. Analyze column layout and encoding
    3. Build parser (likely pdfplumber-based, not CMap)
    4. Add fee extraction patterns specific to Awash
    5. Add balance verification
    
    Usage (future):
        adapter = AwashPDFAdapter()
        result = adapter.parse("awash_statement.pdf")
    """
    
    BANK_NAME = "Awash Bank"
    
    def parse(self, pdf_source, filename: str = "") -> AwashParseResult:
        """
        Parse an Awash Bank PDF statement.
        
        Currently returns stub result — needs real samples.
        """
        return AwashParseResult(
            account_number=None,
            account_name=None,
            statement_period=None,
            opening_balance=None,
            closing_balance=None,
            transactions=[],
            errors=[
                "Awash Bank adapter is a stub. Need real statement samples to implement.",
                "Please provide 3+ Awash Bank PDF statements (savings and current accounts).",
            ],
            warnings=["This adapter will be implemented once real samples are analyzed."],
            status="stub"
        )
    
    @staticmethod
    def detect_bank(text: str) -> bool:
        """Check if PDF content is from Awash Bank"""
        text_upper = text.upper()
        return any(kw in text_upper for kw in [
            "AWASH BANK", "AWASH BANK S.C", "AWASH INTERNATIONAL BANK"
        ])
