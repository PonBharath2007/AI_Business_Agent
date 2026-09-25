import re
from datetime import date
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.models import Customer, Invoice
from backend.app.ai.document_intelligence import is_valid_customer_name
from backend.app.utils.logger import logger

def normalize_phone(phone: Optional[str]) -> str:
    """
    Extracts all digits from phone string.
    E.g. '+91 9876543210', '9876543210', '+919876543210' -> '919876543210' or '9876543210'
    """
    if not phone:
        return ""
    return re.sub(r'\D', '', str(phone).strip())

def phone_matches(phone1: Optional[str], phone2: Optional[str]) -> bool:
    """
    Compares two phone numbers by their normalized digit representation.
    If both have at least 10 digits, checks if the last 10 digits match.
    """
    d1 = normalize_phone(phone1)
    d2 = normalize_phone(phone2)
    if not d1 or not d2:
        return False
    if len(d1) >= 10 and len(d2) >= 10:
        return d1[-10:] == d2[-10:]
    return d1 == d2

def normalize_email(email: Optional[str]) -> str:
    """
    Trims and lowercases an email address.
    """
    if not email:
        return ""
    return str(email).strip().lower()

def normalize_name(name: Optional[str]) -> str:
    """
    Removes punctuation and lowercases a customer name for robust comparison.
    """
    if not name:
        return ""
    return re.sub(r'[^\w\s]', '', str(name)).lower().strip()

def find_matching_customer(
    db: Session,
    business_id: int,
    customer_id: Optional[int] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    name: Optional[str] = None
) -> Tuple[Optional[Customer], str]:
    """
    Customer Matching Engine with strict priority:
    1. Customer ID, if already known
    2. Exact normalized email
    3. Exact normalized phone number (e.g. 9876543210 == +91 9876543210)
    4. Exact normalized customer name + supporting contact information
    """
    # 1. Customer ID if known
    if customer_id:
        try:
            cid_int = int(customer_id)
            c = db.query(Customer).filter(Customer.id == cid_int, Customer.business_id == business_id).first()
            if c:
                return c, f"Matched by Customer ID #{c.id}"
        except (ValueError, TypeError):
            pass

    # 2. Exact normalized email
    norm_email = normalize_email(email)
    if norm_email and "@" in norm_email:
        c = db.query(Customer).filter(
            Customer.business_id == business_id,
            Customer.email.ilike(norm_email)
        ).first()
        if c:
            return c, f"Matched by exact Email '{c.email}'"

    # 3. Exact normalized phone number
    norm_ph = normalize_phone(phone)
    if norm_ph and len(norm_ph) >= 10:
        all_customers = db.query(Customer).filter(Customer.business_id == business_id).all()
        for c in all_customers:
            if c.phone and phone_matches(c.phone, norm_ph):
                return c, f"Matched by Phone '{c.phone}'"

    # 4. Exact normalized customer name
    norm_nm = normalize_name(name)
    if norm_nm and is_valid_customer_name(name) and len(norm_nm) >= 2:
        all_customers = db.query(Customer).filter(Customer.business_id == business_id).all()
        # First check exact normalized name
        for c in all_customers:
            c_norm = normalize_name(c.name)
            if c_norm == norm_nm:
                return c, f"Matched by exact Name '{c.name}'"

    return None, "No existing customer found"

def find_or_create_customer(
    db: Session,
    business_id: int,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    customer_id: Optional[int] = None
) -> Tuple[Customer, bool, str]:
    """
    Finds existing customer using matching priority, or creates a new customer record.
    Returns: (customer, is_new, match_reason)
    """
    existing, reason = find_matching_customer(
        db=db,
        business_id=business_id,
        customer_id=customer_id,
        email=email,
        phone=phone,
        name=name
    )

    if existing:
        updated = False
        # Update missing contact details if provided on new invoice
        clean_email = normalize_email(email)
        if clean_email and not existing.email:
            existing.email = clean_email
            updated = True
        clean_phone = (phone or "").strip()
        if clean_phone and not existing.phone:
            existing.phone = clean_phone
            updated = True
        clean_comp = (company or "").strip()
        if clean_comp and not existing.company:
            existing.company = clean_comp
            updated = True

        if updated:
            try:
                db.commit()
                db.refresh(existing)
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not update customer contact details: {e}")

        return existing, False, reason

    # Create new customer
    clean_name = (name or "").strip()
    if not clean_name:
        clean_name = "Unnamed Customer"

    new_cust = Customer(
        business_id=business_id,
        name=clean_name,
        email=normalize_email(email) or None,
        phone=(phone or "").strip() or None,
        company=(company or "").strip() or clean_name,
        status="active"
    )
    db.add(new_cust)
    db.commit()
    db.refresh(new_cust)

    return new_cust, True, "New customer created"

def compute_customer_financial_summary(customer: Customer) -> Dict[str, Any]:
    """
    Computes accurate financial summary for a customer across ALL of that customer's invoices:
    - total_invoices
    - total_billed / total_amount
    - total_paid / paid_amount
    - total_pending / outstanding_amount
    - overdue_amount
    - payment_status ("Paid", "Partially Paid", "Unpaid", "No Invoices")
    """
    invoices = customer.invoices or []
    today = date.today()

    total_billed = 0.0
    total_paid = 0.0
    total_pending = 0.0
    overdue_amount = 0.0

    for inv in invoices:
        tot = float(inv.amount or 0.0)
        paid = float(inv.paid_amount or 0.0)

        # Payment calculation rules per invoice:
        # If paid_amount >= total_amount: pending_amount = 0, payment_status = Paid
        # If paid_amount > 0 and paid_amount < total_amount: pending_amount = total_amount - paid_amount, payment_status = Partially Paid
        # If paid_amount <= 0: pending_amount = total_amount, payment_status = Unpaid
        if (paid >= tot and tot > 0) or (inv.status or "").lower() == "paid":
            pend = 0.0
            paid = tot
        elif inv.pending_amount is not None:
            pend = max(0.0, float(inv.pending_amount))
        else:
            pend = max(0.0, tot - paid)

        total_billed += tot
        total_paid += paid
        total_pending += pend

        if pend > 0 and inv.due_date and inv.due_date < today:
            overdue_amount += pend

    total_billed = round(total_billed, 2)
    total_paid = round(total_paid, 2)
    total_pending = round(total_pending, 2)
    overdue_amount = round(overdue_amount, 2)

    # Derived customer payment status
    if len(invoices) == 0:
        payment_status = "No Invoices"
    elif total_pending <= 0:
        payment_status = "Paid"
    elif total_paid > 0 and total_pending > 0:
        payment_status = "Partially Paid"
    else:
        payment_status = "Unpaid"

    return {
        "total_invoices": len(invoices),
        "total_billed": total_billed,
        "total_amount": total_billed,
        "total_paid": total_paid,
        "paid_amount": total_paid,
        "total_pending": total_pending,
        "pending_amount": total_pending,
        "outstanding_amount": total_pending,
        "overdue_amount": overdue_amount,
        "payment_status": payment_status
    }
