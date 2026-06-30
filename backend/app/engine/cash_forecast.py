"""
Cash Forecast Engine — ReconET

Predicts cash position for the next 30 days based on:
1. Current cash position
2. Recurring patterns (payroll, rent, loan payments, standing orders)
3. Historical inflow/outflow patterns
4. Known upcoming obligations

This answers: "Can I pay payroll on Friday?"
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict
import statistics


@dataclass
class ForecastDay:
    """One day in the cash forecast"""
    date: str
    day_name: str           # Monday, Tuesday, etc.
    inflow: float = 0.0
    outflow: float = 0.0
    balance: float = 0.0
    is_weekend: bool = False
    events: List[str] = field(default_factory=list)
    is_critical: bool = False  # Below safety threshold


@dataclass
class CashForecast:
    """30-day cash forecast"""
    company_id: str
    forecast_date: str
    starting_balance: float
    days: List[ForecastDay]
    # Summary
    min_balance: float = 0.0
    min_balance_date: Optional[str] = None
    max_balance: float = 0.0
    total_inflow: float = 0.0
    total_outflow: float = 0.0
    net_change: float = 0.0
    # Alerts
    critical_days: int = 0
    below_threshold_date: Optional[str] = None
    alerts: List[str] = field(default_factory=list)


@dataclass
class RecurringPattern:
    """A detected recurring payment/receipt"""
    pattern_id: str
    pattern_type: str       # payroll, rent, loan, standing_order, salary, vendor
    description: str
    amount: float
    frequency: str          # weekly, biweekly, monthly, quarterly
    next_expected_date: str
    day_of_month: Optional[int] = None  # For monthly patterns
    day_of_week: Optional[int] = None   # For weekly patterns
    confidence: float = 0.0
    occurrences: int = 0
    last_seen: Optional[str] = None


class CashForecastEngine:
    """
    Generate 30-day cash forecast from recurring patterns.
    
    Usage:
        engine = CashForecastEngine()
        forecast = engine.forecast(
            current_balance=1826630,
            patterns=[...],
            days=30
        )
    """
    
    SAFETY_THRESHOLD = 500000  # ETB 500K
    
    def forecast(
        self,
        current_balance: float,
        patterns: List[RecurringPattern],
        transactions: List[Dict] = None,
        days: int = 30,
        company_id: str = "",
    ) -> CashForecast:
        """
        Generate cash forecast.
        
        Args:
            current_balance: Current adjusted cash position
            patterns: Detected recurring patterns
            transactions: Historical transactions for pattern detection
            days: Number of days to forecast
        """
        today = date.today()
        forecast_days = []
        balance = current_balance
        min_balance = current_balance
        min_balance_date = str(today)
        max_balance = current_balance
        total_inflow = 0.0
        total_outflow = 0.0
        critical_days = 0
        below_threshold_date = None
        alerts = []
        
        # Generate events for each day
        daily_events = self._generate_daily_events(patterns, today, days)
        
        # Generate forecast for each day
        for i in range(days):
            forecast_date = today + timedelta(days=i)
            day_name = forecast_date.strftime("%A")
            is_weekend = forecast_date.weekday() >= 5
            
            day_events = daily_events.get(forecast_date, [])
            day_inflow = sum(e["amount"] for e in day_events if e["type"] == "inflow")
            day_outflow = sum(e["amount"] for e in day_events if e["type"] == "outflow")
            
            balance = balance + day_inflow - day_outflow
            total_inflow += day_inflow
            total_outflow += day_outflow
            
            is_critical = balance < self.SAFETY_THRESHOLD
            
            if is_critical:
                critical_days += 1
                if below_threshold_date is None:
                    below_threshold_date = str(forecast_date)
            
            if balance < min_balance:
                min_balance = balance
                min_balance_date = str(forecast_date)
            if balance > max_balance:
                max_balance = balance
            
            event_descriptions = [e["description"] for e in day_events]
            
            forecast_days.append(ForecastDay(
                date=str(forecast_date),
                day_name=day_name,
                inflow=round(day_inflow, 2),
                outflow=round(day_outflow, 2),
                balance=round(balance, 2),
                is_weekend=is_weekend,
                events=event_descriptions,
                is_critical=is_critical,
            ))
        
        # Alerts
        if below_threshold_date:
            alerts.append(
                f"⚠️ Cash drops below ETB {self.SAFETY_THRESHOLD:,.0f} on {below_threshold_date}. "
                f"Minimum: ETB {min_balance:,.0f} on {min_balance_date}"
            )
        
        if min_balance < 0:
            alerts.append(
                f"🔴 Cash goes NEGATIVE (ETB {min_balance:,.0f}) on {min_balance_date}. "
                f"Immediate action required."
            )
        
        return CashForecast(
            company_id=company_id,
            forecast_date=str(today),
            starting_balance=current_balance,
            days=forecast_days,
            min_balance=min_balance,
            min_balance_date=min_balance_date,
            max_balance=max_balance,
            total_inflow=total_inflow,
            total_outflow=total_outflow,
            net_change=total_inflow - total_outflow,
            critical_days=critical_days,
            below_threshold_date=below_threshold_date,
            alerts=alerts,
        )
    
    def _generate_daily_events(
        self, patterns: List[RecurringPattern], start_date: date, days: int
    ) -> Dict[date, List[Dict]]:
        """Generate expected events for each day based on patterns"""
        events = defaultdict(list)
        
        for pattern in patterns:
            if pattern.frequency == "monthly":
                events.update(self._monthly_events(pattern, start_date, days))
            elif pattern.frequency == "biweekly":
                events.update(self._biweekly_events(pattern, start_date, days))
            elif pattern.frequency == "weekly":
                events.update(self._weekly_events(pattern, start_date, days))
            elif pattern.frequency == "quarterly":
                events.update(self._quarterly_events(pattern, start_date, days))
        
        return events
    
    def _monthly_events(
        self, pattern: RecurringPattern, start: date, days: int
    ) -> Dict[date, List[Dict]]:
        """Generate monthly recurring events"""
        events = defaultdict(list)
        is_outflow = pattern.pattern_type in (
            "payroll", "rent", "loan", "standing_order", "salary", "vendor", "utility"
        )
        
        for i in range(days + 30):  # Look ahead extra for month boundaries
            d = start + timedelta(days=i)
            if d.day == pattern.day_of_month:
                events[d].append({
                    "type": "outflow" if is_outflow else "inflow",
                    "amount": pattern.amount,
                    "description": f"{pattern.description} (monthly)",
                    "pattern_type": pattern.pattern_type,
                })
        
        return events
    
    def _biweekly_events(
        self, pattern: RecurringPattern, start: date, days: int
    ) -> Dict[date, List[Dict]]:
        """Generate biweekly recurring events"""
        events = defaultdict(list)
        is_outflow = pattern.pattern_type in ("payroll", "salary")
        
        # Find next occurrence
        next_date = date.fromisoformat(pattern.next_expected_date) if pattern.next_expected_date else start
        
        for i in range(days + 14):
            d = start + timedelta(days=i)
            if d >= next_date and (d - next_date).days % 14 == 0:
                events[d].append({
                    "type": "outflow" if is_outflow else "inflow",
                    "amount": pattern.amount,
                    "description": f"{pattern.description} (biweekly)",
                    "pattern_type": pattern.pattern_type,
                })
        
        return events
    
    def _weekly_events(
        self, pattern: RecurringPattern, start: date, days: int
    ) -> Dict[date, List[Dict]]:
        """Generate weekly recurring events"""
        events = defaultdict(list)
        target_day = pattern.day_of_week or 4  # Default Friday
        
        for i in range(days):
            d = start + timedelta(days=i)
            if d.weekday() == target_day:
                events[d].append({
                    "type": "outflow",
                    "amount": pattern.amount,
                    "description": f"{pattern.description} (weekly)",
                    "pattern_type": pattern.pattern_type,
                })
        
        return events
    
    def _quarterly_events(
        self, pattern: RecurringPattern, start: date, days: int
    ) -> Dict[date, List[Dict]]:
        """Generate quarterly recurring events"""
        events = defaultdict(list)
        is_outflow = pattern.pattern_type in ("loan", "tax", "insurance")
        
        next_date = date.fromisoformat(pattern.next_expected_date) if pattern.next_expected_date else start
        
        for i in range(days + 90):
            d = start + timedelta(days=i)
            if d >= next_date and (d - next_date).days % 90 == 0:
                events[d].append({
                    "type": "outflow" if is_outflow else "inflow",
                    "amount": pattern.amount,
                    "description": f"{pattern.description} (quarterly)",
                    "pattern_type": pattern.pattern_type,
                })
        
        return events
    
    def to_dict(self, forecast: CashForecast) -> Dict:
        """Convert to dict for API response"""
        return {
            "company_id": forecast.company_id,
            "forecast_date": forecast.forecast_date,
            "starting_balance": round(forecast.starting_balance, 2),
            "days": [
                {
                    "date": d.date,
                    "day_name": d.day_name,
                    "inflow": d.inflow,
                    "outflow": d.outflow,
                    "balance": d.balance,
                    "is_weekend": d.is_weekend,
                    "events": d.events,
                    "is_critical": d.is_critical,
                }
                for d in forecast.days
            ],
            "summary": {
                "min_balance": round(forecast.min_balance, 2),
                "min_balance_date": forecast.min_balance_date,
                "max_balance": round(forecast.max_balance, 2),
                "total_inflow": round(forecast.total_inflow, 2),
                "total_outflow": round(forecast.total_outflow, 2),
                "net_change": round(forecast.net_change, 2),
                "critical_days": forecast.critical_days,
                "below_threshold_date": forecast.below_threshold_date,
            },
            "alerts": forecast.alerts,
            "safety_threshold": self.SAFETY_THRESHOLD,
        }
