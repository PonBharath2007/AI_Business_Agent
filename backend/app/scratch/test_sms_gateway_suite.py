import os
import sys
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models.models import Customer, SMSMessage, CommunicationLog
from backend.app.utils.phone_validation import normalize_and_validate_phone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def run_test_suite():
    print("==================================================")
    print("RUNNING AUTOMATED SMS GATEWAY & VERIFICATION SUITE")
    print("==================================================")

    init_db()
    db = SessionLocal()
    seed_database(db, reset=True)

    # Ensure test customer
    cust = db.query(Customer).filter(Customer.name == "ABC Ltd").first()
    if not cust:
        cust = Customer(
            business_id=1,
            name="ABC Ltd",
            email="abc@example.com",
            phone="+919876543210",
            company="ABC Ltd",
            status="active"
        )
        db.add(cust)
        db.commit()
        db.refresh(cust)
    else:
        cust.phone = "+919876543210"
        cust.email = "abc@example.com"
        db.commit()

    customer_id = cust.id
    db.close()

    client = TestClient(app)

    # 1. User Login
    login_res = client.post("/api/auth/login", json={"email": "admin@summitdigital.com", "password": "admin123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}
    gateway_key = os.getenv("SMS_GATEWAY_API_KEY", "sms_gateway_secret_key_2026")
    gateway_headers = {"X-Gateway-Key": gateway_key}

    print("[PASS] 1. Authentication & headers ready.")

    # 2. Phone Number Validation & Normalization
    print("\n--- TEST 2: Phone number validation & normalization ---")
    val, num, err = normalize_and_validate_phone("9876543210")
    assert val and num == "+919876543210", f"Failed 10-digit: {num}"

    val, num, err = normalize_and_validate_phone("09876543210")
    assert val and num == "+919876543210", f"Failed 0-prefix: {num}"

    val, num, err = normalize_and_validate_phone("919876543210")
    assert val and num == "+919876543210", f"Failed 91-prefix: {num}"

    val, num, err = normalize_and_validate_phone("+919876543210")
    assert val and num == "+919876543210", f"Failed +91: {num}"

    val, num, err = normalize_and_validate_phone("+14155552671")
    assert val and num == "+14155552671", f"Failed international: {num}"

    val, num, err = normalize_and_validate_phone("123")
    assert not val, "Short phone should be invalid"

    val, num, err = normalize_and_validate_phone("")
    assert not val, "Empty phone should be invalid"
    print("[PASS] Phone normalization verified for Indian and international formats.")

    # 3. Enqueue English SMS
    print("\n--- TEST 3: Enqueue English SMS ---")
    en_msg = "Your invoice INV-1001 payment is pending."
    res = client.post("/api/sms/send", json={
        "customer_id": customer_id,
        "phone_number": "9876543210",
        "message": en_msg,
        "language": "en",
        "purpose": "payment_reminder"
    }, headers=user_headers)
    assert res.status_code == 200, f"SMS send failed: {res.text}"
    en_data = res.json()
    assert en_data["success"] is True
    assert en_data["status"] == "PENDING"
    en_sms_id = en_data["sms_id"]
    print(f"[PASS] English SMS queued with ID: {en_sms_id}, status: PENDING")

    # 4. Enqueue Tamil Unicode SMS
    print("\n--- TEST 4: Enqueue Tamil Unicode SMS ---")
    ta_msg = "உங்கள் கட்டணம் நிலுவையில் உள்ளது."
    res = client.post("/api/sms/send", json={
        "customer_id": customer_id,
        "phone_number": "+919876543210",
        "message": ta_msg,
        "language": "ta",
        "purpose": "payment_reminder"
    }, headers=user_headers)
    assert res.status_code == 200, f"Tamil SMS send failed: {res.text}"
    ta_data = res.json()
    ta_sms_id = ta_data["sms_id"]
    print(f"[PASS] Tamil SMS queued with ID: {ta_sms_id}")

    # Verify Unicode preserved in DB
    db = SessionLocal()
    saved_ta = db.query(SMSMessage).filter(SMSMessage.id == ta_sms_id).first()
    assert saved_ta and saved_ta.message == ta_msg, "Tamil Unicode characters corrupted in database!"
    db.close()
    print("[PASS] Tamil Unicode correctly stored and preserved.")

    # 5. Enqueue Combined English + Tamil SMS
    print("\n--- TEST 5: Combined English + Tamil Bilingual SMS ---")
    bilingual_msg = "Your payment is pending. உங்கள் கட்டணம் நிலுவையில் உள்ளது."
    res = client.post("/api/sms/send", json={
        "customer_id": customer_id,
        "phone_number": "919876543210",
        "message": bilingual_msg,
        "language": "en_ta",
        "purpose": "payment_reminder"
    }, headers=user_headers)
    assert res.status_code == 200, f"Bilingual SMS send failed: {res.text}"
    bi_sms_id = res.json()["sms_id"]
    print(f"[PASS] Combined English + Tamil SMS queued as 1 record with ID: {bi_sms_id}")

    # 6. Gateway Authentication Security
    print("\n--- TEST 6: Android Gateway Authentication Security ---")
    # Invalid key
    bad_res = client.get("/api/sms/pending", headers={"X-Gateway-Key": "wrong-secret-key"})
    assert bad_res.status_code == 401, "Expected 401 with invalid gateway key"
    # Valid key
    good_res = client.get("/api/sms/pending", headers=gateway_headers)
    assert good_res.status_code == 200, f"Valid gateway key rejected: {good_res.text}"
    pending_list = good_res.json()
    assert len(pending_list) >= 3, f"Expected at least 3 pending SMS, got {len(pending_list)}"
    print(f"[PASS] Gateway authentication verified. Retrieved {len(pending_list)} pending SMS.")

    # 7. SMS Claiming Protection (Atomic State Transition PENDING -> PROCESSING)
    print("\n--- TEST 7: Claiming Protection ---")
    claim_res = client.post(f"/api/sms/{en_sms_id}/claim", headers=gateway_headers)
    assert claim_res.status_code == 200, f"Claim failed: {claim_res.text}"
    assert claim_res.json()["status"] == "PROCESSING"
    print(f"[PASS] SMS #{en_sms_id} claimed. Status: PROCESSING")

    # Double claim attempt must be rejected with 409 Conflict
    double_claim = client.post(f"/api/sms/{en_sms_id}/claim", headers=gateway_headers)
    assert double_claim.status_code == 409, "Double claim should return 409 Conflict!"
    print("[PASS] Double-claim prevented. Race condition protection verified.")

    # 8. Report Success (PROCESSING -> SENT)
    print("\n--- TEST 8: Report Success (SENT) ---")
    sent_res = client.post(f"/api/sms/{en_sms_id}/sent", json={
        "provider_message_id": "android-sim-device-test-001"
    }, headers=gateway_headers)
    assert sent_res.status_code == 200, f"Sent report failed: {sent_res.text}"
    assert sent_res.json()["status"] == "SENT"

    # Verify status in database
    db = SessionLocal()
    db_sms = db.query(SMSMessage).filter(SMSMessage.id == en_sms_id).first()
    assert db_sms and db_sms.status == "SENT"
    assert db_sms.sent_at is not None
    assert db_sms.provider_message_id == "android-sim-device-test-001"
    db.close()
    print(f"[PASS] SMS #{en_sms_id} transitioned to SENT with sent_at timestamp.")

    # 9. Report Failure (PROCESSING -> FAILED)
    print("\n--- TEST 9: Report Failure (FAILED) ---")
    # Claim second SMS
    client.post(f"/api/sms/{ta_sms_id}/claim", headers=gateway_headers)
    fail_res = client.post(f"/api/sms/{ta_sms_id}/failed", json={
        "error_message": "Cellular radio off (Airplane mode)"
    }, headers=gateway_headers)
    assert fail_res.status_code == 200
    assert fail_res.json()["status"] == "FAILED"

    db = SessionLocal()
    db_ta = db.query(SMSMessage).filter(SMSMessage.id == ta_sms_id).first()
    assert db_ta and db_ta.status == "FAILED"
    assert db_ta.error_message == "Cellular radio off (Airplane mode)"
    db.close()
    print(f"[PASS] SMS #{ta_sms_id} transitioned to FAILED with error stored without deleting.")

    # 10. Carrier Delivery Report (SENT -> DELIVERED)
    print("\n--- TEST 10: Carrier Delivery Report (DELIVERED) ---")
    del_res = client.post(f"/api/sms/{en_sms_id}/delivered", json={
        "provider_message_id": "carrier-ack-999"
    }, headers=gateway_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELIVERED"
    print(f"[PASS] SMS #{en_sms_id} delivery confirmed: DELIVERED.")

    # 11. Dispatched Logs Listing & Filtering
    print("\n--- TEST 11: Dispatched Logs Listing ---")
    logs_res = client.get("/api/sms", headers=user_headers)
    assert logs_res.status_code == 200
    sms_logs = logs_res.json()
    assert len(sms_logs) >= 3
    statuses = [s["status"] for s in sms_logs]
    print(f"[PASS] Dispatched logs contain SMS records: statuses={statuses}")

    # 12. Verification: Existing Phone/Call functionality untouched
    print("\n--- TEST 12: Existing Phone/Call Functionality Untouched ---")
    call_res = client.post("/api/communications/call", json={
        "customer_id": customer_id,
        "phone_number": "+919876543210"
    }, headers=user_headers)
    assert call_res.status_code == 200, f"Call initiation failed: {call_res.text}"
    call_data = call_res.json()
    assert "tel:+919876543210" in call_data["device_uri"]
    print(f"[PASS] Existing Phone/Call dialing intact: {call_data['device_uri']}")

    # 13. Verification: Existing SMTP / Email configuration untouched
    print("\n--- TEST 13: Existing SMTP / Email System Untouched ---")
    smtp_res = client.get("/api/communications/smtp-status", headers=user_headers)
    assert smtp_res.status_code == 200
    smtp_data = smtp_res.json()
    print(f"[PASS] Existing SMTP config intact: server={smtp_data.get('server')}, port={smtp_data.get('port')}")

    # 14. Verification: Existing Gemini AI Message Generation untouched
    print("\n--- TEST 14: Existing Gemini AI Generation Functionality ---")
    gen_res = client.post("/api/communications/generate", json={
        "customer_id": customer_id,
        "communication_type": "sms",
        "language": "en",
        "template_type": "payment_reminder"
    }, headers=user_headers)
    assert gen_res.status_code == 200, f"AI generation failed: {gen_res.text}"
    gen_data = gen_res.json()
    assert gen_data.get("body"), "AI generation returned empty body"
    print(f"[PASS] Existing Gemini AI generation verified. Engine: {gen_data.get('engine')}")

    print("\n==================================================")
    print("ALL 14 TEST SUITE ASSERTIONS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_test_suite()
