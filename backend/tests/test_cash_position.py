"""
Tests for Cash Position Engine
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
from app.engine.cash_position import CashPositionEngine


class TestCashPosition:
    def test_empty_accounts(self):
        engine = CashPositionEngine()
        position = engine.compute(bank_accounts=[], transactions=[])
        assert position.adjusted_position == 0.0
        assert len(position.accounts) == 0

    def test_single_account_no_adjustments(self):
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[{"id": "a1", "company_id": "c1", "bank_name": "CBE", "account_number": "123", "account_type": "current"}],
            transactions=[{"id": "t1", "bank_account_id": "a1", "date": "2026-06-30", "amount": -1000, "balance": 50000}],
        )
        assert position.total_raw_balance == 50000
        assert position.adjusted_position == 50000
        assert len(position.accounts) == 1

    def test_outstanding_cheques_subtracted(self):
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[{"id": "a1", "company_id": "c1", "bank_name": "CBE", "account_number": "123", "account_type": "current"}],
            transactions=[{"id": "t1", "bank_account_id": "a1", "date": "2026-06-30", "amount": -1000, "balance": 100000}],
            cheques=[{"id": "c1", "bank_account_id": "a1", "cheque_number": "CHQ-001", "amount": 30000, "status": "issued", "issue_date": "2026-06-15", "payee_name": "ABC"}],
        )
        assert position.total_outstanding_cheques == 30000
        assert position.adjusted_position == 70000  # 100K - 30K

    def test_multi_bank_aggregation(self):
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[
                {"id": "a1", "company_id": "c1", "bank_name": "CBE", "account_number": "111", "account_type": "current"},
                {"id": "a2", "company_id": "c1", "bank_name": "Dashen", "account_number": "222", "account_type": "savings"},
            ],
            transactions=[
                {"id": "t1", "bank_account_id": "a1", "date": "2026-06-30", "amount": -1000, "balance": 800000},
                {"id": "t2", "bank_account_id": "a2", "date": "2026-06-30", "amount": -500, "balance": 450000},
            ],
        )
        assert position.total_raw_balance == 1250000
        assert position.adjusted_position == 1250000
        assert "CBE" in position.by_bank
        assert "Dashen" in position.by_bank
        assert position.by_bank["CBE"] == 800000
        assert position.by_bank["Dashen"] == 450000

    def test_stale_cheque_alert(self):
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[{"id": "a1", "company_id": "c1", "bank_name": "CBE", "account_number": "123", "account_type": "current"}],
            transactions=[{"id": "t1", "bank_account_id": "a1", "date": "2026-06-30", "amount": 0, "balance": 500000}],
            cheques=[{"id": "c1", "bank_account_id": "a1", "cheque_number": "CHQ-001", "amount": 45000, "status": "issued", "issue_date": "2026-01-01", "payee_name": "ABC"}],
        )
        assert len(position.stale_cheques) == 1
        assert position.stale_cheques[0]["amount"] == 45000

    def test_trend_calculation(self):
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[{"id": "a1", "company_id": "c1", "bank_name": "CBE", "account_number": "123", "account_type": "current"}],
            transactions=[{"id": "t1", "bank_account_id": "a1", "date": "2026-06-30", "amount": 0, "balance": 600000}],
            previous_position=500000,
        )
        assert position.change_amount == 100000
        assert position.change_percent == 20.0

    def test_to_dict(self):
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[{"id": "a1", "company_id": "c1", "bank_name": "CBE", "account_number": "123", "account_type": "current"}],
            transactions=[{"id": "t1", "bank_account_id": "a1", "date": "2026-06-30", "amount": 0, "balance": 500000}],
        )
        d = engine.to_dict(position)
        assert "accounts" in d
        assert "totals" in d
        assert "by_bank" in d
        assert "alerts" in d
        assert "trend" in d
        assert d["totals"]["adjusted_position"] == 500000
