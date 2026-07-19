import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgrespassword@localhost:5432/betting_lakehouse"
)

try:
    print(f"[DB] Attempting connection to PostgreSQL: {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    # Test connection
    with engine.connect() as conn:
        pass
    print("[DB] PostgreSQL connection successful.")
except Exception as e:
    print(f"[WARNING] [DB] PostgreSQL connection failed: {e}")
    # Fallback to local SQLite database in app directory
    db_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sqlite_db_path = os.path.join(db_dir, "betting_lakehouse.db")
    os.makedirs(os.path.dirname(sqlite_db_path), exist_ok=True)
    FALLBACK_URL = f"sqlite:///{sqlite_db_path}"
    print(f"[INFO] [DB] Falling back to local SQLite database: {FALLBACK_URL}")
    engine = create_engine(
        FALLBACK_URL, 
        connect_args={"check_same_thread": False} if "sqlite" in FALLBACK_URL else {}
    )

# Session factory for transaction contexts
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency to get database session context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
