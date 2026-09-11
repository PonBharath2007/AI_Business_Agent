import sys
import os
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ai.document_intelligence import (
    deterministic_invoice_parser,
    normalize_extracted_document,
    validate_invoice_extraction,
    extract_amount_by_labels,
    TOTAL_LABELS,
    PAID_LABELS,
    PENDING_LABELS
)

def run_all_tests():
    print("=" * 70)
    print("RUNNING EXTENSIVE OCR & INVOICE EXTRACTION TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Main User Error Fix Verification
    # -------------------------------------------------------------
    print("\n[TEST 1] Main Invoice Example:")
    main_invoice_text = """
Customer: Bharath
Invoice Number: INV-9001
Total Amount: ₹5,000
Paid Amount: ₹3,500
Unpaid/Pending Amount: ₹1,500
"""
    parsed = deterministic_invoice_parser("main_test.txt", main_invoice_text)
    normalized = normalize_extracted_document(parsed, "main_test.txt", main_invoice_text)
    validated = validate_invoice_extraction(normalized)

    print(f"  Customer: {validated.get('customer_name')}")
    print(f"  Total Amount: {validated.get('total_amount')}")
    print(f"  Paid Amount: {validated.get('paid_amount')}")
    print(f"  Pending Amount: {validated.get('pending_amount')}")
    print(f"  Payment Status: {validated.get('payment_status')}")
    print(f"  Summary: {validated.get('summary')}")
    print(f"  Action: {validated.get('recommended_action')}")

    assert validated["customer_name"] == "Bharath", f"Expected Bharath, got {validated.get('customer_name')}"
    assert validated["total_amount"] == 5000.0, f"Expected 5000.0, got {validated.get('total_amount')}"
    assert validated["paid_amount"] == 3500.0, f"Expected 3500.0, got {validated.get('paid_amount')}"
    assert validated["pending_amount"] == 1500.0, f"Expected 1500.0, got {validated.get('pending_amount')}"
    assert validated["payment_status"] == "Partially Paid", f"Expected Partially Paid, got {validated.get('payment_status')}"
    assert "₹1,500.00 remains pending" in validated["summary"], f"Summary missing 1,500 pending: {validated.get('summary')}"
    assert "1,500.00 pending balance" in validated["recommended_action"], f"Action missing 1,500 pending: {validated.get('recommended_action')}"
    assert validated["validation_status"] == "VALID", f"Expected VALID, got {validated.get('validation_status')}"
    print("✓ TEST 1 PASSED: Main invoice correctly separated into Total 5000, Paid 3500, Pending 1500, Partially Paid.")

    # -------------------------------------------------------------
    # 2. Formats A, B, C, D Verification
    # -------------------------------------------------------------
    print("\n[TEST 2] Invoice Layout Formats A, B, C, D:")
    formats = [
        ("Format A (Subtotal, Total, Paid, Balance Due)", """
Subtotal        ₹5,000
Total           ₹5,000
Paid            ₹3,500
Balance Due     ₹1,500
"""),
        ("Format B (Invoice Total, Amount Received, Balance)", """
Invoice Total   ₹5,000
Amount Received ₹3,500
Balance         ₹1,500
"""),
        ("Format C (Grand Total, Payment, Due)", """
Grand Total     ₹5,000
Payment         ₹3,500
Due             ₹1,500
"""),
        ("Format D (Total, Paid - No explicit balance)", """
Total           ₹5,000
Paid            ₹3,500
""")
    ]

    for label, txt in formats:
        p = deterministic_invoice_parser("fmt.txt", txt)
        n = normalize_extracted_document(p, "fmt.txt", txt)
        v = validate_invoice_extraction(n)
        print(f"  {label} -> Total={v['total_amount']}, Paid={v['paid_amount']}, Pending={v['pending_amount']}, Status={v['payment_status']}")
        assert v["total_amount"] == 5000.0, f"{label}: Expected 5000 total, got {v['total_amount']}"
        assert v["paid_amount"] == 3500.0, f"{label}: Expected 3500 paid, got {v['paid_amount']}"
        assert v["pending_amount"] == 1500.0, f"{label}: Expected 1500 pending, got {v['pending_amount']}"
        assert v["payment_status"] == "Partially Paid", f"{label}: Expected Partially Paid, got {v['payment_status']}"
    print("✓ TEST 2 PASSED: Formats A, B, C, D all parsed and calculated accurately.")

    # -------------------------------------------------------------
    # 3. Deterministic Cases 1, 2, 3, 4, 5
    # -------------------------------------------------------------
    print("\n[TEST 3] Edge Cases from Requirement 20:")

    # CASE 1: Total = 5000, Paid = 0 -> Pending = 5000, Status = Unpaid
    c1_txt = "Customer: Bharath\nInvoice No: INV-C1\nTotal Amount: ₹5,000\nPaid: 0"
    v1 = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("c1.txt", c1_txt), "c1.txt", c1_txt))
    assert v1["total_amount"] == 5000.0 and v1["paid_amount"] == 0.0 and v1["pending_amount"] == 5000.0
    assert v1["payment_status"] == "Unpaid"
    print("  ✓ Case 1 Passed: Total 5000, Paid 0 -> Pending 5000, Status Unpaid")

    # CASE 2: Total = 5000, Paid = 3500 -> Pending = 1500, Status = Partially Paid
    c2_txt = "Customer: Bharath\nInvoice No: INV-C2\nTotal Amount: ₹5,000\nPaid Amount: ₹3,500"
    v2 = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("c2.txt", c2_txt), "c2.txt", c2_txt))
    assert v2["total_amount"] == 5000.0 and v2["paid_amount"] == 3500.0 and v2["pending_amount"] == 1500.0
    assert v2["payment_status"] == "Partially Paid"
    print("  ✓ Case 2 Passed: Total 5000, Paid 3500 -> Pending 1500, Status Partially Paid")

    # CASE 3: Total = 5000, Paid = 5000 -> Pending = 0, Status = Paid
    c3_txt = "Customer: Bharath\nInvoice No: INV-C3\nTotal Amount: ₹5,000\nPaid Amount: ₹5,000"
    v3 = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("c3.txt", c3_txt), "c3.txt", c3_txt))
    assert v3["total_amount"] == 5000.0 and v3["paid_amount"] == 5000.0 and v3["pending_amount"] == 0.0
    assert v3["payment_status"] == "Paid"
    assert "fully paid" in v3["summary"].lower()
    print("  ✓ Case 3 Passed: Total 5000, Paid 5000 -> Pending 0, Status Paid")

    # CASE 4: Total = 5000, Paid = 6000 -> Flag for review (paid exceeds total)
    c4_txt = "Customer: Bharath\nInvoice No: INV-C4\nTotal Amount: ₹5,000\nPaid Amount: ₹6,000"
    v4 = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("c4.txt", c4_txt), "c4.txt", c4_txt))
    assert v4["validation_status"] == "NEEDS_REVIEW"
    assert any("exceeds total" in w.lower() for w in v4["validation_warnings"])
    print("  ✓ Case 4 Passed: Paid 6000 > Total 5000 correctly flagged NEEDS_REVIEW")

    # CASE 5: Total = 5000, Paid missing, Balance Due = 1500 -> Flag for review
    c5_txt = "Customer: Bharath\nInvoice No: INV-C5\nTotal Amount: ₹5,000\nBalance Due: ₹1,500"
    v5 = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("c5.txt", c5_txt), "c5.txt", c5_txt))
    assert v5["validation_status"] == "NEEDS_REVIEW"
    assert any("cannot be safely determined" in w.lower() for w in v5["validation_warnings"])
    print("  ✓ Case 5 Passed: Paid missing with explicit balance correctly flagged NEEDS_REVIEW")

    # -------------------------------------------------------------
    # 4. Conflicting Values Case (Section 18)
    # -------------------------------------------------------------
    print("\n[TEST 4] Conflicting Balance Values (Section 18):")
    conflict_txt = """
Customer: Bharath
Invoice No: INV-CONF
Total Amount: ₹5,000
Paid Amount: ₹3,500
Balance Due: ₹2,000
"""
    v_conf = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("conf.txt", conflict_txt), "conf.txt", conflict_txt))
    assert v_conf["validation_status"] == "NEEDS_REVIEW"
    assert any("Payment values require review: Total minus Paid does not match Balance Due" in w for w in v_conf["validation_warnings"])
    print("  ✓ Test 4 Passed: Conflict (5000 - 3500 != 2000) correctly flagged NEEDS_REVIEW with exact warning message.")

    # -------------------------------------------------------------
    # 5. Multi-Page Document Support (Section 9 & 20 Case 6)
    # -------------------------------------------------------------
    print("\n[TEST 5] Multi-page PDF / Document Support:")
    multi_page_txt = """
=== PAGE 1 of 2 ===
TAX INVOICE
Seller: Enterprise IT Solutions Ltd
Bill To: Bharath
Invoice Number: INV-MP-2026
Issue Date: 2026-09-01
Due Date: 2026-09-20

| Item | Description | Quantity | Rate | Total |
| 1 | Enterprise AI Operations Setup | 1 | 5000.00 | 5000.00 |

[Terms and conditions continue on next page...]

=== PAGE 2 of 2 ===
[FINANCIAL SUMMARY & RECONCILIATION]
Subtotal: ₹5,000.00
Tax: ₹0.00
Grand Total: ₹5,000.00
Amount Paid: ₹3,500.00
Balance Due: ₹1,500.00
Payment Status: Partially Paid

Remittance details: State Bank of India
Thank you for your business.
"""
    v_mp = validate_invoice_extraction(normalize_extracted_document(deterministic_invoice_parser("mp.txt", multi_page_txt), "mp.txt", multi_page_txt))
    assert v_mp["customer_name"] == "Bharath"
    assert v_mp["invoice_number"] == "INV-MP-2026"
    assert v_mp["total_amount"] == 5000.0
    assert v_mp["paid_amount"] == 3500.0
    assert v_mp["pending_amount"] == 1500.0
    assert v_mp["payment_status"] == "Partially Paid"
    assert v_mp["validation_status"] == "VALID"
    print("  ✓ Test 5 Passed: Multi-page payment summary extracted and validated perfectly.")

    print("\n" + "=" * 70)
    print("ALL OCR & INVOICE EXTRACTION UNIT TESTS PASSED PERFECTLY!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    if not run_all_tests():
        sys.exit(1)
