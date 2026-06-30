"""
Fee Intelligence Engine — ReconET

Tracks every bank fee, categorizes, trends, and benchmarks.
Answers: "Am I overpaying bank fees?"

The insight: Ethiopian businesses pay 0.3-1.5% of transaction volume in fees.
Most don't know. Those who do can save 20-40% by:
- Batching transfers (fewer per-transaction fees)
- Using cheaper banks for recurring transfers
- Avoiding unnecessary services (balance certificates, statement requests)
- Negotiating based on volume
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date
from collections import defaultdict
import statistics


@dataclass
class FeeBreakdown:
    """Fee breakdown for a period"""
    period_month: int
    period_year: int
    # Totals
    total_fees: float = 0.0
    total_bank_charges: float = 0.0
    total_vat: float = 0.0
    total_wht: float = 0.0
    # By type
    transfer_fees: float = 0.0
    cheque_fees: float = 0.0
    commission_fees: float = 0.0
    statement_fees: float = 0.0
    other_fees: float = 0.0
    # Metrics
    transaction_count: int = 0
    fee_transaction_count: int = 0
    fee_to_volume_ratio: float = 0.0
    total_volume: float = 0.0


@dataclass
class FeeTrend:
    """Month-over-month fee trend"""
    current: FeeBreakdown
    previous: Optional[FeeBreakdown]
    change_amount: float = 0.0
    change_percent: float = 0.0
    top_fee_drivers: List[Dict] = field(default_factory=list)
    savings_opportunities: List[Dict] = field(default_factory=list)


@dataclass
class FeeBenchmark:
    """Peer benchmarking (anonymous aggregation)"""
    your_fees: float
    your_volume: float
    your_ratio: float
    peer_median_fees: float
    peer_median_ratio: float
    percentile_rank: int  # 1-100 (1 = lowest fees)
    potential_savings: float
    comparison_text: str
    comparison_text_am: str


class FeeIntelligenceEngine:
    """
    Analyze bank fees: categorize, trend, benchmark.
    
    Usage:
        engine = FeeIntelligenceEngine()
        breakdown = engine.analyze_period(transactions, month=6, year=2026)
        trend = engine.analyze_trend(current_txns, previous_txns)
        benchmark = engine.benchmark(fee_data, peer_data)
    """
    
    # Ethiopian bank fee keywords for categorization
    TRANSFER_KEYWORDS = ["TRANSFER", "FT", "FUND TRANSFER", "INTERBANK"]
    CHEQUE_KEYWORDS = ["CHEQUE", "CHQ", "CHECK", "CLEARING"]
    COMMISSION_KEYWORDS = ["COMMISSION", "COMM"]
    STATEMENT_KEYWORDS = ["STATEMENT", "BALANCE CERTIFICATE", "LETTER"]
    
    def analyze_period(
        self, transactions: List[Dict], month: int, year: int
    ) -> FeeBreakdown:
        """
        Analyze fees for a specific period.
        
        Args:
            transactions: Transaction dicts with date, amount, fee_amount, bank_charge, gov_tax, description
            month: Period month
            year: Period year
        """
        breakdown = FeeBreakdown(period_month=month, period_year=year)
        
        for txn in transactions:
            # Check if transaction is in the period
            txn_date = txn.get("date")
            if isinstance(txn_date, str):
                try:
                    txn_date = date.fromisoformat(txn_date)
                except ValueError:
                    continue
            if not isinstance(txn_date, date):
                continue
            if txn_date.month != month or txn_date.year != year:
                continue
            
            breakdown.transaction_count += 1
            breakdown.total_volume += abs(txn.get("amount", 0))
            
            fee_amount = txn.get("fee_amount", 0) or 0
            bank_charge = txn.get("bank_charge", 0) or 0
            gov_tax = txn.get("gov_tax", 0) or 0
            
            if fee_amount > 0:
                breakdown.fee_transaction_count += 1
                breakdown.total_fees += fee_amount
                breakdown.total_bank_charges += bank_charge
                breakdown.total_vat += gov_tax
                
                # Categorize by type
                desc = (txn.get("description") or txn.get("narrative") or "").upper()
                category = self._categorize_fee(desc)
                
                if category == "transfer":
                    breakdown.transfer_fees += fee_amount
                elif category == "cheque":
                    breakdown.cheque_fees += fee_amount
                elif category == "commission":
                    breakdown.commission_fees += fee_amount
                elif category == "statement":
                    breakdown.statement_fees += fee_amount
                else:
                    breakdown.other_fees += fee_amount
        
        # Compute ratio
        if breakdown.total_volume > 0:
            breakdown.fee_to_volume_ratio = (breakdown.total_fees / breakdown.total_volume) * 100
        
        return breakdown
    
    def analyze_trend(
        self, current_transactions: List[Dict], previous_transactions: List[Dict],
        current_month: int, current_year: int,
        previous_month: int, previous_year: int,
    ) -> FeeTrend:
        """Compare current period fees to previous period"""
        current = self.analyze_period(current_transactions, current_month, current_year)
        previous = self.analyze_period(previous_transactions, previous_month, previous_year)
        
        change_amount = current.total_fees - previous.total_fees
        change_percent = (change_amount / previous.total_fees * 100) if previous.total_fees > 0 else 0
        
        # Find top fee drivers (categories with biggest increase)
        drivers = []
        categories = [
            ("transfer_fees", "Transfer Fees", current.transfer_fees, previous.transfer_fees),
            ("cheque_fees", "Cheque Fees", current.cheque_fees, previous.cheque_fees),
            ("commission_fees", "Commission", current.commission_fees, previous.commission_fees),
            ("statement_fees", "Statement/Certificate", current.statement_fees, previous.statement_fees),
            ("other_fees", "Other Fees", current.other_fees, previous.other_fees),
        ]
        
        for key, label, curr_val, prev_val in categories:
            change = curr_val - prev_val
            if abs(change) > 100:  # Only significant changes
                drivers.append({
                    "category": key,
                    "label": label,
                    "current": curr_val,
                    "previous": prev_val,
                    "change": change,
                    "change_percent": (change / prev_val * 100) if prev_val > 0 else 0,
                })
        
        drivers.sort(key=lambda d: abs(d["change"]), reverse=True)
        
        # Savings opportunities
        savings = self._identify_savings(current, previous)
        
        return FeeTrend(
            current=current,
            previous=previous,
            change_amount=change_amount,
            change_percent=change_percent,
            top_fee_drivers=drivers,
            savings_opportunities=savings,
        )
    
    def benchmark(
        self, your_fees: float, your_volume: float,
        peer_fee_data: List[Dict] = None,
    ) -> FeeBenchmark:
        """
        Benchmark fees against peers.
        
        If no peer data provided, uses Ethiopian market estimates.
        """
        your_ratio = (your_fees / your_volume * 100) if your_volume > 0 else 0
        
        # Ethiopian market benchmarks (estimated)
        # Based on typical Ethiopian business banking fees
        if peer_fee_data:
            peer_ratios = [
                (p["fees"] / p["volume"] * 100) if p["volume"] > 0 else 0
                for p in peer_fee_data
            ]
            peer_median = statistics.median(peer_ratios) if peer_ratios else 0.5
        else:
            # Market estimates for Ethiopian businesses
            # Small business: 0.3-0.8% of volume
            # Medium business: 0.2-0.5% of volume
            peer_median = 0.4  # 0.4% median
        
        # Calculate percentile
        if peer_fee_data:
            peer_ratios_sorted = sorted(peer_ratios)
            rank = sum(1 for r in peer_ratios_sorted if r < your_ratio)
            percentile = int((rank / len(peer_ratios_sorted)) * 100) if peer_ratios_sorted else 50
        else:
            # Estimate percentile from market data
            if your_ratio <= 0.2:
                percentile = 10
            elif your_ratio <= 0.4:
                percentile = 30
            elif your_ratio <= 0.6:
                percentile = 50
            elif your_ratio <= 0.8:
                percentile = 70
            elif your_ratio <= 1.0:
                percentile = 85
            else:
                percentile = 95
        
        # Potential savings (difference from median)
        target_fees = your_volume * (peer_median / 100)
        potential_savings = max(0, your_fees - target_fees)
        
        # Comparison text
        if your_ratio < peer_median:
            comparison = f"You're paying less than the median ({your_ratio:.2f}% vs {peer_median:.2f}%). Good job."
            comparison_am = f"ከመካከለኛው በታች ነዎት ({your_ratio:.2f}% vs {peer_median:.2f}%)። ጥሩ ስራ።"
        elif your_ratio < peer_median * 1.2:
            comparison = f"You're close to the median ({your_ratio:.2f}% vs {peer_median:.2f}%). Room for minor optimization."
            comparison_am = f"ከመካከለኛው ጋር ቅርብ ነዎት ({your_ratio:.2f}% vs {peer_median:.2f}%)። ምንም ያህል ማሻሻያ ይችላል።"
        else:
            comparison = f"You're paying {your_ratio/peer_median:.1f}x the median ({your_ratio:.2f}% vs {peer_median:.2f}%). Potential savings: ETB {potential_savings:,.0f}/period."
            comparison_am = f"ከመካከለኛው {your_ratio/peer_median:.1f}x ይከፍላሉ ({your_ratio:.2f}% vs {peer_median:.2f}%)። ለማዳን የሚቻለው: ETB {potential_savings:,.0f}/ période።"
        
        return FeeBenchmark(
            your_fees=your_fees,
            your_volume=your_volume,
            your_ratio=your_ratio,
            peer_median_fees=target_fees,
            peer_median_ratio=peer_median,
            percentile_rank=percentile,
            potential_savings=potential_savings,
            comparison_text=comparison,
            comparison_text_am=comparison_am,
        )
    
    def _categorize_fee(self, description: str) -> str:
        """Categorize fee from transaction description"""
        if any(kw in description for kw in self.TRANSFER_KEYWORDS):
            return "transfer"
        if any(kw in description for kw in self.CHEQUE_KEYWORDS):
            return "cheque"
        if any(kw in description for kw in self.COMMISSION_KEYWORDS):
            return "commission"
        if any(kw in description for kw in self.STATEMENT_KEYWORDS):
            return "statement"
        return "other"
    
    def _identify_savings(self, current: FeeBreakdown, previous: FeeBreakdown) -> List[Dict]:
        """Identify savings opportunities"""
        opportunities = []
        
        # High transfer fees → suggest batching
        if current.transfer_fees > 10000:
            avg_per_transfer = current.transfer_fees / max(current.fee_transaction_count, 1)
            opportunities.append({
                "type": "batch_transfers",
                "title": "Batch your transfers",
                "title_am": "ሽግግሮችዎን ያዋህዱ",
                "description": (
                    f"You paid ETB {current.transfer_fees:,.0f} in transfer fees this period. "
                    f"Average ETB {avg_per_transfer:,.0f} per transfer. "
                    f"Batching multiple payments into fewer transfers can reduce per-transaction fees."
                ),
                "potential_saving": current.transfer_fees * 0.2,  # Estimate 20% savings
            })
        
        # High cheque fees → suggest electronic
        if current.cheque_fees > 5000:
            opportunities.append({
                "type": "reduce_cheques",
                "title": "Reduce cheque usage",
                "title_am": "የቼክ አጠቃቀምን ይቀንሱ",
                "description": (
                    f"You paid ETB {current.cheque_fees:,.0f} in cheque fees. "
                    f"Electronic transfers are often cheaper and faster."
                ),
                "potential_saving": current.cheque_fees * 0.3,
            })
        
        # Statement fees → use online banking
        if current.statement_fees > 2000:
            opportunities.append({
                "type": "online_banking",
                "title": "Use online banking",
                "title_am": "ኦንላይን ባንኪንግ ይጠቀሙ",
                "description": (
                    f"You paid ETB {current.statement_fees:,.0f} for statements and certificates. "
                    f"Online banking provides these for free."
                ),
                "potential_saving": current.statement_fees * 0.8,
            })
        
        # Fees increasing month-over-month
        if previous.total_fees > 0:
            change = (current.total_fees - previous.total_fees) / previous.total_fees
            if change > 0.3:  # 30% increase
                opportunities.append({
                    "type": "investigate_increase",
                    "title": "Fees increased significantly",
                    "title_am": "ክፍያዎች በእጅጉ ጨመረ",
                    "description": (
                        f"Your fees increased by {change*100:.0f}% vs last period. "
                        f"Investigate the root cause — new services, more transactions, or fee schedule change."
                    ),
                    "potential_saving": current.total_fees - previous.total_fees,
                })
        
        return opportunities
    
    def to_breakdown_dict(self, breakdown: FeeBreakdown) -> Dict:
        """Convert to dict"""
        return {
            "period": f"{breakdown.period_month}/{breakdown.period_year}",
            "total_fees": round(breakdown.total_fees, 2),
            "total_bank_charges": round(breakdown.total_bank_charges, 2),
            "total_vat": round(breakdown.total_vat, 2),
            "total_wht": round(breakdown.total_wht, 2),
            "by_type": {
                "transfer": round(breakdown.transfer_fees, 2),
                "cheque": round(breakdown.cheque_fees, 2),
                "commission": round(breakdown.commission_fees, 2),
                "statement": round(breakdown.statement_fees, 2),
                "other": round(breakdown.other_fees, 2),
            },
            "metrics": {
                "transaction_count": breakdown.transaction_count,
                "fee_transaction_count": breakdown.fee_transaction_count,
                "total_volume": round(breakdown.total_volume, 2),
                "fee_to_volume_ratio": round(breakdown.fee_to_volume_ratio, 4),
            },
        }
    
    def to_trend_dict(self, trend: FeeTrend) -> Dict:
        """Convert to dict"""
        return {
            "current": self.to_breakdown_dict(trend.current),
            "previous": self.to_breakdown_dict(trend.previous) if trend.previous else None,
            "change": {
                "amount": round(trend.change_amount, 2),
                "percent": round(trend.change_percent, 1),
            },
            "top_drivers": trend.top_fee_drivers,
            "savings_opportunities": trend.savings_opportunities,
        }
    
    def to_benchmark_dict(self, benchmark: FeeBenchmark) -> Dict:
        """Convert to dict"""
        return {
            "your_fees": round(benchmark.your_fees, 2),
            "your_volume": round(benchmark.your_volume, 2),
            "your_ratio": round(benchmark.your_ratio, 4),
            "peer_median_ratio": round(benchmark.peer_median_ratio, 4),
            "percentile_rank": benchmark.percentile_rank,
            "potential_savings": round(benchmark.potential_savings, 2),
            "comparison": benchmark.comparison_text,
            "comparison_am": benchmark.comparison_text_am,
        }
