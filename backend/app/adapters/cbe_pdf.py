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

Extraction strategy (CBE-specific):
- PRIMARY: CMap-based extraction (for DEVEXP+ encoded PDFs)
- FALLBACK: pdfplumber / Tesseract OCR (for scanned or standard PDFs)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import date
from enum import Enum

from app.engine.pdf_extractor import PDFExtractor, PDFExtractionResult, ExtractedPage, ExtractedTable, ExtractionMethod, PDFType
from app.engine.cmap_extractor import CMapPDFExtractor, CMapExtractionResult
from app.engine.balance_verifier import BalanceVerifier, Transaction, VerificationResult, VerificationStatus
from app.engine.ethiopian_calendar import (
    parse_cbe_date, classify_reference_code, extract_cheque_number,
    BANK_REFERENCE_CODES
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
        "overdraft_hint": r'(?:Overdraft|\bOD\b)',
    }
    
    # Column layouts for each account type
    # Based on REAL CBE statement (user confirmed June 2026)
    # Actual columns: Date | Particulars | Reference | Narrative | Value Date | Debit | Credit | Balance
    COLUMN_LAYOUTS = {
        CBEAccountType.SAVINGS: {
            "date": ["Date"],
            "particulars": ["Particulars", "Particular"],
            "reference": ["Reference", "Ref", "Ref No", "Chq No/Ref"],
            "narrative": ["Narrative", "Narration", "Description", "Details"],
            "value_date": ["Value Date", "ValueDate", "Val Date"],
            "debit": ["Debit", "Debit Amount", "Withdrawal", "Dr"],
            "credit": ["Credit", "Credit Amount", "Deposit", "Cr"],
            "balance": ["Balance", "Balances", "Running Balance", "Bal"],
        },
        CBEAccountType.CURRENT: {
            "date": ["Date"],
            "particulars": ["Particulars", "Particular"],
            "reference": ["Reference", "Ref", "Ref No", "Chq No/Ref"],
            "narrative": ["Narrative", "Narration", "Description", "Details"],
            "value_date": ["Value Date", "ValueDate", "Val Date"],
            "debit": ["Debit", "Debit Amount", "Withdrawal", "Dr"],
            "credit": ["Credit", "Credit Amount", "Deposit", "Cr"],
            "balance": ["Balance", "Balances", "Running Balance", "Bal"],
        },
    }
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.cmap_extractor = CMapPDFExtractor()
        self.balance_verifier = BalanceVerifier()
        self.fee_extractor = FeeExtractor()
    
    def _extract_with_cmap_fallback(
        self, pdf_source, filename: str = ""
    ) -> PDFExtractionResult:
        """
        Extract text from CBE PDF using CMap decoding (primary),
        falling back to pdfplumber/Tesseract (for other banks or scanned PDFs).
        
        Returns:
            PDFExtractionResult compatible with existing parse() logic
        """
        # --- PRIMARY: CMap extraction ---
        try:
            cmap_result = self.cmap_extractor.extract(pdf_source)
            
            if cmap_result.success and cmap_result.full_text.strip():
                # Convert CMap result to PDFExtractionResult format
                pages = []
                for cmap_page in cmap_result.pages:
                    pages.append(ExtractedPage(
                        page_number=cmap_page.page_number,
                        text=cmap_page.full_text,
                        tables=[]  # CMap gives raw text, not tables
                    ))
                
                return PDFExtractionResult(
                    pages=pages,
                    total_pages=cmap_result.total_pages,
                    pdf_type=PDFType.TEXT_BASED,
                    extraction_method=ExtractionMethod.PDFPLUMBER,  # reuse enum
                    full_text=cmap_result.full_text,
                    metadata={
                        "cmap_fonts_decoded": cmap_result.fonts_decoded,
                        "extraction_path": "cmap"
                    }
                )
        except Exception as e:
            # CMap failed — fall through to standard extractor
            pass
        
        # --- FALLBACK: pdfplumber / Tesseract OCR ---
        return self.pdf_extractor.extract(pdf_source, filename)

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
        
        # Step 1: Extract text from PDF
        # Try CMap extraction first (handles CBE's DEVEXP+ encoded PDFs)
        # Falls back to pdfplumber/Tesseract if CMap fails
        extraction = self._extract_with_cmap_fallback(pdf_source, filename)
        
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
                    status=VerificationStatus.FAILED, opening_balance=0, closing_balance=0,
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
                    status=VerificationStatus.FAILED, opening_balance=0, closing_balance=0,
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
        
        # Pattern 3: Group fee rows with their parent transactions
        transactions = self._group_fee_rows(transactions)
        
        # Sort by date
        transactions.sort(key=lambda t: t.date)
        
        # Assign row indices
        for i, txn in enumerate(transactions):
            txn.row_index = i + 1
        
        return transactions
    
    def _group_fee_rows(self, transactions: List[CBETransaction]) -> List[CBETransaction]:
        """
        Fee Pattern 3: Group fee rows with their parent transactions.
        
        CBE sometimes shows fees as separate rows:
        15/06/2026  TRANSFER TO ABC    FT-001    100,000.00
        15/06/2026  SERVICE CHARGE     FEE-001        25.00
        
        This method detects fee rows and merges them into the parent.
        """
        if len(transactions) < 2:
            return transactions
        
        # Fee row keywords
        fee_keywords = [
            "SERVICE CHARGE", "BANK FEE", "TRANSFER FEE", "COMMISSION",
            "STAMP DUTY", "BANK CHARGE", "FEE", "CHARGE", "VAT",
        ]
        
        result = []
        i = 0
        while i < len(transactions):
            txn = transactions[i]
            
            # Check if this is a fee row
            is_fee_row = False
            if txn.debit > 0 and txn.credit == 0:
                desc_upper = (txn.narrative or txn.particulars or "").upper()
                ref_upper = (txn.reference or "").upper()
                for kw in fee_keywords:
                    if kw in desc_upper or kw in ref_upper:
                        is_fee_row = True
                        break
            
            if is_fee_row and len(result) > 0:
                # Merge with previous transaction
                parent = result[-1]
                parent.fee_amount += txn.debit
                # Guess if it's bank charge or tax (15% VAT)
                estimated_tax = txn.debit * 0.15 / 1.15
                estimated_charge = txn.debit - estimated_tax
                parent.bank_charge += estimated_charge
                parent.gov_tax += estimated_tax
                parent.gross_amount = parent.debit if parent.debit > 0 else parent.credit
                parent.net_amount = parent.gross_amount
                i += 1
                continue
            
            result.append(txn)
            i += 1
        
        return result
    
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
            # Handle dash or empty for no amount
            if text == "-" or text == "":
                return 0.0
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
        
        # Get text fields (actual CBE format: 8 columns)
        particulars = get_value("particulars")
        reference = get_value("reference")
        narrative = get_value("narrative")
        
        # Get amounts
        debit = parse_amount(get_value("debit"))
        credit = parse_amount(get_value("credit"))
        balance = parse_amount(get_value("balance"))
        if balance == 0 and not get_value("balance"):
            balance = None
        
        # Skip rows with no amount (header rows, empty rows)
        if debit == 0 and credit == 0:
            return None
        
        # Skip closing balance rows
        combined_text = f"{particulars} {narrative}".upper()
        if "CLOSING BALANCE" in combined_text or "OPENING BALANCE" in combined_text:
            return None
        
        # Classify reference code
        # FT = Fund Transfer (account to account)
        # TT = Cash transactions
        ref_code, ref_desc = classify_reference_code(reference, bank="cbe")
        cheque_num = extract_cheque_number(reference, narrative)
        
        # Combine particulars and narrative for full description
        description = f"{particulars} {narrative}".strip()
        
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
        Parse transactions from CMap-extracted text.
        
        CBE CMap text format (multi-line blocks):
            4,125.54          <- balance after txn
            .00               <- credit (0 if none)
            -1,002.00         <- debit (negative)
            01 01 2022        <- transaction date
            FT22001773M3      <- reference
            ATM Cash Withdrawal <- narrative
            01 01 2022        <- value date
        """
        transactions = []
        
        # Date pattern: DD MM YYYY or DD/MM/YYYY or DD-MM-YYYY
        date_re = re.compile(r'^(\d{1,2})[/\-\.\s](\d{1,2})[/\-\.\s](\d{4})$')
        # Amount pattern: number with optional commas, decimal, negative
        amount_re = re.compile(r'^[\-]?[\d,]+\.\d{2}$')
        # Just .00
        zero_re = re.compile(r'^\.00$')
        # Reference pattern: starts with FT, CHQ, CD, CPO, ECS, PKR, VPCH, TT
        ref_re = re.compile(r'^(FT|CHQ|CD|CPO|ECS|PKR|VPCH|TT)', re.IGNORECASE)
        # Balance B/F, Opening Balance, Closing Balance markers
        marker_re = re.compile(r'(Balance B/F|Opening Balance|Closing Balance|Statement)', re.IGNORECASE)
        # Account info lines
        info_re = re.compile(r'(Account|Currency|Account Type|From \d|NAEL|AHIMED|SARA|YOSEPH)', re.IGNORECASE)
        
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Find transaction blocks by looking for date lines
        # Then extract the 3 lines before (balance, credit, debit) and 2-3 lines after (ref, narrative, value_date)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line is a date
            if not date_re.match(line):
                i += 1
                continue
            
            txn_date = parse_cbe_date(line)
            if not txn_date:
                i += 1
                continue
            
            # Skip dates that are clearly not transaction dates
            # (e.g., dates in header/footer, dates before 2020 or after 2030)
            if txn_date.year < 2020 or txn_date.year > 2030:
                i += 1
                continue
            
            # Found a transaction date. Extract block.
            # Lines before date: [i-3]=balance, [i-2]=credit, [i-1]=debit
            # Lines after date: [i+1]=reference, [i+2]=narrative, [i+3]=value_date
            
            # Extract amounts from lines before date
            debit = 0.0
            credit = 0.0
            balance = None
            
            # Check 3 lines before the date for amounts
            for j in range(max(0, i - 3), i):
                amt_line = lines[j]
                
                if zero_re.match(amt_line):
                    continue
                
                if amount_re.match(amt_line):
                    val = float(amt_line.replace(",", ""))
                    
                    # Skip if it looks like a balance B/F or opening balance
                    if j > 0 and marker_re.match(lines[j - 1] if j > 0 else ""):
                        balance = val
                        continue
                    
                    # Negative = debit, positive = credit
                    if val < 0:
                        debit = abs(val)
                    elif val > 0:
                        if credit > 0:
                            # Second positive = balance
                            balance = val
                        else:
                            credit = val
            
            # Extract reference and narrative from lines after date
            reference = ""
            narrative = ""
            value_date = None
            
            # Look at lines after the date
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j]
                
                # Skip empty lines
                if not next_line:
                    continue
                
                # Check if it's a date (value date)
                if date_re.match(next_line):
                    value_date = parse_cbe_date(next_line)
                    break  # Value date is the last part of the block
                
                # Check if it's a reference
                if ref_re.match(next_line) and not reference:
                    reference = next_line
                    continue
                
                # Check if it's an amount (shouldn't be, but handle it)
                if amount_re.match(next_line) or zero_re.match(next_line):
                    break  # Next transaction block starting
                
                # Skip info lines
                if info_re.match(next_line):
                    continue
                
                # Otherwise it's narrative
                if not narrative:
                    narrative = next_line
                else:
                    # Multi-line narrative — append
                    narrative += " " + next_line
            
            # Skip if no amounts found (header/footer dates)
            if debit == 0 and credit == 0:
                i += 1
                continue
            
            # Clean up narrative
            narrative = narrative.strip()
            if len(narrative) > 100:
                narrative = narrative[:100]
            
            # Classify reference
            ref_code, ref_desc = classify_reference_code(reference or narrative, bank="cbe")
            
            transactions.append(CBETransaction(
                date=txn_date,
                value_date=value_date,
                narrative=narrative,
                particulars=reference,
                reference=reference,
                debit=debit,
                credit=credit,
                balance=balance,
                transaction_type=ref_desc,
                reference_code=ref_code,
            ))
            
            i += 1
        
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
