"""
Cash Position Engine — ReconET

The core value: shows real cash position across all banks,
adjusted for outstanding cheques, uncleared deposits, and pending transfers.

This is what makes a CFO open ReconET every morning.

How it works:
1. Pulls latest balance from each bank account
2. Subtracts outstanding cheques (issued but not cleared)
3. Adds uncleared deposits (deposited but not reflected)
4. Accounts for pending transfers (in-flight)
5. Computes adjusted cash position
6. Flags if below safety threshold
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date, timedelta
from enum import Enum


class AccountType(str, Enum):
    CURRENT = "current"
    SAVINGS = "savings"
    FIXED_DEPOSIT = "fixed_deposit"
    OVERDRAFT = "overdraft"


@dataclass
class BankAccountSnapshot:
    """Snapshot of a single bank account"""
    account_id: str
    bank_name: str
    account_number: str
    account_type: AccountType
    currency: str = "ETB"
    # Balances
    raw_balance: float = 0.0          # Latest balance from statement
    outstanding_cheques: float = 0.0  # Cheques issued, not cleared
    uncleared_deposits: float = 0.0   # Deposits made, not reflected
    pending_transfers: float = 0.0    # Transfers in flight
    # Result
    adjusted_balance: float = 0.0     # Raw - cheques + deposits - transfers
    # Metadata
    last_transaction_date: Optional[str] = None
    last_updated: Optional[str] = None
    statement_period: Optional[str] = None
    transaction_count: int = 0
    # Alerts
    alerts: List[str] = field(default_factory=list)


@dataclass
class CashPosition:
    """Aggregated cash position across all banks"""
    company_id: str
    snapshot_date: str
    # Per-account
    accounts: List[BankAccountSnapshot]
    # Totals
    total_raw_balance: float = 0.0
    total_outstanding_cheques: float = 0.0
    total_uncleared_deposits: float = 0.0
    total_pending_transfers: float = 0.0
    adjusted_position: float = 0.0
    # By bank
    by_bank: Dict[str, float] = field(default_factory=dict)
    # Alerts
    stale_cheques: List[Dict] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    # Trend
    previous_position: Optional[float] = None
    change_amount: Optional[float] = None
    change_percent: Optional[float] = None


class CashPositionEngine:
    """
    Compute real cash position across all bank accounts.
    
    Usage:
        engine = CashPositionEngine()
        position = engine.compute(
            bank_accounts=[...],
            transactions=[...],
            cheques=[...],
        )
    """
    
    STALE_CHEQUE_DAYS = 90
    SAFETY_THRESHOLD = 500000  # ETB 500K default
    
    def compute(
        self,
        bank_accounts: List[Dict],
        transactions: List[Dict],
        cheques: List[Dict] = None,
        previous_position: float = None,
    ) -> CashPosition:
        """
        Compute cash position from bank accounts, transactions, and cheques.
        
        Args:
            bank_accounts: List of bank account dicts with id, bank_name, account_number, account_type
            transactions: List of transaction dicts with bank_account_id, date, amount, balance
            cheques: List of cheque dicts with bank_account_id, amount, status, issue_date
            previous_position: Previous period's adjusted position (for trend)
        """
        cheques = cheques or []
        today = date.today()
        
        # Group transactions by bank account
        txn_by_account = {}
        for txn in transactions:
            acct_id = txn.get("bank_account_id")
            if acct_id not in txn_by_account:
                txn_by_account[acct_id] = []
            txn_by_account[acct_id].append(txn)
        
        # Group cheques by bank account
        cheque_by_account = {}
        for chq in cheques:
            acct_id = chq.get("bank_account_id")
            if acct_id not in cheque_by_account:
                cheque_by_account[acct_id] = []
            cheque_by_account[acct_id].append(chq)
        
        # Process each account
        account_snapshots = []
        total_raw = 0.0
        total_cheques = 0.0
        total_deposits = 0.0
        total_transfers = 0.0
        by_bank = {}
        all_stale = []
        all_alerts = []
        
        for acct in bank_accounts:
            acct_id = acct.get("id")
            bank_name = acct.get("bank_name", "Unknown")
            txns = txn_by_account.get(acct_id, [])
            acct_cheques = cheque_by_account.get(acct_id, [])
            
            snapshot = self._compute_account(acct, txns, acct_cheques, today)
            account_snapshots.append(snapshot)
            
            total_raw += snapshot.raw_balance
            total_cheques += snapshot.outstanding_cheques
            total_deposits += snapshot.uncleared_deposits
            total_transfers += snapshot.pending_transfers
            
            # Aggregate by bank
            if bank_name not in by_bank:
                by_bank[bank_name] = 0.0
            by_bank[bank_name] += snapshot.adjusted_balance
            
            all_alerts.extend(snapshot.alerts)
        
        # Find stale cheques across all accounts
        for chq in cheques:
            if chq.get("status") in ("issued", "deposited", "clearing"):
                issue_date = chq.get("issue_date")
                if isinstance(issue_date, str):
                    try:
                        issue_date = date.fromisoformat(issue_date)
                    except ValueError:
                        continue
                if isinstance(issue_date, date):
                    days_outstanding = (today - issue_date).days
                    if days_outstanding > self.STALE_CHEQUE_DAYS:
                        all_stale.append({
                            "cheque_number": chq.get("cheque_number"),
                            "amount": chq.get("amount", 0),
                            "payee": chq.get("payee_name", ""),
                            "issue_date": str(issue_date),
                            "days_outstanding": days_outstanding,
                            "bank_account_id": chq.get("bank_account_id"),
                        })
        
        # Compute totals
        adjusted = total_raw - total_cheques + total_deposits - total_transfers
        
        # Trend
        change_amount = None
        change_percent = None
        if previous_position is not None:
            change_amount = adjusted - previous_position
            if previous_position != 0:
                change_percent = (change_amount / abs(previous_position)) * 100
        
        # Safety threshold alert
        if adjusted < self.SAFETY_THRESHOLD:
            all_alerts.append(
                f"⚠️ Cash position ETB {adjusted:,.2f} is below safety threshold "
                f"ETB {self.SAFETY_THRESHOLD:,.2f}"
            )
        
        # Stale cheque alerts
        if all_stale:
            total_stale = sum(c["amount"] for c in all_stale)
            all_alerts.append(
                f"⚠️ {len(all_stale)} stale cheque(s) totaling ETB {total_stale:,.2f}"
            )
        
        return CashPosition(
            company_id=bank_accounts[0].get("company_id", "") if bank_accounts else "",
            snapshot_date=str(today),
            accounts=account_snapshots,
            total_raw_balance=total_raw,
            total_outstanding_cheques=total_cheques,
            total_uncleared_deposits=total_deposits,
            total_pending_transfers=total_transfers,
            adjusted_position=adjusted,
            by_bank=by_bank,
            stale_cheques=all_stale,
            alerts=all_alerts,
            previous_position=previous_position,
            change_amount=change_amount,
            change_percent=change_percent,
        )
    
    def _compute_account(
        self, account: Dict, transactions: List[Dict], cheques: List[Dict], today: date
    ) -> BankAccountSnapshot:
        """Compute adjusted balance for a single account"""
        
        acct_id = account.get("id")
        bank_name = account.get("bank_name", "Unknown")
        account_number = account.get("account_number", "")
        account_type = account.get("account_type", "current")
        
        # Get latest balance from transactions
        raw_balance = 0.0
        last_txn_date = None
        txn_count = 0
        
        if transactions:
            # Sort by date descending, get latest balance
            sorted_txns = sorted(transactions, key=lambda t: t.get("date", ""), reverse=True)
            for txn in sorted_txns:
                balance = txn.get("balance")
                if balance is not None and balance != 0:
                    raw_balance = float(balance)
                    break
            
            # If no balance found, sum amounts
            if raw_balance == 0:
                for txn in transactions:
                    amount = txn.get("amount", 0)
                    raw_balance += float(amount)
            
            last_txn_date = sorted_txns[0].get("date") if sorted_txns else None
            txn_count = len(transactions)
        
        # Outstanding cheques
        outstanding_cheques = 0.0
        for chq in cheques:
            if chq.get("status") in ("issued", "deposited", "clearing"):
                outstanding_cheques += float(chq.get("amount", 0))
        
        # Uncleared deposits (credit transactions in last 3 days that might not be reflected)
        uncleared_deposits = 0.0
        pending_transfers = 0.0
        alerts = []
        
        for txn in transactions:
            txn_date = txn.get("date")
            if isinstance(txn_date, str):
                try:
                    txn_date = date.fromisoformat(txn_date)
                except ValueError:
                    continue
            
            if not isinstance(txn_date, date):
                continue
            
            days_ago = (today - txn_date).days
            amount = float(txn.get("amount", 0))
            desc = (txn.get("description") or "").upper()
            
            # Recent credits might be uncleared
            if amount > 0 and days_ago <= 2:
                if any(kw in desc for kw in ["DEPOSIT", "CHEQUE DEPOSIT", "CD"]):
                    uncleared_deposits += amount
            
            # Pending transfers
            if "TRANSFER" in desc and "PENDING" in desc:
                pending_transfers += abs(amount)
        
        # Adjusted balance
        adjusted = raw_balance - outstanding_cheques + uncleared_deposits - pending_transfers
        
        # Account-level alerts
        if outstanding_cheques > raw_balance * 0.5:
            alerts.append(
                f"{bank_name} {account_number}: Outstanding cheques "
                f"({outstanding_cheques:,.0f}) are >50% of balance ({raw_balance:,.0f})"
            )
        
        return BankAccountSnapshot(
            account_id=acct_id,
            bank_name=bank_name,
            account_number=account_number,
            account_type=AccountType(account_type) if account_type in [e.value for e in AccountType] else AccountType.CURRENT,
            raw_balance=raw_balance,
            outstanding_cheques=outstanding_cheques,
            uncleared_deposits=uncleared_deposits,
            pending_transfers=pending_transfers,
            adjusted_balance=adjusted,
            last_transaction_date=str(last_txn_date) if last_txn_date else None,
            transaction_count=txn_count,
            alerts=alerts,
        )
    
    def to_dict(self, position: CashPosition) -> Dict:
        """Convert to dict for API response"""
        return {
            "company_id": position.company_id,
            "snapshot_date": position.snapshot_date,
            "accounts": [
                {
                    "account_id": a.account_id,
                    "bank_name": a.bank_name,
                    "account_number": a.account_number,
                    "account_type": a.account_type.value,
                    "currency": a.currency,
                    "raw_balance": round(a.raw_balance, 2),
                    "outstanding_cheques": round(a.outstanding_cheques, 2),
                    "uncleared_deposits": round(a.uncleared_deposits, 2),
                    "pending_transfers": round(a.pending_transfers, 2),
                    "adjusted_balance": round(a.adjusted_balance, 2),
                    "last_transaction_date": a.last_transaction_date,
                    "transaction_count": a.transaction_count,
                    "alerts": a.alerts,
                }
                for a in position.accounts
            ],
            "totals": {
                "raw_balance": round(position.total_raw_balance, 2),
                "outstanding_cheques": round(position.total_outstanding_cheques, 2),
                "uncleared_deposits": round(position.total_uncleared_deposits, 2),
                "pending_transfers": round(position.total_pending_transfers, 2),
                "adjusted_position": round(position.adjusted_position, 2),
            },
            "by_bank": {k: round(v, 2) for k, v in position.by_bank.items()},
            "stale_cheques": position.stale_cheques,
            "alerts": position.alerts,
            "trend": {
                "previous_position": round(position.previous_position, 2) if position.previous_position else None,
                "change_amount": round(position.change_amount, 2) if position.change_amount is not None else None,
                "change_percent": round(position.change_percent, 1) if position.change_percent is not None else None,
            },
            "safety_threshold": self.SAFETY_THRESHOLD,
            "below_threshold": position.adjusted_position < self.SAFETY_THRESHOLD,
        }
