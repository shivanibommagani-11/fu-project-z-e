"""
Database session management and configuration.
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Fetch database URL from .env
DB_URL = os.getenv("DB_URL")

if not DB_URL:
    logger.warning("DB_URL environment variable is not set!")

# Create the SQLAlchemy engine
# pool_pre_ping=True ensures the connection is valid before each request
engine = create_engine(DB_URL, pool_pre_ping=True)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()

def init_db():
    """
    Initialize database connection.
    Schema creation (Base.metadata.create_all) is skipped because 
    the enterprise Oracle database already manages tables and indexes.
    """
    try:
        # ❌ We removed Base.metadata.create_all(bind=engine) here
        # to prevent ORA-01408 and other schema modification errors.
        
        # ✅ Test the connection safely by running a simple ping query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM DUAL"))
            logger.info("Successfully connected to the Oracle database. (Schema creation bypassed)")
            
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        raise

def get_db():
    """
    FastAPI dependency to provide a database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()