import os
import sys
import time
import statistics
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure utf-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_suite(mode="current"):
    print("\n" + "=" * 75)
    print(f"  RUNNING BENCHMARK MODE: {mode.upper()}")
    print("=" * 75)

    if mode == "sqlite":
        os.environ["DATABASE_URL"] = f"sqlite:///{(PROJECT_ROOT / 'ai_business_agent.db').as_posix()}"
        os.environ["ALLOW_SQLITE_FALLBACK"] = "true"
        # Reload database engine
        import importlib
        import backend.app.database.session as sess
        sess.DATABASE_URL = os.environ["DATABASE_URL"]
        sess.engine = sess.create_configured_engine(sess.DATABASE_URL)
        sess.SessionLocal = sess.sessionmaker(autocommit=False, autoflush=False, bind=sess.engine)

    from backend.app.main import app
    from fastapi.testclient import TestClient
    from backend.app.database.session import engine, SessionLocal
    from sqlalchemy import text
    from backend.app.models.models import User

    client = TestClient(app)

    db_url_safe = str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url)
    dialect = engine.dialect.name
    print(f"\n[1] Database Connection: {dialect} ({db_url_safe})")

    # Raw SQL SELECT 1
    raw_query_times = []
    with engine.connect() as conn:
        for _ in range(10):
            q_start = time.perf_counter()
            conn.execute(text("SELECT 1"))
            raw_query_times.append((time.perf_counter() - q_start) * 1000)

    print(f"  -> Raw SQL 'SELECT 1' Latency (10 runs):")
    print(f"     Min: {min(raw_query_times):.2f}ms | Median: {statistics.median(raw_query_times):.2f}ms | Avg: {statistics.mean(raw_query_times):.2f}ms | p95: {sorted(raw_query_times)[int(len(raw_query_times)*0.95)]:.2f}ms")

    # ORM User Count
    db = SessionLocal()
    orm_query_times = []
    for _ in range(10):
        q_start = time.perf_counter()
        _ = db.query(User).count()
        orm_query_times.append((time.perf_counter() - q_start) * 1000)
    db.close()
    print(f"  -> ORM Query (User.count) Latency (10 runs):")
    print(f"     Min: {min(orm_query_times):.2f}ms | Median: {statistics.median(orm_query_times):.2f}ms | Avg: {statistics.mean(orm_query_times):.2f}ms | p95: {sorted(orm_query_times)[int(len(orm_query_times)*0.95)]:.2f}ms")

    # Benchmark Helper
    def bench(label, method, url, headers=None, json_data=None, runs=10):
        times = []
        status_code = None
        for _ in range(runs):
            t_req = time.perf_counter()
            if method.upper() == "GET":
                res = client.get(url, headers=headers)
            elif method.upper() == "POST":
                res = client.post(url, headers=headers, json=json_data)
            times.append((time.perf_counter() - t_req) * 1000)
            status_code = res.status_code
        p95 = sorted(times)[int(len(times) * 0.95)]
        print(f"  {label:<38} [{status_code}]: Min {min(times):6.2f}ms | Med {statistics.median(times):6.2f}ms | Avg {statistics.mean(times):6.2f}ms | p95 {p95:6.2f}ms")
        return res, times

    print("\n[2] API Endpoint Latencies:")
    bench("GET / (Root Metadata)", "GET", "/", runs=10)
    bench("GET /api/health", "GET", "/api/health", runs=10)

    # Auth
    login_res, _ = bench("POST /api/auth/login", "POST", "/api/auth/login",
                         json_data={"email": "admin@summitdigital.com", "password": "admin123"}, runs=5)
    
    token = None
    if login_res.status_code == 200:
        token = login_res.json().get("access_token")
    if not token:
        from backend.app.auth.jwt import create_access_token
        # Try to find a user id
        db = SessionLocal()
        first_user = db.query(User).first()
        uid = str(first_user.id) if first_user else "20"
        email = first_user.email if first_user else "admin@summitdigital.com"
        db.close()
        token = create_access_token(data={"sub": uid, "email": email})

    headers = {"Authorization": f"Bearer {token}"}

    print("\n[3] Authenticated Core Application Endpoints:")
    bench("GET /api/dashboard/summary", "GET", "/api/dashboard/summary", headers=headers, runs=10)
    bench("GET /api/analytics/overview", "GET", "/api/analytics/overview", headers=headers, runs=10)
    bench("GET /api/customers", "GET", "/api/customers", headers=headers, runs=10)
    bench("GET /api/invoices", "GET", "/api/invoices", headers=headers, runs=10)
    bench("GET /api/tasks", "GET", "/api/tasks", headers=headers, runs=10)
    bench("GET /api/approvals", "GET", "/api/approvals", headers=headers, runs=10)
    bench("GET /api/notifications", "GET", "/api/notifications", headers=headers, runs=10)

def measure_ocr_speed():
    print("\n" + "=" * 75)
    print("  [4] DOCUMENT OCR & PARSING ENGINE BENCHMARK")
    print("=" * 75)
    sample_pdf = PROJECT_ROOT / "uploads" / "21_1789032136_972a80_Bharath_Invoice.pdf"
    if not sample_pdf.exists():
        print("Sample file not found, skipping OCR test.")
        return

    import fitz
    pdf_bytes = sample_pdf.read_bytes()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    doc.close()

    # Raw PyMuPDF speed
    raw_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "".join(page.get_text() for page in doc)
        doc.close()
        raw_times.append((time.perf_counter() - t0) * 1000)

    print(f"PyMuPDF Raw Text Extraction ({len(pdf_bytes)/1024:.1f} KB PDF, {page_count} pages):")
    print(f"  Min: {min(raw_times):.2f}ms | Median: {statistics.median(raw_times):.2f}ms | Avg: {statistics.mean(raw_times):.2f}ms")
    print(f"  Characters extracted: {len(text)}")

    # Full document processor pipeline
    from backend.app.services.document_processor import extract_text_from_pdf
    pipeline_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        res = extract_text_from_pdf(str(sample_pdf))
        pipeline_times.append((time.perf_counter() - t0) * 1000)

    print(f"Full Multi-Stage Extraction Pipeline (Tables + Text + Page Analysis):")
    print(f"  Min: {min(pipeline_times):.2f}ms | Median: {statistics.median(pipeline_times):.2f}ms | Avg: {statistics.mean(pipeline_times):.2f}ms")
    print(f"  Total Extracted Characters: {len(res.get('text', ''))}")
    print(f"  Has Scanned Pages / OCR trigger: {res.get('has_scanned_pages')}")

if __name__ == "__main__":
    t_start = time.perf_counter()
    from backend.app.main import app
    import_time = (time.perf_counter() - t_start) * 1000
    print(f"\n>> Python & FastAPI Initial Application Import Time: {import_time:.2f} ms")

    # Mode 1: Active Configuration (Supabase Cloud PostgreSQL)
    run_suite(mode="supabase (active)")

    # Mode 2: Local SQLite
    run_suite(mode="sqlite")

    # OCR Benchmark
    measure_ocr_speed()
