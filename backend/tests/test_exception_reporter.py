"""
Tests for Exception Reporter
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.exception_reporter import ExceptionReporter, ExceptionCategory, Severity


class TestExceptionReporter:
    def test_empty_inputs(self):
        reporter = ExceptionReporter()
        report = reporter.generate()
        assert report.total_exceptions == 0
        assert report.summary == []
    
    def test_unmatched_bank_atm(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            unmatched_bank=[{"id": "b1", "amount": -5000, "description": "ATM WITHDRAWAL", "date": "2026-06-15"}]
        )
        assert report.total_exceptions == 1
        assert report.items[0].category == ExceptionCategory.MISSING_GL
        assert report.items[0].severity == Severity.LOW
    
    def test_unmatched_bank_transfer(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            unmatched_bank=[{"id": "b1", "amount": -100000, "description": "TRANSFER TO ABC", "date": "2026-06-15", "reference": "FT-001"}]
        )
        assert report.total_exceptions == 1
        assert report.items[0].category == ExceptionCategory.MISSING_GL
        assert report.items[0].severity == Severity.HIGH
    
    def test_unmatched_gl(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            unmatched_gl=[{"id": "g1", "amount": 50000, "description": "Vendor payment", "date": "2026-06-15"}]
        )
        assert report.total_exceptions == 1
        assert report.items[0].category == ExceptionCategory.MISSING_BANK
        assert report.items[0].severity == Severity.HIGH
    
    def test_low_confidence_match(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            matches=[{"bank_transaction": {"id": "b1", "amount": 100000}, "confidence": 55, "match_type": "fuzzy_match"}]
        )
        assert report.total_exceptions == 1
        assert report.items[0].category == ExceptionCategory.REVIEW_REQUIRED
        assert report.items[0].severity == Severity.HIGH
    
    def test_fee_issue_detection(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            all_transactions=[{"id": "b1", "amount": -100000, "description": "TRANSFER TO ABC", "fee_amount": 0}]
        )
        assert report.total_exceptions == 1
        assert report.items[0].category == ExceptionCategory.FEE_NOT_EXTRACTED
    
    def test_severity_counts(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            unmatched_bank=[
                {"id": "b1", "amount": -5000, "description": "ATM WITHDRAWAL", "date": "2026-06-15"},
                {"id": "b2", "amount": -100000, "description": "TRANSFER TO XYZ", "date": "2026-06-15", "reference": "FT-002"},
            ],
            unmatched_gl=[
                {"id": "g1", "amount": 50000, "description": "Missing entry", "date": "2026-06-15"},
            ]
        )
        assert report.by_severity["low"] == 1
        assert report.by_severity["high"] == 2
    
    def test_to_dict(self):
        reporter = ExceptionReporter()
        report = reporter.generate(
            unmatched_bank=[{"id": "b1", "amount": -5000, "description": "ATM", "date": "2026-06-15"}]
        )
        d = reporter.to_dict(report)
        assert "total_exceptions" in d
        assert "by_severity" in d
        assert "summary" in d
        assert "items" in d
        assert len(d["items"]) == 1
        assert "description_am" in d["items"][0]  # Amharic
