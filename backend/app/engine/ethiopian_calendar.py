"""
Ethiopian Calendar → Gregorian Calendar Converter

Uses py-ethiopian-date-converter library for accurate conversion.
Falls back to manual calculation if library not installed.

Ethiopian calendar (Ge'ez) is used by CBE and other Ethiopian banks.
- 13 months: 12 months of 30 days + 1 month of 5 (or 6 in leap year)
- Ethiopian New Year: September 11 (Gregorian) — Meskerem 1
- Ethiopian year 2018 = Gregorian 2025/2026
"""

from datetime import date, timedelta
from typing import Optional, Tuple
import re

# Try to use the official library first
try:
    from ethiopian_date import EthiopianDateConverter
    HAS_LIBRARY = True
except ImportError:
    HAS_LIBRARY = False

# Ethiopian month names
ETHIOPIAN_MONTHS = {
    1: "Meskerem",      # ~Sep 11 - Oct 10
    2: "Tikimt",        # ~Oct 11 - Nov 9
    3: "Hidar",         # ~Nov 10 - Dec 9
    4: "Tahsas",        # ~Dec 10 - Jan 8
    5: "Tir",           # ~Jan 9 - Feb 7
    6: "Yekatit",       # ~Feb 8 - Mar 9
    7: "Megabit",       # ~Mar 10 - Apr 8
    8: "Miazia",        # ~Apr 9 - May 8
    9: "Ginbot",        # ~May 9 - Jun 7
    10: "Sene",         # ~Jun 8 - Jul 7
    11: "Hamle",        # ~Jul 8 - Aug 6
    12: "Nehase",       # ~Aug 7 - Sep 5
    13: "Pagume",       # ~Sep 6 - Sep 10 (5 or 6 days)
}


def _is_ethiopian_leap_year(eth_year: int) -> bool:
    """Check if an Ethiopian year is a leap year"""
    return (eth_year % 4) == 3


