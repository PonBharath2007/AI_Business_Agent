import os
import io
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models.models import Approval, Task, Invoice, Document

def test_golden_workflow():
    print("==================================================")
    print("TESTING GOLDEN DEMO WORKFLOW (DOCUMENT -> AGENT -> APPROVAL)")
    print("==================================================")
    
    init_db()
    db = SessionLocal()
    seed_database(db, reset=True)
    db.close()

    client = TestClient(app)
    login_res = client.post("/api/auth/login", json={"email": "admin@summitdigital.com", "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a simulated invoice file
    sample_text = """
INVOICE #INV-9002
Issued to: ABC Ltd
Email: accounts@abc.example
Date: 2026-07-01
Due Date: 2026-07-20

Description: Enterprise Cloud Architecture & Digital Operations
Amount Due: $55,000.00
Terms: Net 15 days. Unpaid balance subject to 1.5% monthly late fee.
"""
    file_bytes = sample_text.encode("utf-8")
    files = {"file": ("invoice_sample_abc.txt", io.BytesIO(file_bytes), "text/plain")}

    # 2. Upload Document
    upload_res = client.post("/api/documents/upload", files=files, headers=headers)
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    doc_id = upload_res.json()["id"]
    print(f"[PASS] 1. Uploaded document id: {doc_id}")

    # 3. Process Document with AI Workflow Engine
    proc_res = client.post(f"/api/documents/{doc_id}/analyze", headers=headers)
    assert proc_res.status_code == 200, f"Process failed: {proc_res.text}"
    proc_data = proc_res.json()
    print("[PASS] 2. Processed document via AI Agent:", proc_data.get("message"))

    # 4. Check DB for auto-created High-Priority Task and Approval Request
    db = SessionLocal()
    new_doc = db.query(Document).filter(Document.id == doc_id).first()
    assert new_doc.processing_status == "completed"
    assert new_doc.extracted_data is not None

    inv = db.query(Invoice).filter(Invoice.invoice_number == "INV-9002").first()
    assert inv is not None, "Invoice was not recorded in DB"
    assert inv.status == "overdue", f"Invoice status was {inv.status}, expected overdue"

    # Check Task
    task = db.query(Task).filter(Task.source_id == inv.id).first()
    assert task is not None, "High priority task was not generated"
    print(f"[PASS] 3. High-Priority Task auto-generated: '{task.title}' ({task.priority})")

    # Check Approval
    app_item = db.query(Approval).filter(Approval.action_type == "send_payment_reminder", Approval.status == "pending").order_by(Approval.id.desc()).first()
    assert app_item is not None, "Approval request was not queued"
    print(f"[PASS] 4. HITL Approval Item queued: '{app_item.recommendation}'")

    # 5. Simulate Business Owner Approving the Action
    approve_res = client.post(f"/api/approvals/{app_item.id}/approve", headers=headers)
    assert approve_res.status_code == 200, f"Approval failed: {approve_res.text}"
    print(f"[PASS] 5. Business Owner Approved Action: {approve_res.json().get('message')}")

    db.close()
    print("==================================================")
    print("GOLDEN WORKFLOW VERIFIED END-TO-END WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    test_golden_workflow()
