"""
Tests for Cash Forecast Engine
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, timedelta
from app.engine.cash_forecast import CashForecastEngine, RecurringPattern


class TestCashForecast:
    def test_empty_forecast(self):
        engine = CashForecastEngine()
        forecast = engine.forecast(current_balance=1000000, patterns=[], days=30)
        assert forecast.starting_balance == 1000000
        assert len(forecast.days) == 30
        # No patterns = balance stays flat
        assert forecast.days[-1].balance == 1000000

    def test_monthly_payroll_outflow(self):
        engine = CashForecastEngine()
        tomorrow = date.today() + timedelta(days=5)
        patterns = [
            RecurringPattern(
                pattern_id="p1",
                pattern_type="payroll",
                description="Monthly payroll",
                amount=500000,
                frequency="monthly",
                next_expected_date=str(tomorrow),
                day_of_month=tomorrow.day,
                confidence=0.9,
            )
        ]
        forecast = engine.forecast(current_balance=2000000, patterns=patterns, days=30)
        assert forecast.total_outflow > 0
        assert forecast.min_balance < 2000000

    def test_safety_threshold_alert(self):
        engine = CashForecastEngine()
        tomorrow = date.today() + timedelta(days=2)
        patterns = [
            RecurringPattern(
                pattern_id="p1",
                pattern_type="payroll",
                description="Big payroll",
                amount=1500000,
                frequency="monthly",
                next_expected_date=str(tomorrow),
                day_of_month=tomorrow.day,
                confidence=0.9,
            )
        ]
        forecast = engine.forecast(current_balance=1000000, patterns=patterns, days=30)
        assert forecast.critical_days > 0
        assert len(forecast.alerts) > 0

    def test_weekly_pattern(self):
        engine = CashForecastEngine()
        patterns = [
            RecurringPattern(
                pattern_id="p1",
                pattern_type="vendor",
                description="Weekly delivery",
                amount=10000,
                frequency="weekly",
                next_expected_date=str(date.today()),
                day_of_week=0,  # Monday
                confidence=0.8,
            )
        ]
        forecast = engine.forecast(current_balance=500000, patterns=patterns, days=30)
        # Should have ~4 Mondays in 30 days
        assert forecast.total_outflow >= 30000

    def test_to_dict(self):
        engine = CashForecastEngine()
        forecast = engine.forecast(current_balance=1000000, patterns=[], days=7)
        d = engine.to_dict(forecast)
        assert "days" in d
        assert "summary" in d
        assert "alerts" in d
        assert len(d["days"]) == 7