def _is_gregorian_leap_year(year: int) -> bool:
    """Check if a Gregorian year is a leap year"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def ethiopian_to_gregorian(eth_year: int, eth_month: int, eth_day: int) -> date:
    """
    Convert Ethiopian date to Gregorian date.
    
    Uses py-ethiopian-date-converter library if available,
    falls back to manual calculation.
    
    Args:
        eth_year: Ethiopian year (e.g., 2017, 2018)
        eth_month: Ethiopian month (1-13)
        eth_day: Ethiopian day (1-30, or 1-6 for Pagume)
    
    Returns:
        Gregorian date object
    """
    if not (1 <= eth_month <= 13):
        raise ValueError(f"Ethiopian month must be 1-13, got {eth_month}")
    
    if eth_month == 13:
        max_days = 6 if _is_ethiopian_leap_year(eth_year) else 5
    else:
        max_days = 30
    
    if not (1 <= eth_day <= max_days):
        raise ValueError(f"Ethiopian day must be 1-{max_days} for month {eth_month}, got {eth_day}")
    
    # Use library if available
    if HAS_LIBRARY:
        converter = EthiopianDateConverter()
        greg_date = converter.to_gregorian(eth_year, eth_month, eth_day)
        return date(greg_date.year, greg_date.month, greg_date.day)
    
    # Fallback: manual calculation
    return _manual_ethiopian_to_gregorian(eth_year, eth_month, eth_day)


def _manual_ethiopian_to_gregorian(eth_year: int, eth_month: int, eth_day: int) -> date:
    """Manual calculation when library not available"""
    gregorian_new_year = eth_year + 7
    
    if _is_gregorian_leap_year(gregorian_new_year):
        new_year_date = date(gregorian_new_year, 9, 12)
    else:
        new_year_date = date(gregorian_new_year, 9, 11)
    
    days_from_new_year = 0
    for m in range(1, eth_month):
        if m == 13:
            days_from_new_year += 6 if _is_ethiopian_leap_year(eth_year) else 5
        else:
            days_from_new_year += 30
    days_from_new_year += (eth_day - 1)
    
    return new_year_date + timedelta(days=days_from_new_year)


def gregorian_to_ethiopian(greg_date: date) -> Tuple[int, int, int]:
    """
    Convert Gregorian date to Ethiopian date.
    
    Uses py-ethiopian-date-converter library if available.
    """
    if HAS_LIBRARY:
        converter = EthiopianDateConverter()
        eth_date = converter.to_ethiopian(greg_date.year, greg_date.month, greg_date.day)
        return (eth_date.year, eth_date.month, eth_date.day)
    
    return _manual_gregorian_to_ethiopian(greg_date)


def _manual_gregorian_to_ethiopian(greg_date: date) -> Tuple[int, int, int]:
    """Manual calculation when library not available"""
    greg_year = greg_date.year
    greg_month = greg_date.month
    greg_day = greg_date.day
    
    if _is_gregorian_leap_year(greg_year):
        new_year_day = 12
    else:
        new_year_day = 11
    
    if greg_month < 9 or (greg_month == 9 and greg_day < new_year_day):
        eth_year = greg_year - 7
    else:
        eth_year = greg_year - 7 + 1
    
    greg_new_year_year = eth_year + 7
    if _is_gregorian_leap_year(greg_new_year_year):
        new_year_date = date(greg_new_year_year, 9, 12)
    else:
        new_year_date = date(greg_new_year_year, 9, 11)
    
    days_diff = (greg_date - new_year_date).days
    
    if days_diff < 0:
        eth_year -= 1
        greg_new_year_year = eth_year + 7
        if _is_gregorian_leap_year(greg_new_year_year):
            new_year_date = date(greg_new_year_year, 9, 12)
        else:
            new_year_date = date(greg_new_year_year, 9, 11)
        days_diff = (greg_date - new_year_date).days
    
    eth_month = (days_diff // 30) + 1
    eth_day = (days_diff % 30) + 1
    
    if eth_month > 13:
        eth_month = 13
        max_pagume = 6 if _is_ethiopian_leap_year(eth_year) else 5
        if eth_day > max_pagume:
            eth_day = max_pagume
    
    if eth_month == 13:
        max_pagume = 6 if _is_ethiopian_leap_year(eth_year) else 5
        if eth_day > max_pagume:
            eth_year += 1
            eth_month = 1
            eth_day = eth_day - max_pagume
    
    return (eth_year, eth_month, eth_day)


def parse_ethiopian_date(date_str: str) -> Optional[date]:
    """
    Parse a date string that might be in Ethiopian or Gregorian format.
    
    Strategy:
    - If year > 2024, assume Gregorian
    - If year < 2024 (e.g., 2017, 2018), could be Ethiopian
    - Try Gregorian first, then Ethiopian conversion
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    for sep in ['/', '-', '.', ' ']:
        parts = date_str.split(sep)
        if len(parts) == 3:
            try:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                
                if year < 100:
                    year += 2000
                
                if 2000 <= year <= 2030:
                    try:
                        greg_date = date(year, month, day)
                        if year >= 2024:
                            return greg_date
                        if 1 <= month <= 13 and 1 <= day <= 30:
                            try:
                                eth_date = ethiopian_to_gregorian(year, month, day)
                                if 2020 <= eth_date.year <= 2030:
                                    return eth_date
                            except ValueError:
                                pass
                        return greg_date
                    except ValueError:
                        pass
                
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                if year < 100:
                    year += 2000
                
                try:
                    return date(year, month, day)
                except ValueError:
                    pass
                    
            except (ValueError, IndexError):
                continue
    
    return None


