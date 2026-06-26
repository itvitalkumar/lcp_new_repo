"""
backend/app/database.py
Campus Central API - Database Connection & Session Management

Phase 1 (June 18, 2026): Initial SQLite setup with basic engine and session.
Phase 2 (June 19, 2026): Added Azure SQL support with connection pooling.
Phase 3 (June 25, 2026): Azure SQL Database (replaces SQLite in production).
Phase 4 (June 26, 2026): ENHANCED - Connection pooling optimized for Azure SQL.
                         Added retry logic for transient errors.
                         Better error handling and logging.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .config import settings
import logging
import time

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE ENGINE WITH CONNECTION POOLING
# ============================================================

def create_database_engine():
    """
    Create SQLAlchemy engine with connection pooling optimized for Azure SQL.
    Uses different configurations for SQLite (local) vs Azure SQL (production).
    """
    database_url = settings.DATABASE_URL
    is_sqlite = "sqlite" in database_url
    
    if is_sqlite:
        # SQLite configuration (local development)
        logger.info("🔧 Using SQLite database (local development mode)")
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG
        )
    else:
        # Azure SQL configuration (production)
        logger.info("☁️ Using Azure SQL database (production mode)")
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=300,
            pool_pre_ping=True,
            echo=settings.DEBUG,
            connect_args={
                "timeout": 30,
                "autocommit": False,
            }
        )
        
        @event.listens_for(engine, "engine_connect")
        def ping_connection(connection, branch):
            """Check if connection is alive before using it."""
            if branch:
                return
            try:
                connection.scalar("SELECT 1")
            except Exception as e:
                logger.warning(f"⚠️ Connection ping failed: {e}")
                connection.invalidate()
                raise
    
    return engine


# Create engine
engine = create_database_engine()

# ============================================================
# SESSION FACTORY
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================================
# BASE CLASS FOR MODELS
# ============================================================

Base = declarative_base()

# ============================================================
# DEPENDENCY: GET DATABASE SESSION
# ============================================================

def get_db():
    """
    Dependency that provides a database session.
    Ensures proper cleanup after request.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"❌ Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# ============================================================
# HEALTH CHECK FUNCTION
# ============================================================

def check_database_health() -> dict:
    """
    Check database connectivity and health.
    Returns status dictionary for monitoring endpoints.
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as healthy")).fetchone()
            if result and result[0] == 1:
                return {
                    "status": "healthy",
                    "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite",
                    "pool_size": engine.pool.size() if hasattr(engine, 'pool') else "N/A",
                    "checked_in": engine.pool.checkedin() if hasattr(engine, 'pool') else "N/A",
                }
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite",
        }
    return {"status": "unknown"}

# ============================================================
# RETRY HELPER FOR TRANSIENT ERRORS
# ============================================================

def retry_on_db_error(func, max_retries=3, delay=1):
    """
    Helper function to retry database operations on transient errors.
    Useful for Azure SQL occasional connection drops.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"🔄 Retry {attempt + 1}/{max_retries} on DB error: {e}")
                    time.sleep(delay * (attempt + 1))
                    continue
            raise
    return None

# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_database():
    """
    Initialize database by creating all tables.
    Safe to call multiple times (checks existence).
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
        logger.info(f"   Database: {'Azure SQL' if 'mssql' in settings.DATABASE_URL else 'SQLite (fallback)'}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False