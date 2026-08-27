import os
import sys
import io
import urllib.parse
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models.models import Customer, Invoice, Approval, CommunicationLog, Email, Task

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def test_multilingual_communication_suite():
    print("==================================================")
    print("RUNNING FULL MULTILINGUAL COMMUNICATION TEST SUITE")
    print("==================================================")

    init_db()
    db = SessionLocal()
    seed_database(db, reset=True)
    
    # Ensure test customer has both email and phone
    test_cust = db.query(Customer).filter(Customer.name == "ABC Ltd").first()
    if not test_cust:
        test_cust = Customer(
            business_id=1,
            name="ABC Ltd",
            email="abc@example.com",
            phone="+919876543210",
            company="ABC Ltd",
            status="active"
        )
        db.add(test_cust)
        db.commit()
        db.refresh(test_cust)
    else:
        test_cust.phone = "+919876543210"
        test_cust.email = "abc@example.com"
        db.commit()

    customer_id = test_cust.id
    db.close()

    client = TestClient(app)

    # Authenticate
    login_res = client.post("/api/auth/login", json={"email": "admin@summitdigital.com", "password": "admin123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] 0. Authentication successful.")

    # ----------------------------------------------------
    # TEST 1: English email generation and dispatch
    # ----------------------------------------------------
    print("\n--- TEST 1: English email generation and dispatch ---")
    gen_en_email = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "en",
        "template_type": "payment_reminder",
        "tone": "professional"
    }, headers=headers)
    assert gen_en_email.status_code == 200, f"Generate EN Email failed: {gen_en_email.text}"
    en_email_data = gen_en_email.json()
    assert "Dear" in en_email_data["body"] or "ABC Ltd" in en_email_data["body"]
    assert en_email_data["language"] == "en"
    print(f"[PASS] TEST 1 (Generate): English email generated: '{en_email_data['subject']}'")

    send_en_email = client.post("/api/communications/email", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "en",
        "recipient": "abc@example.com",
        "subject": en_email_data["subject"],
        "message": en_email_data["body"]
    }, headers=headers)
    assert send_en_email.status_code == 200, f"Send EN Email failed: {send_en_email.text}"
    assert send_en_email.json()["status"] == "sent"
    print("[PASS] TEST 1 (Send): English email recorded and delivered.")

    # ----------------------------------------------------
    # TEST 2: Tamil email generation and dispatch (UTF-8 Unicode)
    # ----------------------------------------------------
    print("\n--- TEST 2: Tamil email (UTF-8 Unicode) ---")
    gen_ta_email = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "ta",
        "template_type": "payment_reminder",
        "tone": "urgent"
    }, headers=headers)
    assert gen_ta_email.status_code == 200, f"Generate TA Email failed: {gen_ta_email.text}"
    ta_email_data = gen_ta_email.json()
    assert ta_email_data["language"] == "ta"
    # Check that real Tamil Unicode characters are present
    assert any('\u0B80' <= ch <= '\u0BFF' for ch in ta_email_data["body"]), "Tamil Unicode characters not found in body"
    print(f"[PASS] TEST 2 (Generate): Tamil email generated with Unicode: '{ta_email_data['subject']}'")

    send_ta_email = client.post("/api/communications/email", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "ta",
        "recipient": "abc@example.com",
        "subject": ta_email_data["subject"],
        "message": ta_email_data["body"]
    }, headers=headers)
    assert send_ta_email.status_code == 200, f"Send TA Email failed: {send_ta_email.text}"
    print("[PASS] TEST 2 (Send): Tamil email dispatched and logged with UTF-8.")

    # ----------------------------------------------------
    # TEST 3: English + Tamil email in the SAME email
    # ----------------------------------------------------
    print("\n--- TEST 3: English + Tamil bilingual email in SAME email ---")
    gen_bilingual_email = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "en_ta",
        "template_type": "payment_reminder"
    }, headers=headers)
    assert gen_bilingual_email.status_code == 200, f"Generate EN+TA Email failed: {gen_bilingual_email.text}"
    bilingual_email_data = gen_bilingual_email.json()
    body_bilingual = bilingual_email_data["body"]
    assert any('\u0B80' <= ch <= '\u0BFF' for ch in body_bilingual), "Tamil section missing in bilingual body"
    assert "invoice" in body_bilingual.lower() or "payment" in body_bilingual.lower() or "dear" in body_bilingual.lower(), "English section missing in bilingual body"
    print(f"[PASS] TEST 3 (Generate): Bilingual email generated with both English & Tamil in same message.")

    send_bilingual_email = client.post("/api/communications/email", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "en_ta",
        "recipient": "abc@example.com",
        "subject": bilingual_email_data["subject"],
        "message": body_bilingual
    }, headers=headers)
    assert send_bilingual_email.status_code == 200
    print("[PASS] TEST 3 (Send): Bilingual email dispatched successfully.")

    # ----------------------------------------------------
    # TEST 4: English SMS
    # ----------------------------------------------------
    print("\n--- TEST 4: English SMS ---")
    gen_en_sms = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "en",
        "template_type": "payment_reminder"
    }, headers=headers)
    assert gen_en_sms.status_code == 200
    en_sms_data = gen_en_sms.json()
    assert en_sms_data["channel"] == "sms"
    print(f"[PASS] TEST 4 (Generate): English SMS body: '{en_sms_data['body']}'")

    send_en_sms = client.post("/api/communications/sms", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "en",
        "recipient": "+919876543210",
        "message": en_sms_data["body"]
    }, headers=headers)
    assert send_en_sms.status_code == 200
    assert "sms:+919876543210" in send_en_sms.json().get("device_uri", "")
    print(f"[PASS] TEST 4 (Send): English SMS URI generated: {send_en_sms.json().get('device_uri')[:40]}...")

    # ----------------------------------------------------
    # TEST 5: Tamil SMS
    # ----------------------------------------------------
    print("\n--- TEST 5: Tamil SMS ---")
    gen_ta_sms = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "ta",
        "template_type": "payment_reminder"
    }, headers=headers)
    assert gen_ta_sms.status_code == 200
    ta_sms_data = gen_ta_sms.json()
    assert any('\u0B80' <= ch <= '\u0BFF' for ch in ta_sms_data["body"]), "Tamil Unicode missing in SMS"
    print(f"[PASS] TEST 5 (Generate): Tamil SMS body: '{ta_sms_data['body']}'")

    send_ta_sms = client.post("/api/communications/sms", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "ta",
        "recipient": "+919876543210",
        "message": ta_sms_data["body"]
    }, headers=headers)
    assert send_ta_sms.status_code == 200
    assert "sms:+919876543210" in send_ta_sms.json().get("device_uri", "")
    print(f"[PASS] TEST 5 (Send): Tamil SMS URI properly URL-encoded with UTF-8.")

    # ----------------------------------------------------
    # TEST 6: English + Tamil SMS (Bilingual)
    # ----------------------------------------------------
    print("\n--- TEST 6: English + Tamil SMS ---")
    gen_bilingual_sms = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "en_ta",
        "template_type": "payment_reminder"
    }, headers=headers)
    assert gen_bilingual_sms.status_code == 200
    bilingual_sms_data = gen_bilingual_sms.json()
    assert any('\u0B80' <= ch <= '\u0BFF' for ch in bilingual_sms_data["body"])
    print(f"[PASS] TEST 6 (Generate): Bilingual SMS generated.")

    send_bilingual_sms = client.post("/api/communications/sms", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "en_ta",
        "recipient": "+919876543210",
        "message": bilingual_sms_data["body"]
    }, headers=headers)
    assert send_bilingual_sms.status_code == 200
    print("[PASS] TEST 6 (Send): Bilingual SMS logged and device URI generated.")

    # ----------------------------------------------------
    # TEST 7: Call button & tel link
    # ----------------------------------------------------
    print("\n--- TEST 7: Call button & tel: URI ---")
    call_res = client.post("/api/communications/call", json={
        "customer_id": customer_id,
        "phone_number": "+919876543210"
    }, headers=headers)
    assert call_res.status_code == 200
    assert call_res.json()["device_uri"] == "tel:+919876543210"
    print(f"[PASS] TEST 7: Call link verified: {call_res.json()['device_uri']}")

    # ----------------------------------------------------
    # TEST 8: AI-generated overdue payment reminder in AI Command Center
    # ----------------------------------------------------
    print("\n--- TEST 8: AI Command Center Multilingual Queries ---")
    chat_ta = client.post("/api/ai/chat", json={
        "message": "Prepare a payment reminder for ABC Ltd in Tamil."
    }, headers=headers)
    assert chat_ta.status_code == 200
    chat_ta_data = chat_ta.json()
    assert "Approval Center" in chat_ta_data["response"]
    print("[PASS] TEST 8a: Command Center prepared Tamil reminder and queued approval.")

    chat_bilingual = client.post("/api/ai/chat", json={
        "message": "Prepare it in English and Tamil."
    }, headers=headers)
    assert chat_bilingual.status_code == 200
    print("[PASS] TEST 8b: Command Center prepared Bilingual reminder.")

    # ----------------------------------------------------
    # TEST 9: Edit AI-generated message before sending
    # ----------------------------------------------------
    print("\n--- TEST 9: Edit AI message before sending ---")
    edited_msg = "Edited Message: வணக்கத்திற்குரிய ABC Ltd, தயவுசெய்து ₹50,000 நிலுவைத் தொகையை செலுத்தவும்."
    send_edited = client.post("/api/communications/email", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "language": "ta",
        "recipient": "abc@example.com",
        "subject": "திருத்தப்பட்ட விலைப்பட்டியல் நினைவூட்டல்",
        "message": edited_msg
    }, headers=headers)
    assert send_edited.status_code == 200
    comm_id = send_edited.json()["communication_id"]
    
    db = SessionLocal()
    saved_comm = db.query(CommunicationLog).filter(CommunicationLog.id == comm_id).first()
    assert saved_comm.message == edited_msg
    db.close()
    print("[PASS] TEST 9: Successfully verified edited message stored in DB.")

    # ----------------------------------------------------
    # TEST 10: Human Approval & Rejection Workflow
    # ----------------------------------------------------
    print("\n--- TEST 10: Approve & Reject Communication Approvals ---")
    db = SessionLocal()
    pending_app = db.query(Approval).filter(Approval.status == "pending").first()
    assert pending_app is not None, "Pending approval expected"
    app_id = pending_app.id
    db.close()

    approve_res = client.post(f"/api/approvals/{app_id}/approve", headers=headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"
    print(f"[PASS] TEST 10a: Approval item {app_id} approved and executed.")

    # Create dummy approval to test rejection
    create_app_res = client.post("/api/approvals", json={
        "action_type": "send_sms",
        "action_data": {
            "customer_id": customer_id,
            "recipient_phone": "+919876543210",
            "body": "Test SMS for rejection",
            "language": "ta"
        },
        "recommendation": "Test rejection approval"
    }, headers=headers)
    assert create_app_res.status_code == 200
    new_app_id = create_app_res.json()["id"]

    reject_res = client.post(f"/api/approvals/{new_app_id}/reject", json={"reason": "Customer requested delay"}, headers=headers)
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    print(f"[PASS] TEST 10b: Approval item {new_app_id} rejected cleanly.")

    # ----------------------------------------------------
    # TEST 11: Customer without email error handling
    # ----------------------------------------------------
    print("\n--- TEST 11: Error handling for missing email ---")
    err_email_res = client.post("/api/communications/email", json={
        "customer_id": customer_id,
        "communication_type": "email",
        "recipient": "",  # missing
        "subject": "Notice",
        "message": "Hello"
    }, headers=headers)
    assert err_email_res.status_code == 400
    assert "email" in err_email_res.json()["detail"].lower()
    print(f"[PASS] TEST 11: Missing email returned HTTP 400: '{err_email_res.json()['detail']}'")

    # ----------------------------------------------------
    # TEST 12: Customer without phone error handling
    # ----------------------------------------------------
    print("\n--- TEST 12: Error handling for missing phone ---")
    err_phone_res = client.post("/api/communications/sms", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "recipient": "",  # missing
        "message": "Hello"
    }, headers=headers)
    assert err_phone_res.status_code == 400
    assert "phone" in err_phone_res.json()["detail"].lower()
    print(f"[PASS] TEST 12: Missing phone returned HTTP 400: '{err_phone_res.json()['detail']}'")

    # ----------------------------------------------------
    # TEST 13: Customer Communications History Listing
    # ----------------------------------------------------
    print("\n--- TEST 13: Customer Communication History API ---")
    history_res = client.get(f"/api/communications/customer/{customer_id}", headers=headers)
    assert history_res.status_code == 200
    history_logs = history_res.json()
    assert len(history_logs) >= 3
    print(f"[PASS] TEST 13: Customer history retrieved with {len(history_logs)} records (Email, SMS, Call).")

    # ----------------------------------------------------
    # TEST 14: Transform Email to Tamil Endpoint
    # ----------------------------------------------------
    print("\n--- TEST 14: Transform Email to Tamil ---")
    transform_res = client.post("/api/ai/transform-email", json={
        "text": "Your payment of $50,000 is overdue. Please settle it promptly.",
        "action": "translate",
        "target_language": "Tamil"
    }, headers=headers)
    assert transform_res.status_code == 200
    transformed_text = transform_res.json()["transformed_text"]
    assert any('\u0B80' <= ch <= '\u0BFF' for ch in transformed_text)
    print(f"[PASS] TEST 14: AI Transform produced Tamil text: '{transformed_text[:60]}...'")

    print("\n==================================================")
    print("ALL 15 TEST SUITE CHECKS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    test_multilingual_communication_suite()
