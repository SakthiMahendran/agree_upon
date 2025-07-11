#api/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////data/test.db" if os.getenv("SPACE_ID") else "sqlite:///./test.db"
) if os.getenv("SPACE_ID") else "sqlite:///./test.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ------------------------------------------------------------
# 🛠️  Lightweight auto-migration for SQLite (add missing columns)
# ------------------------------------------------------------
from sqlalchemy import text, inspect

def _ensure_sqlite_columns():
    """Add new columns that were introduced after initial DB creation.
    Currently ensures `state` column exists on `conversations` table.
    This is *not* a full migration system but prevents runtime crashes
    during development when the schema evolves.
    """
    # Only run for SQLite databases
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect() as conn:
        insp = inspect(conn)
        if "conversations" not in insp.get_table_names():
            # Table will be created by Base.metadata.create_all later
            return

        # Fetch existing column names
        existing_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(conversations);"))}

        if "state" not in existing_cols:
            # Add the column; Text type, nullable
            conn.execute(text("ALTER TABLE conversations ADD COLUMN state TEXT;"))
            conn.commit()

# Run immediately on import so it's executed before first request
_try_migrate = None
try:
    _ensure_sqlite_columns()
except Exception as e:
    # Do not crash the app if auto-migration fails; just log.
    import logging
    logging.getLogger("api.database").warning("Auto-migration failed: %s", e)

# Dependency to use in endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
