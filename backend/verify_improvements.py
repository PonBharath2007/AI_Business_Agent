import sys
import os
import json

from pathlib import Path

# Ensure utf-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("STARTING VERIFICATION OF TWO MAJOR REQUIREMENTS")
    print("=" * 60)

    # 1. Authenticate as the primary business user (User 20, business_id 21)
    print("\n[STEP 1] Authenticating as Primary Business User (ID 20)...")
    from backend.app.auth.jwt import create_access_token
    token = create_access_token(data={"sub": "20", "email": "ponbharathramesh26@gmail.com"})
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Authenticated successfully as business user.")

    # 2. Test Customer 48 Invoice Auto-Selection (Requirement 1)
    print("\n[STEP 2] Testing Customer 48 (Bharath) Invoices...")
    cust_res = client.get("/api/customers/48/invoices", headers=headers)
    assert cust_res.status_code == 200, f"Expected 200, got {cust_res.status_code}"
    cust_data = cust_res.json()
    print("Customer Data:", cust_data["customer"])
    print("Recommended Invoice ID:", cust_data["recommended_invoice_id"])
    print(f"Total Invoices found for Customer 48: {len(cust_data['invoices'])}")
    
    assert cust_data["customer"]["name"].lower() == "bharath"
    assert cust_data["customer"]["phone"] == "9566860154"
    assert cust_data["customer"]["email"] == "ponbharathramesh26@gmail.com"
    assert cust_data["recommended_invoice_id"] is not None
    assert len(cust_data["invoices"]) >= 1

    rec_inv = next(i for i in cust_data["invoices"] if i["id"] == cust_data["recommended_invoice_id"])
    print("Auto-selected Invoice Details:")
    print(f"  - Number: {rec_inv.get('invoice_number')}")
    print(f"  - Total Amount: {rec_inv.get('total_amount') or rec_inv.get('amount')}")
    print(f"  - Paid Amount: {rec_inv.get('paid_amount')}")
    print(f"  - Pending Amount: {rec_inv.get('pending_amount')}")
    print(f"  - Due Date: {rec_inv.get('due_date')}")
    print(f"  - Status: {rec_inv.get('status')}")
    print("✓ Customer invoice auto-selection and field mapping verified.")

    # 3. Test Customer with NO Invoices
    print("\n[STEP 3] Testing Customer with NO Invoices...")
    # Create a dummy customer without invoices
    new_cust = client.post("/api/customers", json={
        "name": "Zero Invoice User",
        "email": "zero_invoices@test.com",
        "phone": "9998887770"
    }, headers=headers)
    assert new_cust.status_code in [200, 201], f"Customer creation failed: {new_cust.status_code} {new_cust.text}"
    zero_cust_id = new_cust.json()["id"]

    zero_res = client.get(f"/api/customers/{zero_cust_id}/invoices", headers=headers)
    assert zero_res.status_code == 200
    zero_data = zero_res.json()
    assert zero_data["recommended_invoice_id"] is None
    assert len(zero_data["invoices"]) == 0
    print("✓ Graceful empty invoice response for zero-invoice customer verified.")

    # Clean up test customer
    client.delete(f"/api/customers/{zero_cust_id}", headers=headers)

    # 4. Test File Validation (Requirement 2)
    print("\n[STEP 4] Testing File Validation on /api/documents/upload...")
    # 4a. Empty file
    empty_upload = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=headers
    )
    print(f"Empty file upload status: {empty_upload.status_code} ({empty_upload.text})")
    assert empty_upload.status_code == 400, "Empty file should return 400 Bad Request"

    # 4b. Invalid file type (.exe)
    invalid_upload = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"MZ...", "application/x-dosexec")},
        headers=headers
    )
    print(f"Invalid extension upload status: {invalid_upload.status_code} ({invalid_upload.text})")
    assert invalid_upload.status_code == 400, "Unsupported file extension should return 400"
    print("✓ File validation rules strictly enforced.")

    # 5. Test Real Document Upload & Extraction Pipeline (Requirement 2)
    print("\n[STEP 5] Testing Full Document Processing Pipeline with Math Validation...")
    sample_invoice_content = """TAX INVOICE
Seller: Apex Tech Solutions
Seller Address: 45 Cyber Park, Bangalore, India
GSTIN: 29ABCDE1234F1Z5

Invoice No: INV-2026-9901
Invoice Date: 2026-08-01
Due Date: 2026-08-20
Payment Status: Partially Paid

Bill To: bharath
Customer ID: 48
Phone: 9566860154
Email: ponbharathramesh26@gmail.com
Billing Address: 12 Temple Street, Coimbatore, Tamil Nadu

| Item | Description | Quantity | Unit Price | Total |
| 1 | AI Operations Agent License | 1 | 40000.00 | 40000.00 |
| 2 | Cloud Setup & Integration | 1 | 10000.00 | 10000.00 |

| Metric | Amount |
| Subtotal | 50000.00 |
| Total GST | 9000.00 |
| Discount | 2000.00 |
| Grand Total | 57000.00 |
| Paid | 20000.00 |
| Balance Due | 37000.00 |

Terms & Conditions:
1. Interest at 18% p.a. will be charged on delayed payments.
2. Subject to Coimbatore jurisdiction.
"""
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("Apex_Invoice_INV-2026-9901.txt", sample_invoice_content.encode("utf-8"), "text/plain")},
        headers=headers
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.status_code} {upload_res.text}"
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    print(f"Uploaded Document ID: {doc_id}")

    # Inspect processing status and extracted data
    get_doc = client.get(f"/api/documents/{doc_id}", headers=headers)
    assert get_doc.status_code == 200
    doc_info = get_doc.json()
    extracted = doc_info.get("extracted_data") or {}

    print("\nExtracted Document Data:")
    print(f"  - Document Status: {doc_info.get('processing_status')}")
    print(f"  - Document Type: {doc_info.get('document_type')}")
    print(f"  - Invoice Number: {extracted.get('invoice_number')}")
    print(f"  - Customer Name: {extracted.get('customer_name')}")
    print(f"  - Customer Phone: {extracted.get('customer_phone')}")
    print(f"  - Customer Email: {extracted.get('customer_email')}")
    print(f"  - Subtotal: {extracted.get('subtotal')}")
    print(f"  - Tax: {extracted.get('tax')}")
    print(f"  - Discount: {extracted.get('discount')}")
    print(f"  - Total: {extracted.get('total_amount')}")
    print(f"  - Paid: {extracted.get('paid_amount')}")
    print(f"  - Pending: {extracted.get('pending_amount')}")
    print(f"  - Payment Status: {extracted.get('payment_status')}")
    print(f"  - Math Validation: {extracted.get('math_validation')}")
    print(f"  - Customer Match: {extracted.get('customer_match')}")

    # Assertions on extracted data
    assert extracted.get("invoice_number") == "INV-2026-9901", f"Expected INV-2026-9901, got {extracted.get('invoice_number')}"
    assert extracted.get("customer_name") == "bharath", f"Expected bharath, got {extracted.get('customer_name')}"
    assert float(extracted.get("total_amount") or 0) == 57000.0, f"Expected total 57000, got {extracted.get('total_amount')}"
    assert float(extracted.get("paid_amount") or 0) == 20000.0, f"Expected paid 20000, got {extracted.get('paid_amount')}"
    assert float(extracted.get("pending_amount") or 0) == 37000.0, f"Expected pending 37000, got {extracted.get('pending_amount')}"
    assert extracted.get("payment_status") == "partially_paid", f"Expected partially_paid, got {extracted.get('payment_status')}"

    # Verify math validation
    math_val = extracted.get("math_validation") or {}
    assert math_val.get("is_valid") is True, f"Expected math validation to pass: {math_val}"
    print("✓ Mathematical validation passed: 50000 + 9000 - 2000 = 57000 and 57000 - 20000 = 37000.")

    # Verify customer matching matched Customer 48
    c_match = extracted.get("customer_match") or {}
    print(f"Customer match result: {c_match}")
    assert c_match.get("matched") is True
    assert c_match.get("customer_id") == 48

    # 6. Test OCR text retrieval endpoint
    print("\n[STEP 6] Testing GET /api/documents/{doc_id}/ocr...")
    ocr_res = client.get(f"/api/documents/{doc_id}/ocr", headers=headers)
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()
    assert ocr_data["document_id"] == doc_id
    assert "TAX INVOICE" in ocr_data["ocr_text"]
    assert ocr_data["length"] > 100
    print("✓ OCR text retrieval endpoint verified.")

    # 7. Test AI Email Generation with auto-selected context
    print("\n[STEP 7] Testing AI Email Generation with Customer 48...")
    email_gen_res = client.post("/api/ai/generate-email", json={
        "customer_id": 48,
        "invoice_id": cust_data["recommended_invoice_id"],
        "template_type": "payment_reminder",
        "tone": "professional",
        "language": "en"
    }, headers=headers)
    assert email_gen_res.status_code == 200
    eg = email_gen_res.json()
    print("Generated Email Subject:", eg.get("subject"))
    assert eg.get("subject")
    assert eg.get("body")
    print("✓ AI Email generation verified.")

    # 8. Test Communication / SMS Generation
    print("\n[STEP 8] Testing SMS Generation with Customer 48...")
    sms_gen_res = client.post("/api/communications/generate", json={
        "customer_id": 48,
        "invoice_id": cust_data["recommended_invoice_id"],
        "communication_type": "sms",
        "language": "en",
        "template_type": "payment_reminder",
        "purpose": "payment_reminder",
        "tone": "professional",
        "phone_number": "9566860154"
    }, headers=headers)
    assert sms_gen_res.status_code == 200
    sg = sms_gen_res.json()
    print("Generated SMS Body:", sg.get("body"))
    assert sg.get("body")
    print("✓ AI SMS generation verified.")

    # Clean up uploaded test document
    client.delete(f"/api/documents/{doc_id}", headers=headers)

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
