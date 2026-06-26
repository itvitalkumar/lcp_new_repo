"""
backend/app/main.py
Campus Central API - FastAPI entry point

Phase 1 (June 18, 2026): Initial deployment.
Phase 2 (June 19, 2026): CORS fix + Azure deployment stability + preflight handling.
Phase 3 (June 25, 2026): Azure Key Vault integration for secrets.
                         Azure SQL Database (replaces SQLite).
                         JWT_SECRET now fetched from Key Vault.
                         Database URL built dynamically from Key Vault secrets.
Phase 4 (June 26, 2026): ENHANCED - Database initialization with retry logic.
                         Added startup validation for database connectivity.
                         Better error handling and logging.
                         FIXED: Startup event moved AFTER app creation.
"""

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from sqlalchemy.orm import Session
import os
import time
import logging

from app.config import settings
from app.database import engine, Base, get_db, check_database_health, init_database

# ========== LOGGING SETUP ==========
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================
# IMPORT ALL MODELS (REQUIRED FOR TABLE CREATION)
# ============================================================
from app.models import (
    User,
    TeacherGroup,
    CelebrationGroup,
    GroupMember,
    Message,
    Payment,
    SuccessStory,
    OTPCode,
    SocialPost,
    SocialComment,
    SocialLike,
    ConnectionRequest,
    FriendStory
)


# ============================================================
# ✅ ENHANCED: INITIALIZE DATABASE WITH RETRY
# ============================================================
def initialize_database():
    """
    Initialize database tables with retry logic for Azure SQL.
    Retries up to 3 times if connection fails.
    """
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Database initialization attempt {attempt + 1}/{max_retries}")
            
            # Create tables
            Base.metadata.create_all(bind=engine)
            
            # Verify connection
            health = check_database_health()
            if health.get("status") == "healthy":
                logger.info("✅ Database tables created/verified successfully")
                logger.info(f"   Database: {health.get('database', 'Unknown')}")
                logger.info(f"   Pool Size: {health.get('pool_size', 'N/A')}")
                return True
            else:
                logger.warning(f"⚠️ Database health check failed: {health}")
                
        except Exception as e:
            logger.error(f"❌ Database initialization attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("❌ All database initialization attempts failed")
                return False
    
    return False


# ============================================================
# FASTAPI APP (MOVED BEFORE STARTUP EVENT)
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ============================================================
# CORS (MUST BE FIRST MIDDLEWARE)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ✅ ENHANCED: STARTUP EVENT - Initialize database on app startup
# ============================================================
@app.on_event("startup")
async def startup_event():
    """
    Run on application startup.
    Initializes database and logs startup status.
    """
    logger.info("🚀 Starting Campus Central API...")
    logger.info(f"📊 Database URL: {'Azure SQL' if 'mssql' in settings.DATABASE_URL else 'SQLite (fallback)'}")
    logger.info(f"🔧 Debug Mode: {settings.DEBUG}")
    logger.info(f"🧪 Test Mode: {settings.TEST_MODE}")
    
    # Initialize database
    success = initialize_database()
    
    if success:
        logger.info("✅ Database initialized successfully")
    else:
        logger.warning("⚠️ Database initialization failed - app will continue but some features may not work")


# ============================================================
# GLOBAL REQUEST LOGGER
# ============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with method, path, status, and duration."""
    start = time.time()
    try:
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.0f}ms)")
        return response
    except Exception as e:
        logger.error(f"❌ Request failed: {request.method} {request.url.path} - {e}")
        raise


# ============================================================
# HANDLE PREFLIGHT (OPTIONS REQUESTS)
# ============================================================
@app.options("/{path:path}")
async def preflight_handler(path: str):
    """Handle CORS preflight OPTIONS requests."""
    return Response(status_code=200)


# ============================================================
# STATIC FILES
# ============================================================
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ============================================================
# ROUTERS
# ============================================================
from routers import (
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

from routers.payment import router as payment_router

# ========== INCLUDE ALL ROUTERS ==========
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


# ============================================================
# ROOT ENDPOINT
# ============================================================
@app.get("/")
def root():
    """Root endpoint with database status."""
    health = check_database_health()
    return {
        "message": "Welcome to Campus Central API",
        "status": "running",
        "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite (fallback)",
        "database_health": health.get("status", "unknown"),
        "version": settings.APP_VERSION
    }


# ============================================================
# ✅ ENHANCED: HEALTH CHECK
# ============================================================
@app.get("/health")
def health():
    """
    Enhanced health check endpoint for Azure monitoring.
    Includes database connectivity status.
    """
    health_status = check_database_health()
    
    return {
        "status": health_status.get("status", "unknown"),
        "database": health_status.get("database", "Unknown"),
        "pool_size": health_status.get("pool_size", "N/A"),
        "timestamp": time.time()
    }


# ============================================================
# PUBLIC JOIN
# ============================================================
@app.get("/join/{group_id}")
def join_group(group_id: str, db: Session = Depends(get_db)):
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


# ============================================================
# VERSION
# ============================================================
@app.get("/api/version")
def version():
    """Returns the current API version and available features."""
    health = check_database_health()
    return {
        "version": settings.APP_VERSION,
        "features": [
            "Batchmate Finder",
            "Crush Corner",
            "Startup Nest",
            "Mood & Memory",
            "Find My Friend",
        ],
        "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite (fallback)",
        "database_health": health.get("status", "unknown")
    }


# ============================================================
# ✅ ENHANCED: INIT DATABASE TABLES (WITH RETRY)
# ============================================================
@app.get("/init-db")
def init_database_endpoint():
    """
    One-time endpoint to create all tables.
    Useful for first deployment or manual table creation.
    """
    try:
        # Call the enhanced init function
        success = initialize_database()
        if success:
            return {
                "status": "✅ All tables created successfully",
                "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite (fallback)"
            }
        else:
            return {
                "status": "❌ Failed to create tables",
                "message": "Check logs for details"
            }
    except Exception as e:
        logger.error(f"❌ Init-db error: {e}")
        return {
            "status": "❌ Failed to create tables",
            "error": str(e)
        }


# ============================================================
# ✅ ADDED: FORCE REFRESH DATABASE CONNECTION
# ============================================================
@app.post("/api/admin/refresh-db")
async def refresh_database():
    """
    Admin endpoint to force refresh database connection pool.
    Useful when connection issues occur.
    """
    try:
        from app.database import engine
        engine.dispose()
        return {
            "success": True,
            "message": "Database connection pool disposed and recreated",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"❌ Refresh DB error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# RUN LOCALLY ONLY
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)