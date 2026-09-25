import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date, timedelta
from backend.app.database.session import SessionLocal
from backend.app.models.models import Business, Customer, Invoice
from backend.app.services.customer_service import (
    find_or_create_customer,
    compute_customer_financial_summary
)
from backend.app.services.invoice_service import create_invoice_record

def run_test():
    db = SessionLocal()
    try:
        # 1. Get or create a test business
        biz = db.query(Business).first()
        if not biz:
            biz = Business(
                name="Test Scenario Corp",
                email="biz_test@opsnova.com",
                currency="INR"
            )
            db.add(biz)
            db.commit()
            db.refresh(biz)

        print(f"Using business ID: {biz.id} ({biz.name})")

        # Clean up any existing test records for Bharath to ensure clean test
        old_custs = db.query(Customer).filter(
            Customer.business_id == biz.id,
            Customer.name == "Bharath"
        ).all()
        for c in old_custs:
            for inv in c.invoices:
                db.delete(inv)
            db.delete(c)
        db.commit()

        # Step 1: First purchase
        # Customer: Bharath, Phone: 9876543210, Email: bharath@gmail.com
        # Invoice: INV-001, Total = 5000, Paid = 3500, Pending = 1500
        print("\n--- STEP 1: First Purchase ---")
        cust1, is_new1, reason1 = find_or_create_customer(
            db=db,
            business_id=biz.id,
            name="Bharath",
            email="bharath@gmail.com",
            phone="9876543210"
        )
        assert is_new1 is True, f"Expected new customer, got is_new={is_new1}"
        print(f"Customer 1 created: ID {cust1.id}, Name: {cust1.name}, Status: is_new={is_new1} ({reason1})")

        from backend.app.schemas.schemas import InvoiceCreate

        inv1_payload = InvoiceCreate(
            customer_id=cust1.id,
            invoice_number="INV-001",
            amount=5000.0,
            paid_amount=3500.0,
            currency="INR",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status="partially_paid"
        )
        inv1 = create_invoice_record(db, biz.id, inv1_payload)
        print(f"Invoice 1 created: {inv1.invoice_number}, Total: {inv1.amount}, Paid: {inv1.paid_amount}, Pending: {inv1.pending_amount}, Status: {inv1.status}")
        assert float(inv1.amount) == 5000.0
        assert float(inv1.paid_amount) == 3500.0
        assert float(inv1.pending_amount) == 1500.0
        assert inv1.status == "partially_paid"

        # Step 2: Later the SAME customer purchases again
        # Phone formatted with country code: +91 9876543210
        # Invoice: INV-002, Total = 3000, Paid = 1000, Pending = 2000
        print("\n--- STEP 2: Second Purchase by SAME customer ---")
        cust2, is_new2, reason2 = find_or_create_customer(
            db=db,
            business_id=biz.id,
            name="Bharath",
            email="bharath@gmail.com",
            phone="+91 9876543210"
        )
        print(f"Customer 2 resolved: ID {cust2.id}, Name: {cust2.name}, Status: is_new={is_new2} ({reason2})")
        assert is_new2 is False, f"Expected customer reuse, but got is_new={is_new2}"
        assert cust2.id == cust1.id, f"Expected same customer ID {cust1.id}, got {cust2.id}"

        # Verify only ONE Bharath customer record exists
        bharath_count = db.query(Customer).filter(
            Customer.business_id == biz.id,
            Customer.name == "Bharath"
        ).count()
        assert bharath_count == 1, f"Expected 1 Bharath customer, got {bharath_count}"
        print(f"Verified customer count for 'Bharath': {bharath_count} (Only ONE record)")

        inv2_payload = InvoiceCreate(
            customer_id=cust2.id,
            invoice_number="INV-002",
            amount=3000.0,
            paid_amount=1000.0,
            currency="INR",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status="partially_paid"
        )
        inv2 = create_invoice_record(db, biz.id, inv2_payload)
        print(f"Invoice 2 created: {inv2.invoice_number}, Total: {inv2.amount}, Paid: {inv2.paid_amount}, Pending: {inv2.pending_amount}, Status: {inv2.status}")
        assert float(inv2.amount) == 3000.0
        assert float(inv2.paid_amount) == 1000.0
        assert float(inv2.pending_amount) == 2000.0
        assert inv2.status == "partially_paid"

        # Step 3: Check Customer Financial Summary
        # Expected:
        # Invoices: 2
        # Total Billed: ₹8,000
        # Total Paid: ₹4,500
        # Total Outstanding: ₹3,500
        print("\n--- STEP 3: Customer Financial Summary Verification ---")
        summary = compute_customer_financial_summary(cust1)
        print(f"Customer Summary: {summary}")
        assert summary["total_invoices"] == 2, f"Expected 2 invoices, got {summary['total_invoices']}"
        assert summary["total_billed"] == 8000.0, f"Expected 8000 billed, got {summary['total_billed']}"
        assert summary["total_paid"] == 4500.0, f"Expected 4500 paid, got {summary['total_paid']}"
        assert summary["outstanding_amount"] == 3500.0, f"Expected 3500 outstanding, got {summary['outstanding_amount']}"
        assert summary["total_pending"] == 3500.0
        assert summary["payment_status"] == "Partially Paid"
        print("SUMMARY VERIFIED: Total Billed=8,000, Total Paid=4,500, Outstanding=3,500")

        # Step 4: Pay Rs. 1,000 toward INV-001
        # Expected:
        # INV-001 -> Paid = 4500, Pending = 500
        # INV-002 -> Paid = 1000, Pending = 2000 (unchanged)
        # Customer Outstanding: Rs. 2,500
        print("\n--- STEP 4: Record Rs. 1,000 payment on INV-001 ---")
        from backend.app.routes.invoices import record_invoice_payment
        from backend.app.schemas.schemas import InvoicePaymentCreate

        pay_schema = InvoicePaymentCreate(
            amount=1000.0,
            notes="Customer paid Rs. 1,000 toward INV-001"
        )
        updated_inv1 = record_invoice_payment(
            invoice_id=inv1.id,
            payment_in=pay_schema,
            db=db,
            business=biz
        )
        print(f"Updated INV-001: Total={updated_inv1['amount']}, Paid={updated_inv1['paid_amount']}, Pending={updated_inv1['pending_amount']}, Status={updated_inv1['status']}")
        assert float(updated_inv1["paid_amount"]) == 4500.0
        assert float(updated_inv1["pending_amount"]) == 500.0
        assert updated_inv1["status"] == "partially_paid"

        # Check INV-002 remains unchanged
        db.refresh(inv2)
        print(f"Check INV-002: Total={inv2.amount}, Paid={inv2.paid_amount}, Pending={inv2.pending_amount}")
        assert float(inv2.paid_amount) == 1000.0
        assert float(inv2.pending_amount) == 2000.0

        # Recalculate customer summary
        db.refresh(cust1)
        summary_after_pay = compute_customer_financial_summary(cust1)
        print(f"Customer Summary after payment: {summary_after_pay}")
        assert summary_after_pay["total_billed"] == 8000.0
        assert summary_after_pay["total_paid"] == 5500.0
        assert summary_after_pay["outstanding_amount"] == 2500.0, f"Expected 2500 outstanding, got {summary_after_pay['outstanding_amount']}"
        print("PAYMENT TEST VERIFIED: INV-001 Pending=500, INV-002 Pending=2,000, Customer Outstanding=2,500")

        # Step 5: Test Customer 360 endpoint
        print("\n--- STEP 5: Customer 360 API Verification ---")
        from backend.app.services.business_intelligence import get_customer_360
        c360 = get_customer_360(db=db, business=biz, customer_id=cust1.id)
        assert c360 is not None
        assert c360["financials"]["total_billed"] == 8000.0
        assert c360["financials"]["total_paid"] == 5500.0
        assert c360["financials"]["outstanding_amount"] == 2500.0
        assert len(c360["invoices"]) == 2
        print(f"Customer 360 verified: Financials={c360['financials']}")

        print("\nALL TEST SCENARIO REQUIREMENTS PASSED WITH 100% SUCCESS!")

    finally:
        db.close()

if __name__ == "__main__":
    run_test()
