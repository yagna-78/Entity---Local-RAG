import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Database Configuration
DB_USER = os.getenv("SUPABASE_USER")
DB_PASSWORD = os.getenv("SUPABASE_PASSWORD")
DB_HOST = os.getenv("SUPABASE_HOST")
DB_PORT = os.getenv("SUPABASE_PORT", "5432")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

# Construct Connection String
# Format: postgresql://user:password@host:port/dbname
if not all([DB_USER, DB_PASSWORD, DB_HOST]):
    logger.warning("Supabase credentials not found in environment variables. Database features will be disabled.")
    DATABASE_URL = None
else:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Setup
engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    try:
        # Create Engine
        # pool_pre_ping=True helps verify connections before usage
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database engine initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")

def get_db():
    """
    Dependency generator for FastAPI to get a database session.
    """
    if SessionLocal is None:
        return None
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def execute_read_only_query(query: str):
    """
    Executes a raw SQL query safely.
    Ensures input is a SELECT statement using simple string check (additional validation in Agent layer).
    Returns a list of dicts.
    """
    if not engine:
        raise Exception("Database not configured.")

    # Basic safety check — allow SELECT and WITH (CTEs)
    q_check = query.strip().lower()
    if not (q_check.startswith("select") or q_check.startswith("with")):
        raise Exception("Security Alert: Only SELECT/WITH statements are allowed.")

    with engine.connect() as connection:
        result = connection.execute(text(query))
        keys = result.keys()
        return [dict(zip(keys, row)) for row in result.fetchall()]
