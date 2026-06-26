"""
backend/app/database.py

Campus Central - Production Database Layer

Architecture:
    Azure App Service
        ↓
    Managed Identity
        ↓
    Azure SQL Database

Supports:
- Azure SQL (Production)
- SQLite (Local development)
- Connection pooling
- Automatic token refresh
- Retry handling (transient errors only)
"""

import logging
import struct
import time

from azure.identity import DefaultAzureCredential

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from .config import settings

logger = logging.getLogger(__name__)

# ==========================================================
# Constants
# ==========================================================

# SQL Server access token attribute for pyodbc
SQL_COPT_SS_ACCESS_TOKEN = 1256

# Azure SQL transient error codes
# Reference: https://docs.microsoft.com/en-us/azure/azure-sql/database/troubleshoot-common-errors-issues
TRANSIENT_ERROR_CODES = {
    "40197",  # Service has encountered an error processing your request
    "40501",  # Service is busy
    "40613",  # Database unavailable
    "49918",  # Cannot process request, not enough resources
    "49919",  # Cannot process request, too many operations
    "49920",  # Cannot process request, too many operations for current state
}


# ==========================================================
# Azure Credential (Lazy-loaded)
# ==========================================================

_credential = None


def get_credential():
    """
    Lazy-initialize DefaultAzureCredential.
    This avoids startup delays during module import.
    """
    global _credential

    if _credential is None:
        _credential = DefaultAzureCredential(
            exclude_visual_studio_code_credential=True,
            exclude_shared_token_cache_credential=True,
            exclude_interactive_browser_credential=True,  # Avoid unnecessary prompt in production
        )
        logger.info("✅ Azure credential initialized")

    return _credential


# ==========================================================
# Build SQLAlchemy URL
# ==========================================================

def build_database_url():
    """
    Build SQLAlchemy database URL.

    Local:
        SQLite

    Production:
        Azure SQL via Managed Identity
    """

    if settings.USE_SQLITE:
        logger.info("Using SQLite database: %s", settings.SQLITE_DATABASE_URL)
        return settings.SQLITE_DATABASE_URL

    logger.info(
        "Connecting to Azure SQL (%s/%s)",
        settings.DB_HOST,
        settings.DB_NAME,
    )

    return URL.create(
        "mssql+pyodbc",
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        query={
            "driver": settings.DB_DRIVER,
            "Encrypt": "yes",
            "TrustServerCertificate": "no",
            # ✅ DO NOT add Authentication=ActiveDirectoryMsi here
            # We inject the token manually via attrs_before
        },
    )


# ==========================================================
# Transient Error Detection
# ==========================================================

def is_transient_error(exception: OperationalError) -> bool:
    """
    Determine if an OperationalError is a transient error that should be retried.
    
    Detects transient errors by:
    1. Message keywords (timeout, connection, deadlock, etc.)
    2. Azure SQL specific error codes
    
    Args:
        exception: The SQLAlchemy OperationalError
        
    Returns:
        True if the error is transient and should be retried
    """
    message = str(exception).lower()
    
    # Check for known transient patterns in the error message
    transient_patterns = (
        "timeout" in message,
        "transport" in message,
        "connection" in message,
        "deadlock" in message,
        "login timeout" in message,
        "the service is currently busy" in message,
        "resource governor" in message,
    )
    
    if any(transient_patterns):
        return True
    
    # Check for Azure SQL specific error codes
    for code in TRANSIENT_ERROR_CODES:
        if code in message:
            return True
    
    return False


# ==========================================================
# Create Engine
# ==========================================================

def create_database_engine():

    database_url = build_database_url()

    if settings.USE_SQLITE:
        engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,
            },
            echo=settings.DEBUG,
            poolclass=NullPool,  # Best practice for SQLite with FastAPI
        )
        return engine

    engine = create_engine(
        database_url,
        echo=settings.DEBUG,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        pool_reset_on_return="rollback",  # Best practice for Azure SQL
    )

    # ------------------------------------------------------
    # Inject Azure SQL Access Token
    # ------------------------------------------------------

    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        """
        Inject Azure AD access token for SQL Server connections.
        
        Args:
            dialect: SQLAlchemy dialect (unused but required by event signature)
            conn_rec: Connection record (unused but required by event signature)
            cargs: Connection arguments
            cparams: Connection parameters (modified in-place)
        """
        try:
            token = get_credential().get_token(
                "https://database.windows.net/.default"
            ).token.encode("utf-16-le")

            token_struct = struct.pack(
                f"<I{len(token)}s",
                len(token),
                token,
            )

            attrs_before = cparams.get("attrs_before", {})
            attrs_before[SQL_COPT_SS_ACCESS_TOKEN] = token_struct
            cparams["attrs_before"] = attrs_before
            
        except Exception:
            logger.exception("Failed to provide access token")
            raise

    return engine


