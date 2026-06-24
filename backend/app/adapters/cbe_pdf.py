"""
CBE PDF Adapter — Parse Commercial Bank of Ethiopia PDF statements.

CBE has 4 account types with different PDF layouts:
1. Saving Account:  Balances | Credit | Debit | Value Date | Narrative | Reference | Particulars | Date
2. Current Account: Date | Particulars | Reference | Narrative | Value Date | Debit | Credit | Balances
3. Current with Overdraft: Same as Current, allows negative balances
4. Time Deposit: Fixed-term, skip for now

This adapter:
1. Auto-detects account type from PDF content
2. Extracts transactions from the correct column layout
3. Handles Ethiopian calendar dates
4. Extracts reference codes (FT, CHQ, CD, CPO, ECS, PKR, VPCH)
5. Verifies balance before returning results
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import date
from enum import Enum

from app.engine.pdf_extractor import PDFExtractor, PDFExtractionResult, ExtractedTable
from app.engine.balance_verifier import BalanceVerifier, Transaction, VerificationResult
from app.engine.ethiopian_calendar import (
    parse_cbe_date, classify_reference_code, extract_cheque_number,
    REFERENCE_CODES
)
from app.engine.fee_extractor import FeeExtractor


class CBEAccountType(str, Enum):
    """CBE account types with different PDF layouts"""
    SAVINGS = "savings"
    CURRENT = "current"
    CURRENT_OVERDRAFT = "current_overdraft"
    TIME_DEPOSIT = "time_deposit"
    UNKNOWN = "unknown"


@dataclass
class CBETransaction:
    """Parsed CBE transaction with all extracted fields"""
    # Core fields
    date: date
    value_date: Optional[date]
    narrative: str
    particulars: str
    reference: str
    
    # Amounts
    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None
    
    # Derived fields
    transaction_type: Optional[str] = None  # From reference code
    reference_code: Optional[str] = None    # FT, CHQ, CD, etc.
    cheque_number: Optional[str] = None     # If CHQ reference
    
    # Fee extraction
    fee_amount: float = 0.0
    bank_charge: float = 0.0
    gov_tax: float = 0.0
    gross_amount: float = 0.0
    net_amount: float = 0.0
    
    # Metadata
    row_index: int = 0
    raw_row: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "date": str(self.date),
            "value_date": str(self.value_date) if self.value_date else None,
            "narrative": self.narrative,
            "particulars": self.particulars,
            "reference": self.reference,
            "debit": self.debit,
            "credit": self.credit,
            "balance": self.balance,
            "transaction_type": self.transaction_type,
            "reference_code": self.reference_code,
            "cheque_number": self.cheque_number,
            "fee_amount": self.fee_amount,
            "bank_charge": self.bank_charge,
            "gov_tax": self.gov_tax,
            "gross_amount": self.gross_amount,
            "net_amount": self.net_amount,
        }


@dataclass
class CBEParseResult:
    """Result of parsing a CBE PDF statement"""
    account_type: CBEAccountType
    account_number: Optional[str]
    account_name: Optional[str]
    statement_period: Optional[str]
    opening_balance: Optional[float]
    closing_balance: Optional[float]
    transactions: List[CBETransaction]
    verification: VerificationResult
    extraction_details: dict
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CBEPDFAdapter:
    """
    Parse CBE PDF bank statements.
    
    Usage:
        adapter = CBEPDFAdapter()
        result = adapter.parse("cbe_statement.pdf")
        
        if result.verification.status == "passed":
            for txn in result.transactions:
                print(f"{txn.date} {txn.narrative} {txn.debit} {txn.credit}")
        else:
            print(result.verification.message)
    """
    
    # Header/footer patterns for balance extraction
    PATTERNS = {
        # Account info
        "account_number": r'(?:Account\s*(?:No|Number|#))\s*[:.]?\s*(\d{10,})',
        "account_name": r'(?:Account\s*Name)\s*[:.]?\s*([A-Za-z\s&]+)',
        
        # Balance patterns
        "opening_balance": r'(?:Opening\s*Balance|B/F|Balance\s*b/f|BF)\s*[:.]?\s*([\d,]+\.?\d*)',
        "closing_balance": r'(?:Closing\s*Balance|C/F|Balance\s*c/f|CF|Carried\s*Forward)\s*[:.]?\s*([\d,]+\.?\d*)',
        
        # Period
        "period_from": r'(?:From|Period\s*From)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        "period_to": r'(?:To|Period\s*To)\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        
        # Statement type detection
        "savings_hint": r'(?:Saving|Savings)\s*Account',
        "current_hint": r'(?:Current)\s*Account',
        "overdraft_hint": r'(?:Overdraft|OD)',
    }
    
    # Column layouts for each account type
    # Order matters — we match columns by header text
    COLUMN_LAYOUTS = {
        CBEAccountType.SAVINGS: {
            "date": ["Date"],
            "value_date": ["Value Date", "ValueDate", "Val Date"],
            "particulars": ["Particulars", "Particular"],
            "reference": ["Reference", "Ref", "Ref No"],
            "narrative": ["Narrative", "Narration", "Description", "Details"],
            "debit": ["Debit", "Debit Amount", "Withdrawal", "Dr"],
            "credit": ["Credit", "Credit Amount", "Deposit", "Cr"],
            "balance": ["Balances", "Balance", "Running Balance", "Bal"],
        },
        CBEAccountType.CURRENT: {
            "date": ["Date"],
            "particulars": ["Particulars", "Particular"],
            "reference": ["Reference", "Ref", "Ref No"],
            "narrative": ["Narrative", "Narration", "Description", "Details"],
            "value_date": ["Value Date", "ValueDate", "Val Date"],
            "debit": ["Debit", "Debit Amount", "Withdrawal", "Dr"],
            "credit": ["Credit", "Credit Amount", "Deposit", "Cr"],
            "balance": ["Balances", "Balance", "Running Balance", "Bal"],
        },
    }
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.balance_verifier = BalanceVerifier()
        self.fee_extractor = FeeExtractor()
    
    def parse(self, pdf_source, filename: str = "") -> CBEParseResult:
        """
        Parse a CBE PDF statement.
        
        Args:
            pdf_source: File path or file-like object
            filename: Original filename
        
        Returns:
            CBEParseResult with transactions and verification
        """
        errors = []
        warnings = []
        
        # Step 1: Extract text and tables from PDF
        extraction = self.pdf_extractor.extract(pdf_source, filename)
        
        if extraction.extraction_method.value == "failed":
            return CBEParseResult(
                account_type=CBEAccountType.UNKNOWN,
                account_number=None,
                account_name=None,
                statement_period=None,
                opening_balance=None,
                closing_balance=None,
                transactions=[],
                verification=VerificationResult(
                    status="failed", opening_balance=0, closing_balance=0,
                    calculated_closing=0, total_credits=0, total_debits=0,
                    transaction_count=0, difference=0,
                    message="Failed to extract content from PDF.",
                    details={"errors": extraction.errors}
                ),
                extraction_details={"method": "failed", "errors": extraction.errors},
                errors=extraction.errors
            )
        
        # Step 2: Detect account type
        account_type = self._detect_account_type(extraction.full_text)
        
        # Step 3: Extract account metadata
        account_number = self._extract_pattern("account_number", extraction.full_text)
        account_name = self._extract_pattern("account_name", extraction.full_text)
        period_from = self._extract_pattern("period_from", extraction.full_text)
        period_to = self._extract_pattern("period_to", extraction.full_text)
        statement_period = f"{period_from} to {period_to}" if period_from and period_to else None
        
        # Step 4: Extract opening/closing balances
        opening_balance = self._extract_balance("opening_balance", extraction.full_text)
        closing_balance = self._extract_balance("closing_balance", extraction.full_text)
        
        # Step 5: Parse transactions from tables
        transactions = self._parse_transactions(extraction, account_type)
        
        if not transactions:
            errors.append("No transactions found in PDF.")
            return CBEParseResult(
                account_type=account_type,
                account_number=account_number,
                account_name=account_name,
                statement_period=statement_period,
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                transactions=[],
                verification=VerificationResult(
                    status="failed", opening_balance=0, closing_balance=0,
                    calculated_closing=0, total_credits=0, total_debits=0,
                    transaction_count=0, difference=0,
                    message="No transactions found in PDF."
                ),
                extraction_details={"method": extraction.extraction_method.value},
                errors=errors
            )
        
        # Step 6: Extract fees from transaction descriptions
        for txn in transactions:
            self._extract_fees(txn)
        
        # Step 7: Verify balances
        verification = self.balance_verifier.verify(
            [Transaction(
                date=str(t.date), description=t.narrative,
                debit=t.debit, credit=t.credit, balance=t.balance
            ) for t in transactions],
            opening_balance=opening_balance,
            closing_balance=closing_balance
        )
        
        return CBEParseResult(
            account_type=account_type,
            account_number=account_number,
            account_name=account_name,
            statement_period=statement_period,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            transactions=transactions,
            verification=verification,
            extraction_details={
                "method": extraction.extraction_method.value,
                "pdf_type": extraction.pdf_type.value,
                "total_pages": extraction.total_pages,
                "tables_found": sum(len(p.tables) for p in extraction.pages),
                "transactions_parsed": len(transactions),
            },
            errors=errors,
            warnings=warnings
        )
    
    def _detect_account_type(self, text: str) -> CBEAccountType:
        """Auto-detect CBE account type from PDF content"""
        text_upper = text.upper()
        
        if re.search(self.PATTERNS["savings_hint"], text_upper):
            return CBEAccountType.SAVINGS
        elif re.search(self.PATTERNS["overdraft_hint"], text_upper):
            return CBEAccountType.CURRENT_OVERDRAFT
        elif re.search(self.PATTERNS["current_hint"], text_upper):
            return CBEAccountType.CURRENT
        else:
            # Try to detect from column layout
            # Savings has: Balances | Credit | Debit | Value Date
            # Current has: Date | Particulars | Debit | Credit | Balances
            if "VALUE DATE" in text_upper and "BALANCES" in text_upper:
                # Check column order — Savings has Balance first
                balance_pos = text_upper.find("BALANCES")
                credit_pos = text_upper.find("CREDIT")
                if balance_pos < credit_pos:
                    return CBEAccountType.SAVINGS
            
            return CBEAccountType.CURRENT  # Default to Current
    
    def _extract_pattern(self, pattern_name: str, text: str) -> Optional[str]:
        """Extract a pattern from text"""
        pattern = self.PATTERNS.get(pattern_name)
        if not pattern:
            return None
        
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_balance(self, pattern_name: str, text: str) -> Optional[float]:
        """Extract a balance value from text"""
        value = self._extract_pattern(pattern_name, text)
        if value:
            try:
                return float(value.replace(",", ""))
            except ValueError:
                return None
        return None
    
    def _parse_transactions(
        self, extraction: PDFExtractionResult, account_type: CBEAccountType
    ) -> List[CBETransaction]:
        """Parse transactions from extracted tables"""
        transactions = []
        
        for page in extraction.pages:
            for table in page.tables:
                txns = self._parse_table(table, account_type)
                transactions.extend(txns)
        
        # If no transactions from tables, try text parsing
        if not transactions:
            transactions = self._parse_from_text(extraction.full_text, account_type)
        
        # Sort by date
        transactions.sort(key=lambda t: t.date)
        
        # Assign row indices
        for i, txn in enumerate(transactions):
            txn.row_index = i + 1
        
        return transactions
    
    def _parse_table(
        self, table: ExtractedTable, account_type: CBEAccountType
    ) -> List[CBETransaction]:
        """Parse transactions from a single table"""
        if not table.headers or not table.rows:
            return []
        
        # Map headers to field names
        layout = self.COLUMN_LAYOUTS.get(account_type, self.COLUMN_LAYOUTS[CBEAccountType.CURRENT])
        column_map = self._map_columns(table.headers, layout)
        
        if not column_map:
            return []
        
        transactions = []
        
        for row in table.rows:
            txn = self._parse_row(row, column_map, table.headers)
            if txn:
                transactions.append(txn)
        
        return transactions
    
    def _map_columns(
        self, headers: List[str], layout: Dict[str, List[str]]
    ) -> Dict[str, int]:
        """Map PDF column headers to field indices"""
        column_map = {}
        
        # Normalize headers for matching
        normalized_headers = [h.upper().strip() for h in headers]
        
        for field_name, possible_names in layout.items():
            for name in possible_names:
                name_upper = name.upper()
                for i, header in enumerate(normalized_headers):
                    if name_upper in header or header in name_upper:
                        column_map[field_name] = i
                        break
                if field_name in column_map:
                    break
        
        return column_map
    
    def _parse_row(
        self, row: List[str], column_map: Dict[str, int], headers: List[str]
    ) -> Optional[CBETransaction]:
        """Parse a single table row into a CBETransaction"""
        def get_value(field: str) -> str:
            idx = column_map.get(field)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return ""
        
        def parse_amount(text: str) -> float:
            """Parse amount from text, handling commas and whitespace"""
            if not text:
                return 0.0
            text = text.strip().replace(",", "").replace(" ", "")
            try:
                return float(text)
            except ValueError:
                return 0.0
        
        # Get date
        date_str = get_value("date")
        if not date_str:
            return None
        
        txn_date = parse_cbe_date(date_str)
        if not txn_date:
            return None
        
        # Get value date
        value_date_str = get_value("value_date")
        value_date = parse_cbe_date(value_date_str) if value_date_str else None
        
        # Get text fields
        narrative = get_value("narrative")
        particulars = get_value("particulars")
        reference = get_value("reference")
        
        # Get amounts
        debit = parse_amount(get_value("debit"))
        credit = parse_amount(get_value("credit"))
        balance = parse_amount(get_value("balance"))
        if balance == 0 and not get_value("balance"):
            balance = None
        
        # Skip rows with no amount
        if debit == 0 and credit == 0:
            return None
        
        # Classify reference code
        ref_code, ref_desc = classify_reference_code(reference)
        cheque_num = extract_cheque_number(reference, narrative)
        
        # Combine narrative and particulars for description
        description = narrative or particulars
        
        return CBETransaction(
            date=txn_date,
            value_date=value_date,
            narrative=narrative,
            particulars=particulars,
            reference=reference,
            debit=debit,
            credit=credit,
            balance=balance,
            transaction_type=ref_desc,
            reference_code=ref_code,
            cheque_number=cheque_num,
            raw_row=row,
        )
    
    def _parse_from_text(
        self, text: str, account_type: CBEAccountType
    ) -> List[CBETransaction]:
        """
        Fallback: Parse transactions from raw text when table extraction fails.
        
        Looks for patterns like:
        15/06/2026  TRANSFER TO ABC  FT-2026-001  100,040.00
        """
        transactions = []
        
        # Pattern: date at start of line, followed by text, then amounts
        # This is a rough heuristic for when table extraction fails
        date_pattern = r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})'
        amount_pattern = r'([\d,]+\.?\d*)'
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for lines starting with a date
            date_match = re.match(date_pattern, line)
            if not date_match:
                continue
            
            date_str = date_match.group(1)
            txn_date = parse_cbe_date(date_str)
            if not txn_date:
                continue
            
            # Extract amounts from the line
            amounts = re.findall(amount_pattern, line)
            if len(amounts) < 2:  # Need at least date + one amount
                continue
            
            # Try to identify debit, credit, balance
            # This is heuristic — amounts after the date
            amount_values = []
            for amt_str in amounts[1:]:  # Skip the date
                try:
                    amount_values.append(float(amt_str.replace(",", "")))
                except ValueError:
                    continue
            
            if not amount_values:
                continue
            
            # Extract narrative (text between date and first amount)
            narrative_start = line.find(date_str) + len(date_str)
            first_amount_pos = len(line)
            for amt in amounts[1:]:
                pos = line.find(amt, narrative_start)
                if pos != -1:
                    first_amount_pos = min(first_amount_pos, pos)
                    break
            
            narrative = line[narrative_start:first_amount_pos].strip()
            
            # Guess debit/credit/balance from position
            debit = 0.0
            credit = 0.0
            balance = None
            
            if len(amount_values) >= 3:
                # debit, credit, balance
                debit = amount_values[0]
                credit = amount_values[1]
                balance = amount_values[2]
            elif len(amount_values) == 2:
                # Could be amount + balance
                if account_type == CBEAccountType.SAVINGS:
                    # Savings: Credit, Debit, Balance
                    credit = amount_values[0]
                    balance = amount_values[1]
                else:
                    debit = amount_values[0]
                    balance = amount_values[1]
            elif len(amount_values) == 1:
                debit = amount_values[0]
            
            ref_code, ref_desc = classify_reference_code(narrative)
            
            transactions.append(CBETransaction(
                date=txn_date,
                value_date=None,
                narrative=narrative,
                particulars="",
                reference="",
                debit=debit,
                credit=credit,
                balance=balance,
                transaction_type=ref_desc,
                reference_code=ref_code,
            ))
        
        return transactions
    
    def _extract_fees(self, txn: CBETransaction):
        """Extract fees from transaction narrative"""
        description = txn.narrative or txn.particulars
        amount = txn.debit if txn.debit > 0 else txn.credit
        
        if not description or amount == 0:
            return
        
        result = self.fee_extractor.extract_from_text(description, abs(amount))
        
        txn.fee_amount = result.total_fees
        txn.bank_charge = result.bank_charge
        txn.gov_tax = result.gov_tax
        txn.gross_amount = result.gross_amount
        txn.net_amount = result.net_amount
