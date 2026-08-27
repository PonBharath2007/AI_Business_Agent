import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# ============================================================
# PROJECT PATH CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if "PYTHONPATH" in os.environ:
    python_paths = os.environ["PYTHONPATH"].split(os.pathsep)
    if str(PROJECT_ROOT) not in python_paths:
        os.environ["PYTHONPATH"] = (
            f"{PROJECT_ROOT}{os.pathsep}{os.environ['PYTHONPATH']}"
        )
else:
    os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")

# ============================================================
# FASTAPI IMPORTS & SETUP
# ============================================================
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.app.database.session import init_db, SessionLocal
from backend.app.database.seed_data import seed_database
from backend.app.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    try:
        init_db()
        db = SessionLocal()
        try:
            seed_database(db, reset=False)
            logger.info("Database initialized and ready.")
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}", exc_info=True)
        raise
    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title="AI Business Operations Agent API",
    description="An Intelligent Digital Employee for Small Businesses.",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================
# CORS CONFIGURATION
# ============================================================

default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://ai-business-agent-ten.vercel.app",
]

cors_origins_env = os.getenv("CORS_ORIGINS", "")
custom_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
origins = list(set(default_origins + custom_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$|^https:\/\/.*\.onrender\.com$|^http:\/\/localhost(:\d+)?$|^http:\/\/127\.0\.0\.1(:\d+)?$",
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ROUTES & STATIC FILES
# ============================================================

from backend.app.routes import (
    auth, dashboard, customers, documents, invoices, tasks, approvals, 
    ai, analytics, activities, notifications, settings, policies, memory, 
    workflows, intelligence, exceptions, communications
)

app.include_router(auth.router)
app.include_router(auth.users_router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(documents.router)
app.include_router(invoices.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(ai.router)
app.include_router(communications.router)
app.include_router(analytics.router)
app.include_router(activities.router)
app.include_router(notifications.router)
app.include_router(settings.router)
app.include_router(policies.router)
app.include_router(memory.router)
app.include_router(workflows.router)
app.include_router(intelligence.router)
app.include_router(exceptions.router)

upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Our digital operations team is looking into it."},
    )

@app.get("/")
def root():
    return {"app": "AI Business Operations Agent", "status": "operational", "version": "1.0.0", "docs_url": "/docs"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "engine": "FastAPI + SQLAlchemy + Gemini AI"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)