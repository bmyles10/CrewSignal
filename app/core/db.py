"""
NOTES:
1. The database is like a shared notebook that many people write in at the same time.
   check_same_thread=False tells SQLite it's OK for multiple workers to use the same
   connection, so requests don't crash into each other.
2. WAL mode is like giving everyone their own scratch pad first, then copying it to the
   main notebook when they're done. This means readers and writers don't block each
   other, making the database much faster under load.
3. create_db_and_tables() runs once when the server starts to make sure all the tables
   already exist before any requests come in — like setting up the filing cabinet before
   opening for business.
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