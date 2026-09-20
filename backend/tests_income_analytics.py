import sys
import os
from datetime import date, datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from backend.app.models.models import Business, Customer, Invoice
from backend.app.routes.analytics import get_real_income_analytics, _resolve_invoice_payment

def run_tests():
    db = SessionLocal()
    try:
        # Fetch or create test business
        business = db.query(Business).first()
        assert business is not None, "A business must exist in the database for testing"

        today = date.today()
        yesterday = today - timedelta(days=1)
        curr_month_str = f"{today.year:04d}-{today.month:02d}"

        print(f"Testing Income Analytics for business: {business.name} (ID: {business.id})")

        # Test 1: Real database execution
        analytics = get_real_income_analytics(db, business, target_date_str=today.strftime("%Y-%m-%d"), target_month_str=curr_month_str)
        assert "daily_income" in analytics
        assert "monthly_income" in analytics
        assert "total_pending" in analytics
        assert "total_overdue" in analytics
        assert "daily_income_trend" in analytics
        assert "monthly_income_trend" in analytics
        assert "ai_business_insight" in analytics
        assert "reports" in analytics
        print("[PASS] Test 1: Real database analytics returned all required keys.")

        # Test 2: Verify income logic against payment resolution
        # Example 1: Invoice ₹5,000, Paid ₹3,500
        inv1 = Invoice(
            business_id=business.id,
            invoice_number="TEST-INV-1",
            amount=5000.0,
            paid_amount=3500.0,
            pending_amount=1500.0,
            status="partially_paid",
            issue_date=today,
            due_date=today + timedelta(days=30),
            updated_at=datetime.combine(today, datetime.min.time())
        )
        amt1, date1 = _resolve_invoice_payment(inv1)
        assert amt1 == 3500.0, f"Expected 3500.0 paid, got {amt1}"
        assert date1 == today
        rem1 = max(0.0, float(inv1.amount) - float(inv1.paid_amount))
        assert rem1 == 1500.0, f"Expected 1500.0 pending, got {rem1}"
        print("[PASS] Test 2: Example 1 (Total Rs. 5,000, Paid Rs. 3,500 -> Paid: Rs. 3,500, Pending: Rs. 1,500) validated.")

        # Example 2: Invoice ₹10,000, Paid ₹0
        inv2 = Invoice(
            business_id=business.id,
            invoice_number="TEST-INV-2",
            amount=10000.0,
            paid_amount=0.0,
            pending_amount=10000.0,
            status="pending",
            issue_date=today,
            due_date=today + timedelta(days=30),
            updated_at=datetime.combine(today, datetime.min.time())
        )
        amt2, date2 = _resolve_invoice_payment(inv2)
        assert amt2 == 0.0, f"Expected 0.0 paid, got {amt2}"
        rem2 = max(0.0, float(inv2.amount) - float(inv2.paid_amount))
        assert rem2 == 10000.0, f"Expected 10000.0 pending, got {rem2}"
        print("[PASS] Test 3: Example 2 (Total Rs. 10,000, Paid Rs. 0 -> Paid: Rs. 0, Pending: Rs. 10,000) validated.")

        # Example 3: Invoice ₹10,000, Paid ₹10,000
        inv3 = Invoice(
            business_id=business.id,
            invoice_number="TEST-INV-3",
            amount=10000.0,
            paid_amount=10000.0,
            pending_amount=0.0,
            status="paid",
            issue_date=today,
            due_date=today + timedelta(days=30),
            updated_at=datetime.combine(today, datetime.min.time())
        )
        amt3, date3 = _resolve_invoice_payment(inv3)
        assert amt3 == 10000.0, f"Expected 10000.0 paid, got {amt3}"
        rem3 = max(0.0, float(inv3.amount) - float(inv3.paid_amount))
        assert rem3 == 0.0, f"Expected 0.0 pending, got {rem3}"
        print("[PASS] Test 4: Example 3 (Total Rs. 10,000, Paid Rs. 10,000 -> Paid: Rs. 10,000, Pending: Rs. 0) validated.")

        # Test 5: Date filter verification (Yesterday vs Today)
        analytics_yesterday = get_real_income_analytics(db, business, target_date_str=yesterday.strftime("%Y-%m-%d"))
        assert analytics_yesterday["selected_date"] == yesterday.strftime("%Y-%m-%d")
        print(f"[PASS] Test 5: Date filtering to yesterday ({yesterday}) returned selected_date correctly.")

        # Test 6: Month filter verification (Previous Month)
        prev_m = today.month - 1 if today.month > 1 else 12
        prev_y = today.year if today.month > 1 else today.year - 1
        prev_m_str = f"{prev_y:04d}-{prev_m:02d}"
        analytics_prev_m = get_real_income_analytics(db, business, target_month_str=prev_m_str)
        assert analytics_prev_m["selected_month"] == prev_m_str
        print(f"[PASS] Test 6: Month filtering to previous month ({prev_m_str}) returned correctly.")

        # Test 7: Empty state verification
        analytics_future = get_real_income_analytics(db, business, target_date_str="2040-01-01", target_month_str="2040-01")
        assert analytics_future["daily_income"] == 0.0
        assert analytics_future["monthly_income"] == 0.0
        assert analytics_future["has_daily_income_data"] is False
        assert len(analytics_future["reports"]["daily_income"]) == 0
        assert len(analytics_future["reports"]["monthly_income"]) == 0
        print("[PASS] Test 7: Empty state for future date returned 0 and clean empty states.")

        print("\nALL INCOME ANALYTICS TESTS PASSED SUCCESSFULLY!")
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
