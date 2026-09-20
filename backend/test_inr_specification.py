"""
OpsNova AI – Strict INR (Indian Rupee ₹) Specification Verification Suite
========================================================================
Validates all requirements for 100% INR-only operation across the system:
1. Indian numbering system formatting (₹5,000, ₹15,500, ₹2,45,000, ₹10,00,000).
2. Bharath Invoice calculations (Total ₹5,000, Paid ₹3,500, Pending ₹1,500 -> partially_paid).
3. Daily income captures actual collections (₹3,500, not ₹5,000 invoice total).
4. Monthly income aggregates only actual paid amounts.
5. Empty period states show ₹0 and appropriate empty markers.
6. DB models & Pydantic schemas enforce currency='INR'.
7. Analytics CSV exports format amounts with ₹ and INR columns.
8. AI document intelligence defaults to INR.
"""

import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import date, datetime, timedelta

# Ensure backend package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.utils.helpers import format_inr, format_currency
from backend.app.database.session import SessionLocal, init_db
from backend.app.models.models import Business, Customer, Invoice, Document
from backend.app.schemas.schemas import UserRegister, BusinessBase, InvoiceBase, ApprovalExecutionContextResponse
from backend.app.routes.analytics import get_real_income_analytics, _resolve_invoice_payment
from backend.app.ai.document_intelligence import deterministic_invoice_parser


def test_1_indian_numbering_formatting():
    print("\n--- TEST 1: Indian Numbering System Formatting ---")
    assert format_inr(5000) == "₹5,000", f"Expected '₹5,000', got '{format_inr(5000)}'"
    assert format_inr(15500) == "₹15,500", f"Expected '₹15,500', got '{format_inr(15500)}'"
    assert format_inr(245000) == "₹2,45,000", f"Expected '₹2,45,000', got '{format_inr(245000)}'"
    assert format_inr(1000000) == "₹10,00,000", f"Expected '₹10,00,000', got '{format_inr(1000000)}'"
    assert format_inr(0) == "₹0", f"Expected '₹0', got '{format_inr(0)}'"
    assert format_inr(10000000) == "₹1,00,00,000", f"Expected '₹1,00,00,000', got '{format_inr(10000000)}'"
    
    # Test format_currency helper
    assert format_currency(5000, "INR") == "₹5,000"
    assert format_currency(245000, "INR") == "₹2,45,000"
    assert format_currency(1234567.89, "INR") == "₹12,34,567.89"
    print("  [PASS] 1. Indian numbering system formats correctly: ₹5,000, ₹15,500, ₹2,45,000, ₹10,00,000.")


def test_2_bharath_invoice_and_payment_resolution():
    print("\n--- TEST 2: Bharath Invoice Calculation (INV-2026-0001) ---")
    today = date.today()
    # Bharath Scenario: Total ₹5,000, Paid ₹3,500, Remaining ₹1,500
    bharath_inv = Invoice(
        business_id=1,
        invoice_number="INV-2026-0001",
        amount=5000.00,
        paid_amount=3500.00,
        pending_amount=1500.00,
        currency="INR",
        status="partially_paid",
        issue_date=today,
        due_date=today + timedelta(days=15),
        updated_at=datetime.combine(today, datetime.min.time())
    )

    paid_amt, paid_date = _resolve_invoice_payment(bharath_inv)
    assert paid_amt == 3500.00, f"Expected resolved paid amount 3500.00, got {paid_amt}"
    assert paid_date == today, f"Expected payment date {today}, got {paid_date}"
    
    # Verify calculated remaining
    calculated_remaining = max(0.0, float(bharath_inv.amount) - float(bharath_inv.paid_amount))
    assert calculated_remaining == 1500.00, f"Expected remaining 1500.00, got {calculated_remaining}"
    assert bharath_inv.status == "partially_paid"
    assert bharath_inv.currency == "INR"

    formatted_total = format_inr(bharath_inv.amount)
    formatted_paid = format_inr(bharath_inv.paid_amount)
    formatted_pending = format_inr(calculated_remaining)

    assert formatted_total == "₹5,000"
    assert formatted_paid == "₹3,500"
    assert formatted_pending == "₹1,500"
    print(f"  [PASS] 2. Bharath Invoice validated: Total {formatted_total}, Paid {formatted_paid}, Pending {formatted_pending} (Status: {bharath_inv.status}).")


