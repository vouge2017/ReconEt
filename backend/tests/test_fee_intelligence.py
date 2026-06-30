"""
Tests for Fee Intelligence Engine
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.fee_intelligence import FeeIntelligenceEngine


class TestFeeIntelligence:
    def test_empty_transactions(self):
        engine = FeeIntelligenceEngine()
        breakdown = engine.analyze_period([], 6, 2026)
        assert breakdown.total_fees == 0
        assert breakdown.transaction_count == 0

    def test_fee_categorization(self):
        engine = FeeIntelligenceEngine()
        txns = [
            {"id": "t1", "date": "2026-06-15", "amount": -100000, "fee_amount": 50, "bank_charge": 43.48, "gov_tax": 6.52, "description": "TRANSFER TO ABC"},
            {"id": "t2", "date": "2026-06-16", "amount": -50000, "fee_amount": 10, "bank_charge": 8.70, "gov_tax": 1.30, "description": "CHEQUE PAYMENT"},
            {"id": "t3", "date": "2026-06-17", "amount": -20000, "fee_amount": 25, "bank_charge": 21.74, "gov_tax": 3.26, "description": "BALANCE CERTIFICATE"},
        ]
        breakdown = engine.analyze_period(txns, 6, 2026)
        assert breakdown.total_fees == 85
        assert breakdown.transfer_fees == 50
        assert breakdown.cheque_fees == 10
        assert breakdown.statement_fees == 25
        assert breakdown.fee_transaction_count == 3

    def test_fee_to_volume_ratio(self):
        engine = FeeIntelligenceEngine()
        txns = [
            {"id": "t1", "date": "2026-06-15", "amount": -100000, "fee_amount": 50, "bank_charge": 43, "gov_tax": 7, "description": "TRANSFER"},
        ]
        breakdown = engine.analyze_period(txns, 6, 2026)
        assert breakdown.fee_to_volume_ratio > 0
        assert breakdown.fee_to_volume_ratio < 1  # Less than 1%

    def test_trend_analysis(self):
        engine = FeeIntelligenceEngine()
        current = [
            {"id": "t1", "date": "2026-06-15", "amount": -100000, "fee_amount": 100, "bank_charge": 87, "gov_tax": 13, "description": "TRANSFER"},
        ]
        previous = [
            {"id": "t2", "date": "2026-05-15", "amount": -100000, "fee_amount": 50, "bank_charge": 43, "gov_tax": 7, "description": "TRANSFER"},
        ]
        trend = engine.analyze_trend(current, previous, 6, 2026, 5, 2026)
        assert trend.change_amount == 50
        assert trend.change_percent == 100.0

    def test_benchmark(self):
        engine = FeeIntelligenceEngine()
        benchmark = engine.benchmark(your_fees=5000, your_volume=1000000)
        assert benchmark.your_ratio == 0.5
        assert benchmark.potential_savings > 0  # Above median
        assert benchmark.percentile_rank >= 50

    def test_savings_opportunities(self):
        engine = FeeIntelligenceEngine()
        # High transfer fees
        txns = [
            {"id": f"t{i}", "date": f"2026-06-{10+i}", "amount": -100000,
             "fee_amount": 5000, "bank_charge": 4348, "gov_tax": 652, "description": "TRANSFER"}
            for i in range(10)
        ]
        previous = [
            {"id": f"p{i}", "date": f"2026-05-{10+i}", "amount": -100000,
             "fee_amount": 50, "bank_charge": 43, "gov_tax": 7, "description": "TRANSFER"}
            for i in range(10)
        ]
        trend = engine.analyze_trend(txns, previous, 6, 2026, 5, 2026)
        assert len(trend.savings_opportunities) > 0