def parse_cbe_date(date_str: str, assume_ethiopian: bool = False) -> Optional[date]:
    """
    Parse a date from CBE PDF statement.
    
    CBE statements may use Ethiopian calendar. This function:
    1. Tries to parse as Gregorian first
    2. If assume_ethiopian=True or year < 2024, converts from Ethiopian
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    for sep in ['/', '-', '.', ' ']:
        parts = date_str.split(sep)
        if len(parts) == 3:
            try:
                p0, p1, p2 = int(parts[0]), int(parts[1]), int(parts[2])
                
                if p0 > 31:
                    year, month, day = p0, p1, p2
                elif p2 > 31:
                    day, month, year = p0, p1, p2
                else:
                    day, month, year = p0, p1, p2
                
                if year < 100:
                    year += 2000
                
                if assume_ethiopian or (year < 2024 and 1 <= month <= 13):
                    try:
                        return ethiopian_to_gregorian(year, month, day)
                    except ValueError:
                        pass
                
                try:
                    return date(year, month, day)
                except ValueError:
                    pass
                    
            except (ValueError, IndexError):
                continue
    
    return None


def format_ethiopian_date(greg_date: date) -> str:
    """Format a Gregorian date as Ethiopian date string"""
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg_date)
    month_name = ETHIOPIAN_MONTHS.get(eth_month, f"Month {eth_month}")
    return f"{eth_day:02d}/{eth_month:02d}/{eth_year} ({month_name})"


# ─── Reference Code System (Configurable per bank) ─────────────────

# Default reference codes — can be overridden per bank
DEFAULT_REFERENCE_CODES = {
    "FT": "Fund Transfer — intercompany candidate",
    "TT": "Telegraphic Transfer — FX transaction, check NBE rate",
    "CHQ": "Cheque — link to cheque register",
    "CD": "Cheque Deposit — deposit in transit candidate",
    "CPO": "Cash Payment Order — payroll/vendor payment",
    "ECS": "Electronic Clearing — salary/auto-debit",
    "PKR": "Payment to Supplier — vendor payment, match to AP",
    "VPCH": "Voucher Payment — government/institutional",
    "SO": "Standing Order — recurring payment",
    "RT": "Real Time transfer",
    "INT": "Interest — bank interest payment",
    "FEE": "Fee — bank service charge",
    "TRF": "Transfer — alternative to FT",
    "TRX": "Transaction — generic",
    "XFER": "Transfer — alternative code",
    "TRANSFER": "Transfer — alternative code",
    "IBFT": "Interbank Fund Transfer",
}

# Per-bank reference code overrides
# Each bank can define its own codes
BANK_REFERENCE_CODES = {
    "cbe": DEFAULT_REFERENCE_CODES.copy(),
    "dashen": DEFAULT_REFERENCE_CODES.copy(),
    "awash": DEFAULT_REFERENCE_CODES.copy(),
}


def classify_reference_code(reference: str, bank: str = "cbe") -> Tuple[Optional[str], Optional[str]]:
    """
    Extract and classify reference code from transaction reference.
    
    Uses bank-specific code dictionary if available.
    
    Args:
        reference: Transaction reference string
        bank: Bank name for code lookup (default: "cbe")
    
    Returns:
        Tuple of (code, description) or (None, None)
    """
    if not reference:
        return (None, None)
    
    ref_upper = reference.upper().strip()
    
    # Get bank-specific codes, fall back to defaults
    codes = BANK_REFERENCE_CODES.get(bank.lower(), DEFAULT_REFERENCE_CODES)
    
    # Try to match known codes (longest match first)
    sorted_codes = sorted(codes.keys(), key=len, reverse=True)
    
    for code in sorted_codes:
        if ref_upper.startswith(code):
            return (code, codes[code])
        if re.search(rf'\b{code}\b', ref_upper):
            return (code, codes[code])
    
    return (None, None)


def extract_cheque_number(reference: str, description: str = "") -> Optional[str]:
    """
    Extract cheque number from reference or description.
    
    CBE format: "CHQ-001234" or "CHQ 001234" or in description "CHEQUE NO 1234"
    """
    text = f"{reference} {description}".upper()
    
    match = re.search(r'CHQ[- ]?(\d{4,})', text)
    if match:
        return match.group(1)
    
    match = re.search(r'CHEQUE\s*(?:NO|NUMBER|#)\s*(\d{4,})', text)
    if match:
        return match.group(1)
    
    return None


# ─── Fiscal Year Configuration ─────────────────────────────────────

class FiscalYearType:
    """Fiscal year types for different customer types"""
    ETHIOPIAN = "ethiopian"    # Jul 8 - Jul 7 (government, public sector)
    GREGORIAN = "gregorian"    # Jan 1 - Dec 31 (private companies)


def get_fiscal_year_end(fy_type: str = FiscalYearType.GREGORIAN, year: int = 2026) -> date:
    """Get the fiscal year end date for a given type and year"""
    if fy_type == FiscalYearType.ETHIOPIAN:
        return date(year, 7, 7)  # Ethiopian fiscal year ends Jul 7
    else:
        return date(year, 12, 31)  # Gregorian fiscal year ends Dec 31


def is_fiscal_year_boundary(d1: date, d2: date, fy_type: str = FiscalYearType.GREGORIAN) -> bool:
    """Check if two dates cross a fiscal year boundary"""
    if fy_type == FiscalYearType.ETHIOPIAN:
        fy_end_1 = date(d1.year, 7, 7)
        fy_end_2 = date(d2.year, 7, 7)
        in_fy1 = d1 <= fy_end_1
        in_fy2 = d2 <= fy_end_2
        return (d1.year != d2.year) or (in_fy1 != in_fy2)
    else:
        return d1.year != d2.year
