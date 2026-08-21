import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from backend.app.database.base import Base

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_business_agent.db")
environment = os.getenv("ENVIRONMENT", "development").lower()
allow_sqlite_fallback = os.getenv(
    "ALLOW_SQLITE_FALLBACK",
    "false" if environment == "production" else "true"
).lower() == "true"

# Normalize relative sqlite path to absolute project root path
if DATABASE_URL.startswith("sqlite:///./") or DATABASE_URL == "sqlite:///ai_business_agent.db":
    db_file_name = DATABASE_URL.split("/")[-1]
    abs_db_path = PROJECT_ROOT / db_file_name
    DATABASE_URL = f"sqlite:///{abs_db_path.as_posix()}"

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True
    )
except Exception as e:
    if not allow_sqlite_fallback:
        raise RuntimeError(
            "Database initialization failed and SQLite fallback is disabled. "
            "Check DATABASE_URL and the Supabase connection settings."
        ) from e

    # Keep local development usable when the configured database is unavailable.
    print(f"[Warning] Failed to initialize {DATABASE_URL}: {e}. Falling back to local SQLite.")
    abs_db_path = PROJECT_ROOT / "ai_business_agent.db"
    DATABASE_URL = f"sqlite:///{abs_db_path.as_posix()}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.app.models.models import (
        Business, User, Customer, Document, Invoice,
        Task, Approval, Activity, Email, Notification
    )
    Base.metadata.create_all(bind=engine)
