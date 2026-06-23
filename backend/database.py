"""
Database configuration and session management.
Uses SQLite via SQLAlchemy for simplicity.
"""

import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crane_ai.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a DB session and ensures it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Column migrations (ALTER TABLE for existing DBs) ────────────────────────
# SQLite's create_all() only creates missing tables; it never adds new columns
# to existing tables. We handle this with a safe try/except ALTER TABLE.

_REPORT_MIGRATIONS = [
    "ALTER TABLE reports ADD COLUMN follow_up_status VARCHAR(20)",
    "ALTER TABLE reports ADD COLUMN follow_up_closed_by INTEGER REFERENCES users(id)",
    "ALTER TABLE reports ADD COLUMN follow_up_closed_at DATETIME",
    "ALTER TABLE reports ADD COLUMN follow_up_note TEXT",
]

_KNOWLEDGE_GAP_MIGRATIONS = [
    "ALTER TABLE knowledge_gaps ADD COLUMN detected_by VARCHAR(40) DEFAULT 'system'",
    "ALTER TABLE knowledge_gaps ADD COLUMN missing_information TEXT",
    "ALTER TABLE knowledge_gaps ADD COLUMN affected_asset_type VARCHAR(100)",
    "ALTER TABLE knowledge_gaps ADD COLUMN suggested_file_to_update VARCHAR(200)",
    "ALTER TABLE knowledge_gaps ADD COLUMN suggested_section_or_node VARCHAR(200)",
    "ALTER TABLE knowledge_gaps ADD COLUMN evidence_checked TEXT",
    "ALTER TABLE knowledge_gaps ADD COLUMN confidence FLOAT DEFAULT 0.0",
    "ALTER TABLE knowledge_gaps ADD COLUMN resolution_note TEXT",
    "ALTER TABLE knowledge_gaps ADD COLUMN knowledge_content_added TEXT",
]


def _run_migrations():
    """Add new columns to existing tables without dropping data."""
    with engine.connect() as conn:
        for stmt in _REPORT_MIGRATIONS + _KNOWLEDGE_GAP_MIGRATIONS:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                # Column already exists — ignore
                pass


def init_db():
    """Create all tables, then apply column migrations."""
    from backend import models  # noqa: F401 – imported for side-effects
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    logger.info("Database initialised (V3 schema with knowledge gap workflow).")
