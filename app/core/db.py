"""
NOTES:
1. Thread Safety: SQLite strictly enforces single-thread access by default. We pass `check_same_thread=False` to the connection arguments so FastAPI's async webhook workers can share the connection pool without crashing under high load.
2. Lifespan Bootstrapping: The `create_db_and_tables` function will be called directly by main.py when the server boots to ensure our tracking ledger always exists before the first client payload hits the gateway.
"""

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from app.core.config import settings
import os

# Create the physical database directory if it doesn't exist
DATABASE_DIR = "database"
os.makedirs(DATABASE_DIR, exist_ok=True)

# Define the local SQLite connection string
sqlite_url = f"sqlite:///{DATABASE_DIR}/crewsignal.db"

# The Engine is the core connection pool to the database
# check_same_thread=False is REQUIRED for FastAPI + SQLite concurrency
engine = create_engine(
    sqlite_url,
    echo=False, # Set to True if you want to see raw SQL queries in the terminal
    connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def set_sqlite_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

def create_db_and_tables():
    """Reads all SQLModel classes and generates the physical tables in the database."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    Dependency generator for FastAPI endpoints. 
    Yields a fresh database session and safely closes it after the request finishes.
    """
    with Session(engine) as session:
        yield session