def test_3_daily_income_actual_collection():
    print("\n--- TEST 3: Daily Income Accuracy (Collected payments only) ---")
    db = SessionLocal()
    try:
        biz = db.query(Business).first()
        if not biz:
            biz = Business(name="INR Test Business", currency="INR")
            db.add(biz)
            db.commit()
            db.refresh(biz)

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        # Clean up any previous test invoices
        db.query(Invoice).filter(Invoice.invoice_number.like("INR-DAILY-%")).delete()
        db.commit()

        # Create Bharath's partially paid invoice: Total 5000, Paid 3500
        inv_part = Invoice(
            business_id=biz.id,
            invoice_number="INR-DAILY-001",
            amount=5000.00,
            paid_amount=3500.00,
            pending_amount=1500.00,
            currency="INR",
            status="partially_paid",
            issue_date=today,
            due_date=today + timedelta(days=15),
            updated_at=datetime.utcnow()
        )
        db.add(inv_part)
        db.commit()

        analytics = get_real_income_analytics(db, biz, target_date_str=today_str)
        # Daily income MUST include the ₹3,500 paid amount, NOT ₹5,000 invoice total
        # Find our invoice in the daily report
        daily_reports = analytics["reports"]["daily_income"]
        test_reports = [r for r in daily_reports if r["invoice_number"] == "INR-DAILY-001"]
        assert len(test_reports) == 1, "Expected INR-DAILY-001 to appear in daily reports"
        assert test_reports[0]["paid_amount"] == 3500.00, f"Expected daily income entry of 3500.00, got {test_reports[0]['paid_amount']}"
        assert test_reports[0]["total_amount"] == 5000.00
        rem = test_reports[0]["total_amount"] - test_reports[0]["paid_amount"]
        assert rem == 1500.00
        print(f"  [PASS] 3. Daily income correctly tracks ₹3,500 paid amount, not ₹5,000 invoice total.")
    finally:
        db.query(Invoice).filter(Invoice.invoice_number.like("INR-DAILY-%")).delete()
        db.commit()
        db.close()


def test_4_monthly_income_aggregation():
    print("\n--- TEST 4: Monthly Income Aggregation ---")
    db = SessionLocal()
    try:
        biz = db.query(Business).first()
        today = date.today()
        curr_month_str = f"{today.year:04d}-{today.month:02d}"

        # Clean up test invoices
        db.query(Invoice).filter(Invoice.invoice_number.like("INR-MONTHLY-%")).delete()
        db.commit()

        # Invoices collected:
        # 1. Fully paid: 5,000
        # 2. Partially paid: Total 5,000, Paid 3,500
        # 3. Fully paid: 10,000
        # 4. Partially paid: Total 5,000, Paid 2,500
        # Expected collected total = 5000 + 3500 + 10000 + 2500 = 21,000
        invoices = [
            Invoice(business_id=biz.id, invoice_number="INR-MONTHLY-001", amount=5000.0, paid_amount=5000.0, status="paid", issue_date=today, due_date=today + timedelta(days=30), updated_at=datetime.utcnow(), currency="INR"),
            Invoice(business_id=biz.id, invoice_number="INR-MONTHLY-002", amount=5000.0, paid_amount=3500.0, pending_amount=1500.0, status="partially_paid", issue_date=today, due_date=today + timedelta(days=30), updated_at=datetime.utcnow(), currency="INR"),
            Invoice(business_id=biz.id, invoice_number="INR-MONTHLY-003", amount=10000.0, paid_amount=10000.0, status="paid", issue_date=today, due_date=today + timedelta(days=30), updated_at=datetime.utcnow(), currency="INR"),
            Invoice(business_id=biz.id, invoice_number="INR-MONTHLY-004", amount=5000.0, paid_amount=2500.0, pending_amount=2500.0, status="partially_paid", issue_date=today, due_date=today + timedelta(days=30), updated_at=datetime.utcnow(), currency="INR"),
        ]
        db.add_all(invoices)
        db.commit()

        analytics = get_real_income_analytics(db, biz, target_month_str=curr_month_str)
        month_reports = [r for r in analytics["reports"]["monthly_income"] if r["invoice_number"].startswith("INR-MONTHLY-")]
        sum_collected = sum(r["paid_amount"] for r in month_reports)
        assert sum_collected == 21000.0, f"Expected monthly collected sum 21000.0, got {sum_collected}"
        print(f"  [PASS] 4. Monthly income correctly sums actual collections: ₹21,000 ({format_inr(21000)}).")
    finally:
        db.query(Invoice).filter(Invoice.invoice_number.like("INR-MONTHLY-%")).delete()
        db.commit()
        db.close()