# ==========================================================
# Engine
# ==========================================================

engine = create_database_engine()

# ==========================================================
# Startup Validation
# ==========================================================

if not settings.USE_SQLITE:
    logger.info("✅ Azure SQL Managed Identity authentication enabled.")

# ==========================================================
# Session Factory
# ==========================================================

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Prevents unnecessary object reloads after commit
)

# ==========================================================
# Base Model
# ==========================================================

Base = declarative_base()

# ==========================================================
# Dependency
# ==========================================================

def get_db():
    """
    FastAPI dependency that provides a database session.
    Ensures rollback on error and always closes the session.
    """

    db = SessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        logger.exception("Database transaction failed")
        db.rollback()
        raise

    finally:
        db.close()


# ==========================================================
# Database Health Check
# ==========================================================

def check_database_health():
    """
    Health check used by:

        /health
        /
        Azure Health Probe

    Returns a dictionary describing database status.
    """

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        pool = engine.pool

        return {
            "status": "healthy",
            "database": (
                "SQLite"
                if settings.USE_SQLITE
                else "Azure SQL"
            ),
            "pool_size": getattr(pool, "size", lambda: "N/A")(),
            "checked_in": getattr(pool, "checkedin", lambda: "N/A")(),
            "checked_out": getattr(pool, "checkedout", lambda: "N/A")(),
            "overflow": getattr(pool, "overflow", lambda: "N/A")(),
        }

    except Exception as ex:
        logger.exception("Database health check failed")
        
        # Only expose detailed error messages in debug mode
        if settings.DEBUG:
            error_message = str(ex)
        else:
            error_message = "Database connection failed"
        
        return {
            "status": "unhealthy",
            "database": (
                "SQLite"
                if settings.USE_SQLITE
                else "Azure SQL"
            ),
            "error": error_message,
        }


# ==========================================================
# Retry Helper (Transient Errors Only)
# ==========================================================

def retry_database_operation(
    operation,
    retries=3,
    base_delay=2,
):
    """
    Retry helper for transient Azure SQL failures with exponential backoff.

    Only retries SQLAlchemy OperationalErrors that are detected as transient:
        - Timeout errors
        - Connection errors
        - Deadlock errors
        - Azure SQL specific error codes (40197, 40501, etc.)

    Uses exponential backoff: 2s, 4s, 8s

    All other errors are raised immediately.

    Example:
        retry_database_operation(
            lambda: session.execute(...)
        )
    """

    for attempt in range(retries):
        try:
            return operation()

        except OperationalError as ex:
            if not is_transient_error(ex):
                logger.exception("Non-transient database error")
                raise

            if attempt == retries - 1:
                logger.exception(
                    "Database operation failed permanently after %s retries",
                    retries
                )
                raise

            # Exponential backoff: 2s, 4s, 8s, ...
            delay = base_delay * (2 ** attempt)
            
            logger.warning(
                "Transient database error. "
                "Retry %s/%s in %ss: %s",
                attempt + 1,
                retries,
                delay,
                str(ex),
            )

            time.sleep(delay)

        except SQLAlchemyError:
            logger.exception("SQLAlchemy error (non-operational)")
            raise

        except Exception:
            logger.exception("Unexpected error during database operation")
            raise

    return None


# ==========================================================
# Database Initialization
# ==========================================================

def initialize_database(create_tables: bool = False) -> bool:
    """
    Initialize the database.

    Parameters
    ----------
    create_tables : bool
        False (default):
            Only verify connectivity.

        True:
            Create missing tables (development only).
    """

    try:
        logger.info("Initializing database...")

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Database connection verified successfully.")

        if create_tables:
            logger.warning(
                "Creating database tables using SQLAlchemy metadata."
            )
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified.")

        return True

    except Exception:
        logger.exception("Database initialization failed")
        return False


# ==========================================================
# Dispose Engine
# ==========================================================

def close_database_connections():
    """
    Gracefully dispose SQLAlchemy engine.

    Safe to call during FastAPI shutdown.
    """

    try:
        logger.info("Closing database connection pool...")
        engine.dispose()
        logger.info("Database connection pool closed.")

    except Exception:
        logger.exception(
            "Error while closing database connections"
        )


# ==========================================================
# Startup Validation
# ==========================================================

def validate_database_connection() -> bool:
    """
    Lightweight validation used by startup health checks.

    Does NOT create tables.
    Does NOT modify the database.
    """

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Database validation successful.")
        return True

    except Exception:
        logger.exception("Database validation failed")
        return False


# ==========================================================
# Module Loaded
# ==========================================================

logger.info("Database module loaded successfully")