"""
Fee Extraction Engine — Core Module
"""
import re
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class FeeType(str, Enum):
    BANK_CHARGE = "bank_charge"
    GOV_TAX = "gov_tax"
    STAMP_DUTY = "stamp_duty"
    TRANSFER_FEE = "transfer_fee"
    CHEQUE_FEE = "cheque_fee"
    FX_COMMISSION = "fx_commission"
    UNKNOWN = "unknown"


@dataclass
class ExtractedFee:
    fee_type: FeeType
    amount: float
    raw_text: str
    confidence: float


@dataclass
class FeeExtractionResult:
    gross_amount: float
    bank_charge: float
    gov_tax: float
    total_fees: float
    net_amount: float
    fee_breakdown: List[ExtractedFee]
    extraction_method: str
    confidence: float
    needs_review: bool


class FeeExtractor:
    """Extract fees from Ethiopian bank transaction descriptions"""
    
    CBE_FEE_PATTERNS = [
        # Combined pattern first (most specific — catches FEE 25 TAX 15)
        (r'(?:FEE|CHG|CHARGE)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:TAX|VAT)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
         None, 0.95),
        # Individual patterns (only match if combined didn't)
        (r'(?:FEE|CHARGE|COMM(?:ISSION)?)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
         FeeType.BANK_CHARGE, 0.9),
        (r'(?:TAX|VAT|GOV\s*TAX)\s*[:=]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
         FeeType.GOV_TAX, 0.9),
    ]
    
    def extract_from_text(self, description: str, amount: float) -> FeeExtractionResult:
        if not description:
            return self._no_fee_result(amount)
        
        description = description.upper().strip()
        fees_found = []
        combined_matched = False
        
        for pattern, fee_type, confidence in self.CBE_FEE_PATTERNS:
            # Skip individual patterns if combined already matched
            if combined_matched and fee_type is not None:
                continue
            
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if fee_type is None and len(groups) == 2:
                    # Combined pattern matched
                    combined_matched = True
                    fee_amount = self._parse_amount(groups[0])
                    tax_amount = self._parse_amount(groups[1])
                    
                    if fee_amount > 0:
                        fees_found.append(ExtractedFee(
                            fee_type=FeeType.BANK_CHARGE,
                            amount=fee_amount,
                            raw_text=match.group(0),
                            confidence=confidence
                        ))
                    if tax_amount > 0:
                        fees_found.append(ExtractedFee(
                            fee_type=FeeType.GOV_TAX,
                            amount=tax_amount,
                            raw_text=match.group(0),
                            confidence=confidence
                        ))
                elif len(groups) >= 1:
                    fee_amount = self._parse_amount(groups[0])
                    if fee_amount > 0:
                        fees_found.append(ExtractedFee(
                            fee_type=fee_type or FeeType.UNKNOWN,
                            amount=fee_amount,
                            raw_text=match.group(0),
                            confidence=confidence
                        ))
        
        bank_charge = sum(f.amount for f in fees_found if f.fee_type in 
                         [FeeType.BANK_CHARGE, FeeType.TRANSFER_FEE, FeeType.CHEQUE_FEE])
        gov_tax = sum(f.amount for f in fees_found if f.fee_type == FeeType.GOV_TAX)
        total_fees = bank_charge + gov_tax
        
        if fees_found:
            avg_confidence = sum(f.confidence for f in fees_found) / len(fees_found)
            method = "embedded_text"
        else:
            avg_confidence = 0.0
            method = "none"
        
        gross_amount = amount
        net_amount = amount
        
        return FeeExtractionResult(
            gross_amount=gross_amount,
            bank_charge=bank_charge,
            gov_tax=gov_tax,
            total_fees=total_fees,
            net_amount=net_amount,
            fee_breakdown=fees_found,
            extraction_method=method,
            confidence=avg_confidence,
            needs_review=avg_confidence < 0.8 if fees_found else False
        )
    
    def _parse_amount(self, text: str) -> float:
        if not text:
            return 0.0
        try:
            return float(text.replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0
    
    def _no_fee_result(self, amount: float) -> FeeExtractionResult:
        return FeeExtractionResult(
            gross_amount=amount,
            bank_charge=0.0,
            gov_tax=0.0,
            total_fees=0.0,
            net_amount=amount,
            fee_breakdown=[],
            extraction_method="none",
            confidence=0.0,
            needs_review=False
        )


def format_fee_summary(results: List[FeeExtractionResult]) -> dict:
    """Format a list of fee extraction results into a summary dict"""
    total_gross = sum(r.gross_amount for r in results)
    total_bank_charges = sum(r.bank_charge for r in results)
    total_gov_tax = sum(r.gov_tax for r in results)
    total_fees = sum(r.total_fees for r in results)
    needs_review = sum(1 for r in results if r.needs_review)

    # Group by extraction method
    by_method = {}
    for r in results:
        method = r.extraction_method
        if method not in by_method:
            by_method[method] = {"count": 0, "total_fees": 0.0}
        by_method[method]["count"] += 1
        by_method[method]["total_fees"] += r.total_fees

    return {
        "total_transactions": len(results),
        "total_gross_amount": total_gross,
        "total_bank_charges": total_bank_charges,
        "total_gov_tax": total_gov_tax,
        "total_fees": total_fees,
        "fee_percentage": (total_fees / total_gross * 100) if total_gross > 0 else 0,
        "needs_review": needs_review,
        "by_extraction_method": by_method
    }
