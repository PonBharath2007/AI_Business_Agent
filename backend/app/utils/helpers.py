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
    
    # Clean currency symbols like $, ₹, €, £ and commas
    cleaned = str(amount_str)
    cleaned = re.sub(r'[^\d.]', '', cleaned)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def format_currency(amount: float, currency: str = "USD") -> str:
    currency = currency or "USD"
    symbol = "$"
    if currency == "INR" or "₹" in currency:
        symbol = "₹"
    elif currency == "EUR" or "€" in currency:
        symbol = "€"
    elif currency == "GBP" or "£" in currency:
        symbol = "£"
    return f"{symbol}{amount:,.2f}"
