"""
Ethiopian Calendar → Gregorian Calendar Converter

Ethiopian calendar (Ge'ez) is used by CBE and other Ethiopian banks.
- 13 months: 12 months of 30 days + 1 month of 5 (or 6 in leap year)
- Ethiopian New Year: September 11 (Gregorian) — Meskerem 1
- Ethiopian year 2017 = Gregorian 2024/2025
- Ethiopian year 2018 = Gregorian 2025/2026

The offset: Ethiopian calendar is ~7-8 years behind Gregorian.
- Ethiopian month 1 (Meskerem) starts around Sep 11
- Ethiopian month 2 (Tikimt) starts around Oct 11
- ... and so on

Key for CBE: dates in PDF statements may be in Ethiopian format.
Must convert to Gregorian before storing in database.
"""

from datetime import date, timedelta
from typing import Optional, Tuple
import re


# Ethiopian month names and their Gregorian start dates (non-leap year)
# Meskerem starts on Sep 11 (or Sep 12 in Gregorian leap year)
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

# Gregorian month/day when each Ethiopian month starts (approximate)
# These are the base dates for Ethiopian year → Gregorian year mapping
# Ethiopian New Year (Meskerem 1) = September 11 in Gregorian
ETH_NEW_YEAR_MONTH = 9  # September
ETH_NEW_YEAR_DAY = 11


