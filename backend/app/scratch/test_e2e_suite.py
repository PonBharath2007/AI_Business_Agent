import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed_data import seed_database
from backend.app.models.models import User, Business, Invoice, Customer

def run_comprehensive_verification():
    print("==================================================")
    print("STARTING FULL END-TO-END SUITE VERIFICATION")
    print("==================================================")

    init_db()
    db = SessionLocal()
    seed_database(db, reset=True)
    db.close()

    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] 1. API Health Check passed:", res.json())

    # 2. Authenticate
    login_res = client.post("/api/auth/login", json={"email": "admin@summitdigital.com", "password": "admin123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] 2. JWT Authentication successful.")

    # 3. Dashboard
    dash_res = client.get("/api/dashboard", headers=headers)
    assert dash_res.status_code == 200, f"Dashboard failed: {dash_res.text}"
    dash_data = dash_res.json()
    assert "summary" in dash_data and "daily_brief" in dash_data
    print(f"[PASS] 3. Dashboard API: Total Customers = {dash_data['summary']['total_customers']}, Overdue = {dash_data['summary']['overdue_invoices_count']}")

    # 4. Business Health Score
    health_res = client.get("/api/intelligence/health-score", headers=headers)
    assert health_res.status_code == 200, f"Health score failed: {health_res.text}"
    health_data = health_res.json()
    assert 0 <= health_data["overall_score"] <= 100
    print(f"[PASS] 4. Business Health Score API: Score = {health_data['overall_score']}/100, Rating = '{health_data['rating']}', Categories = {len(health_data['categories'])}")

    # 5. Cash Flow Forecast & Aging
    cf_res = client.get("/api/intelligence/cash-flow", headers=headers)
    assert cf_res.status_code == 200, f"Cash flow failed: {cf_res.text}"
    cf_data = cf_res.json()
    assert "aging_buckets" in cf_data and "expected_inflow_30d" in cf_data
    print(f"[PASS] 5. Cash Flow Intelligence API: Inflow 30d = {cf_data['expected_inflow_30d']}, Outstanding = {cf_data['outstanding_receivables']}")

    # 6. AI Root Cause Analysis
    rca_res = client.post("/api/intelligence/root-cause", json={"query": "Why are payments getting delayed?"}, headers=headers)
    assert rca_res.status_code == 200, f"Root cause failed: {rca_res.text}"
    rca_data = rca_res.json()
    assert len(rca_data["key_factors"]) > 0
    print(f"[PASS] 6. AI Root Cause Analysis API: Delay rate = {rca_data['delay_rate']}, Factors = {len(rca_data['key_factors'])}")

    # 7. What-If Business Simulator
    sim_res = client.post("/api/intelligence/what-if", json={"scenario": "early_discount", "param_discount_pct": 5.0}, headers=headers)
    assert sim_res.status_code == 200, f"What-If failed: {sim_res.text}"
    sim_data = sim_res.json()
    print(f"[PASS] 7. What-If Simulator API: Scenario = '{sim_data['scenario_title']}', Impact = {sim_data['impact_percentage']}")

    # 8. Customer 360
    c360_res = client.get("/api/intelligence/customer-360/1", headers=headers)
    assert c360_res.status_code == 200, f"Customer 360 failed: {c360_res.text}"
    c360_data = c360_res.json()
    print(f"[PASS] 8. Customer 360 API: Customer = '{c360_data['customer']['name']}', Tag = '{c360_data['behavior']['tag']}', Score = {c360_data['behavior']['score']}/100")

    # 9. Exception Center
    exc_res = client.get("/api/exceptions", headers=headers)
    assert exc_res.status_code == 200, f"Exceptions failed: {exc_res.text}"
    exceptions = exc_res.json()
    print(f"[PASS] 9. Exception Center API: Active Exceptions = {len(exceptions)}")

    # 10. AI Command Center Agent Queries
    queries = [
        "What needs my attention today?",
        "Show all overdue invoices.",
        "Why are payments getting delayed?",
        "Prepare payment reminders for all overdue customers."
    ]
    for q in queries:
        chat_res = client.post("/api/ai/chat", json={"message": q}, headers=headers)
        assert chat_res.status_code == 200, f"Chat failed for '{q}': {chat_res.text}"
        resp_data = chat_res.json()
        assert "response" in resp_data and len(resp_data["response"]) > 0
        print(f"[PASS] 10. Command Center Agent Tool Query: '{q}' -> Response Length = {len(resp_data['response'])} chars, Actions = {len(resp_data.get('suggested_actions', []))}")

    # 11. Business Policies CRUD
    pol_res = client.get("/api/policies", headers=headers)
    assert pol_res.status_code == 200
    pols = pol_res.json()
    print(f"[PASS] 11. Business Policies API: {len(pols)} active policies configured.")

    # 12. AI Business Memory CRUD
    mem_res = client.get("/api/memory", headers=headers)
    assert mem_res.status_code == 200
    mems = mem_res.json()
    print(f"[PASS] 12. AI Business Memory API: {len(mems)} memory items recorded.")

    # 13. Workflow Rules & Executions
    wf_res = client.get("/api/workflows", headers=headers)
    assert wf_res.status_code == 200
    rules = wf_res.json()
    assert len(rules) > 0
    exec_res = client.post(f"/api/workflows/{rules[0]['id']}/execute", headers=headers)
    assert exec_res.status_code == 200
    print(f"[PASS] 13. AI Workflow Rules & Execution API: {len(rules)} rules, execution response = '{exec_res.json()['message']}'")

    # 14. Email AI Transformation
    transform_res = client.post("/api/ai/transform-email", json={"text": "Please pay your invoice of $5,000 as soon as possible.", "action": "make_urgent"}, headers=headers)
    assert transform_res.status_code == 200
    print("[PASS] 14. AI Email Transformation API: Transformed text generated successfully.")

    print("==================================================")
    print("ALL 14 END-TO-END MODULE TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_comprehensive_verification()
