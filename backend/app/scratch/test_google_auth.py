import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models.models import User, Business, Customer, Invoice

# Ensure UTF-8 output encoding for Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def run_google_auth_test_suite():
    print("==================================================")
    print("RUNNING GOOGLE AUTH & AUTHENTICATION ENHANCEMENT SUITE")
    print("==================================================")

    init_db()
    db = SessionLocal()
    seed_database(db, reset=True)
    db.close()

    client = TestClient(app)

    # ----------------------------------------------------
    # TEST 1: Register with Email + Password (Local)
    # ----------------------------------------------------
    print("\n--- TEST 1: Register with Email/Password ---")
    reg_payload = {
        "name": "Alex Mercer",
        "email": "alex.mercer@innovate.io",
        "password": "SecurePassword123!",
        "business_name": "Mercer Innovations",
        "currency": "USD"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "alex.mercer@innovate.io"
    assert reg_data["user"]["auth_provider"] == "local"
    local_token = reg_data["access_token"]
    print(f"[PASS] TEST 1: Local user registered with ID: {reg_data['user']['id']}")

    # ----------------------------------------------------
    # TEST 2: Login with Email + Password (Local)
    # ----------------------------------------------------
    print("\n--- TEST 2: Login with Email/Password ---")
    login_res = client.post("/api/auth/login", json={
        "email": "alex.mercer@innovate.io",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["name"] == "Alex Mercer"
    print("[PASS] TEST 2: Local user logged in successfully.")

    # ----------------------------------------------------
    # TEST 3: Access Protected Route with Local Token & Logout
    # ----------------------------------------------------
    print("\n--- TEST 3: Access Protected Routes & Profile ---")
    headers_local = {"Authorization": f"Bearer {local_token}"}
    me_res = client.get("/api/auth/me", headers=headers_local)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alex.mercer@innovate.io"
    print("[PASS] TEST 3: /api/auth/me verified local session.")

    # ----------------------------------------------------
    # TEST 4: Google Auth Config and Consent URL Generation
    # ----------------------------------------------------
    print("\n--- TEST 4: Google Auth Config & Login URL ---")
    config_res = client.get("/api/auth/google/config")
    assert config_res.status_code == 200
    print(f"[PASS] TEST 4a: Google config endpoint returned: {config_res.json()}")

    login_url_res = client.get("/api/auth/google/login", follow_redirects=False)
    # If not configured, returns 200 with fallback info, if configured returns 307
    assert login_url_res.status_code in [200, 307]
    print("[PASS] TEST 4b: Google login consent endpoint functional.")

    # ----------------------------------------------------
    # TEST 5: Create New Account Using Google Sign-In
    # ----------------------------------------------------
    print("\n--- TEST 5: New User Google Sign-In (Provisioning) ---")
    mock_google_userinfo = {
        "sub": "google-oauth2|10928374651928374",
        "email": "sarah.chen@googleworkspace.com",
        "name": "Sarah Chen",
        "picture": "https://lh3.googleusercontent.com/a/mock-avatar-sarah",
        "email_verified": True
    }

    with patch("backend.app.routes.auth.verify_google_id_token", return_value=mock_google_userinfo):
        google_res = client.post("/api/auth/google/verify", json={
            "credential": "mock-valid-google-id-token"
        })
        assert google_res.status_code == 200, f"Google verify failed: {google_res.text}"
        google_data = google_res.json()
        assert "access_token" in google_data
        assert google_data["user"]["email"] == "sarah.chen@googleworkspace.com"
        assert google_data["user"]["auth_provider"] == "google"
        assert google_data["user"]["google_id"] == "google-oauth2|10928374651928374"
        assert google_data["user"]["profile_picture"] == "https://lh3.googleusercontent.com/a/mock-avatar-sarah"
        assert google_data["user"]["email_verified"] is True
        google_token = google_data["access_token"]
        sarah_user_id = google_data["user"]["id"]
        print(f"[PASS] TEST 5: New Google user provisioned with ID: {sarah_user_id} and isolated business.")

    # ----------------------------------------------------
    # TEST 6: Login Again Using Existing Google Account (Idempotent)
    # ----------------------------------------------------
    print("\n--- TEST 6: Login Again Using Existing Google Account ---")
    with patch("backend.app.routes.auth.verify_google_id_token", return_value=mock_google_userinfo):
        google_login_again = client.post("/api/auth/google/verify", json={
            "credential": "mock-valid-google-id-token"
        })
        assert google_login_again.status_code == 200
        assert google_login_again.json()["user"]["id"] == sarah_user_id, "User ID should match existing record"
        print("[PASS] TEST 6: Existing Google user logged in without duplicate creation.")

    # ----------------------------------------------------
    # TEST 7: Account Linking — Existing Local Account uses same verified Google email
    # ----------------------------------------------------
    print("\n--- TEST 7: Safe Account Linking ---")
    # Alex Mercer was created in TEST 1 as a local user (email: alex.mercer@innovate.io)
    alex_google_userinfo = {
        "sub": "google-oauth2|9988776655443322",
        "email": "alex.mercer@innovate.io",  # SAME email
        "name": "Alex Mercer",
        "picture": "https://lh3.googleusercontent.com/a/mock-avatar-alex",
        "email_verified": True
    }

    with patch("backend.app.routes.auth.verify_google_id_token", return_value=alex_google_userinfo):
        link_res = client.post("/api/auth/google/verify", json={
            "credential": "mock-alex-google-token"
        })
        assert link_res.status_code == 200
        linked_user = link_res.json()["user"]
        assert linked_user["email"] == "alex.mercer@innovate.io"
        assert linked_user["google_id"] == "google-oauth2|9988776655443322"
        assert linked_user["email_verified"] is True
        
        # Verify in database there is only ONE user with this email
        db = SessionLocal()
        users_count = db.query(User).filter(User.email == "alex.mercer@innovate.io").count()
        assert users_count == 1, f"Expected 1 user record, found {users_count}"
        db.close()
        print("[PASS] TEST 7: Account linking succeeded safely. No duplicate user created.")

    # ----------------------------------------------------
    # TEST 8: Google OAuth Cancellation and Error Handling
    # ----------------------------------------------------
    print("\n--- TEST 8: Google OAuth Cancellation & Error Callback ---")
    cancel_res = client.get("/api/auth/google/callback?error=access_denied", follow_redirects=False)
    assert cancel_res.status_code == 307
    assert "error=google_cancelled" in cancel_res.headers["location"]
    print(f"[PASS] TEST 8: Cancellation redirected correctly: {cancel_res.headers['location']}")

    # ----------------------------------------------------
    # TEST 9: Protected Dashboard Features Work for Google User
    # ----------------------------------------------------
    print("\n--- TEST 9: Protected Routes with Google Session ---")
    headers_google = {"Authorization": f"Bearer {google_token}"}
    
    # 9a. Customers API
    cust_res = client.get("/api/customers", headers=headers_google)
    assert cust_res.status_code == 200
    print("[PASS] TEST 9a: Customers route accessible for Google user.")

    # 9b. Invoices API
    inv_res = client.get("/api/invoices", headers=headers_google)
    assert inv_res.status_code == 200
    print("[PASS] TEST 9b: Invoices route accessible for Google user.")

    # 9c. AI Chat / Command Center API
    chat_res = client.post("/api/ai/chat", json={"message": "What is our business operational status?"}, headers=headers_google)
    assert chat_res.status_code == 200
    print("[PASS] TEST 9c: AI Command Center functional for Google user.")

    # 9d. Multilingual Communication API
    comm_gen = client.post("/api/communications/generate", json={
        "communication_type": "email",
        "language": "en_ta",
        "template_type": "payment_reminder"
    }, headers=headers_google)
    assert comm_gen.status_code == 200
    print("[PASS] TEST 9d: Multilingual communication generator functional for Google user.")

    # ----------------------------------------------------
    # TEST 10: Forgot Password Works for Local Users
    # ----------------------------------------------------
    print("\n--- TEST 10: Forgot Password for Local Users ---")
    forgot_res = client.post("/api/auth/forgot-password", json={
        "email": "alex.mercer@innovate.io",
        "new_password": "BrandNewPassword2026!"
    })
    assert forgot_res.status_code == 200
    assert forgot_res.json()["status"] == "success"

    # Login with new password
    new_login_res = client.post("/api/auth/login", json={
        "email": "alex.mercer@innovate.io",
        "password": "BrandNewPassword2026!"
    })
    assert new_login_res.status_code == 200
    print("[PASS] TEST 10: Forgot password reset and subsequent login verified.")

    print("\n==================================================")
    print("ALL 10 GOOGLE AUTH & ACCOUNT LINKING TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_google_auth_test_suite()