def is_gregorian_leap_year(year: int) -> bool:
    """Check if a Gregorian year is a leap year"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def is_ethiopian_leap_year(eth_year: int) -> bool:
    """Check if an Ethiopian year is a leap year"""
    # Ethiopian leap year: (year % 4) == 3
    return (eth_year % 4) == 3


def ethiopian_to_gregorian(eth_year: int, eth_month: int, eth_day: int) -> date:
    """
    Convert Ethiopian date to Gregorian date.
    
    Args:
        eth_year: Ethiopian year (e.g., 2017, 2018)
        eth_month: Ethiopian month (1-13)
        eth_day: Ethiopian day (1-30, or 1-6 for Pagume)
    
    Returns:
        Gregorian date object
    
    Examples:
        >>> ethiopian_to_gregorian(2017, 1, 1)  # Meskerem 1, 2017
        datetime.date(2024, 9, 11)
        >>> ethiopian_to_gregorian(2018, 1, 1)  # Meskerem 1, 2018
        datetime.date(2025, 9, 11)
    """
    # Validate inputs
    if not (1 <= eth_month <= 13):
        raise ValueError(f"Ethiopian month must be 1-13, got {eth_month}")
    
    if eth_month == 13:
        max_days = 6 if is_ethiopian_leap_year(eth_year) else 5
    else:
        max_days = 30
    
    if not (1 <= eth_day <= max_days):
        raise ValueError(f"Ethiopian day must be 1-{max_days} for month {eth_month}, got {eth_day}")
    
    # Step 1: Find the Gregorian date of Ethiopian New Year (Meskerem 1)
    # Ethiopian year N starts in September of Gregorian year N + 7 (approximately)
    # More precisely: Ethiopian New Year = Sep 11 in most years, Sep 12 in Gregorian leap years
    # when the Gregorian year is divisible by 4 and the Ethiopian year starts after Feb 29
    
    gregorian_new_year = eth_year + 7  # Approximate mapping
    
    # Check if the Gregorian year is a leap year
    # If so, Ethiopian New Year might be Sep 12 instead of Sep 11
    if is_gregorian_leap_year(gregorian_new_year):
        # In Gregorian leap years, Ethiopian New Year is Sep 12
        new_year_date = date(gregorian_new_year, ETH_NEW_YEAR_MONTH, 12)
    else:
        new_year_date = date(gregorian_new_year, ETH_NEW_YEAR_MONTH, ETH_NEW_YEAR_DAY)
    
    # Step 2: Calculate days from Meskerem 1 to the target date
    # Each full month has 30 days, Pagume has 5 or 6
    days_from_new_year = 0
    
    # Add days for complete months before the target month
    for m in range(1, eth_month):
        if m == 13:
            # Pagume month
            days_from_new_year += 6 if is_ethiopian_leap_year(eth_year) else 5
        else:
            days_from_new_year += 30
    
    # Add days within the target month (subtract 1 because day 1 = 0 offset)
    days_from_new_year += (eth_day - 1)
    
    # Step 3: Convert to Gregorian
    gregorian_date = new_year_date + timedelta(days=days_from_new_year)
    
    return gregorian_date


def gregorian_to_ethiopian(greg_date: date) -> Tuple[int, int, int]:
    """
    Convert Gregorian date to Ethiopian date.
    
    Args:
        greg_date: Gregorian date object
    
    Returns:
        Tuple of (ethiopian_year, ethiopian_month, ethiopian_day)
    """
    greg_year = greg_date.year
    greg_month = greg_date.month
    greg_day = greg_date.day
    
    # Step 1: Determine which Ethiopian year this falls in
    # Ethiopian year starts around Sep 11-12
    # If Gregorian date is before Sep 11, it's still the previous Ethiopian year
    
    if is_gregorian_leap_year(greg_year):
        new_year_day = 12
    else:
        new_year_day = 11
    
    if greg_month < 9 or (greg_month == 9 and greg_day < new_year_day):
        # Before Ethiopian New Year — previous Ethiopian year
        eth_year = greg_year - 7
    else:
        # After Ethiopian New Year
        eth_year = greg_year - 7 + 1
    
    # Step 2: Find the Gregorian date of Ethiopian New Year for this Ethiopian year
    greg_new_year_year = eth_year + 7
    if is_gregorian_leap_year(greg_new_year_year):
        new_year_date = date(greg_new_year_year, 9, 12)
    else:
        new_year_date = date(greg_new_year_year, 9, 11)
    
    # Step 3: Calculate days from New Year
    days_diff = (greg_date - new_year_date).days
    
    if days_diff < 0:
        # Shouldn't happen with correct year calculation above
        # Try the previous Ethiopian year
        eth_year -= 1
        greg_new_year_year = eth_year + 7
        if is_gregorian_leap_year(greg_new_year_year):
            new_year_date = date(greg_new_year_year, 9, 12)
        else:
            new_year_date = date(greg_new_year_year, 9, 11)
        days_diff = (greg_date - new_year_date).days
    
    # Step 4: Convert days to month and day
    # Each month has 30 days, Pagume has 5 or 6
    eth_month = (days_diff // 30) + 1
    eth_day = (days_diff % 30) + 1
    
    # Handle Pagume overflow
    if eth_month > 13:
        eth_month = 13
        max_pagume = 6 if is_ethiopian_leap_year(eth_year) else 5
        if eth_day > max_pagume:
            # This shouldn't happen, but handle gracefully
            eth_day = max_pagume
    
    # Handle the case where we're in Pagume (month 13)
    if eth_month == 13:
        max_pagume = 6 if is_ethiopian_leap_year(eth_year) else 5
        if eth_day > max_pagume:
            # We're past Pagume — this means we're in the next Ethiopian year
            eth_year += 1
            eth_month = 1
            eth_day = eth_day - max_pagume
    
    return (eth_year, eth_month, eth_day)


def parse_ethiopian_date(date_str: str) -> Optional[date]:
    """
    Parse a date string that might be in Ethiopian or Gregorian format.
    
    Handles formats commonly found in CBE PDF statements:
    - "15/06/2018" — could be Ethiopian (DD/MM/YYYY) or Gregorian
    - "2018/06/15" — YYYY/MM/DD
    - "15-06-2018" — DD-MM-YYYY
    - "2018-06-15" — ISO format (Gregorian)
    
    Strategy:
    - If year > 2000, assume Gregorian
    - If year < 2000 (e.g., 2017, 2018), could be Ethiopian
    - Try Gregorian first, then Ethiopian conversion
    
    Returns:
        Gregorian date object, or None if parsing fails
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Try common separators
    for sep in ['/', '-', '.', ' ']:
        parts = date_str.split(sep)
        if len(parts) == 3:
            try:
                # Try different orderings
                # DD/MM/YYYY (most common for Ethiopian banks)
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                
                if year < 100:
                    # Two-digit year — assume 20xx
                    year += 2000
                
                # If year looks like Ethiopian (e.g., 2017, 2018)
                # Ethiopian years are ~7 years behind Gregorian
                if 2000 <= year <= 2030:
                    # Could be either — try Gregorian first
                    try:
                        greg_date = date(year, month, day)
                        # If the year is very recent (2024+), it's likely Gregorian
                        if year >= 2024:
                            return greg_date
                        # If year < 2024, might be Ethiopian
                        # Check if it's a valid Ethiopian date
                        if 1 <= month <= 13 and 1 <= day <= 30:
                            # Try Ethiopian conversion
                            try:
                                eth_date = ethiopian_to_gregorian(year, month, day)
                                # If the result is reasonable (within 2020-2030), use it
                                if 2020 <= eth_date.year <= 2030:
                                    return eth_date
                            except ValueError:
                                pass
                        # Default to Gregorian
                        return greg_date
                    except ValueError:
                        pass
                
                # Try YYYY/MM/DD format
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
    
    Args:
        date_str: Date string from PDF
        assume_ethiopian: Force Ethiopian calendar interpretation
    
    Returns:
        Gregorian date object
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Parse the numeric components
    for sep in ['/', '-', '.', ' ']:
        parts = date_str.split(sep)
        if len(parts) == 3:
            try:
                p0, p1, p2 = int(parts[0]), int(parts[1]), int(parts[2])
                
                # Determine if DD/MM/YYYY or YYYY/MM/DD
                if p0 > 31:  # Must be YYYY/MM/DD
                    year, month, day = p0, p1, p2
                elif p2 > 31:  # Must be DD/MM/YYYY
                    day, month, year = p0, p1, p2
                else:
                    # Ambiguous — default to DD/MM/YYYY
                    day, month, year = p0, p1, p2
                
                if year < 100:
                    year += 2000
                
                # Check if Ethiopian
                if assume_ethiopian or (year < 2024 and 1 <= month <= 13):
                    try:
                        return ethiopian_to_gregorian(year, month, day)
                    except ValueError:
                        pass
                
                # Try as Gregorian
                try:
                    return date(year, month, day)
                except ValueError:
                    pass
                    
            except (ValueError, IndexError):
                continue
    
    return None


