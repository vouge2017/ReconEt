"""
Tests for Anomaly Detector
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
from app.engine.anomaly_detector import AnomalyDetector


class TestAnomalyDetector:
    def test_empty_transactions(self):
        detector = AnomalyDetector()
        alerts = detector.scan(transactions=[])
        assert len(alerts) == 0

    def test_duplicate_detection(self):
        detector = AnomalyDetector()
        alerts = detector.scan(
            transactions=[
                {"id": "t1", "date": "2026-06-15", "amount": -250000, "description": "PAYMENT TO ABC TRADING", "reference": "FT-001"},
                {"id": "t2", "date": "2026-06-16", "amount": -250000, "description": "PAYMENT TO ABC TRADING", "reference": "FT-002"},
            ]
        )
        assert any(a.alert_type == "duplicate" for a in alerts)
        assert any(a.severity == "critical" for a in alerts)

    def test_weekend_detection(self):
        detector = AnomalyDetector()
        # 2026-06-13 is a Saturday
        alerts = detector.scan(
            transactions=[
                {"id": "t1", "date": "2026-06-13", "amount": -100000, "description": "TRANSFER TO XYZ", "reference": "FT-001"},
            ]
        )
        assert any(a.alert_type == "weekend" for a in alerts)

    def test_spike_detection(self):
        detector = AnomalyDetector()
        # Historical: 10 payments of ~100K
        historical = [
            {"id": f"h{i}", "date": f"2026-0{1 + i // 4}-15", "amount": -100000 + (i * 1000),
             "description": "PAYMENT TO VENDOR A", "reference": f"FT-{i:03d}"}
            for i in range(12)
        ]
        # Current: 500K payment (5x spike)
        current = [
            {"id": "t1", "date": "2026-06-15", "amount": -500000,
             "description": "PAYMENT TO VENDOR A", "reference": "FT-999"},
        ]
        alerts = detector.scan(transactions=current, historical_transactions=historical)
        assert any(a.alert_type == "spike" for a in alerts)

    def test_new_payee_detection(self):
        detector = AnomalyDetector()
        historical = [
            {"id": f"h{i}", "date": f"2026-0{i+1}-15", "amount": -100000,
             "description": "PAYMENT TO KNOWN VENDOR", "reference": f"FT-{i:03d}"}
            for i in range(6)
        ]
        current = [
            {"id": "t1", "date": "2026-06-15", "amount": -200000,
             "description": "PAYMENT TO NEW ENTITY XYZ", "reference": "FT-999"},
        ]
        alerts = detector.scan(transactions=current, historical_transactions=historical)
        assert any(a.alert_type == "new_payee" for a in alerts)

    def test_round_amount_detection(self):
        detector = AnomalyDetector()
        alerts = detector.scan(
            transactions=[
                {"id": "t1", "date": "2026-06-15", "amount": -500000,
                 "description": "TRANSFER TO ABC", "reference": "FT-001"},
            ]
        )
        assert any(a.alert_type == "round_amount" for a in alerts)
        assert any(a.severity == "info" for a in alerts)

    def test_stale_cheque_detection(self):
        detector = AnomalyDetector()
        alerts = detector.scan(
            transactions=[],
            cheques=[
                {"id": "c1", "cheque_number": "CHQ-001", "amount": 45000,
                 "payee_name": "ABC Trading", "issue_date": "2026-01-01", "status": "issued"},
            ]
        )
        assert any(a.alert_type == "stale_cheque" for a in alerts)

    def test_fee_anomaly(self):
        detector = AnomalyDetector()
        # Normal fees of ~25, then one of 2500
        txns = [
            {"id": f"t{i}", "date": f"2026-06-{10+i}", "amount": -100000,
             "description": "TRANSFER", "reference": f"FT-{i}", "fee_amount": 25}
            for i in range(5)
        ]
        txns.append({"id": "t99", "date": "2026-06-20", "amount": -100000,
                      "description": "TRANSFER", "reference": "FT-99", "fee_amount": 2500})
        alerts = detector.scan(transactions=txns)
        assert any(a.alert_type == "fee_anomaly" for a in alerts)
