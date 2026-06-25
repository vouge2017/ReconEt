"""
Tests for Fee Extraction Engine

Tests the 4 fee patterns:
1. Embedded in description: "TRANSFER FEE 25 TAX 15"
2. Separate line item: "SERVICE CHARGE 25"
3. Separate row in table: Fee as own transaction row
4. Deducted but not itemized: Tariff database lookup
"""

import os
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.engine.fee_extractor import FeeExtractor, FeeType


@pytest.fixture
def extractor():
    return FeeExtractor(use_tariff_db=False)  # Disable tariff DB for unit tests


class TestFeePattern1_Embedded:
    """Test Pattern 1: Fees embedded in transaction description"""
    
    def test_fee_and_tax_combined(self, extractor):
        """TRANSFER FEE 25 TAX 15"""
        result = extractor.extract_from_text("TRANSFER FEE 25 TAX 15", 100040)
        assert result.bank_charge == 25.0
        assert result.gov_tax == 15.0
        assert result.total_fees == 40.0
    
    def test_fee_only(self, extractor):
        """SERVICE CHARGE 25"""
        result = extractor.extract_from_text("SERVICE CHARGE 25", 100025)
        assert result.bank_charge == 25.0
        assert result.gov_tax == 0.0
        assert result.total_fees == 25.0
    
    def test_commission(self, extractor):
        """COMMISSION 10"""
        result = extractor.extract_from_text("COMMISSION 10", 50010)
        assert result.bank_charge == 10.0
    
    def test_amount_with_commas(self, extractor):
        """FEE 1,000"""
        result = extractor.extract_from_text("FEE 1,000", 101000)
        assert result.bank_charge == 1000.0
    
    def test_no_fee_in_description(self, extractor):
        """ATM Cash Withdrawal — no fee text"""
        result = extractor.extract_from_text("ATM Cash Withdrawal", 1000)
        # Should return no-fee result (tariff DB disabled)
        assert result.total_fees == 0.0
    
    def test_empty_description(self, extractor):
        """Empty description"""
        result = extractor.extract_from_text("", 1000)
        assert result.total_fees == 0.0


class TestFeePattern2_SeparateLine:
    """Test Pattern 2: Fee as separate line item"""
    
    def test_service_charge(self, extractor):
        """SERVICE CHARGE 50"""
        result = extractor.extract_from_text("SERVICE CHARGE 50", 50)
        assert result.bank_charge == 50.0
    
    def test_bank_fee(self, extractor):
        """BANK FEE 25"""
        result = extractor.extract_from_text("BANK FEE 25", 25)
        assert result.bank_charge == 25.0
    
    def test_transfer_fee(self, extractor):
        """TRANSFER FEE 100"""
        result = extractor.extract_from_text("TRANSFER FEE 100", 100)
        assert result.bank_charge == 100.0


class TestFeeExtractionEdgeCases:
    """Test edge cases"""
    
    def test_zero_amount(self, extractor):
        """Zero amount transaction"""
        result = extractor.extract_from_text("FEE 25", 0)
        assert result.total_fees == 25.0  # Fee is still extracted
    
    def test_none_description(self, extractor):
        """None description"""
        result = extractor.extract_from_text(None, 1000)
        assert result.total_fees == 0.0
    
    def test_fee_in_atm_narrative(self, extractor):
        """ATM Cash Withdrawal — no fees in text"""
        result = extractor.extract_from_text("ATM Cash Withdrawal FT22001773M3", 1002)
        # Fee not in text — tariff DB would catch it, but disabled
        assert result.total_fees == 0.0


class TestFeeConfidence:
    """Test confidence scores"""
    
    def test_combined_pattern_high_confidence(self, extractor):
        """Combined FEE + TAX pattern should have high confidence"""
        result = extractor.extract_from_text("FEE 25 TAX 15", 100040)
        assert result.confidence >= 0.9
    
    def test_service_charge_confidence(self, extractor):
        """SERVICE CHARGE should have good confidence"""
        result = extractor.extract_from_text("SERVICE CHARGE 50", 50)
        assert result.confidence >= 0.8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