def format_ethiopian_date(greg_date: date) -> str:
    """
    Format a Gregorian date as Ethiopian date string.
    
    Returns: "DD/MM/YYYY (Ethiopian)" format
    """
    eth_year, eth_month, eth_day = gregorian_to_ethiopian(greg_date)
    month_name = ETHIOPIAN_MONTHS.get(eth_month, f"Month {eth_month}")
    return f"{eth_day:02d}/{eth_month:02d}/{eth_year} ({month_name})"


# Reference code mapping for matching logic
REFERENCE_CODES = {
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
}


def classify_reference_code(reference: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract and classify reference code from transaction reference.
    
    Args:
        reference: Transaction reference string (e.g., "FT-2026-001", "CHQ-001234")
    
    Returns:
        Tuple of (code, description) or (None, None) if no code found
    """
    if not reference:
        return (None, None)
    
    ref_upper = reference.upper().strip()
    
    # Try to match known codes
    for code, description in REFERENCE_CODES.items():
        if ref_upper.startswith(code):
            return (code, description)
        # Also check for code with separator
        if f" {code} " in f" {ref_upper} " or f"-{code}-" in f"-{ref_upper}-":
            return (code, description)
        # Check for code at word boundary
        if re.search(rf'\b{code}\b', ref_upper):
            return (code, description)
    
    return (None, None)


def extract_cheque_number(reference: str, description: str = "") -> Optional[str]:
    """
    Extract cheque number from reference or description.
    
    CBE format: "CHQ-001234" or "CHQ 001234" or in description "CHEQUE NO 1234"
    """
    text = f"{reference} {description}".upper()
    
    # Pattern 1: CHQ-NNNNNN
    match = re.search(r'CHQ[- ]?(\d{4,})', text)
    if match:
        return match.group(1)
    
    # Pattern 2: CHEQUE NO NNNNNN
    match = re.search(r'CHEQUE\s*(?:NO|NUMBER|#)\s*(\d{4,})', text)
    if match:
        return match.group(1)
    
    return None
