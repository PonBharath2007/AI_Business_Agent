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
    from sqlalchemy import text
    from backend.app.models.models import (
        Business, User, Customer, Document, Invoice,
        Task, Approval, Activity, Email, Notification,
        CommunicationLog
    )
    Base.metadata.create_all(bind=engine)

    # Safe schema migration for newly added User OAuth fields
    with engine.connect() as conn:
        dialect_name = engine.dialect.name
        columns_to_add = [
            ("auth_provider", "VARCHAR(50) DEFAULT 'local'"),
            ("google_id", "VARCHAR(255)"),
            ("profile_picture", "VARCHAR(500)"),
            ("email_verified", "BOOLEAN DEFAULT FALSE")
        ]

        for col_name, col_type in columns_to_add:
            try:
                if dialect_name == "postgresql":
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                    conn.commit()
                elif dialect_name == "sqlite":
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
            except Exception:
                # Column likely already exists
                pass

        # Ensure password_hash can be null in postgres
        if dialect_name == "postgresql":
            try:
                conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;"))
                conn.commit()
            except Exception:
                pass
