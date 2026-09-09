import re
from typing import Tuple

def normalize_and_validate_phone(phone: str) -> Tuple[bool, str, str]:
    """
    Normalizes and validates telephone numbers for SMS dispatch.
    Returns: (is_valid: bool, normalized_phone: str, error_message: str)
    
    Supports:
    - Standard Indian 10-digit mobile numbers: e.g. 9876543210 -> +919876543210
    - Indian numbers with trunk prefix 0: e.g. 09876543210 -> +919876543210
    - Indian numbers with 91 prefix: e.g. 919876543210 -> +919876543210
    - Indian numbers with +91: e.g. +919876543210 -> +919876543210
    - International numbers starting with + (7-15 digits E.164 standard)
    """
    if not phone or not isinstance(phone, str):
        return False, "", "Phone number cannot be empty."
    
    raw = phone.strip()
    if not raw:
        return False, "", "Phone number cannot be empty."

    # Remove formatting characters like spaces, dashes, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", raw)

    # 1. Standard + prefix check
    if cleaned.startswith("+"):
        digits = cleaned[1:]
        if not digits.isdigit():
            return False, "", f"Invalid characters in phone number: {phone}"
        if len(digits) < 7 or len(digits) > 15:
            return False, "", f"Phone number length must be between 7 and 15 digits according to E.164: {phone}"
        
        # Indian specific validation if +91
        if digits.startswith("91") and len(digits) == 12:
            mobile_part = digits[2:]
            if mobile_part[0] not in "6789":
                return False, "", f"Indian mobile numbers must start with 6, 7, 8, or 9: {phone}"
            return True, f"+{digits}", ""
        
        return True, f"+{digits}", ""

    # 2. No leading +, check if all digits
    if not cleaned.isdigit():
        return False, "", f"Invalid phone number format: {phone}"

    # 10 digits starting with 6-9 (Indian standard mobile)
    if len(cleaned) == 10:
        if cleaned[0] in "6789":
            return True, f"+91{cleaned}", ""
        else:
            return False, "", f"10-digit mobile numbers must start with 6, 7, 8, or 9: {phone}"

    # 11 digits starting with 0 (Indian trunk dial e.g. 09876543210)
    if len(cleaned) == 11 and cleaned.startswith("0"):
        mobile_part = cleaned[1:]
        if mobile_part[0] in "6789":
            return True, f"+91{mobile_part}", ""
        else:
            return False, "", f"Indian mobile numbers must start with 6, 7, 8, or 9: {phone}"

    # 12 digits starting with 91 (Indian number without +)
    if len(cleaned) == 12 and cleaned.startswith("91"):
        mobile_part = cleaned[2:]
        if mobile_part[0] in "6789":
            return True, f"+{cleaned}", ""
        else:
            return False, "", f"Indian mobile numbers must start with 6, 7, 8, or 9: {phone}"

    # General international number without + if 11-15 digits
    if 7 <= len(cleaned) <= 15:
        return True, f"+{cleaned}", ""

    return False, "", f"Invalid phone number length ({len(cleaned)} digits): {phone}"
