"""
CBE Adapter with Fee Extraction — Updated

Integrates FeeExtractor to handle three fee scenarios:
1. Embedded in description (CBE common format)
2. Separate columns (some exports)
3. Separate rows (when bank posts fees as own lines)
"""
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

from app.adapters import CBEAdapter
from app.engine.fee_extractor import FeeExtractor, FeeExtractionResult


class CBEAdapterWithFees(CBEAdapter):
    """
    Enhanced CBE adapter that extracts fees from transactions.
    
    Usage:
        adapter = CBEAdapterWithFees()
        df = adapter.parse("cbe_statement.csv")
        # df now has: fee_amount, fee_type, gross_amount, net_amount columns
    """
    
    def __init__(self):
        super().__init__()
        self.fee_extractor = FeeExtractor()
    
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Override normalize to add fee extraction"""
        
        # First, do standard normalization
        normalized = super().normalize(df)
        
        # Then extract fees
        normalized = self._extract_fees(normalized)
        
        return normalized
    
    def _extract_fees(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract fees from all transactions"""
        
        fee_amounts = []
        fee_types = []
        gross_amounts = []
        net_amounts = []
        fee_details = []
        
        for idx, row in df.iterrows():
            description = str(row.get("description", ""))
            amount = abs(float(row.get("amount", 0)))
            
            # Try to extract fees from description
            result = self.fee_extractor.extract_from_text(description, amount)
            
            fee_amounts.append(result.total_fees)
            fee_types.append(self._get_fee_type_label(result))
            gross_amounts.append(result.gross_amount)
            net_amounts.append(result.net_amount)
            fee_details.append({
                "bank_charge": result.bank_charge,
                "gov_tax": result.gov_tax,
                "extraction_method": result.extraction_method,
                "confidence": result.confidence,
                "needs_review": result.needs_review
            })
        
        # Add fee columns
        df["fee_amount"] = fee_amounts
        df["fee_type"] = fee_types
        df["gross_amount"] = gross_amounts
        df["net_amount"] = net_amounts
        df["fee_details"] = fee_details
        
        return df
    
    def _get_fee_type_label(self, result: FeeExtractionResult) -> str:
        """Get human-readable fee type label"""
        if result.total_fees == 0:
            return "none"
        
        has_charge = result.bank_charge > 0
        has_tax = result.gov_tax > 0
        
        if has_charge and has_tax:
            return "charge+tax"
        elif has_charge:
            return "charge_only"
        elif has_tax:
            return "tax_only"
        else:
            return "unknown"
    
    def get_fee_summary(self, df: pd.DataFrame) -> dict:
        """Generate fee summary for reporting"""
        
        total_gross = df["gross_amount"].sum()
        total_fees = df["fee_amount"].sum()
        total_net = df["net_amount"].sum()
        
        # Count by fee type
        fee_type_counts = df["fee_type"].value_counts().to_dict()
        
        # Count transactions needing review
        needs_review = sum(
            1 for details in df["fee_details"] 
            if details.get("needs_review", False)
        )
        
        return {
            "total_transactions": len(df),
            "total_gross_amount": total_gross,
            "total_fees": total_fees,
            "total_net_amount": total_net,
            "fee_percentage": (total_fees / total_gross * 100) if total_gross > 0 else 0,
            "fee_type_breakdown": fee_type_counts,
            "needs_review": needs_review,
            "extraction_methods": df["fee_details"].apply(
                lambda x: x.get("extraction_method", "unknown")
            ).value_counts().to_dict()
        }


class DashenAdapterWithFees(CBEAdapterWithFees):
    """
    Dashen adapter with fee extraction.
    Dashen typically posts fees as separate line items.
    """
    
    def _extract_fees(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Override to handle Dashen's separate fee rows.
        Groups fee rows with their parent transaction.
        """
        
        fee_amounts = []
        fee_types = []
        gross_amounts = []
        net_amounts = []
        fee_details = []
        
        # First pass: identify fee rows vs main transactions
        fee_keywords = ["SERVICE CHARGE", "TRANSFER FEE", "STAMP DUTY", 
                       "COMMISSION", "BANK FEE", "CHARGE"]
        
        is_fee_row = df["description"].str.upper().apply(
            lambda x: any(kw in str(x) for kw in fee_keywords)
        )
        
        # For now, treat all rows independently
        # TODO: Group fee rows with parent transaction
        for idx, row in df.iterrows():
            description = str(row.get("description", ""))
            amount = abs(float(row.get("amount", 0)))
            
            if is_fee_row[idx]:
                # This is a fee row itself
                result = self.fee_extractor.extract_from_text(description, amount)
                fee_amounts.append(amount)
                fee_types.append("fee_row")
                gross_amounts.append(0)  # Fee rows have no gross
                net_amounts.append(amount)
                fee_details.append({
                    "bank_charge": amount,
                    "gov_tax": 0,
                    "extraction_method": "separate_row",
                    "confidence": 0.9,
                    "needs_review": False
                })
            else:
                # Main transaction - check for embedded fees
                result = self.fee_extractor.extract_from_text(description, amount)
                fee_amounts.append(result.total_fees)
                fee_types.append(self._get_fee_type_label(result))
                gross_amounts.append(result.gross_amount)
                net_amounts.append(result.net_amount)
                fee_details.append({
                    "bank_charge": result.bank_charge,
                    "gov_tax": result.gov_tax,
                    "extraction_method": result.extraction_method,
                    "confidence": result.confidence,
                    "needs_review": result.needs_review
                })
        
        df["fee_amount"] = fee_amounts
        df["fee_type"] = fee_types
        df["gross_amount"] = gross_amounts
        df["net_amount"] = net_amounts
        df["fee_details"] = fee_details
        
        return df


def get_adapter_for_bank(bank_name: str):
    """Factory function to get the right adapter with fee extraction"""
    
    adapters = {
        "cbe": CBEAdapterWithFees,
        "dashen": DashenAdapterWithFees,
        # Add more as needed
    }
    
    adapter_class = adapters.get(bank_name.lower(), CBEAdapterWithFees)
    return adapter_class()
