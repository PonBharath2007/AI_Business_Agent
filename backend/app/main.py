import sys
import os
from pathlib import Path

# Add project root directory to sys.path and PYTHONPATH automatically
# This prevents 'ModuleNotFoundError: No module named backend' in uvicorn reload subprocesses regardless of execution folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if "PYTHONPATH" in os.environ:
    if str(PROJECT_ROOT) not in os.environ["PYTHONPATH"].split(os.pathsep):
        os.environ["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{os.environ['PYTHONPATH']}"
else:
    os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load .env from both project root and backend folder
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
from backend.app.database.session import init_db, SessionLocal
from backend.app.database.seed_data import seed_database
from backend.app.routes import (
    auth, dashboard, customers, documents, invoices,
    tasks, approvals, ai, analytics, activities, notifications, settings,
    policies, memory, workflows, intelligence, exceptions
)
from backend.app.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()
    # Seed initial demo data if empty
    db = SessionLocal()
    try:
        seed_database(db, reset=False)
        logger.info("Database initialized and ready.")
    finally:
        db.close()
    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title="AI Business Operations Agent API",
    description="An Intelligent Digital Employee for Small Businesses. REST APIs for Document Intelligence, AI Workflows, Invoices, Human-in-the-Loop Approvals, and Command Center.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads & sample documents
upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# Exception handler for clean error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Our digital operations team is looking into it."}
    )

# Include API Routers
app.include_router(auth.router)
app.include_router(auth.users_router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(documents.router)
app.include_router(invoices.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(ai.router)
app.include_router(analytics.router)
app.include_router(activities.router)
app.include_router(notifications.router)
app.include_router(settings.router)
app.include_router(policies.router)
app.include_router(memory.router)
app.include_router(workflows.router)
app.include_router(intelligence.router)
app.include_router(exceptions.router)


@app.get("/")
def root():
    return {
        "app": "AI Business Operations Agent",
        "status": "operational",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "engine": "FastAPI + SQLAlchemy + Gemini AI"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
