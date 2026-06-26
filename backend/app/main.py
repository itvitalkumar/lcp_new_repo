"""
backend/app/main.py

Campus Central API - FastAPI entry point

Architecture:
    Azure App Service
        ↓
    FastAPI + Uvicorn
        ↓
    Azure SQL (via Managed Identity)

Features:
- Azure Key Vault integration for secrets
- Azure SQL Database with Managed Identity
- CORS configuration
- Request logging with timing
- Health checks for Azure monitoring
- Database initialization with retry logic
- Router registration
- Static file serving
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.database import (
    engine,
    get_db,
    check_database_health,
    initialize_database,
    close_database_connections,
)
from app.dependencies import get_current_admin_user
from app.models import User  # Only import User for admin dependency

# ==========================================================
# Logging Configuration
# ==========================================================

# Let Uvicorn handle logging configuration
logger = logging.getLogger(__name__)


# ==========================================================
# Application Lifespan Context Manager
# ==========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    # --- Startup ---
    logger.info("🚀 Starting Campus Central API...")
    logger.info(f"📊 Database: {'Azure SQL' if not settings.USE_SQLITE else 'SQLite'}")
    logger.info(f"📦 Version: {settings.APP_VERSION}")
    logger.info(f"🔧 Environment: {'Development' if settings.DEBUG else 'Production'}")

    # Initialize database with retry logic
    # CRITICAL: Table creation is disabled in production
    # Production migrations must be handled via Alembic
    create_tables = settings.DEBUG and settings.CREATE_TABLES_ON_STARTUP
    success = initialize_database(create_tables=create_tables)

    if success:
        if create_tables:
            logger.info("✅ Database initialized with table creation (development mode)")
        else:
            logger.info("✅ Database connection verified (production mode)")
    else:
        logger.error("❌ Database initialization failed - app may not function correctly")

    yield  # Application runs here

    # --- Shutdown ---
    logger.info("🛑 Shutting down Campus Central API...")
    close_database_connections()
    logger.info("✅ Clean shutdown complete")


# ==========================================================
# Create FastAPI Application
# ==========================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ==========================================================
# CORS Middleware
# ==========================================================

# Validate CORS configuration for production
if not settings.ALLOWED_ORIGINS:
    if settings.DEBUG:
        logger.warning("⚠️ ALLOWED_ORIGINS is empty. Using ['*'] for development only.")
    else:
        raise RuntimeError(
            "ALLOWED_ORIGINS must be configured in production. "
            "Please set ALLOWED_ORIGINS in your environment or .env file."
        )

# CORS configuration
# IMPORTANT: allow_credentials=True requires explicit origins, not ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Must be explicit in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
    max_age=600,
)

logger.info(f"✅ CORS configured with origins: {settings.ALLOWED_ORIGINS}")


# ==========================================================
# Request Logging Middleware
# ==========================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with method, path, status, duration, and client IP.
    """
    start_time = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    logger.info(f"→ {method} {path} from {client_ip}")

    try:
        response = await call_next(request)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # Add response time header
        response.headers["X-Response-Time"] = f"{duration:.0f}ms"

        logger.info(
            f"← {method} {path} → {response.status_code} "
            f"({duration:.1f}ms) from {client_ip}"
        )
        return response

    except Exception:
        logger.exception(f"✗ {method} {path} failed from {client_ip}")
        raise


# ==========================================================
# Static Files
# ==========================================================

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ==========================================================
# Root Endpoint
# ==========================================================

@app.get("/")
async def root():
    """
    Root endpoint - API information.
    Does NOT query the database for faster response.
    Does NOT expose debug information in production.
    """
    response = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }
    
    # Only expose debug info in development
    if settings.DEBUG:
        response["debug"] = settings.DEBUG
        response["database"] = "Azure SQL" if not settings.USE_SQLITE else "SQLite"
    
    return response


# ==========================================================
# Health Check Endpoint
# ==========================================================

