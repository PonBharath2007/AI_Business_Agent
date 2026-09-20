import re
from datetime import datetime, date
from typing import Any, Dict, Optional

def parse_date(date_str: Any) -> Optional[date]:
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Try multiple standard formats
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y/%m/%d"
    ]
    cleaned = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    
    # Regex fallback for YYYY-MM-DD
    match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', cleaned)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
            
    return None

def parse_amount(amount_str: Any) -> float:
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    if not amount_str:
        return 0.0
    
    cleaned = str(amount_str).strip()
    # Extract the primary numeric sequence with optional commas and decimal places
    m = re.search(r'[\d,]+(?:\.\d{1,2})?', cleaned)
    if m:
        num_str = m.group(0).replace(',', '')
        try:
            return float(num_str)
        except ValueError:
            pass
    return 0.0

def format_inr(amount: float) -> str:
    try:
        val = float(amount or 0.0)
    except (ValueError, TypeError):
        val = 0.0

    is_neg = val < 0
    val = abs(val)

    if val % 1 == 0:
        s = f"{int(val)}"
        dec = ""
    else:
        s = f"{int(val)}"
        dec = f".{int(round((val - int(val)) * 100)):02d}"

    if len(s) <= 3:
        res = s
    else:
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        res = ",".join(groups) + "," + last3

    sign = "-" if is_neg else ""
    return f"{sign}₹{res}{dec}"


def format_currency(amount: float, currency: str = "INR") -> str:
    """
    Central currency formatter for OpsNova AI.
    The entire application strictly supports INR (₹) using Indian number grouping.
    """
    return format_inr(amount)

