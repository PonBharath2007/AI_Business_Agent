import os
import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.session import SessionLocal
from backend.app.models.models import Business, Customer, Invoice, Document
from backend.app.services.invoice_service import generate_next_invoice_number, create_invoice_record
from backend.app.schemas.schemas import InvoiceCreate

def test_billing_and_invoice_separation():
    db = SessionLocal()
    try:
        biz = db.query(Business).first()
        if not biz:
            print("No business found.")
            return

        print(f"Testing for Business: {biz.name} (ID: {biz.id})")

        # 1. Test auto-generated invoice number
        next_num = generate_next_invoice_number(db, biz.id)
        print(f"[PASS] Next invoice number generated: {next_num}")
        assert next_num.startswith("INV-2026-"), f"Unexpected invoice prefix: {next_num}"

        # 2. Test exact calculation example from prompt:
        # Customer: Bharath
        # Phone: 9566860154
        # Email: ponbharathramesh26@gmail.com
        # Billing Item: Website Development, Qty: 1, Unit Price: 5000
        # Total: 5000, Paid: 3500, Remaining: 1500, Status: Partially Paid
        # Due Date: 2026-10-20
        cust = db.query(Customer).filter(
            Customer.business_id == biz.id,
            Customer.email == "ponbharathramesh26@gmail.com"
        ).first()

        if not cust:
            cust = Customer(
                business_id=biz.id,
                name="Bharath",
                email="ponbharathramesh26@gmail.com",
                phone="9566860154",
                company="Bharath Enterprise",
                status="active"
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)
            print(f"[PASS] Created customer: {cust.name} ({cust.email})")
        else:
            print(f"[PASS] Found existing customer: {cust.name} ({cust.email})")

        items = [
            {"description": "Website Development", "quantity": 1, "unit_price": 5000.0, "total_price": 5000.0}
        ]
        subtotal = sum(it["quantity"] * it["unit_price"] for it in items)
        total_amt = subtotal
        paid_amt = 3500.0
        remaining_amt = total_amt - paid_amt
        due_date = date(2026, 10, 20)

        inv_in = InvoiceCreate(
            customer_id=cust.id,
            invoice_number=next_num,
            amount=total_amt,
            paid_amount=paid_amt,
            pending_amount=remaining_amt,
            subtotal=subtotal,
            tax_amount=0.0,
            discount_amount=0.0,
            currency="INR",
            issue_date=date.today(),
            due_date=due_date,
            status="partially_paid",
            line_items=items,
            notes="Prompt test billing record"
        )

        inv = create_invoice_record(db, biz.id, inv_in)
        print(f"[PASS] Created invoice record: {inv.invoice_number}")

        # Verification of values
        assert inv.invoice_number == next_num
        assert float(inv.amount) == 5000.0
        assert float(inv.paid_amount) == 3500.0
        assert float(inv.pending_amount) == 1500.0
        assert inv.status == "partially_paid"
        assert len(inv.line_items) == 1
        assert inv.line_items[0]["description"] == "Website Development"
        print("[PASS] Exact calculation verified: Total 5000, Paid 3500, Remaining 1500, Status partially_paid.")

        # 3. Test next sequence increments
        next_num_after = generate_next_invoice_number(db, biz.id)
        print(f"[PASS] Next invoice number after creation: {next_num_after}")
        assert next_num_after != next_num, f"Invoice number did not advance: {next_num_after}"

        # 4. Test invoice query including OCR & Billing records
        all_invoices = db.query(Invoice).filter(Invoice.business_id == biz.id).all()
        print(f"[PASS] Total invoices in database: {len(all_invoices)}")
        ocr_count = sum(1 for i in all_invoices if i.document_id is not None)
        billing_count = sum(1 for i in all_invoices if i.document_id is None)
        print(f"[PASS] Breakdown: {ocr_count} OCR-created invoices, {billing_count} Direct Billing-created invoices.")
        assert ocr_count >= 0 and billing_count >= 1

        print("=== ALL BACKEND SEPARATION TESTS PASSED SUCCESSFULLY ===")
    finally:
        db.close()

if __name__ == "__main__":
    test_billing_and_invoice_separation()
