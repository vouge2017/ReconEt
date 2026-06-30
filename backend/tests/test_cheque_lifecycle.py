"""
Tests for Cheque Lifecycle Engine
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
from app.engine.cheque_lifecycle import ChequeLifecycleEngine


class TestChequeLifecycle:
    def test_empty(self):
        engine = ChequeLifecycleEngine()
        summary = engine.get_summary([])
        assert summary.total_outstanding == 0

    def test_match_clearing(self):
        engine = ChequeLifecycleEngine()
        cheques = [
            {"id": "c1", "cheque_number": "CHQ-001", "amount": 50000, "status": "issued",
             "issue_date": "2026-06-10", "payee_name": "ABC Trading"},
        ]
        transactions = [
            {"id": "t1", "date": "2026-06-14", "amount": -50000,
             "description": "CHEQUE CHQ-001 CLEARING", "reference": "CHQ-001"},
        ]
        matches = engine.match_clearing(cheques, transactions)
        assert len(matches) == 1
        assert matches[0].cheque_number == "CHQ-001"
        assert matches[0].days_to_clear == 4

    def test_stale_detection(self):
        engine = ChequeLifecycleEngine()
        cheques = [
            {"id": "c1", "cheque_number": "CHQ-001", "amount": 45000, "status": "issued",
             "issue_date": str(date.today() - timedelta(days=120)), "payee_name": "ABC"},
        ]
        stale = engine.detect_stale(cheques)
        assert len(stale) == 1
        assert stale[0]["days_outstanding"] > 90

    def test_overdue_detection(self):
        engine = ChequeLifecycleEngine()
        cheques = [
            {"id": "c1", "cheque_number": "CHQ-001", "amount": 30000, "status": "issued",
             "issue_date": str(date.today() - timedelta(days=20)),
             "expected_clear_date": str(date.today() - timedelta(days=5)),
             "payee_name": "XYZ"},
        ]
        overdue = engine.detect_overdue(cheques)
        assert len(overdue) == 1

    def test_summary_counts(self):
        engine = ChequeLifecycleEngine()
        cheques = [
            {"id": "c1", "amount": 50000, "status": "issued", "issue_date": "2026-06-01"},
            {"id": "c2", "amount": 30000, "status": "cleared", "issue_date": "2026-05-01"},
            {"id": "c3", "amount": 20000, "status": "issued", "issue_date": "2026-06-10"},
        ]
        summary = engine.get_summary(cheques)
        assert summary.total_outstanding == 2
        assert summary.total_cleared == 1
        assert summary.outstanding_amount == 70000
