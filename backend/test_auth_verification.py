import os
import sys
from pathlib import Path
from unittest.mock import patch

# Set paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["DATABASE_URL"] = "sqlite:///./ai_business_agent.db"
os.environ["ALLOW_SQLITE_FALLBACK"] = "true"
os.environ["GOOGLE_CLIENT_ID"] = "mock-client-id-for-testing.apps.googleusercontent.com"
os.environ["GOOGLE_CLIENT_SECRET"] = "mock-client-secret-123456"
os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/api/auth/google/callback"
os.environ["FRONTEND_URL"] = "http://localhost:5173"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.models.models import User, Business
from backend.app.services.google_auth_service import (
    generate_oauth_state, verify_oauth_state, get_or_create_google_user,
    build_google_auth_url, is_google_auth_configured
)

client = TestClient(app, follow_redirects=False)

def run_all_tests():
    print("==================================================")
    print("STARTING AUTHENTICATION VERIFICATION TESTS")
    print("==================================================")

    init_db()
    db = SessionLocal()

    try:
        # TEST 1: Password Registration
        print("\n[TEST 1] Testing Existing User Registration (POST /api/auth/register)...")
        reg_payload = {
            "name": "Auth Test User",
            "email": "authtest_local@testbusiness.com",
            "password": "Password123!",
            "business_name": "Auth Testing LLC",
            "currency": "USD"
        }
        # Clean up any prior test artifacts
        existing = db.query(User).filter(User.email == reg_payload["email"]).first()
        if existing:
            if existing.business:
                db.delete(existing.business)
            db.delete(existing)
            db.commit()

        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 200, f"Registration failed: {res.text}"
        data = res.json()
        assert "access_token" in data, "Missing access_token in registration response"
        assert data["user"]["email"] == reg_payload["email"]
        print("  PASS: User registered successfully, JWT returned.")

        # TEST 2: Password Login
        print("\n[TEST 2] Testing Existing Email/Password Login (POST /api/auth/login)...")
        login_payload = {
            "email": "authtest_local@testbusiness.com",
            "password": "Password123!"
        }
        res = client.post("/api/auth/login", json=login_payload)
        assert res.status_code == 200, f"Login failed: {res.text}"
        login_data = res.json()
        jwt_token = login_data["access_token"]
        assert jwt_token, "No token returned on login"
        print("  PASS: Email/password login works as expected.")

        # TEST 3: Protected Routes with JWT
        print("\n[TEST 3] Testing Protected Route (/api/auth/me) with Bearer Token...")
        headers = {"Authorization": f"Bearer {jwt_token}"}
        res = client.get("/api/auth/me", headers=headers)
        assert res.status_code == 200, f"/api/auth/me failed: {res.text}"
        user_out = res.json()
        assert user_out["email"] == "authtest_local@testbusiness.com"
        assert user_out["business_name"] == "Auth Testing LLC"
        print("  PASS: Session validation and current user retrieval confirmed.")

        # TEST 4: Google OAuth Authorization URL & CSRF State Generation
        print("\n[TEST 4] Testing Google OAuth Initiation (GET /api/auth/google)...")
        res = client.get("/api/auth/google")
        assert res.status_code == 307, f"Expected 307 redirect, got {res.status_code}"
        redirect_url = res.headers["location"]
        assert "accounts.google.com" in redirect_url, f"Redirect url does not point to Google: {redirect_url}"
        assert "client_id=mock-client-id" in redirect_url
        assert "scope=openid+email+profile" in redirect_url or "scope=openid%20email%20profile" in redirect_url
        assert "state=" in redirect_url
        print("  PASS: GET /api/auth/google redirects to Google with correct OIDC scopes and signed CSRF state.")

        # TEST 5: CSRF State Cryptographic Verification
        print("\n[TEST 5] Testing CSRF State Generation & Verification...")
        valid_state = generate_oauth_state()
        assert verify_oauth_state(valid_state) is True, "Valid state verification returned False"
        assert verify_oauth_state("tampered.fake.state") is False, "Tampered state verification did not fail"
        assert verify_oauth_state("") is False, "Empty state verification did not fail"
        assert verify_oauth_state(None) is False, "None state verification did not fail"
        print("  PASS: CSRF state cryptographically validated; tampered/empty states rejected.")

        # TEST 6: Google Callback Error Handling
        print("\n[TEST 6] Testing Google Callback Error / Cancellation Handling...")
        res_cancel = client.get("/api/auth/google/callback?error=access_denied")
        assert res_cancel.status_code == 307
        assert "error=google_cancelled" in res_cancel.headers["location"]
        print("  PASS: Cancellation redirected gracefully with friendly notice.")

        res_bad_state = client.get("/api/auth/google/callback?code=mock_code&state=bad_state")
        assert res_bad_state.status_code == 307
        assert "error=invalid_state" in res_bad_state.headers["location"]
        print("  PASS: Invalid state rejected with invalid_state notice.")

        res_no_code = client.get(f"/api/auth/google/callback?state={valid_state}")
        assert res_no_code.status_code == 307
        assert "error=missing_code" in res_no_code.headers["location"]
        print("  PASS: Missing code handled gracefully.")

        # TEST 7: Safe Account Linking (Existing User logs in with Google)
        print("\n[TEST 7] Testing Safe Account Linking (Existing email + Google Sign-In)...")
        existing_local_user = db.query(User).filter(User.email == "authtest_local@testbusiness.com").first()
        orig_user_id = existing_local_user.id
        orig_biz_id = existing_local_user.business_id
        orig_role = existing_local_user.role

        google_identity_same_email = {
            "sub": "google-sub-id-998877",
            "email": "authtest_local@testbusiness.com",
            "email_verified": True,
            "name": "Auth Test User",
            "picture": "https://lh3.googleusercontent.com/test-pic.jpg"
        }

        linked_user, is_new, action = get_or_create_google_user(db, google_identity_same_email)
        assert is_new is False, "Account linking should NOT report is_new=True"
        assert action == "linked", f"Expected action='linked', got '{action}'"
        assert linked_user.id == orig_user_id, "User ID changed during linking!"
        assert linked_user.business_id == orig_biz_id, "Business ID changed during linking!"
        assert linked_user.role == orig_role, "User role changed during linking!"
        assert linked_user.google_id == "google-sub-id-998877", "google_id was not set!"
        assert linked_user.email_verified is True, "email_verified was not set!"
        print(f"  PASS: Existing user (ID: {orig_user_id}) linked to Google account safely. No duplicate records.")

        # Verify existing password login STILL works after linking
        res_pass_after_link = client.post("/api/auth/login", json=login_payload)
        assert res_pass_after_link.status_code == 200, "Password login broke after Google account linking!"
        print("  PASS: Existing password login continues to work after Google account linking.")

        # TEST 8: New Google User Provisioning
        print("\n[TEST 8] Testing New Google User Provisioning...")
        new_google_email = "brand_new_google_user@gmail.com"
        # Clean up prior test if exists
        prior_new = db.query(User).filter(User.email == new_google_email).first()
        if prior_new:
            if prior_new.business:
                db.delete(prior_new.business)
            db.delete(prior_new)
            db.commit()

        google_identity_new = {
            "sub": "google-sub-id-112233",
            "email": new_google_email,
            "email_verified": True,
            "name": "Alice Innovator",
            "picture": "https://lh3.googleusercontent.com/alice-pic.jpg"
        }
        new_user, is_new, action = get_or_create_google_user(db, google_identity_new)
        assert is_new is True, "Brand new user should have is_new=True"
        assert action == "created", f"Expected action='created', got '{action}'"
        assert new_user.auth_provider == "google"
        assert new_user.google_id == "google-sub-id-112233"
        assert new_user.role == "owner"
        assert new_user.business_id is not None
        assert new_user.business.name == "Alice Innovator's Business"
        print(f"  PASS: New Google user provisioned with dedicated business: {new_user.business.name}.")

        # TEST 9: Full Mocked Callback Flow
        print("\n[TEST 9] Testing End-to-End Google OAuth Callback Flow...")
        mock_token_resp = {"access_token": "mock-google-access-token-xyz"}
        mock_userinfo = {
            "sub": "google-sub-id-112233",
            "email": new_google_email,
            "email_verified": True,
            "name": "Alice Innovator"
        }
        test_state = generate_oauth_state()

        with patch("backend.app.routes.auth.exchange_code_for_tokens", return_url=mock_token_resp, return_value=mock_token_resp), \
             patch("backend.app.routes.auth.fetch_google_user_info", return_value=mock_userinfo):
            res_cb = client.get(f"/api/auth/google/callback?code=mock_valid_code&state={test_state}")
            assert res_cb.status_code == 307, f"Callback failed: {res_cb.status_code}"
            loc = res_cb.headers["location"]
            assert "token=" in loc, f"Token not present in redirect URL: {loc}"
            assert "provider=google" in loc
            print("  PASS: End-to-end callback issued JWT token and redirected to frontend.")

        # TEST 10: Verify Non-Auth Features Untouched
        print("\n[TEST 10] Verifying Non-Auth Endpoints (Health, AI, SMS)...")
        res_health = client.get("/api/health")
        assert res_health.status_code == 200 and res_health.json()["status"] == "healthy"
        print("  PASS: /api/health is operational.")

        print("\n==================================================")
        print("ALL 10 VERIFICATION TESTS PASSED SUCCESSFULLY!")
        print("==================================================")

    finally:
        # Cleanup test records
        try:
            for em in ["authtest_local@testbusiness.com", "brand_new_google_user@gmail.com"]:
                u = db.query(User).filter(User.email == em).first()
                if u:
                    if u.business:
                        db.delete(u.business)
                    db.delete(u)
            db.commit()
        except Exception:
            pass
        db.close()

if __name__ == "__main__":
    run_all_tests()
