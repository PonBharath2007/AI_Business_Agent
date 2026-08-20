import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models.models import User, Business, Customer, Invoice

def test_auth_and_isolation():
    print("==================================================")
    print("RUNNING AUTHENTICATION & MULTI-USER ISOLATION TESTS")
    print("==================================================")

    init_db()
    db = SessionLocal()
    seed_database(db, reset=True)
    db.close()

    client = TestClient(app)

    # 1. Test Unauthenticated Access
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}: {unauth_res.text}"
    print("[PASS] 1. Unauthenticated request to /api/auth/me correctly returns 401 Unauthorized.")

    # 2. Test Invalid Credentials
    bad_login = client.post("/api/auth/login", json={"email": "nonexistent@example.com", "password": "wrongpassword"})
    assert bad_login.status_code == 401
    assert "account found" in bad_login.json()["detail"].lower() or "invalid" in bad_login.json()["detail"].lower()
    print("[PASS] 2. Invalid login returns 401 with clean error message.")

    # 3. Register User A (Alpha Solutions)
    reg_a = client.post("/api/auth/register", json={
        "name": "Alice Walker",
        "email": "alice@alphasolutions.com",
        "password": "Password123!",
        "business_name": "Alpha Solutions LLC",
        "currency": "USD"
    })
    assert reg_a.status_code == 200, f"Register A failed: {reg_a.text}"
    token_a = reg_a.json()["access_token"]
    user_a = reg_a.json()["user"]
    assert user_a["email"] == "alice@alphasolutions.com"
    assert user_a["business_name"] == "Alpha Solutions LLC"
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("[PASS] 3. Registered User A ('alice@alphasolutions.com') with business 'Alpha Solutions LLC'.")

    # 4. Duplicate Registration
    dup_res = client.post("/api/auth/register", json={
        "name": "Alice Walker Duplicate",
        "email": "alice@alphasolutions.com",
        "password": "Password123!",
        "business_name": "Alpha Duplicate"
    })
    assert dup_res.status_code == 400
    print("[PASS] 4. Duplicate registration with existing email rejected with 400 Bad Request.")

    # 5. Register User B (Beta Dynamics)
    reg_b = client.post("/api/auth/register", json={
        "name": "Bob Vance",
        "email": "bob@betadynamics.com",
        "password": "Password456!",
        "business_name": "Beta Dynamics Inc",
        "currency": "INR"
    })
    assert reg_b.status_code == 200
    token_b = reg_b.json()["access_token"]
    user_b = reg_b.json()["user"]
    assert user_b["email"] == "bob@betadynamics.com"
    assert user_b["business_name"] == "Beta Dynamics Inc"
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print("[PASS] 5. Registered User B ('bob@betadynamics.com') with business 'Beta Dynamics Inc'.")

    # 6. Verify /api/auth/me and /api/users/me for User A
    me_a = client.get("/api/auth/me", headers=headers_a)
    assert me_a.status_code == 200
    assert me_a.json()["email"] == "alice@alphasolutions.com"
    assert me_a.json()["name"] == "Alice Walker"
    assert me_a.json()["business_name"] == "Alpha Solutions LLC"

    me_alias_a = client.get("/api/users/me", headers=headers_a)
    assert me_alias_a.status_code == 200
    assert me_alias_a.json()["email"] == "alice@alphasolutions.com"
    print("[PASS] 6. /api/auth/me and /api/users/me return dynamic profile for User A.")

    # 7. Verify /api/auth/me for User B
    me_b = client.get("/api/auth/me", headers=headers_b)
    assert me_b.status_code == 200
    assert me_b.json()["email"] == "bob@betadynamics.com"
    assert me_b.json()["name"] == "Bob Vance"
    assert me_b.json()["business_name"] == "Beta Dynamics Inc"
    print("[PASS] 7. /api/auth/me returns dynamic profile for User B.")

    # 8. User A creates a customer and invoice
    cust_a = client.post("/api/customers", json={
        "name": "Alpha Client Prime",
        "email": "prime@alphaclient.com",
        "phone": "+1 555-0199",
        "company": "Alpha Client Prime",
        "status": "active"
    }, headers=headers_a)
    assert cust_a.status_code == 200
    cust_a_id = cust_a.json()["id"]

    inv_a = client.post("/api/invoices", json={
        "customer_id": cust_a_id,
        "invoice_number": "INV-ALPHA-001",
        "amount": 7500.0,
        "issue_date": "2026-08-01",
        "due_date": "2026-08-30",
        "status": "pending",
        "description": "Custom Cloud Consulting Services"
    }, headers=headers_a)
    assert inv_a.status_code == 200
    print("[PASS] 8. User A created customer 'Alpha Client Prime' and invoice 'INV-ALPHA-001'.")

    # 9. Verify Data Isolation: User B CANNOT see User A's customers or invoices
    b_custs = client.get("/api/customers", headers=headers_b)
    assert b_custs.status_code == 200
    assert len(b_custs.json()) == 0, f"Expected 0 customers for User B, found {len(b_custs.json())}"

    b_invs = client.get("/api/invoices", headers=headers_b)
    assert b_invs.status_code == 200
    assert len(b_invs.json()) == 0, f"Expected 0 invoices for User B, found {len(b_invs.json())}"
    print("[PASS] 9. User B cannot see User A's customers or invoices (Strict multi-tenant data isolation verified).")

    # 10. Verify User A sees User A's data
    a_custs = client.get("/api/customers", headers=headers_a)
    assert len(a_custs.json()) == 1
    assert a_custs.json()[0]["name"] == "Alpha Client Prime"

    a_invs = client.get("/api/invoices", headers=headers_a)
    assert len(a_invs.json()) == 1
    assert a_invs.json()[0]["invoice_number"] == "INV-ALPHA-001"
    print("[PASS] 10. User A sees their own isolated customer and invoice.")

    # 11. Test Invalid / Expired Token
    fake_header = {"Authorization": "Bearer invalid.token.signature"}
    fake_res = client.get("/api/auth/me", headers=fake_header)
    assert fake_res.status_code == 401
    print("[PASS] 11. Invalid token correctly rejected with 401.")

    # 12. Test Demo Login
    demo_login = client.post("/api/auth/login", json={"email": "admin@summitdigital.com", "password": "admin123"})
    assert demo_login.status_code == 200
    assert demo_login.json()["user"]["email"] == "admin@summitdigital.com"
    print("[PASS] 12. Optional Demo Login works cleanly for presentation mode.")

    print("==================================================")
    print("ALL AUTHENTICATION & ISOLATION TESTS PASSED (100% SUCCESS)!")
    print("==================================================")

if __name__ == "__main__":
    test_auth_and_isolation()