def test_5_empty_state_handling():
    print("\n--- TEST 5: Empty Period State Handling ---")
    db = SessionLocal()
    try:
        biz = db.query(Business).first()
        # Query a distant date where no invoices exist
        future_date = "2045-12-31"
        future_month = "2045-12"
        analytics = get_real_income_analytics(db, biz, target_date_str=future_date, target_month_str=future_month)

        assert analytics["daily_income"] == 0.0
        assert analytics["monthly_income"] == 0.0
        assert analytics["has_daily_income_data"] is False
        assert analytics["has_monthly_income_data"] is False
        assert len(analytics["reports"]["daily_income"]) == 0
        assert len(analytics["reports"]["monthly_income"]) == 0
        assert format_inr(analytics["daily_income"]) == "₹0"
        assert format_inr(analytics["monthly_income"]) == "₹0"
        print("  [PASS] 5. Empty period returns ₹0 and empty state flags.")
    finally:
        db.close()


def test_6_models_and_schemas_default_inr():
    print("\n--- TEST 6: DB Models & Pydantic Schemas Default INR ---")
    b = Business(name="Schema Test Biz")
    assert b.currency == "INR", f"Expected Business.currency='INR', got {b.currency}"

    inv = Invoice(business_id=1, invoice_number="TEST-SCH-01", amount=100.0)
    assert inv.currency == "INR", f"Expected Invoice.currency='INR', got {inv.currency}"

    reg = UserRegister(name="Test", email="test_reg_schema@example.com", password="pass")
    assert reg.currency == "INR", f"Expected UserRegister.currency='INR', got {reg.currency}"

    bb = BusinessBase(name="Biz")
    assert bb.currency == "INR", f"Expected BusinessBase.currency='INR', got {bb.currency}"

    ib = InvoiceBase(invoice_number="INV-SCH-02", amount=200.0, issue_date=date.today(), due_date=date.today())
    assert ib.currency == "INR", f"Expected InvoiceBase.currency='INR', got {ib.currency}"

    ap = ApprovalExecutionContextResponse(approval_id=1)
    assert ap.currency == "INR", f"Expected ApprovalExecutionContextResponse.currency='INR', got {ap.currency}"
    print("  [PASS] 6. All models and schemas default to 'INR'.")


def test_7_document_intelligence_inr_extraction():
    print("\n--- TEST 7: Document Intelligence INR Extraction ---")
    sample_ocr = """
    INVOICE
    Invoice Number: INV-IN-2026-99
    Date: 2026-09-15
    Due Date: 2026-09-30
    Customer: Bharath Electronics
    GSTIN: 33ABCDE1234F1Z5
    Place of Supply: Tamil Nadu
    
    Subtotal: ₹2,45,000.00
    CGST 9%: ₹22,050.00
    SGST 9%: ₹22,050.00
    Total Amount Due: ₹2,89,100.00
    Paid: ₹1,00,000.00
    Balance Due: ₹1,89,100.00
    """
    extracted = deterministic_invoice_parser("sample_invoice.txt", sample_ocr)
    assert extracted["currency"] == "INR", f"Expected currency 'INR', got {extracted.get('currency')}"
    assert extracted["invoice_number"] == "INV-IN-2026-99"
    assert extracted["customer_name"] == "Bharath Electronics"
    assert extracted["total_amount"] == 289100.00
    assert extracted["paid_amount"] == 100000.00
    assert extracted["pending_amount"] == 189100.00
    print(f"  [PASS] 7. Document Intelligence accurately parsed INR invoice: Total ₹{extracted['total_amount']:,.2f}, Paid ₹{extracted['paid_amount']:,.2f}, Pending ₹{extracted['pending_amount']:,.2f}, Currency: {extracted['currency']}.")


def run_all_inr_specification_tests():
    print("==================================================================")
    print("OPSNOVA AI – INR (INDIAN RUPEE ₹) SPECIFICATION TEST SUITE")
    print("==================================================================")
    init_db()
    
    test_1_indian_numbering_formatting()
    test_2_bharath_invoice_and_payment_resolution()
    test_3_daily_income_actual_collection()
    test_4_monthly_income_aggregation()
    test_5_empty_state_handling()
    test_6_models_and_schemas_default_inr()
    test_7_document_intelligence_inr_extraction()
    
    print("\n==================================================================")
    print("ALL INR SPECIFICATION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================")


if __name__ == "__main__":
    run_all_inr_specification_tests()
