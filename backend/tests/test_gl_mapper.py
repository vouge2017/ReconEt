"""
Tests for GL Account Mapping Engine
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.gl_mapper import GLAccountMapper, DEFAULT_MAPPINGS


class TestGLAccountMapper:
    def test_map_bank_charge(self):
        mapper = GLAccountMapper()
        result = mapper.map_fee("bank_charge", 25.00)
        assert result["gl_code"] == "6500"
        assert result["gl_name"] == "Bank Charges"
        assert result["debit"] == 25.00
        assert result["needs_review"] is False
    
    def test_map_gov_tax(self):
        mapper = GLAccountMapper()
        result = mapper.map_fee("gov_tax", 15.00)
        assert result["gl_code"] == "7100"
        assert result["gl_name"] == "Government Tax (VAT)"
    
    def test_map_wht(self):
        mapper = GLAccountMapper()
        result = mapper.map_fee("wht", 2.00)
        assert result["gl_code"] == "7101"
        assert result["gl_name"] == "Withholding Tax"
    
    def test_map_unknown_type(self):
        mapper = GLAccountMapper()
        result = mapper.map_fee("unknown_fee_type", 100.00)
        assert result["gl_code"] is None
        assert result["needs_review"] is True
    
    def test_map_transaction_with_fees(self):
        mapper = GLAccountMapper()
        txn = {
            "amount": 100040,
            "description": "Payment to ABC Trading",
            "gross_amount": 100000,
            "bank_charge": 25,
            "gov_tax": 15,
            "wht": 0,
        }
        entries = mapper.map_transaction(txn)
        
        # Should have: expense, bank_charge, gov_tax, bank_account
        assert len(entries) == 4
        
        # Verify expense entry
        expense = entries[0]
        assert expense["debit"] == 100000
        assert expense["type"] == "expense"
        
        # Verify bank charge entry
        charge = entries[1]
        assert charge["debit"] == 25
        assert charge["account_code"] == "6500"
        
        # Verify tax entry
        tax = entries[2]
        assert tax["debit"] == 15
        assert tax["account_code"] == "7100"
        
        # Verify bank account credit
        bank = entries[3]
        assert bank["credit"] == 100040
        assert bank["account_code"] == "1100"
    
    def test_custom_mappings(self):
        custom = [{"fee_type": "bank_charge", "gl_account_code": "9999", "gl_account_name": "Custom Charges"}]
        mapper = GLAccountMapper(custom_mappings=custom)
        result = mapper.map_fee("bank_charge", 25.00)
        assert result["gl_code"] == "9999"
        assert result["needs_review"] is True  # Custom mapping flagged for review
    
    def test_get_all_mappings(self):
        mapper = GLAccountMapper()
        all_mappings = mapper.get_all_mappings()
        assert len(all_mappings) >= 8  # At least 8 default mappings
        assert all("fee_type" in m for m in all_mappings)