@app.get("/health")
async def health():
    """
    Enhanced health check endpoint for Azure monitoring.
    Includes database connectivity and connection pool status.
    """
    health_status = check_database_health()

    response = {
        "status": health_status.get("status", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
    }
    
    # Include database details in health check
    if health_status:
        response["database"] = {
            "type": health_status.get("database", "Unknown"),
            "status": health_status.get("status", "unknown"),
            "pool_size": health_status.get("pool_size", "N/A"),
            "checked_in": health_status.get("checked_in", "N/A"),
            "checked_out": health_status.get("checked_out", "N/A"),
            "overflow": health_status.get("overflow", "N/A"),
        }
    
    return response


# ==========================================================
# Version Endpoint
# ==========================================================

@app.get("/api/version")
async def version():
    """
    Get API version and feature information.
    Does NOT query the database.
    """
    response = {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "python": sys.version.split()[0],
        "features": [
            "Batchmate Finder",
            "Crush Corner",
            "Startup Nest",
            "Mood & Memory",
            "Find My Friend",
        ],
    }
    
    # Only expose debug info in development
    if settings.DEBUG:
        response["debug"] = settings.DEBUG
    
    return response


# ==========================================================
# Public Join Endpoint
# ==========================================================

@app.get("/join/{group_id}")
async def join_group(group_id: str, db: Session = Depends(get_db)):
    """
    Public endpoint to check group details before joining.
    Returns group type and member count.
    """
    from app.models import TeacherGroup, CelebrationGroup, GroupMember

    teacher = db.query(TeacherGroup).filter_by(group_id=group_id).first()
    if teacher:
        count = db.query(GroupMember).filter_by(teacher_group_id=teacher.id).count()
        return {
            "success": True,
            "type": "teacher",
            "group_id": teacher.group_id,
            "member_count": count,
        }

    celebration = db.query(CelebrationGroup).filter_by(group_id=group_id).first()
    if celebration:
        count = db.query(GroupMember).filter_by(celebration_group_id=celebration.id).count()
        return {
            "success": True,
            "type": "celebration",
            "group_id": celebration.group_id,
            "member_count": count,
        }

    return {"success": False, "message": "Group not found"}


# ==========================================================
# Admin - Initialize Database (Development Only)
# ==========================================================

@app.get("/init-db")
async def init_database_endpoint():
    """
    Initialize database tables.
    
    ⚠️ DEVELOPMENT ONLY - Disabled in production.
    In production, migrations should be handled via Alembic.
    """
    # Disable this endpoint entirely in production
    if not settings.DEBUG:
        return {
            "status": "error",
            "message": "This endpoint is disabled in production. Use Alembic migrations instead.",
        }

    try:
        success = initialize_database(create_tables=True)
        if success:
            return {
                "status": "success",
                "message": "Database tables created successfully",
                "database": "Azure SQL" if not settings.USE_SQLITE else "SQLite",
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create database tables. Check logs for details.",
            }
    except Exception as e:
        logger.exception("Init-db endpoint error")
        return {
            "status": "error",
            "message": str(e),
        }


# ==========================================================
# Admin - Refresh Database Connection Pool
# ==========================================================

@app.post("/api/admin/refresh-db")
async def refresh_database(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Admin endpoint to force refresh database connection pool.
    Useful when connection issues occur.
    
    ⚠️ Requires admin authentication.
    """
    try:
        engine.dispose()
        logger.info(f"Database connection pool disposed by admin: {current_user.email}")
        return {
            "success": True,
            "message": "Database connection pool disposed and recreated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception(f"Refresh DB error by admin: {current_user.email}")
        return {
            "success": False,
            "error": str(e),
        }


# ==========================================================
# Router Registration
# ==========================================================

from app.routers import (
    auth,
    groups,
    dashboard,
    search,
    stories,
    admin,
    batchmate,
    business,
    startup,
    hive,
    crush,
    avatar,
    forum,
    marriage,
    messages,
    public,
    findmyfriend,
    social_posts,
    users,
    connections,
    mood_memory,
    friend_search,
)
from app.routers.payment import router as payment_router

# API routes
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(stories.router)
app.include_router(admin.router)

app.include_router(batchmate.router)
app.include_router(business.router)
app.include_router(startup.router)
app.include_router(hive.router)
app.include_router(crush.router)
app.include_router(avatar.router)
app.include_router(forum.router)
app.include_router(marriage.router)
app.include_router(messages.router)
app.include_router(public.router)
app.include_router(findmyfriend.router)
app.include_router(payment_router)
app.include_router(social_posts.router)
app.include_router(users.router)
app.include_router(connections.router)
app.include_router(mood_memory.router)
app.include_router(friend_search.router)

logger.info("All routers registered successfully")


# ==========================================================
# Local Development Runner
# ==========================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )