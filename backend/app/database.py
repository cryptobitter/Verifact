import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_FILE_PATH = BACKEND_DIR / "verifact.db"
LEGACY_DB_PATH = BACKEND_DIR / "fractoes.db"
ROOT_LEGACY_DB_PATH = BACKEND_DIR.parent / "fractoes.db"


def _migrate_legacy_db_if_needed():
    """Safely copies legacy fractoes.db to verifact.db if not already present. Never deletes original."""
    if not DB_FILE_PATH.exists():
        source_db = None
        if LEGACY_DB_PATH.exists():
            source_db = LEGACY_DB_PATH
        elif ROOT_LEGACY_DB_PATH.exists():
            source_db = ROOT_LEGACY_DB_PATH

        if source_db:
            try:
                shutil.copy2(source_db, DB_FILE_PATH)
                print(f"[DB MIGRATION] Safely copied legacy database ({source_db.name}) to {DB_FILE_PATH.name}. Original preserved.")
            except Exception as exc:
                print(f"[WARN] Failed to copy legacy database: {exc}")


def _build_engine():
    raw_db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL).strip()

    # Standardize postgres:// to postgresql:// for SQLAlchemy compatibility
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

    if raw_db_url.startswith("postgresql"):
        try:
            pg_engine = create_engine(
                raw_db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 5},
            )
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[DB] Successfully connected to remote PostgreSQL database.")
            return pg_engine
        except Exception as exc:
            print(f"[WARN] Remote PostgreSQL connection failed ({exc}). Falling back to local SQLite ({DB_FILE_PATH}).")

    _migrate_legacy_db_if_needed()

    return create_engine(
        f"sqlite:///{DB_FILE_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )


engine = _build_engine()


def _ensure_sqlite_columns():
    """Ensures newly added columns exist in SQLite databases without needing manual migrations."""
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            if 'users' in tables:
                cols = [col["name"] for col in inspector.get_columns("users")]
                if "last_login_at" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP"))
                if "institution" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN institution VARCHAR(255)"))
                if "license_number" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN license_number VARCHAR(100)"))
    except Exception as exc:
        print(f"[WARN] Failed to auto-migrate columns: {exc}")


_ensure_sqlite_columns()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
