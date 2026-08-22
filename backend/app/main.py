import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# ============================================================
# PROJECT PATH CONFIGURATION
# ============================================================

# Add project root directory to sys.path
# This prevents ModuleNotFoundError: No module named 'backend'
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set PYTHONPATH automatically
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

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

# Load .env from backend folder
load_dotenv(PROJECT_ROOT / "backend" / ".env")


# ============================================================
# FASTAPI IMPORTS
# ============================================================

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse


# ============================================================
# DATABASE
# ============================================================

from backend.app.database.session import init_db, SessionLocal
from backend.app.database.seed_data import seed_database


# ============================================================
# ROUTES
# ============================================================

from backend.app.routes import (
    auth,
    dashboard,
    customers,
    documents,
    invoices,
    tasks,
    approvals,
    ai,
    analytics,
    activities,
    notifications,
    settings,
    policies,
    memory,
    workflows,
    intelligence,
    exceptions,
)


# ============================================================
# LOGGER
# ============================================================

from backend.app.utils.logger import logger


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")

    try:
        # Initialize database tables
        init_db()

        # Seed initial demo data if database is empty
        db = SessionLocal()

        try:
            seed_database(db, reset=False)
            logger.info("Database initialized and ready.")

        finally:
            db.close()

    except Exception as exc:
        logger.error(
            f"Database initialization failed: {exc}",
            exc_info=True
        )

        # Re-raise so deployment/runtime failure is visible
        raise

    yield

    logger.info("Application shutting down...")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Business Operations Agent API",
    description=(
        "An Intelligent Digital Employee for Small Businesses. "
        "REST APIs for Document Intelligence, AI Workflows, "
        "Invoices, Human-in-the-Loop Approvals, and Command Center."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

# Frontend origins that are allowed to communicate with this API.
#
# IMPORTANT:
# Your current Vercel frontend is:
# https://ai-business-agent-9ubt.vercel.app
#
# If your Vercel URL changes in the future, add the new URL here.

origins = [
    # Local development
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",

    # Current Vercel frontend
    "https://ai-business-agent-9ubt.vercel.app",

    # Previous Vercel frontend
    "https://ai-business-agent-ten.vercel.app",
]


# Allow additional origins from CORS_ORIGINS environment variable.
#
# Example Render environment variable:
#
# CORS_ORIGINS=https://example.vercel.app,https://another.vercel.app

cors_origins_env = os.getenv("CORS_ORIGINS", "")

if cors_origins_env:
    custom_origins = [
        origin.strip()
        for origin in cors_origins_env.split(",")
        if origin.strip()
    ]

    origins.extend(custom_origins)


# Remove duplicate origins
origins = list(set(origins))


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STATIC FILES / UPLOADS
# ============================================================

upload_dir = os.getenv("UPLOAD_DIR", "./uploads")

os.makedirs(upload_dir, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory=upload_dir),
    name="uploads",
)


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    logger.error(
        f"Global error on {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": (
                "An internal server error occurred. "
                "Our digital operations team is looking into it."
            )
        },
    )


# ============================================================
# API ROUTERS
# ============================================================

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


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "app": "AI Business Operations Agent",
        "status": "operational",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "FastAPI + SQLAlchemy + Gemini AI",
    }


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )